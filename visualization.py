import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib
from logger import logger

# Set font for Chinese characters
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

def create_visualizations(df, summary):
    try:
        if df.empty or summary.empty:
            st.info("無視覺化資料可用")
            return

        # Selectbox for Group No. filtering
        group_options = ['All'] + sorted(summary['Group No.'].unique().tolist())
        selected_group = st.selectbox("選擇組別編號篩選圖表", group_options)

        # Filter data, exclude D001
        df_filtered = df[df['Site'] != 'D001']
        summary_filtered = summary

        if selected_group != 'All':
            df_filtered = df_filtered[df_filtered['Group No.'] == selected_group]
            summary_filtered = summary_filtered[summary_filtered['Group No.'] == selected_group]

        if df_filtered.empty or summary_filtered.empty:
            st.info("No visualization data available")
            return

        # Bar plot: SKU Demand vs. Stock
        st.subheader("SKU Demand vs. Stock")
        agg_sku = summary_filtered.groupby('Article').agg(
            Total_Demand=('Total_Demand', 'sum'),
            Total_Stock_Available=('Total_Stock_Available', 'sum')
        ).reset_index()
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        melted = agg_sku.melt(id_vars='Article', value_vars=['Total_Demand', 'Total_Stock_Available'],
                              var_name='Type', value_name='Value')
        melted['Type'] = melted['Type'].map({'Total_Demand': 'Demand', 'Total_Stock_Available': 'Stock'})
        sns.barplot(data=melted, x='Article', y='Value', hue='Type', ax=ax1)
        ax1.set_ylabel('Quantity')
        ax1.set_xlabel('SKU')
        plt.xticks(rotation=45)
        st.pyplot(fig1)
        st.write("This chart compares total demand and available stock for each SKU, helping identify stock adequacy.")


        # Heatmap: Net Demand by Site and SKU
        st.subheader("Net Demand Heatmap by Site and SKU")
        pivot_data = df_filtered.pivot_table(values='Net Demand', index='Site', columns='Article', aggfunc='sum')
        if pivot_data.size > 1000:
            # Sample 1000 points
            flat = pivot_data.stack().reset_index()
            sampled = flat.sample(n=1000, random_state=42)
            pivot_data = sampled.pivot(index='Site', columns='Article', values=0)

        fig3, ax3 = plt.subplots(figsize=(12, 8))
        sns.heatmap(pivot_data, cmap='viridis', ax=ax3, cbar_kws={'label': 'Net Demand'})
        ax3.set_xlabel('SKU')
        ax3.set_ylabel('Site')
        plt.xticks(rotation=90)
        st.pyplot(fig3)
        st.write("This heatmap shows net demand distribution across sites and SKUs, with darker colors indicating higher net demand.")
    except Exception as e:
        logger.error(f"Error in create_visualizations: {str(e)}")
        st.error("視覺化生成失敗。")