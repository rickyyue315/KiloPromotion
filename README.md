# Promotion Analysis App

## 安裝步驟

1. 確保已安裝 Python 3.8 或以上版本。
2. 下載或複製此專案到本地。
3. 在專案目錄中執行以下命令安裝依賴：
   ```
   pip install -r requirements.txt
   ```

## 使用方法

1. 在專案目錄中執行以下命令啟動應用程式：
   ```
   streamlit run app.py
   ```
2. 在瀏覽器中開啟顯示的 URL。

## 部署

### 本地運行
```
streamlit run app.py
```

### 雲端部署
此應用程式支援 Streamlit Cloud 部署。只需上傳 `requirements.txt` 和 `app.py` 檔案即可。

## 測試

執行以下命令運行測試：
```
python -m unittest tests.py
```

## 輸入檔案格式

### File A (Inventory and Sales Data)
Excel 檔案 (.xlsx)，包含以下必要欄位：
- Article: 商品編號
- Article Description: 商品描述
- RP Type: 補貨類型 (ND 或 RF)
- Site: 站點
- MOQ: 最低訂購量
- SaSa Net Stock: 淨庫存
- Pending Received: 待收貨
- Safety Stock: 安全庫存
- Last Month Sold Qty: 上月銷售量
- MTD Sold Qty: 本月至今銷售量
- Supply source: 供應來源
- Description p. group: 產品群組描述

### File B (Promotion Target)
Excel 檔案 (.xlsx)，包含兩個工作表：

#### Sheet 1
- Group No.: 組別編號
- Article: 商品編號
- SKU Target: SKU 目標
- Target Type: 目標類型 (HK, MO, ALL)
- Promotion Days: 促銷天數
- Target Cover Days: 目標覆蓋天數

#### Sheet 2
- Site: 站點
- Shop Target(HK): 香港店目標
- Shop Target(MO): 澳門店目標
- Shop Target(ALL): 全店目標

## 限制

- 僅支援指定的欄位格式。
- 不支援合併儲存格處理。
- 檔案大小限制為 10MB。
- 不支援即時資料更新。