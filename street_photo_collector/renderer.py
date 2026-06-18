from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import Article


HEADER = [
    "タイトル",
    "ソース",
    "URL",
    "日付",
    "記事タイプ",
    "作家名",
    "作品・シリーズ・写真集・展示名",
    "判定ストリートジャンル",
    "一致キーワード",
    "関連度スコア",
    "選んだ理由",
    "自分の撮影に役立ちそうな点",
]

ARTICLE_TYPE_LABELS = {
    "Photographer Feature": "作家特集 (Photographer Feature)",
    "Interview": "インタビュー (Interview)",
    "Portfolio or Series": "ポートフォリオ/シリーズ (Portfolio or Series)",
    "Exhibition": "展示 (Exhibition)",
    "Photobook": "写真集 (Photobook)",
    "Award or Contest Result": "受賞/コンテスト結果 (Award or Contest Result)",
    "Other": "その他 (Other)",
}

GENRE_LABELS = {
    "Candid": "キャンディッド (Candid)",
    "Street Portrait": "ストリートポートレート (Street Portrait)",
    "Street Fashion": "ストリートファッション (Street Fashion)",
    "Fine Art Street": "ファインアート・ストリート (Fine Art Street)",
    "Urban Landscape": "都市風景 (Urban Landscape)",
    "Humor or Decisive Moment": "ユーモア/決定的瞬間 (Humor or Decisive Moment)",
    "Silent Stories": "静かな物語 (Silent Stories)",
}


def render_all_outputs(
    articles: list[Article],
    output_path: str | Path,
    notebooklm_path: str | Path,
    csv_path: str | Path,
    errors: list[str] | None = None,
) -> None:
    render_markdown(articles, output_path, errors)
    render_notebooklm_import(articles, notebooklm_path, errors)
    render_csv(articles, csv_path)


def render_markdown(articles: list[Article], output_path: str | Path, errors: list[str] | None = None) -> None:
    path = Path(output_path)
    _ensure_parent(path)

    lines = [
        "# 海外ストリート写真ウォッチリスト",
        "",
        f"生成日時: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "対象: 作家、作品プロジェクト、展示、写真集、受賞・コンテスト結果に紐づく記事。",
        "ジャンル優先度: 静かな物語 > ファインアート・ストリート > 都市風景 > ユーモア/決定的瞬間 > キャンディッド > ストリートポートレート > ストリートファッション",
        "",
    ]

    if not articles:
        lines.extend(["新しく高関連度の記事は収集されませんでした。", ""])
    else:
        for index, article in enumerate(articles, start=1):
            lines.extend(
                [
                    f"## {index}. {article.title}",
                    "",
                    f"- タイトル: {article.title}",
                    f"- ソース: {article.source}",
                    f"- URL: {article.url}",
                    f"- 日付: {article.published_at or '不明'}",
                    f"- 記事タイプ: {_article_type_label(article.article_type)}",
                    f"- 作家名: {_unknown_to_japanese(article.photographer_name)}",
                    f"- 作品・シリーズ・写真集・展示名: {_unknown_to_japanese(article.project_name)}",
                    f"- 判定ストリートジャンル: {_genre_label(article.genre)}",
                    f"- 一致キーワード: {_format_keywords(article)}",
                    f"- 関連度スコア: {article.relevance_score:.2f}",
                    f"- 選んだ理由: {article.why}",
                    f"- 自分の撮影に役立ちそうな点: {article.photography_use}",
                    "",
                ]
            )

    if errors:
        lines.extend(["---", "", "## 取得メモ", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def render_notebooklm_import(articles: list[Article], output_path: str | Path, errors: list[str] | None = None) -> None:
    path = Path(output_path)
    _ensure_parent(path)

    lines = [
        "# NotebookLM用インポート: 海外ストリート写真リサーチ",
        "",
        f"生成日時: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "このファイルはリサーチ用インポートを想定しています。作家、作品群、展示、写真集、コンテスト結果に紐づく記事を優先しています。",
        "",
    ]

    for article in articles:
        lines.extend(
            [
                f"## {article.title}",
                "",
                f"ソース: {article.source}",
                f"URL: {article.url}",
                f"日付: {article.published_at or '不明'}",
                f"記事タイプ: {_article_type_label(article.article_type)}",
                f"作家名: {_unknown_to_japanese(article.photographer_name)}",
                f"作品・シリーズ・写真集・展示名: {_unknown_to_japanese(article.project_name)}",
                f"判定ストリートジャンル: {_genre_label(article.genre)}",
                f"一致キーワード: {_format_keywords(article)}",
                f"関連度スコア: {article.relevance_score:.2f}",
                "",
                f"選んだ理由: {article.why}",
                "",
                f"自分の撮影に役立ちそうな点: {article.photography_use}",
                "",
            ]
        )

    if errors:
        lines.extend(["## 取得メモ", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def render_csv(articles: list[Article], output_path: str | Path) -> None:
    path = Path(output_path)
    _ensure_parent(path)

    with path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(HEADER)
        for article in articles:
            writer.writerow(
                [
                    article.title,
                    article.source,
                    article.url,
                    article.published_at or "不明",
                    _article_type_label(article.article_type),
                    _unknown_to_japanese(article.photographer_name),
                    _unknown_to_japanese(article.project_name),
                    _genre_label(article.genre),
                    _format_keywords(article),
                    f"{article.relevance_score:.2f}",
                    article.why,
                    article.photography_use,
                ]
            )


def _format_keywords(article: Article) -> str:
    return ", ".join(article.matched_keywords) if article.matched_keywords else "なし"


def _article_type_label(value: str) -> str:
    return ARTICLE_TYPE_LABELS.get(value, value)


def _genre_label(value: str) -> str:
    return GENRE_LABELS.get(value, value)


def _unknown_to_japanese(value: str) -> str:
    return "不明" if value == "Unknown" else value


def _ensure_parent(path: Path) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
