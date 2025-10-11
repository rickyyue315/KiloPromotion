import pandas as pd
import numpy as np
from logger import logger

def calculate_demand(df, lead_time=2):
    """
    Calculate demand-related metrics based on the preprocessed DataFrame.

    Parameters:
    df (pd.DataFrame): Preprocessed merged DataFrame from data_preprocessing.py
    lead_time (int): Lead time in days, defaults to 2

    Returns:
    tuple: (df with added columns, summary_df)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    try:
        # Daily Sales Rate = max(0, Last Month Sold Qty / 30)
        df['Daily Sales Rate'] = (df['Last Month Sold Qty'] / 30).clip(lower=0)

        # Site Target % based on Target Type
        conditions = [
            df['Target Type'] == 'HK',
            df['Target Type'] == 'MO',
            df['Target Type'] == 'ALL'
        ]
        choices = [
            df['Shop Target(HK)'],
            df['Shop Target(MO)'],
            df['Shop Target(ALL)']
        ]
        df['Site Target %'] = np.select(conditions, choices, default=0)

        # Regular Demand = Daily Sales Rate * (Target Cover Days + Lead Time)
        df['Regular Demand'] = df['Daily Sales Rate'] * (df['Target Cover Days'] + lead_time)

        # Promo Demand = SKU Target * Site Target %
        df['Promo Demand'] = df['SKU Target'] * df['Site Target %']

        # Total Demand: aggregate Regular Demand by Group+Site, add Promo Demand (sum)
        grouped = df.groupby(['Group No.', 'Site'])
        df_agg = grouped.agg(
            Total_Demand=('Regular Demand', 'sum'),
            Total_Stock=('SaSa Net Stock', 'sum')
        ).reset_index()
        df_agg['Total_Demand'] += grouped['Promo Demand'].sum().values
        df_agg['Total_Stock'] += grouped['Pending Received'].sum().values

        # Merge Total Demand back to df
        df = df.merge(df_agg[['Group No.', 'Site', 'Total_Demand']], on=['Group No.', 'Site'], how='left')
        df.rename(columns={'Total_Demand': 'Total Demand'}, inplace=True)

        # Net Demand = Total Demand - (SaSa Net Stock + Pending Received) + Safety Stock
        df['Net Demand'] = df['Total Demand'] - (df['SaSa Net Stock'] + df['Pending Received']) + df['Safety Stock']

        # Suggested Dispatch Qty: For RF, round up to nearest MOQ multiple, else 0
        def calculate_dispatch_qty(row):
            if row['RP Type'] != 'RF':
                return 0
            base = max(row['Net Demand'], row['MOQ'])
            if row['MOQ'] == 0:
                return base
            return np.ceil(base / row['MOQ']) * row['MOQ']
        df['Suggested Dispatch Qty'] = df.apply(calculate_dispatch_qty, axis=1)

        # Dispatch Type
        conditions = [
            df['Site'] == 'D001',
            df['RP Type'] == 'ND',
            df['Supply source'].isin([1, 4]),
            df['Supply source'] == 2
        ]
        choices = ['D001', 'ND', 'Buyer需要訂貨', '需生成 DN']
        df['Dispatch Type'] = np.select(conditions, choices, default='')

        # Update Notes with assumptions (Lead Time=2)
        df['Notes'] = df['Notes'].apply(lambda x: f"{x}; Lead Time={lead_time}" if x else f"Lead Time={lead_time}")

        # Summary table by Group No. and Article (SKU)
        # Aggregate for non-D001 sites
        non_d001 = df[df['Site'] != 'D001']
        summary_non_d001 = non_d001.groupby(['Group No.', 'Article']).agg(
            Total_Demand=('Total Demand', 'sum'),
            Total_Stock=('SaSa Net Stock', 'sum'),
            Total_Pending=('Pending Received', 'sum'),
            Total_Dispatch=('Suggested Dispatch Qty', 'sum')
        ).reset_index()
        summary_non_d001['Total_Stock_Available'] = summary_non_d001['Total_Stock'] + summary_non_d001['Total_Pending']

        # D001 data
        d001_data = df[df['Site'] == 'D001'][['Group No.', 'Article', 'SaSa Net Stock', 'In Quality Insp.', 'Blocked', 'Pending Received']].rename(columns={
            'SaSa Net Stock': 'D001_SaSa_Net_Stock',
            'In Quality Insp.': 'D001_In_Quality_Insp',
            'Blocked': 'D001_Blocked',
            'Pending Received': 'D001_Pending_Received'
        })

        # Merge
        df_agg = summary_non_d001.merge(d001_data, on=['Group No.', 'Article'], how='left').fillna(0)

        # Out_of_Stock_Warning
        d001_total_stock = df[df['Site'] == 'D001']['SaSa Net Stock'].sum()
        df_agg['Out_of_Stock_Warning'] = np.where(
            df_agg['Total_Dispatch'] > d001_total_stock, 'D001 缺貨', ''
        )

        return df, df_agg
    except Exception as e:
        logger.error(f"Error in calculate_demand: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()