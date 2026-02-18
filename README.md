# extract_world_mwe

<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
棒グラフを含むPDFから、年次データをCSV抽出します。

## 今回の改良

- `--country --series --year-min --year-max` を入力しなくても、**全ページを自動抽出**。
- テキスト抽出だけでなく、`pdfplumber` が使える場合は **棒グラフの高さ（矩形）から値を推定**。
- 出力に `unit=MWe` と `source`（`text` / `bar_height`）を追加。

## 実行

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf -o all_elements.csv
```

出力列:

- `country`
- `page`
- `year`
- `element` (`element_1`, `element_2`, ...)
- `value`
- `unit` (`MWe`)
- `source` (`text` or `bar_height`)
- `line`（テキスト抽出時の元行）

## 補足

- `source=bar_height` は、PDF内の棒グラフがベクター矩形として保持され、かつY軸目盛り数値が読めるページで有効です。
- 国名はページ内の見出し候補テキストから推定します。
- 一部ページではテキスト抽出のみ、または推定が不安定な場合があるため、最終確認を推奨します。

## 依存関係

=======
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

>>>>>>> main
```bash
pip install pdfplumber
```

<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
`pdfplumber` がない場合は `pypdf` にフォールバックします（この場合 `bar_height` は利用不可）。
=======
または
>>>>>>> main

```bash
pip install pypdf
```
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
=======

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
>>>>>>> main
