# Street Photo Collector

海外のストリート写真情報から、一般ニュースではなく「作家・作品・展示・写真集・アワード結果」に紐づく記事を優先して収集するPython MVPです。

OpenAI API、Anthropic API、News API、Google APIなどのAPIキーは使いません。RSSまたは公開HTMLだけを軽く取得し、取得困難なサイトは深追いしない設計です。Instagram、X、Facebookのスクレイピングもしません。

## 収集方針

優先する記事:

- 個人フォトグラファー特集: profile / feature / interview / portfolio / series / project
- 写真展: exhibition / solo show / group show / gallery / museum / exhibition review
- フォトブック: photobook / photo book / monograph / zine / book launch / publisher feature
- 写真コンテスト結果: award / winner / finalist / shortlist / contest results

低優先・減点する記事:

- camera review / lens review / gear / specs / hands-on / deal / sale / discount
- tips / beginner / how to / settings / best camera / best lens
- AI画像生成、スマホ新機能、ソフトウェア更新など作品紹介と関係ない記事
- 作家・作品・展示・写真集・受賞結果に紐づかない一般論記事

## 出力

実行すると以下を生成します。

- `output.md`: 読むための通常レポート
- `notebooklm_import.md`: NotebookLMなどに読み込ませやすい研究用Markdown
- `articles.csv`: 表計算・フィルタ用CSV
- `data/seen.sqlite3`: 重複URL管理用SQLite

各記事には以下を出力します。

- Title
- Source
- URL
- Date
- Article Type
- Photographer Name
- Project / Series / Book / Exhibition Name
- Detected Street Genre
- Matched Keywords
- Relevance Score
- Why this was selected
- Why this may be useful for my photography

## 設定ファイル

- `sources.yaml`: 巡回先、RSS URL、HTML fallback、ソース別加点、除外URLパターン
- `genres.yaml`: ストリート写真ジャンル別キーワード
- `article_types.yaml`: 記事タイプ、高スコア/低スコア条件、説明テンプレート

このMVPは外部依存なしで動くように、設定ファイルをJSON互換YAMLで書いています。将来 `PyYAML` を導入した場合は通常のYAMLも読み込めます。

## 実行方法

```powershell
py -m street_photo_collector --limit 30 --per-source 12 --min-score 4
```

`python` コマンドが使える環境では以下でも動きます。

```bash
python -m street_photo_collector --limit 30 --per-source 12 --min-score 4
```

取得済みURLも含めて再出力を確認したい場合:

```bash
python -m street_photo_collector --limit 30 --per-source 12 --min-score 4 --include-seen
```

## GitHub Actions

`.github/workflows/collect.yml` で週2回実行します。

- cron: `0 22 * * 0,3`
- UTC: 日曜・水曜 22:00
- 日本時間: 月曜・木曜 07:00

つまり、次回の日本時間木曜日の定期実行から新条件が使われます。

Actionsは以下を更新コミットします。

- `output.md`
- `notebooklm_import.md`
- `articles.csv`
- `data/seen.sqlite3`

## AI要約を追加する場合

現状の説明文はAI要約ではなく、記事タイプとキーワードに基づくルールベース生成です。

将来AI要約を追加する場合は、分類・スコアリング後の `Article` を受け取り、`why` と `photography_use` を差し替えるクラスを追加してください。既存の収集、SQLite重複管理、CSV/Markdown出力はそのまま使えます。
