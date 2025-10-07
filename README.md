# 零售推廣目標檢視及派貨系統
## Retail Promotion Target Viewing and Dispatch Suggestion System

### 系統概述 / System Overview
這是一個基於Streamlit的零售推廣目標檢視庫存及派貨建議系統，幫助零售企業分析庫存數據和推廣目標，計算需求並提供派貨建議。

This is a Streamlit-based retail promotion target viewing and dispatch suggestion system that helps retail businesses analyze inventory data and promotion targets, calculate demand, and provide dispatch recommendations.

### 功能特色 / Features
- 📊 **數據載入與驗證** - 支援Excel檔案上傳與自動資料驗證
- 🔍 **智能分析** - 自動計算日常銷售率、總需求、淨需求及派貨建議
- 📈 **視覺化分析** - 提供多種圖表展示分析結果
- 💾 **結果匯出** - 支援Excel格式報告下載
- 🌐 **多語言支援** - 支援中文/英文介面

### 安裝指南 / Installation Guide

#### 系統需求 / System Requirements
- Python 3.8+
- Streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- openpyxl >= 3.1.0
- matplotlib >= 3.7.0
- seaborn >= 0.12.0

#### 安裝步驟 / Installation Steps
1. 克隆或下載專案檔案
2. 安裝依賴包：
   ```bash
   pip install -r requirements.txt
   ```
3. 運行應用程式：
   ```bash
   streamlit run app.py
   ```

### 使用說明 / Usage Instructions

#### 輸入檔案格式要求 / Input File Format Requirements

**檔案A - 庫存與銷售數據 (Inventory and Sales Data)**
必須包含以下欄位：
- `Article` (str) - 產品編號
- `Article Description` (str) - 產品描述
- `RP Type` (str) - 補貨類型：ND（不補貨）或 RF（補貨）
- `Site` (str) - 店鋪編號
- `MOQ` (int) - 最低派貨數量
- `SaSa Net Stock` (int) - 現有庫存數量
- `Pending Received` (int) - 在途訂單數量
- `Safety Stock` (int) - 安全庫存數量
- `Last Month Sold Qty` (int) - 上月銷量
- `MTD Sold Qty` (int) - 本月至今銷量
- `Supply source` (str) - 補貨來源（1、2、4等代碼）
- `Description p. group` (str) - Buyer（買家組別描述）

**檔案B - 推廣目標數據 (Promotion Target Data)**
**Sheet 1:**
- `Group No.` (str) - 產品組別
- `Article` (str) - 產品編號
- `SKU Target` (int) - 推廣目標數量
- `Target Type` (str) - 目標類別 (HK/MO/ALL)
- `Promotion Days` (int) - 推廣日數
- `Target Cover Days` (int) - 推廣目標安全覆蓋日數

**Sheet 2:**
- `Site` (str) - 店鋪編號
- `Shop Target(HK)` (int) - 香港店鋪推廣目標
- `Shop Target(MO)` (int) - 澳門店鋪推廣目標
- `Shop Target(ALL)` (int) - 所有店鋪推廣目標

#### 操作流程 / Operation Process
1. **上傳檔案** - 分別上傳庫存檔案(A)和推廣目標檔案(B)
2. **數據預覽** - 查看預處理後的數據
3. **開始分析** - 點擊分析按鈕進行計算
4. **查看結果** - 瀏覽詳細計算結果和摘要統計
5. **視覺化分析** - 查看圖表分析
6. **匯出報告** - 下載Excel格式分析報告

### 計算邏輯 / Calculation Logic

#### 日常銷售率計算
```
Daily Sales Rate = (Last Month Sold Qty / 30 + MTD Sold Qty / 本月天數) / 2
```

#### 總需求計算
```
總需求 = 日常銷售需求 + 推廣特定需求
日常銷售需求 = Daily Sales Rate * (Promotion Days + Target Cover Days + Lead Time)
推廣特定需求 = SKU Target * Shop Target(對應類型)
```

#### 淨需求計算
```
淨需求 = 總需求 - (SaSa Net Stock + Pending Received) + Safety Stock
```

#### 缺貨數量計算
```
缺貨數量 = max(0, 淨需求 - SaSa Net Stock - Pending Received)
```

#### 條件性通知與建議
- **Supply source 1 或 4**: 生成缺貨通知給Buyer，記錄至Notes欄位
- **Supply source 2**: 生成RP team建議，對照D001庫存進行補貨
- **其他Supply source**: 僅記錄標準Notes

#### 派貨建議
- 若RP Type為RF：建議派貨量 = max(淨需求, MOQ)
- 若RP Type為ND：建議派貨量 = 0

### 系統限制 / System Limitations
- 僅支援.xlsx格式的Excel檔案
- 單次處理數據量建議不超過10,000行
- 圖表顯示最多1,000個數據點
- 不支援即時數據更新

### 錯誤處理 / Error Handling
- 檔案格式驗證
- 必需欄位檢查
- 數據類型轉換異常處理
- 邊界條件處理（負值、異常值、空數據）

### 部署指南 / Deployment Guide

#### 本地部署 / Local Deployment
```bash
streamlit run app.py
```

#### 雲端部署 / Cloud Deployment
支援部署到：
- Streamlit Sharing
- Heroku
- AWS EC2
- Google Cloud Run

### 開發者資訊 / Developer Information
- **開發者**: Ricky
- **版本**: v1.0
- **最後更新**: 2024年10月

### 聯絡資訊 / Contact Information
如有問題或建議，請聯繫開發團隊。

---

**注意**: 本系統僅供內部使用，請勿用於商業用途。