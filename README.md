# extract_world_mwe

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
- PDFテキスト中に `>>>>>>> main` のようなマージ競合マーカー行が混ざっていても、自動的に無視して抽出を続行します。

## 依存関係

```bash
pip install pdfplumber
```

`pdfplumber` がない場合は `pypdf` にフォールバックします（この場合 `bar_height` は利用不可）。
`pdfplumber` がない場合は `pypdf` にフォールバックします（この場合 `bar_height` は利用不可）。

```bash
pip install pypdf
```
