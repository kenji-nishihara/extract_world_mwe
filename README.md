# extract_world_mwe

`World-Nuclear-Outlook-Report_dfed5656_country.pdf` のようなグラフ中心PDFから、
「年 + 数値」を含む行を機械的に抽出するための最小スクリプトです。

## 使い方

```bash
python3 extract_graph_data.py World-Nuclear-Outlook-Report_dfed5656_country.pdf -o output.csv
```

出力CSV列:

- `page`: PDFページ番号
- `year`: 検出した年（`19xx/20xx/21xx`）
- `values`: 同一行で検出した数値群（`|` 区切り）
- `line`: 元テキスト行

## 注意

- グラフ画像そのもの（線の座標）を直接読んで値を復元するものではありません。
- PDF内テキストとして埋め込まれたラベル・凡例・注記から抽出します。
- 最終的な表として使う前に、人手確認を行ってください。

## 依存関係

```bash
pip install pdfplumber
```
