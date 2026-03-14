"""
YouTube の文字起こし（字幕/自動字幕）取得ユーティリティ

注意: YouTube Data API v3 だけでは字幕本文は取得できないため、
youtube-transcript-api を利用して取得する（取得できない動画もある）。
"""

from typing import Iterable, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptError(Exception):
    """文字起こし取得に失敗した場合のエラー"""


def has_transcript(video_id: str) -> bool:
    """
    動画に取得可能な字幕があるかどうかを返す。
    本文は取得せず list_transcripts で有無のみ判定する。
    """
    if not video_id:
        return False
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            CouldNotRetrieveTranscript,
            VideoUnavailable,
        )
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for _ in transcript_list:
            return True
        return False
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, CouldNotRetrieveTranscript):
        return False
    except Exception as e:
        logger.debug("has_transcript check failed for %s: %s", video_id, e)
        return False


def fetch_transcript_text(video_id: str, languages: Optional[Iterable[str]] = None) -> str:
    """
    字幕/自動字幕の文字起こしをプレーンテキストで返す。

    Args:
        video_id: YouTube の videoId
        languages: 優先する言語コード（例: ["ja", "en"]）

    Returns:
        文字起こし（プレーンテキスト）

    Raises:
        TranscriptError: 取得不可
    """
    if not video_id:
        raise TranscriptError("video_id が空です。")

    try:
        # 依存はオプションに近いので、呼び出し時に import する
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            CouldNotRetrieveTranscript,
            VideoUnavailable,
        )
    except Exception as e:
        raise TranscriptError(
            "文字起こし取得ライブラリが見つかりません。requirements を更新してインストールしてください。"
        ) from e

    lang_list = list(languages) if languages is not None else ["ja", "en"]

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=lang_list)
        # transcript: [{"text": "...", "start": 12.3, "duration": 4.2}, ...]
        lines = []
        for item in transcript:
            t = (item.get("text") or "").strip()
            if t:
                lines.append(t)
        text = "\n".join(lines).strip()
        if not text:
            raise TranscriptError("字幕は取得できましたが、内容が空でした。")
        return text
    except (TranscriptsDisabled,) as e:
        raise TranscriptError("この動画は字幕が無効化されています。") from e
    except (NoTranscriptFound,) as e:
        raise TranscriptError("この動画には取得可能な字幕が見つかりませんでした。") from e
    except (VideoUnavailable,) as e:
        raise TranscriptError("この動画は利用できません（非公開/削除/制限の可能性）。") from e
    except (CouldNotRetrieveTranscript,) as e:
        raise TranscriptError("字幕を取得できませんでした（取得制限の可能性）。") from e
    except Exception as e:
        logger.exception("Failed to fetch transcript: %s", e)
        raise TranscriptError(f"字幕取得に失敗しました: {e}") from e

