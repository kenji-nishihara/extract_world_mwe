# extract_world_mwe

`World-Nuclear-Outlook-Report_dfed5656_country.pdf` の国別スタック棒グラフから、
**bar height のみ**で年次カテゴリ別MWeを抽出します。

## 仕様

- 数値はテキストから直接読まず、棒グラフ矩形の高さのみを利用（`source=bar_height` 固定）。
- Y軸目盛り値（0, 200, ...）から線形換算して、棒高さをMWeへ変換。
- 年ラベル（2025〜2050）をX座標で検出し、各棒を最近傍の年に割当。
- 凡例色が取れれば「色→カテゴリ」を凡例から決定、難しい場合はページ内2050表の値で補完マッチング。
- PDF内の `<<<<<<<` / `=======` / `>>>>>>>` 行は無視します。

## 出力

### long形式（デフォルト）

```csv
country,year,category,mwe,unit,source
Argentina,2025,60-year operation,1780.12,MWe,bar_height
...
```

### pivot形式（自動生成）

`*_pivot.csv` も同時に作成します。

```csv
country,year,60-year operation,80-year operation,Under construction,Planned,Proposed,Potential,Government target
Argentina,2025,...
```

## 実行

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf
```

出力先指定:

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf \
  -o world_nuclear_outlook_country_year_category_mwe.csv \
  --pivot-output world_nuclear_outlook_country_year_category_mwe_pivot.csv
```

特定国 + 指定系列だけの横持ち出力（任意）:

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf \
  --country Argentina \
  --series "60-year operation,80-year operation,Government target" \
  -o argentina_selected_series.csv
```

## 依存関係

```bash
pip install pdfplumber
```

## トラブルシュート

### `SyntaxError` で `<<<<<<<` が出る場合

`extract_graph_data.py` に **マージ競合マーカー**（`<<<<<<<`, `=======`, `>>>>>>>`）が混入しています。

1. 競合マーカー有無を確認

```bash
rg -n "^(<<<<<<<|=======|>>>>>>>)" extract_graph_data.py
```

2. 競合マーカーが出る場合は、その行を削除して正しいコードだけ残す
   - もし修正が難しければ、このリポジトリの最新 `extract_graph_data.py` を上書きしてください。

3. 再確認

```bash
python3 extract_graph_data.py --help
```


### デバッグ（特定国のカテゴリ合計確認）

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf --debug-country Armenia
```

抽出後に `totals_by_category` を表示し、`60-year operation` / `80-year operation` が0のままかを確認できます。
