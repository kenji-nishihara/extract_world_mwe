# extract_world_mwe

棒グラフを含むPDFから、年次データをCSV抽出します。

## 今回の仕様

- `--country --series --year-min --year-max` を入力しなくても、**全ページを自動抽出**。
- 数値は**テキストからは抽出せず**、`pdfplumber` で取得した棒グラフ矩形の高さ (`bar_height`) のみを使用。
- グラフの縦軸目盛り（Y軸数値）を読み取り、`bar_height` を **MWe に換算**。
- 出力の `source` は `bar_height` 固定。

## 実行

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf -o all_elements.csv
```

出力列:

- `country`
- `page`
- `year`
- `element` (`element_1`, `element_2`, ...)
- `value` (MWe換算値)
- `unit` (`MWe`)
- `source` (`bar_height`)
- `line`（現状は空文字）

## 補足

- `source=bar_height` は、PDF内の棒グラフがベクター矩形として保持され、かつY軸目盛り数値が読めるページで有効です。
- 国名はページ内の見出し候補テキストから推定します。
- PDFテキスト中に `>>>>>>> main` のようなマージ競合マーカー行が混ざっていても、自動的に無視します。

## 依存関係

```bash
pip install pdfplumber
```

このスクリプトは bar_height 抽出のため `pdfplumber` が必須です。
