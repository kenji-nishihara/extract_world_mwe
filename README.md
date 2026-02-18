# extract_world_mwe

`World-Nuclear-Outlook-Report_dfed5656_country.pdf` のようなグラフ中心PDFから、
年次データをCSVとして抽出するためのスクリプトです。

## できること

1. **候補行抽出モード（従来）**
   - 「年 + 数値」を含む行をまとめて抽出します。
2. **国・系列指定モード（追加）**
   - 例: Argentina の 2025〜2050 年について、
     `60 year operation`, `80 year operation`, `Government target` を列として出力します。

## 使い方

### 1) 候補行抽出（デバッグ/探索用）

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf -o output_candidates.csv
```

出力列:

- `page`
- `year`
- `values`（同一行で検出した数値）
- `line`（元テキスト）

### 2) 国・系列を指定して表にする（推奨）

```bash
python3 extract_graph_data.py \
  World-Nuclear-Outlook-Report_dfed5656_country.pdf \
  --country "Argentina" \
  --series "60 year operation,80 year operation,Government target" \
  --year-min 2025 \
  --year-max 2050 \
  -o argentina_2025_2050.csv
```

出力列（例）:

- `country`
- `year`
- `60 year operation`
- `80 year operation`
- `Government target`


短縮オプション/互換オプションも使えます:

- `-c` / `--country` / `-country`
- `-s` / `--series` / `-series`
- `-y` / `--year-min` / `-year-min`
- `-Y` / `--year-max` / `-year-max`

## 依存関係

以下のどちらか1つがあれば動作します（`pdfplumber` 優先、なければ `pypdf`）。

```bash
pip install pdfplumber
```

または

```bash
pip install pypdf
```

## Windowsで「インストール済みなのに見つからない」場合

`pip` と `python3` が別環境を指している可能性があります。

```powershell
py -m pip install pdfplumber
py extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf --country "Argentina" --series "60 year operation,80 year operation,Government target" -o argentina.csv
```

## 注意

- このスクリプトは **PDF内テキスト** をもとに抽出します。
- グラフ線の画像座標を直接トレースする方式ではありません。
- グラフの文字が画像化されている場合、精度向上にはOCR/手動補正が必要です。
