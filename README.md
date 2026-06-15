# Street Photo Collector

海外のストリート写真情報から、一般的な street photography ニュースではなく、作家・作品・展示・写真集・受賞に紐づく記事を優先して収集・分類・スコアリングする Python MVP です。

OpenAI API、Anthropic API、News API、Google API などの有料 API や API キーは使いません。RSS または公開 HTML を軽く取得し、RSS が無い・取得困難なサイトは深追いしません。Instagram / X / Facebook のスクレイピングも追加しません。

## 全体方針

記事収集に加えて、以下を行います。

- Article Type の分類
- Detected Street Genre の判定
- 加点・減点による Relevance Score 計算
- Photographer Name の抽出
- Project / Series / Book / Exhibition Name の抽出
- Matched Keywords の記録
- Markdown / NotebookLM 用 Markdown / CSV の生成

## 優先して拾う記事

- 作家特集: `profile` / `feature` / `interview` / `portfolio` / `series` / `project`
- 写真展: `exhibition` / `solo show` / `group show` / `gallery` / `museum` / `exhibition review`
- 写真集: `photobook` / `photo book` / `monograph` / `zine` / `book launch` / `publisher feature`
- 受賞: `award` / `winner` / `finalist` / `shortlist` / `contest results`

## 低優先・減点する記事

- `camera review` / `lens review` / `gear` / `specs` / `hands-on` / `deal` / `sale` / `discount`
- `tips` / `beginner` / `how to` / `settings` / `best camera` / `best lens`
- AI 画像生成、スマホ新機能、ソフトウェア更新など作品紹介と関係ない記事
- 作家・作品・展示・写真集・受賞結果に紐づかない一般論記事

## ファイル別の変更点

### sources.yaml

優先ソースを以下に更新しています。

LensCulture / The Independent Photographer / Street Photography Magazine / Magnum Photos / British Journal of Photography(1854) / Aperture / PhMuseum / Huck / It's Nice That / The Photographers' Gallery / Foam / F-Stop Magazine / Burn Magazine / Lenscratch / Photobook Journal / MACK / VOID / Loose Joints / Setanta Books / Paris Photo / Photo London / World Street Photo Awards

RSS があるサイトは RSS を優先し、RSS が無いサイトは HTML から取得します。取得困難なサイトは深追いせず Fetch Notes に残します。

### article_types.yaml

記事タイプを以下の7種で定義します。

- `Photographer Feature`
- `Interview`
- `Portfolio or Series`
- `Exhibition`
- `Photobook`
- `Award or Contest Result`
- `Other`

各タイプに対応する判定キーワード、選定理由、撮影への活用説明を持たせています。

### genres.yaml

Detected Street Genre 用に以下の7ジャンルと判定キーワードを定義します。

- `Candid`
- `Street Portrait`
- `Street Fashion`
- `Fine Art Street`
- `Urban Landscape`
- `Humor or Decisive Moment`
- `Silent Stories`

### street_photo_collector/classify.py

各記事について以下を行います。

- `article_types.yaml` に基づく Article Type 判定
- `genres.yaml` に基づく Detected Street Genre 判定
- Photographer Name 抽出。不明なら `Unknown`
- Project / Series / Book / Exhibition Name 抽出。不明なら `Unknown`
- Matched Keywords の記録

### street_photo_collector/scoring.py

加点・減点ルールを実装します。

加点:

- 作家名あり: `+5`
- 作品シリーズ・プロジェクト・ポートフォリオ名あり: `+5`
- `exhibition` / `gallery` / `museum` / `solo show` / `group show`: `+4`
- `photobook` / `photo book` / `monograph` / `zine` / `book launch`: `+4`
- `award` / `winner` / `finalist` / `shortlist` / `contest results`: `+4`
- `interview` / `profile` / `feature` / `portfolio` / `series` / `project`: `+4`
- 作風語: `+3`

減点:

- `gear` / `specs` / `review` / `deal` / `sale` / `discount`: `-8`
- `tips` / `beginner` / `how to` / `settings`: `-5`
- 作品と無関係な AI / スマホ / ソフト記事: `-5`
- タイトルから作家・展示・写真集・受賞・シリーズの関係が見えない: `-3`

合計を `Relevance Score` として記事に付与します。

### 出力生成

以下の3ファイルを生成します。

- `output.md`
- `notebooklm_import.md`
- `articles.csv`

3ファイルとも次の項目を揃えて出力します。

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

`Why this may be useful for my photography` は AI 要約ではなく、Article Type と Matched Keywords に基づくルールベース説明です。

## 実行方法

```powershell
py -m street_photo_collector --limit 30 --per-source 12 --min-score 4
```

`python` コマンドが使える環境では以下でも動きます。

```bash
python -m street_photo_collector --limit 30 --per-source 12 --min-score 4
```

取得済み URL も含めて再出力を確認したい場合:

```bash
python -m street_photo_collector --limit 30 --per-source 12 --min-score 4 --include-seen
```

## GitHub Actions

`.github/workflows/collect.yml` で週2回実行します。

- cron: `0 22 * * 0,3`
- UTC: 日曜・水曜 22:00
- 日本時間: 月曜・木曜 07:00

次回の日本時間木曜日の定期実行から新条件が使われます。

Actions の実行コマンド:

```bash
python -m street_photo_collector --limit 30 --per-source 12 --min-score 4
```

Actions は以下を更新コミットします。

- `output.md`
- `notebooklm_import.md`
- `articles.csv`
- `data/seen.sqlite3`

## 無料運用と配慮

- 有料 API や API キーは使いません。
- Instagram / X / Facebook のスクレイピングはしません。
- robots.txt、利用規約、サイト負荷に配慮します。
- RSS が無い・取得困難なサイトは無理に深追いしません。
