import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import openpyxl
from datetime import datetime
import logging
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'merged_data' not in st.session_state:
    st.session_state.merged_data = None
if 'summary_data' not in st.session_state:
    st.session_state.summary_data = None

def check_dependencies():
    """Check if all required dependencies are installed"""
    missing_deps = []
    try:
        import streamlit
    except ImportError:
        missing_deps.append("streamlit")
    
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import openpyxl
    except ImportError:
        missing_deps.append("openpyxl")
    
    try:
        import matplotlib
    except ImportError:
        missing_deps.append("matplotlib")
    
    try:
        import seaborn
    except ImportError:
        missing_deps.append("seaborn")
    
    return missing_deps

def load_file_a(file):
    """Load and validate File A (Inventory and Sales Data)"""
    try:
        df = pd.read_excel(file)
        
        # Required columns for File A
        required_columns = [
            'Article', 'Article Description', 'RP Type', 'Site', 'MOQ',
            'SaSa Net Stock', 'Pending Received', 'Safety Stock',
            'Last Month Sold Qty', 'MTD Sold Qty', 'Supply source', 'Description p. group'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"File A missing required columns: {', '.join(missing_columns)}")
            return None
        
        # Data preprocessing for File A
        df['Article'] = df['Article'].astype(str).str.strip()
        df['Article Description'] = df['Article Description'].astype(str).str.strip()
        df['RP Type'] = df['RP Type'].astype(str).str.strip()
        df['Site'] = df['Site'].astype(str).str.strip()
        df['Supply source'] = df['Supply source'].astype(str).str.strip()
        df['Description p. group'] = df['Description p. group'].astype(str).str.strip()
        
        # Convert numeric columns, fill NaN with 0, and handle negative values
        numeric_columns = ['MOQ', 'SaSa Net Stock', 'Pending Received', 
                         'Safety Stock', 'Last Month Sold Qty', 'MTD Sold Qty']
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            # Replace negative values with 0
            df[col] = df[col].apply(lambda x: max(0, x))
        
        # Add Notes column for data cleaning logs
        df['Notes'] = ""
        
        # Log data cleaning actions
        for idx, row in df.iterrows():
            notes = []
            for col in numeric_columns:
                if row[col] < 0:
                    notes.append(f"{col} negative value corrected to 0")
            if row['Last Month Sold Qty'] > 100000 or row['MTD Sold Qty'] > 100000:
                notes.append("Sales quantity outlier adjusted")
                df.at[idx, 'Last Month Sold Qty'] = min(row['Last Month Sold Qty'], 100000)
                df.at[idx, 'MTD Sold Qty'] = min(row['MTD Sold Qty'], 100000)
            
            # Validate Supply source
            if row['Supply source'] not in ['1', '2', '4', '']:
                notes.append(f"Invalid supply source: {row['Supply source']}")
                df.at[idx, 'Supply source'] = "無效來源"
            
            if notes:
                df.at[idx, 'Notes'] = "; ".join(notes)
        
        return df
    
    except Exception as e:
        st.error(f"Error loading File A: {str(e)}")
        logger.error(f"Error loading File A: {str(e)}")
        return None

def load_file_b(file):
    """Load and validate File B (Promotion Target Data)"""
    try:
        # Load Sheet 1
        sheet1_df = pd.read_excel(file, sheet_name=0)
        
        # Required columns for Sheet 1
        sheet1_required = ['Group No.', 'Article', 'SKU Target', 'Target Type', 'Promotion Days', 'Target Cover Days']
        missing_sheet1 = [col for col in sheet1_required if col not in sheet1_df.columns]
        if missing_sheet1:
            st.error(f"File B Sheet 1 missing required columns: {', '.join(missing_sheet1)}")
            return None, None
        
        # Load Sheet 2
        sheet2_df = pd.read_excel(file, sheet_name=1)
        
        # Required columns for Sheet 2
        sheet2_required = ['Site', 'Shop Target(HK)', 'Shop Target(MO)', 'Shop Target(ALL)']
        missing_sheet2 = [col for col in sheet2_required if col not in sheet2_df.columns]
        if missing_sheet2:
            st.error(f"File B Sheet 2 missing required columns: {', '.join(missing_sheet2)}")
            return None, None
        
        # Preprocess Sheet 1
        sheet1_df['Group No.'] = sheet1_df['Group No.'].astype(str).str.strip()
        sheet1_df['Article'] = sheet1_df['Article'].astype(str).str.strip()
        sheet1_df['Target Type'] = sheet1_df['Target Type'].astype(str).str.strip()
        
        numeric_sheet1 = ['SKU Target', 'Promotion Days', 'Target Cover Days']
        for col in numeric_sheet1:
            sheet1_df[col] = pd.to_numeric(sheet1_df[col], errors='coerce').fillna(0).astype(int)
        
        # Preprocess Sheet 2 - Handle percentages
        sheet2_df['Site'] = sheet2_df['Site'].astype(str).str.strip()
        
        # Convert percentage columns to float and handle percentage values
        percentage_columns = ['Shop Target(HK)', 'Shop Target(MO)', 'Shop Target(ALL)']
        for col in percentage_columns:
            # Convert to numeric, handling both percentage strings and numbers
            sheet2_df[col] = pd.to_numeric(sheet2_df[col], errors='coerce').fillna(0)
            
            # If values are greater than 1, assume they are percentages (e.g., 10 for 10%) and convert to decimal
            if (sheet2_df[col] > 1).any():
                sheet2_df[col] = sheet2_df[col] / 100
        
        return sheet1_df, sheet2_df
    
    except Exception as e:
        st.error(f"Error loading File B: {str(e)}")
        logger.error(f"Error loading File B: {str(e)}")
        return None, None

def merge_data(file_a_df, file_b_sheet1, file_b_sheet2):
    """Merge File A and File B data"""
    try:
        # Merge File A with Sheet 1 of File B on Article
        merged = pd.merge(file_a_df, file_b_sheet1, on='Article', how='left')
        
        # Merge with Sheet 2 of File B on Site
        merged = pd.merge(merged, file_b_sheet2, on='Site', how='left')
        
        # Fill missing values from File B with 0
        file_b_columns = ['Group No.', 'SKU Target', 'Target Type', 'Promotion Days', 'Target Cover Days',
                         'Shop Target(HK)', 'Shop Target(MO)', 'Shop Target(ALL)']
        
        for col in file_b_columns:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0) if col in ['Group No.', 'Target Type'] else 0
        
        # Add Notes for missing matches
        for idx, row in merged.iterrows():
            current_notes = row['Notes'] if 'Notes' in row and pd.notna(row['Notes']) else ""
            if pd.isna(row['Group No.']) or row['Group No.'] == 0:
                if current_notes:
                    current_notes += "; "
                current_notes += "No matching promotion target data"
                merged.at[idx, 'Notes'] = current_notes
        
        return merged
    
    except Exception as e:
        st.error(f"Error merging data: {str(e)}")
        logger.error(f"Error merging data: {str(e)}")
        return None

def calculate_daily_sales_rate(last_month_sold, mtd_sold, current_day=None):
    """Calculate daily sales rate"""
    if current_day is None:
        current_day = datetime.now().day
    
    # Avoid division by zero
    if last_month_sold == 0 and mtd_sold == 0:
        return 0
    
    # Calculate daily rate: average of last month and current month
    last_month_daily = last_month_sold / 30 if last_month_sold > 0 else 0
    current_month_daily = mtd_sold / current_day if mtd_sold > 0 else 0
    
    if last_month_sold > 0 and mtd_sold > 0:
        return (last_month_daily + current_month_daily) / 2
    elif last_month_sold > 0:
        return last_month_daily
    else:
        return current_month_daily

def calculate_demand_and_dispatch(merged_df, lead_time=2.5):
    """Calculate demand and dispatch suggestions with out-of-stock handling"""
    try:
        # Make a copy to avoid modifying the original
        result_df = merged_df.copy()
        
        # Calculate daily sales rate
        result_df['Daily Sales Rate'] = result_df.apply(
            lambda row: calculate_daily_sales_rate(row['Last Month Sold Qty'], row['MTD Sold Qty']),
            axis=1
        )
        
        # Calculate total demand
        result_df['Total Demand'] = result_df.apply(
            lambda row: (
                row['Daily Sales Rate'] * (row['Promotion Days'] + row['Target Cover Days'] + lead_time) +  # Regular demand
                row['SKU Target'] * (row['Shop Target(HK)'] if row['Target Type'] == 'HK' else
                                     row['Shop Target(MO)'] if row['Target Type'] == 'MO' else
                                     row['Shop Target(ALL)'])  # Site target = SKU Target * Shop Target Percentage
            ),
            axis=1
        )
        
        # Calculate net demand
        result_df['Net Demand'] = result_df.apply(
            lambda row: max(0, row['Total Demand'] - (row['SaSa Net Stock'] + row['Pending Received']) + row['Safety Stock']
            ),
            axis=1
        )
        
        # Calculate out-of-stock quantity
        result_df['Out of Stock Qty'] = result_df.apply(
            lambda row: max(0, row['Net Demand'] - row['SaSa Net Stock'] - row['Pending Received']),
            axis=1
        )
        
        # Calculate suggested dispatch quantity
        result_df['Suggested Dispatch Qty'] = result_df.apply(
            lambda row: (
                max(row['Net Demand'], row['MOQ']) if row['RP Type'] == 'RF' else 0
        ),
            axis=1
        )
        
        # Add calculation notes and conditional notifications
        for idx, row in result_df.iterrows():
            current_notes = row['Notes'] if pd.notna(row['Notes']) else ""
            if current_notes:
                current_notes += "; "
            
            calculation_notes = []
            if row['RP Type'] == 'RF':
                calculation_notes.append(f"Lead time: {lead_time} days")
            
            if row['Net Demand'] < row['MOQ'] and row['Net Demand'] > 0:
                calculation_notes.append(f"Net demand below MOQ, suggested: {row['Suggested Dispatch Qty']}")
            
            # Conditional notifications based on supply source
            if row['Out of Stock Qty'] > 0:
                if row['Supply source'] in ['1', '4']:
                    buyer_note = f"缺貨通知：Buyer {row['Description p. group']}，缺貨數量 {row['Out of Stock Qty']}"
                    calculation_notes.append(buyer_note)
                elif row['Supply source'] == '2':
                    rp_note = f"RP team建議：對照D001庫存進行補貨，缺貨數量 {row['Out of Stock Qty']}"
                    calculation_notes.append(rp_note)
            
            result_df.at[idx, 'Notes'] = current_notes + "; ".join(calculation_notes)
        
        return result_df
    
    except Exception as e:
        st.error(f"Error in demand calculation: {str(e)}")
        logger.error(f"Error in demand calculation: {str(e)}")
        return None

def create_summary_table(result_df):
    """Create summary table by Group No., Site and Supply source"""
    try:
        if result_df.empty:
            return pd.DataFrame()
        
        # Group by Group No., Site and Supply source
        summary = result_df.groupby(['Group No.', 'Site', 'Supply source']).agg({
            'Total Demand': 'sum',
            'SaSa Net Stock': 'sum',
            'Pending Received': 'sum',
            'Safety Stock': 'sum',
            'Out of Stock Qty': 'sum',
            'Suggested Dispatch Qty': 'sum'
        }).reset_index()
        
        # Add notification summary column
        summary['Notification Summary'] = summary.apply(
            lambda row: create_notification_summary(row),
            axis=1
        )
        
        return summary
    
    except Exception as e:
        st.error(f"Error creating summary table: {str(e)}")
        logger.error(f"Error creating summary table: {str(e)}")
        return pd.DataFrame()

def create_notification_summary(row):
    """Create notification summary for each row in summary table"""
    notifications = []
    
    if row['Out of Stock Qty'] > 0:
        if row['Supply source'] in ['1', '4']:
            notifications.append(f"缺貨通知: {row['Out of Stock Qty']} units")
        elif row['Supply source'] == '2':
            notifications.append(f"RP建議: {row['Out of Stock Qty']} units (檢查D001)")
    
    return "; ".join(notifications) if notifications else "無"

def create_visualizations(result_df, summary_df):
    """Create visualizations for the analysis results"""
    try:
        if result_df.empty:
            st.warning("No data available for visualization")
            return
        
        # Set up the style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("viridis")
        
        # Visualization 1: Bar chart - Total Demand vs Total Inventory by Group No.
        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Chart 1: Total Demand by Group No.
        group_demand = result_df.groupby('Group No.')['Total Demand'].sum().sort_values(ascending=False)
        ax1.bar(range(len(group_demand)), group_demand.values)
        ax1.set_title('Total Demand by Group No.')
        ax1.set_xlabel('Group No.')
        ax1.set_ylabel('Total Demand')
        ax1.set_xticks(range(len(group_demand)))
        ax1.set_xticklabels(group_demand.index, rotation=45)
        
        # Chart 2: Total Inventory by Group No.
        group_inventory = result_df.groupby('Group No.')[['SaSa Net Stock', 'Pending Received', 'Safety Stock']].sum()
        group_inventory['Total Inventory'] = group_inventory.sum(axis=1)
        group_inventory = group_inventory['Total Inventory'].sort_values(ascending=False)
        ax2.bar(range(len(group_inventory)), group_inventory.values)
        ax2.set_title('Total Inventory by Group No.')
        ax2.set_xlabel('Group No.')
        ax2.set_ylabel('Total Inventory')
        ax2.set_xticks(range(len(group_inventory)))
        ax2.set_xticklabels(group_inventory.index, rotation=45)
        
        plt.tight_layout()
        st.pyplot(fig1)
        
        # Visualization 2: Pie chart - Dispatch Suggestion Distribution (RF vs ND)
        fig2, ax3 = plt.subplots(figsize=(10, 6))
        
        dispatch_summary = result_df.groupby('RP Type')['Suggested Dispatch Qty'].sum()
        ax3.pie(dispatch_summary.values, labels=dispatch_summary.index, autopct='%1.1f%%')
        ax3.set_title('Dispatch Suggestion Distribution (RF vs ND)')
        st.pyplot(fig2)
        
        # Visualization 3: Out-of-Stock Analysis by Supply Source
        if 'Out of Stock Qty' in result_df.columns:
            fig3, (ax4, ax5) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Chart 3a: Out-of-Stock by Supply Source
            out_of_stock_by_source = result_df.groupby('Supply source')['Out of Stock Qty'].sum()
            ax4.bar(range(len(out_of_stock_by_source)), out_of_stock_by_source.values)
            ax4.set_title('Out-of-Stock Quantity by Supply Source')
            ax4.set_xlabel('Supply Source')
            ax4.set_ylabel('Out-of-Stock Quantity')
            ax4.set_xticks(range(len(out_of_stock_by_source)))
            ax4.set_xticklabels(out_of_stock_by_source.index, rotation=45)
            
            # Chart 3b: Out-of-Stock vs Available Stock
            stock_comparison = result_df.groupby('Group No.')[['SaSa Net Stock', 'Out of Stock Qty']].sum()
            x = range(len(stock_comparison))
            width = 0.35
            ax5.bar([i - width/2 for i in x], stock_comparison['SaSa Net Stock'], width, label='Available Stock')
            ax5.bar([i + width/2 for i in x], stock_comparison['Out of Stock Qty'], width, label='Out-of-Stock')
            ax5.set_title('Available Stock vs Out-of-Stock by Group')
            ax5.set_xlabel('Group No.')
            ax5.set_ylabel('Quantity')
            ax5.set_xticks(x)
            ax5.set_xticklabels(stock_comparison.index, rotation=45)
            ax5.legend()
            
            plt.tight_layout()
            st.pyplot(fig3)
        
        # Visualization 4: Heatmap - Net Demand by Site and Article
        if len(result_df) > 0:
            # Sample data if too large for heatmap
            if len(result_df) > 1000:
                heatmap_data = result_df.sample(1000)
            else:
                heatmap_data = result_df
            
            # Create pivot table for heatmap
            pivot_data = heatmap_data.pivot_table(
                values='Net Demand',
                index='Site',
                columns='Article',
                aggfunc='sum'
            ).fillna(0)
            
            if not pivot_data.empty:
                fig4, ax6 = plt.subplots(figsize=(12, 8))
                sns.heatmap(pivot_data, cmap='viridis', ax=ax6)
                ax6.set_title('Net Demand Heatmap (Site vs Article)')
                st.pyplot(fig4)
    
    except Exception as e:
        st.error(f"Error creating visualizations: {str(e)}")
        logger.error(f"Error creating visualizations: {str(e)}")

def export_to_excel(result_df, summary_df):
    """Export results to Excel format"""
    try:
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            result_df.to_excel(writer, sheet_name='Detailed Results', index=False)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return output.getvalue()
    
    except Exception as e:
        st.error(f"Error exporting to Excel: {str(e)}")
        logger.error(f"Error exporting to Excel: {str(e)}")
        return None

def main():
    """Main application function"""
    # Check dependencies first
    missing_deps = check_dependencies()
    if missing_deps:
        st.error(f"Missing required dependencies: {', '.join(missing_deps)}")
        st.info("Please install the required packages using: pip install -r requirements.txt")
        return
    
    # Set page configuration
    st.set_page_config(
        page_title="零售推廣目標檢視及派貨系統",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar
    with st.sidebar:
        st.title("📊 系統資訊")
        st.write("**開發者:** Ricky")
        st.write("**版本:** v1.0")
        st.markdown("---")
        
        st.subheader("快速導航")
        if st.button("📁 上傳檔案"):
            st.session_state.current_section = "upload"
        if st.button("🔍 分析結果"):
            st.session_state.current_section = "analysis"
        if st.button("📈 視覺化"):
            st.session_state.current_section = "visualization"
        if st.button("💾 匯出結果"):
            st.session_state.current_section = "export"
        
        st.markdown("---")
        st.subheader("參數設定")
        lead_time = st.slider("Lead Time (天)", min_value=2.0, max_value=3.0, value=2.5, step=0.1)
        st.markdown("---")
        
        # Language selection
        language = st.selectbox("語言 / Language", ["English", "中文"])
    
    # Main content area
    st.title("🏪 零售推廣目標檢視及派貨系統")
    st.markdown("---")
    
    # File upload section
    st.subheader("📁 檔案上傳")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**上傳庫存檔案 (A)**")
        file_a = st.file_uploader(
            "選擇庫存與銷售數據檔案",
            type=['xlsx'],
            key="file_a"
        )
    
    with col2:
        st.write("**上傳推廣目標檔案 (B)**")
        file_b = st.file_uploader(
            "選擇推廣目標數據檔案",
            type=['xlsx'],
            key="file_b"
        )
    
    if file_a and file_b:
        with st.spinner("載入檔案中..."):
            file_a_df = load_file_a(file_a)
            file_b_sheet1, file_b_sheet2 = load_file_b(file_b)
            
            if file_a_df is not None and file_b_sheet1 is not None and file_b_sheet2 is not None:
                merged_data = merge_data(file_a_df, file_b_sheet1, file_b_sheet2)
                
                if merged_data is not None:
                    st.session_state.merged_data = merged_data
                    st.session_state.data_loaded = True
                    st.success("✅ 檔案載入成功！")
    
    # Data preview
    if st.session_state.data_loaded:
        st.subheader("📊 資料預覽")
        st.dataframe(st.session_state.merged_data.head(10))
    
    # Analysis section
    if st.session_state.data_loaded and st.button("🚀 開始分析"):
        with st.spinner("計算需求與派貨建議中..."):
            result_data = calculate_demand_and_dispatch(st.session_state.merged_data, lead_time)
            
            if result_data is not None:
                st.session_state.result_data = result_data
                st.session_state.summary_data = create_summary_table(result_data)
                st.session_state.analysis_complete = True
                st.success("✅ 分析完成！")
    
    # Display results
    if st.session_state.analysis_complete:
        st.subheader("📋 分析結果")
        
        # Display out-of-stock notifications
        if 'Out of Stock Qty' in st.session_state.result_data.columns:
            out_of_stock_data = st.session_state.result_data[
                (st.session_state.result_data['Out of Stock Qty'] > 0) &
                (st.session_state.result_data['Supply source'].isin(['1', '2', '4']))
            ]
            
            if not out_of_stock_data.empty:
                st.subheader("⚠️ 缺貨通知與建議")
                
                # Buyer notifications (Supply source 1, 4)
                buyer_notifications = out_of_stock_data[
                    out_of_stock_data['Supply source'].isin(['1', '4'])
                ]
                if not buyer_notifications.empty:
                    st.warning("**Buyer 缺貨通知:**")
                    for idx, row in buyer_notifications.iterrows():
                        st.write(f"- Article: {row['Article']}, Site: {row['Site']}, Buyer: {row['Description p. group']}, 缺貨數量: {row['Out of Stock Qty']}")
                
                # RP team suggestions (Supply source 2)
                rp_suggestions = out_of_stock_data[
                    out_of_stock_data['Supply source'] == '2'
                ]
                if not rp_suggestions.empty:
                    st.info("**RP Team 補貨建議:**")
                    for idx, row in rp_suggestions.iterrows():
                        st.write(f"- Article: {row['Article']}, Site: {row['Site']}, 缺貨數量: {row['Out of Stock Qty']} (請檢查D001庫存)")
        
        # Detailed results
        st.write("**詳細計算結果:**")
        st.dataframe(st.session_state.result_data)
        
        # Summary table
        st.write("**摘要統計:**")
        st.table(st.session_state.summary_data)
        
        # Visualizations
        st.subheader("📈 視覺化分析")
        create_visualizations(st.session_state.result_data, st.session_state.summary_data)
        
        # Export section
        st.subheader("💾 匯出結果")
        
        if st.session_state.result_data is not None and st.session_state.summary_data is not None:
            excel_data = export_to_excel(st.session_state.result_data, st.session_state.summary_data)
            
            if excel_data:
                current_date = datetime.now().strftime("%Y%m%d")
                st.download_button(
                    label="📥 下載 Excel 報告",
                    data=excel_data,
                    file_name=f"Promotion_Demand_Report_{current_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="點擊下載完整的分析報告"
                )
    
    # Error handling for empty data
    if not st.session_state.data_loaded and (file_a or file_b):
        st.warning("請上傳有效的 Excel 檔案")
    
    # Footer
    st.markdown("---")
    st.markdown("**開發者:** Ricky | **版本:** v1.0")

if __name__ == "__main__":
    main()