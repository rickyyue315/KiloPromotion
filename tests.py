import unittest
import pandas as pd
import tempfile
import os
import io
from data_preprocessing import load_and_preprocess
from business_logic import calculate_demand

class TestPromotionApp(unittest.TestCase):

    def test_column_validation_missing_in_a(self):
        # Create df_a missing 'Description p. group'
        df_a = pd.DataFrame({
            'Article': ['1'],
            'Article Description': ['desc'],
            'RP Type': ['RF'],
            'Site': ['D001'],
            'MOQ': [1],
            'SaSa Net Stock': [10],
            'Pending Received': [0],
            'Safety Stock': [0],
            'Last Month Sold Qty': [5],
            'MTD Sold Qty': [2],
            'Supply source': [1]
            # missing 'Description p. group'
        })
        bio_a = io.BytesIO()
        df_a.to_excel(bio_a, index=False)
        file_a_bytes = bio_a.getvalue()

        # File B minimal
        df_b1 = pd.DataFrame({
            'Group No.': [1],
            'Article': ['1'],
            'SKU Target': [10],
            'Target Type': ['HK'],
            'Promotion Days': [7],
            'Target Cover Days': [14]
        })
        df_b2 = pd.DataFrame({
            'Site': ['D001'],
            'Shop Target(HK)': [0.5],
            'Shop Target(MO)': [0.3],
            'Shop Target(ALL)': [0.2]
        })
        bio_b = io.BytesIO()
        with pd.ExcelWriter(bio_b) as writer:
            df_b1.to_excel(writer, sheet_name='Sheet 1', index=False)
            df_b2.to_excel(writer, sheet_name='Sheet 2', index=False)
        file_b_bytes = bio_b.getvalue()

        result = load_and_preprocess(file_a_bytes, file_b_bytes)
        self.assertTrue(result.empty)

    def test_negative_value_correction(self):
        df_a = pd.DataFrame({
            'Article': ['1'],
            'Article Description': ['desc'],
            'RP Type': ['RF'],
            'Site': ['D001'],
            'MOQ': [1],
            'SaSa Net Stock': [-5],  # negative
            'Pending Received': [0],
            'Safety Stock': [0],
            'Last Month Sold Qty': [5],
            'MTD Sold Qty': [2],
            'Supply source': [1],
            'Description p. group': ['group']
        })
        bio_a = io.BytesIO()
        df_a.to_excel(bio_a, index=False)
        file_a_bytes = bio_a.getvalue()

        df_b1 = pd.DataFrame({
            'Group No.': [1],
            'Article': ['1'],
            'SKU Target': [10],
            'Target Type': ['HK'],
            'Promotion Days': [7],
            'Target Cover Days': [14]
        })
        df_b2 = pd.DataFrame({
            'Site': ['D001'],
            'Shop Target(HK)': [0.5],
            'Shop Target(MO)': [0.3],
            'Shop Target(ALL)': [0.2]
        })
        bio_b = io.BytesIO()
        with pd.ExcelWriter(bio_b) as writer:
            df_b1.to_excel(writer, sheet_name='Sheet 1', index=False)
            df_b2.to_excel(writer, sheet_name='Sheet 2', index=False)
        file_b_bytes = bio_b.getvalue()

        result = load_and_preprocess(file_a_bytes, file_b_bytes)
        self.assertEqual(result['SaSa Net Stock'].iloc[0], 0)

    def test_sales_capping(self):
        df_a = pd.DataFrame({
            'Article': ['1'],
            'Article Description': ['desc'],
            'RP Type': ['RF'],
            'Site': ['D001'],
            'MOQ': [1],
            'SaSa Net Stock': [10],
            'Pending Received': [0],
            'Safety Stock': [0],
            'Last Month Sold Qty': [150000],  # >100000
            'MTD Sold Qty': [2],
            'Supply source': [1],
            'Description p. group': ['group']
        })
        bio_a = io.BytesIO()
        df_a.to_excel(bio_a, index=False)
        file_a_bytes = bio_a.getvalue()

        df_b1 = pd.DataFrame({
            'Group No.': [1],
            'Article': ['1'],
            'SKU Target': [10],
            'Target Type': ['HK'],
            'Promotion Days': [7],
            'Target Cover Days': [14]
        })
        df_b2 = pd.DataFrame({
            'Site': ['D001'],
            'Shop Target(HK)': [0.5],
            'Shop Target(MO)': [0.3],
            'Shop Target(ALL)': [0.2]
        })
        bio_b = io.BytesIO()
        with pd.ExcelWriter(bio_b) as writer:
            df_b1.to_excel(writer, sheet_name='Sheet 1', index=False)
            df_b2.to_excel(writer, sheet_name='Sheet 2', index=False)
        file_b_bytes = bio_b.getvalue()

        result = load_and_preprocess(file_a_bytes, file_b_bytes)
        self.assertEqual(result['Last Month Sold Qty'].iloc[0], 100000)

    def test_merge_logic(self):
        df_a = pd.DataFrame({
            'Article': ['1', '2'],
            'Article Description': ['desc1', 'desc2'],
            'RP Type': ['RF', 'RF'],
            'Site': ['D001', 'D002'],
            'MOQ': [1, 2],
            'SaSa Net Stock': [10, 20],
            'Pending Received': [0, 0],
            'Safety Stock': [0, 0],
            'Last Month Sold Qty': [5, 10],
            'MTD Sold Qty': [2, 4],
            'Supply source': [1, 2],
            'Description p. group': ['group1', 'group2']
        })
        bio_a = io.BytesIO()
        df_a.to_excel(bio_a, index=False)
        file_a_bytes = bio_a.getvalue()

        df_b1 = pd.DataFrame({
            'Group No.': [1, 2],
            'Article': ['1', '2'],
            'SKU Target': [10, 20],
            'Target Type': ['HK', 'MO'],
            'Promotion Days': [7, 7],
            'Target Cover Days': [14, 14]
        })
        df_b2 = pd.DataFrame({
            'Site': ['D001', 'D002'],
            'Shop Target(HK)': [0.5, 0.6],
            'Shop Target(MO)': [0.3, 0.4],
            'Shop Target(ALL)': [0.2, 0.3]
        })
        bio_b = io.BytesIO()
        with pd.ExcelWriter(bio_b) as writer:
            df_b1.to_excel(writer, sheet_name='Sheet 1', index=False)
            df_b2.to_excel(writer, sheet_name='Sheet 2', index=False)
        file_b_bytes = bio_b.getvalue()

        result = load_and_preprocess(file_a_bytes, file_b_bytes)
        self.assertEqual(len(result), 2)
        self.assertEqual(result['Group No.'].iloc[0], 1)
        self.assertEqual(result['Shop Target(HK)'].iloc[0], 0.5)

    def test_calculation_accuracy(self):
        df_a = pd.DataFrame({
            'Article': ['1'],
            'Article Description': ['desc'],
            'RP Type': ['RF'],
            'Site': ['D001'],
            'MOQ': [1],
            'SaSa Net Stock': [2],
            'Pending Received': [1],
            'Safety Stock': [0],
            'Last Month Sold Qty': [30],
            'MTD Sold Qty': [2],
            'Supply source': [1],
            'Description p. group': ['group']
        })
        bio_a = io.BytesIO()
        df_a.to_excel(bio_a, index=False)
        file_a_bytes = bio_a.getvalue()

        df_b1 = pd.DataFrame({
            'Group No.': [1],
            'Article': ['1'],
            'SKU Target': [5],
            'Target Type': ['HK'],
            'Promotion Days': [7],
            'Target Cover Days': [10]
        })
        df_b2 = pd.DataFrame({
            'Site': ['D001'],
            'Shop Target(HK)': [0.5],
            'Shop Target(MO)': [0.3],
            'Shop Target(ALL)': [0.2]
        })
        bio_b = io.BytesIO()
        with pd.ExcelWriter(bio_b) as writer:
            df_b1.to_excel(writer, sheet_name='Sheet 1', index=False)
            df_b2.to_excel(writer, sheet_name='Sheet 2', index=False)
        file_b_bytes = bio_b.getvalue()

        df = load_and_preprocess(file_a_bytes, file_b_bytes)
        df_result, summary = calculate_demand(df, lead_time=2)
        # Daily Sales Rate = max(0, 30/30) = 1
        # Site Target % = 0.5
        # Regular Demand = 1 * (10 + 2) = 12
        # Promo Demand = 5 * 0.5 = 2.5
        # Total Demand = 12 + 2.5 = 14.5
        # Net Demand = 14.5 - (2+1) + 0 = 11.5
        # Suggested Dispatch = max(11.5, 1) = 11.5
        self.assertAlmostEqual(df_result['Suggested Dispatch Qty'].iloc[0], 11.5)

if __name__ == '__main__':
    unittest.main()