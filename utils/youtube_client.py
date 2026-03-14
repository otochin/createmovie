"""
YouTube Data API v3 クライアント（動画検索用）
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.googleapis.com/youtube/v3"
MAX_RESULTS_DEFAULT = 25
MAX_RESULTS_LIMIT = 50


class YouTubeSearchError(Exception):
    """YouTube検索APIのエラー"""
    pass


def search_videos(
    api_key: str,
    keyword: str,
    published_after: Optional[datetime] = None,
    published_before: Optional[datetime] = None,
    max_results: int = MAX_RESULTS_DEFAULT,
) -> list[dict]:
    """
    YouTube Data API v3 で動画を検索する。

    Args:
        api_key: YouTube Data API v3 のAPIキー
        keyword: 検索キーワード
        published_after: この日時以降に公開された動画に絞る（RFC 3339）
        published_before: この日時以前に公開された動画に絞る（RFC 3339）
        max_results: 取得する最大件数（1〜50）

    Returns:
        動画情報のリスト。各要素は video_id, title, channel_title, published_at, thumbnail_url,
        view_count, like_count, comment_count, views_per_day, duration_display, description_snippet を持つ辞書

    Raises:
        YouTubeSearchError: APIエラー時
    """
    if not keyword or not keyword.strip():
        return []

    max_results = max(1, min(max_results, MAX_RESULTS_LIMIT))
    params = {
        "part": "snippet",
        "q": keyword.strip(),
        "type": "video",
        "key": api_key,
        "maxResults": max_results,
    }
    if published_after is not None:
        params["publishedAfter"] = _to_rfc3339(published_after)
    if published_before is not None:
        params["publishedBefore"] = _to_rfc3339(published_before)

    try:
        resp = requests.get(
            f"{BASE_URL}/search",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.exception("YouTube search request failed: %s", e)
        if hasattr(e, "response") and e.response is not None:
            try:
                err_body = e.response.json()
                err_msg = err_body.get("error", {}).get("message", str(e))
                raise YouTubeSearchError(f"YouTube API エラー: {err_msg}") from e
            except Exception:
                pass
        raise YouTubeSearchError(f"リクエストに失敗しました: {e}") from e

    items = data.get("items", [])
    results = []
    video_ids = []
    for item in items:
        vid = item.get("id", {}).get("videoId")
        if not vid:
            continue
        video_ids.append(vid)
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )
        results.append({
            "video_id": vid,
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail_url": thumbnail_url,
            "view_count": None,  # 後で videos.list で取得して埋める
        })

    # 再生数・高評価数・コメント数などを videos.list で取得してマージ
    if results and video_ids:
        details = _fetch_video_details(api_key, video_ids)
        for r in results:
            d = details.get(r["video_id"], {})
            r["view_count"] = d.get("view_count")
            r["like_count"] = d.get("like_count")
            r["comment_count"] = d.get("comment_count")
            r["duration_display"] = d.get("duration_display")
            r["description_snippet"] = d.get("description_snippet")

    # 伸び率（1日あたりの再生数）を計算
    now = datetime.now(timezone.utc)
    for r in results:
        days = 1
        try:
            pub = r.get("published_at", "") or ""
            if pub:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                delta = now - dt
                days = max(1, delta.days)
        except Exception:
            pass
        vc = r.get("view_count") or 0
        r["views_per_day"] = round(vc / days) if vc else None

    # 概要（description）がある動画のみに絞る
    results = [r for r in results if (r.get("description_snippet") or "").strip()]

    # 再生数の降順でソート（None は末尾）
    results.sort(key=lambda r: (r["view_count"] is None, -(r["view_count"] or 0)))

    return results


def _parse_int(value) -> Optional[int]:
    """APIの数値文字列を int に変換。無効なら None。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_duration(iso_duration: str) -> Optional[str]:
    """
    ISO 8601 の duration（例: PT1M30S, PT15S）を「1分30秒」形式に変換する。
    """
    if not iso_duration or not iso_duration.startswith("PT"):
        return None
    s = iso_duration.upper().replace("PT", "")
    hours = 0
    minutes = 0
    seconds = 0
    m = re.match(r"(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if m:
        hours = int(m.group(1) or 0)
        minutes = int(m.group(2) or 0)
        seconds = int(m.group(3) or 0)
    parts = []
    if hours > 0:
        parts.append(f"{hours}時間")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}秒")
    return "".join(parts)


def _fetch_video_details(api_key: str, video_ids: list[str]) -> dict:
    """
    videos.list で動画の詳細（再生数・高評価・コメント・長さ・概要）を取得する。
    最大50件まで1リクエストで取得可能。

    Returns:
        video_id -> {view_count, like_count, comment_count, duration_display, description_snippet} の辞書
    """
    if not video_ids:
        return {}
    ids = video_ids[:50]
    params = {
        "part": "statistics,contentDetails,snippet",
        "id": ",".join(ids),
        "key": api_key,
    }
    out: dict = {}
    try:
        resp = requests.get(
            f"{BASE_URL}/videos",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("items", []):
            vid = item.get("id")
            if not vid:
                continue
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            desc = (snippet.get("description") or "")[:150].strip()
            if len((snippet.get("description") or "")) > 150:
                desc = desc + "…"
            out[vid] = {
                "view_count": _parse_int(stats.get("viewCount")),
                "like_count": _parse_int(stats.get("likeCount")),
                "comment_count": _parse_int(stats.get("commentCount")),
                "duration_display": _parse_duration(content.get("duration", "")),
                "description_snippet": desc or None,
            }
    except requests.RequestException as e:
        logger.warning("Failed to fetch video details: %s", e)
    return out


def _to_rfc3339(dt: datetime) -> str:
    """datetime を RFC 3339 形式の文字列に変換する（API用）"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def published_after_for_preset(preset: str) -> Optional[datetime]:
    """
    プリセット名から「この日時以降」の datetime を返す。

    Args:
        preset: "24h" | "7d" | "30d" | "3m"

    Returns:
        対応する published_after の datetime（UTC）。無効な preset の場合は None
    """
    now = datetime.now(timezone.utc)
    mapping = {
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "3m": now - timedelta(days=90),
    }
    return mapping.get(preset)
