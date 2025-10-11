import pandas as pd
import streamlit as st
import os
import io
from logger import logger

def load_and_preprocess(file_a_bytes, file_b_bytes):
    try:
        # Load File A
        df_a = pd.read_excel(io.BytesIO(file_a_bytes))
        df_a_original = df_a.copy()
        required_cols_a = ['Article', 'Article Description', 'RP Type', 'Site', 'MOQ', 'SaSa Net Stock', 'Pending Received', 'Safety Stock', 'Last Month Sold Qty', 'MTD Sold Qty', 'Supply source', 'Description p. group']
        if not all(col in df_a.columns for col in required_cols_a):
            st.error("File A 缺少必要欄位。")
            return pd.DataFrame()

        # Preprocess File A
        df_a['Article'] = df_a['Article'].astype(str).str.strip()
        df_a['Site'] = df_a['Site'].astype(str).str.strip()
        numeric_cols = ['MOQ', 'SaSa Net Stock', 'Pending Received', 'Safety Stock', 'Last Month Sold Qty', 'MTD Sold Qty']
        for col in numeric_cols:
            df_a[col] = pd.to_numeric(df_a[col], errors='coerce').fillna(0).astype(int)
            df_a[col] = df_a[col].clip(lower=0)  # negative to 0

        # Cap sales at 100,000
        sales_cols = ['Last Month Sold Qty', 'MTD Sold Qty']
        for col in sales_cols:
            mask = df_a[col] > 100000
            df_a.loc[mask, col] = 100000

        # Add Notes
        df_a['Notes'] = ''

        # Log negatives and caps
        for idx, row in df_a.iterrows():
            notes = []
            for col in numeric_cols:
                original = pd.to_numeric(df_a_original[col].iloc[idx], errors='coerce')
                if original < 0:
                    notes.append(f"{col} 負值已設為 0")
            for col in sales_cols:
                original = pd.to_numeric(df_a_original[col].iloc[idx], errors='coerce')
                if original > 100000:
                    notes.append(f"{col} 超過 100,000 已設為 100,000")
            df_a.at[idx, 'Notes'] = '; '.join(notes)

        # Filter RP Type
        df_a = df_a[df_a['RP Type'].isin(['ND', 'RF'])]

        # Empty strings for missing string fields
        string_cols = ['Article Description', 'Description p. group']
        for col in string_cols:
            df_a[col] = df_a[col].fillna('').astype(str)

        # Supply source to int
        df_a['Supply source'] = pd.to_numeric(df_a['Supply source'], errors='coerce').fillna(0).astype(int)

        # Load File B Sheet1
        df_b1 = pd.read_excel(io.BytesIO(file_b_bytes), sheet_name='Sheet 1')
        required_cols_b1 = ['Group No.', 'Article', 'SKU Target', 'Target Type', 'Promotion Days', 'Target Cover Days']
        if not all(col in df_b1.columns for col in required_cols_b1):
            st.error("File B Sheet1 缺少必要欄位。")
            return pd.DataFrame()

        df_b1['Article'] = df_b1['Article'].astype(str).str.strip()
        numeric_cols_b1 = ['SKU Target', 'Promotion Days', 'Target Cover Days']
        for col in numeric_cols_b1:
            df_b1[col] = pd.to_numeric(df_b1[col], errors='coerce').fillna(0).astype(int)
        df_b1['Target Type'] = df_b1['Target Type'].astype(str).str.strip()

        # Load File B Sheet2
        df_b2 = pd.read_excel(io.BytesIO(file_b_bytes), sheet_name='Sheet 2')
        required_cols_b2 = ['Site', 'Shop Target(HK)', 'Shop Target(MO)', 'Shop Target(ALL)']
        if not all(col in df_b2.columns for col in required_cols_b2):
            st.error("File B Sheet2 缺少必要欄位。")
            return pd.DataFrame()

        df_b2['Site'] = df_b2['Site'].astype(str).str.strip()
        numeric_cols_b2 = ['Shop Target(HK)', 'Shop Target(MO)', 'Shop Target(ALL)']
        for col in numeric_cols_b2:
            df_b2[col] = pd.to_numeric(df_b2[col], errors='coerce').fillna(0)

        # Merge df_a with df_b1 on Article
        df_merged = pd.merge(df_a, df_b1, on='Article', how='left')

        # Merge with df_b2 on Site
        df_final = pd.merge(df_merged, df_b2, on='Site', how='left')

        # Fill NaN with 0 for numeric columns from b1 and b2
        fill_cols = numeric_cols_b1 + numeric_cols_b2 + ['Group No.']
        for col in fill_cols:
            if col in df_final.columns:
                df_final[col] = df_final[col].fillna(0)
                if col not in ['Shop Target(HK)', 'Shop Target(MO)', 'Shop Target(ALL)'] and col != 'Group No.':
                    df_final[col] = df_final[col].astype(int)

        # Fill string columns
        df_final['Target Type'] = df_final['Target Type'].fillna('').astype(str)

        # Log unmatched in Notes
        df_final['Notes'] = df_final.apply(lambda row: (row['Notes'] + '; ' if row['Notes'] else '') + ('未匹配 Article' if pd.isna(row['Group No.']) else '') + ('; ' if pd.isna(row['Group No.']) and pd.isna(row['Shop Target(HK)']) else '') + ('未匹配 Site' if pd.isna(row['Shop Target(HK)']) else ''), axis=1)
        df_final['Notes'] = df_final['Notes'].str.strip('; ')

        return df_final

    except Exception as e:
        logger.error(f"Error in load_and_preprocess: {str(e)}")
        st.error(f"處理文件時發生錯誤: {str(e)}")
        return pd.DataFrame()