"""
動画検索ページ（YouTube Data API v3）
"""
import html
from datetime import datetime
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from config.config import config
from config.constants import (
    YOUTUBE_SEARCH_PERIOD_PRESETS,
    YOUTUBE_SEARCH_MAX_RESULTS,
)
from utils.youtube_client import (
    search_videos,
    published_after_for_preset,
    YouTubeSearchError,
)
from utils.youtube_transcript import fetch_transcript_text, has_transcript, TranscriptError
from utils.logger import get_logger

logger = get_logger(__name__)


@st.cache_data(ttl=3600)
def _cached_has_transcript(video_id: str) -> bool:
    """動画に字幕があるかどうか（video_id ごとに1時間キャッシュ）"""
    return has_transcript(video_id)


def _format_published_at(published_at: str) -> str:
    """APIの publishedAt を表示用にフォーマットする"""
    if not published_at:
        return ""
    try:
        # ISO 8601 形式 (例: 2024-03-01T12:00:00Z)
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return published_at


def _format_count(value: Optional[int], suffix: str = "回") -> str:
    """数値を表示用にフォーマットする（万・億対応）。高評価数・コメント数などに利用"""
    if value is None:
        return "—"
    if value >= 100000000:
        return f"{value / 100000000:.1f}億{suffix}"
    if value >= 10000:
        return f"{value / 10000:.1f}万{suffix}"
    return f"{value:,}{suffix}"


def _format_view_count(view_count: Optional[int]) -> str:
    """再生数を表示用にフォーマットする（万・億対応）"""
    return _format_count(view_count, "回")


def _format_views_per_day(views_per_day: Optional[int]) -> str:
    """伸び率（1日あたり再生数）を表示用にフォーマットする"""
    if views_per_day is None:
        return "—"
    if views_per_day >= 10000:
        return f"{views_per_day / 10000:.1f}万回/日"
    return f"{views_per_day:,}回/日"


def show_video_search_page():
    """動画検索ページを表示"""
    st.header("🔍 動画検索")
    st.caption("キーワードと公開時期でYouTube動画を検索し、サムネイルを参考にできます。")
    st.markdown("---")

    # 文字起こし取得後：クリップボードにコピー（ボタン1回でコピー＋表示は最小限でクリア）
    if st.session_state.get("transcript_to_copy") is not None:
        _text = st.session_state.transcript_to_copy
        escaped = html.escape(_text)
        # 自動コピーを試行しつつ、ボタンでもコピー可能に（ユーザージェスチャーがないとブロックされる場合のため）
        transcript_copy_html = f"""
        <div style="margin:0.25rem 0;">
        <textarea id="transcriptCopySrc" style="position:absolute;left:-9999px;" readonly>{escaped}</textarea>
        <button type="button" id="transcriptCopyBtn" style="padding:0.35rem 0.6rem;cursor:pointer;border-radius:4px;">
        クリップボードにコピー
        </button>
        <span id="transcriptCopyStatus" style="margin-left:0.5rem;font-size:0.9em;"></span>
        </div>
        <script>
        (function() {{
          var src = document.getElementById('transcriptCopySrc');
          var btn = document.getElementById('transcriptCopyBtn');
          var status = document.getElementById('transcriptCopyStatus');
          if (!src) return;
          var t = src.value;
          function doCopy() {{
            if (navigator.clipboard && navigator.clipboard.writeText) {{
              navigator.clipboard.writeText(t).then(function() {{
                if (status) {{ status.textContent = 'コピーしました'; status.style.color = 'green'; }}
              }}).catch(function() {{
                if (status) {{ status.textContent = 'コピーできませんでした'; status.style.color = 'red'; }}
              }});
            }}
          }}
          if (btn) btn.onclick = doCopy;
          doCopy();
        }})();
        </script>
        """
        components.html(transcript_copy_html, height=40)
        st.caption("文字起こしを取得しました。上で「クリップボードにコピー」を押すとクリップボードにコピーされます。")
        del st.session_state.transcript_to_copy
        st.markdown("---")

    if st.session_state.get("transcript_error"):
        st.error(st.session_state.transcript_error)
        del st.session_state.transcript_error
        st.markdown("---")

    if not config.youtube_api_key:
        st.warning("⚠️ YouTube Data API キーが設定されていません。")
        st.info(
            "`.env` に `YOUTUBE_API_KEY` を追加してください。"
            "手順は `docs/ENV_SETUP.md` の「5. YouTube Data API キー」を参照してください。"
        )
        return

    period_options = {label: value for value, label in YOUTUBE_SEARCH_PERIOD_PRESETS}
    period_labels = [label for _, label in YOUTUBE_SEARCH_PERIOD_PRESETS]

    with st.form("video_search_form"):
        keyword = st.text_input(
            "キーワード",
            value="雑学女子",
            placeholder="例: ショート 雑学",
            help="検索したいキーワードを入力してください",
        )
        period_label = st.selectbox(
            "公開時期",
            options=period_labels,
            index=2,
            help="この期間内に公開された動画に絞り込みます（デフォルト: 直近30日間）",
        )
        submitted = st.form_submit_button("検索")

    # 検索未送信でも、前回の検索結果があれば表示する（「文字起こしをコピー」で rerun しても結果を維持）
    if submitted:
        if not keyword or not keyword.strip():
            st.warning("キーワードを入力してください。")
            return
        period_value = period_options.get(period_label, "30d")
        published_after = published_after_for_preset(period_value)
        with st.spinner("検索中..."):
            try:
                results = search_videos(
                    api_key=config.youtube_api_key,
                    keyword=keyword,
                    published_after=published_after,
                    max_results=YOUTUBE_SEARCH_MAX_RESULTS,
                )
            except YouTubeSearchError as e:
                st.error(str(e))
                logger.exception("YouTube search failed")
                return
        # 字幕の有無を確認してから保存（ボタン表示のため）
        with st.spinner("字幕の有無を確認中..."):
            for item in results:
                if "has_transcript" not in item:
                    item["has_transcript"] = _cached_has_transcript(item["video_id"])
        st.session_state.video_search_results = results
    else:
        results = st.session_state.get("video_search_results")
        if not results:
            return
        # キャッシュから復元した結果に has_transcript が無い場合は補う（旧データや別タブからの遷移時）
        need_check = any("has_transcript" not in item for item in results)
        if need_check:
            with st.spinner("字幕の有無を確認中..."):
                for item in results:
                    if "has_transcript" not in item:
                        item["has_transcript"] = _cached_has_transcript(item["video_id"])

    if not results:
        st.info("該当する動画は見つかりませんでした。キーワードや公開時期を変えて試してください。")
        return

    st.success(f"**{len(results)}件**の動画が見つかりました。（概要がある動画のみ表示）")
    st.markdown("---")

    # 3列グリッドでカード表示
    cols_per_row = 3
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(results):
                break
            item = results[idx]
            with col:
                # サムネイル（クリックでYouTubeへ）
                video_url = f"https://www.youtube.com/watch?v={item['video_id']}"
                st.image(
                    item["thumbnail_url"],
                    use_container_width=True,
                    caption=item["title"][:60] + ("..." if len(item["title"]) > 60 else ""),
                )
                st.markdown(f"**{item['title']}**")
                st.caption(f"📺 {item['channel_title']}")
                st.caption(f"📅 {_format_published_at(item['published_at'])}")
                if item.get("duration_display"):
                    st.caption(f"⏱️ {item['duration_display']}")
                st.caption(f"▶️ 再生数: {_format_view_count(item.get('view_count'))}")
                st.caption(f"👍 高評価: {_format_count(item.get('like_count'))}  💬 コメント: {_format_count(item.get('comment_count'))}")
                st.caption(f"📈 伸び率: {_format_views_per_day(item.get('views_per_day'))}")
                if item.get("description_snippet"):
                    with st.expander("概要"):
                        st.caption(item["description_snippet"])

                # タイトル・概要をコピー: HTMLボタンでクリップボードに直接コピー（rerun しないので検索結果が消えない）
                title = item.get("title") or ""
                desc = item.get("description_snippet") or ""
                copy_text = f"{title}\n\n{desc}".strip()
                vid = item["video_id"]
                escaped = html.escape(copy_text)
                copy_html = f"""
                <div style="margin:0.25rem 0;">
                <textarea id="copySrc_{vid}" style="position:absolute;left:-9999px;" readonly>{escaped}</textarea>
                <button type="button" id="btnCopy_{vid}" style="padding:0.35rem 0.6rem;cursor:pointer;border-radius:4px;width:100%;">
                タイトル・概要をコピー
                </button>
                <span id="status_{vid}" style="margin-left:0.25rem;font-size:0.85em;"></span>
                </div>
                <script>
                (function() {{
                  var btn = document.getElementById('btnCopy_{vid}');
                  var src = document.getElementById('copySrc_{vid}');
                  var status = document.getElementById('status_{vid}');
                  if (!btn || !src) return;
                  btn.onclick = function() {{
                    var t = src.value;
                    if (navigator.clipboard && navigator.clipboard.writeText) {{
                      navigator.clipboard.writeText(t).then(function() {{
                        status.textContent = 'コピーしました';
                        status.style.color = 'green';
                        setTimeout(function() {{ status.textContent = ''; }}, 2000);
                      }}).catch(function() {{
                        status.textContent = '失敗';
                        status.style.color = 'red';
                      }});
                    }} else {{
                      status.textContent = '非対応';
                      status.style.color = 'orange';
                    }}
                  }};
                }})();
                </script>
                """
                components.html(copy_html, height=42)

                # 文字起こしをコピー（字幕がある動画のみボタン表示）
                if item.get("has_transcript"):
                    if st.button("文字起こしをコピー", key=f"copy_transcript_{item['video_id']}", use_container_width=True):
                        with st.spinner("字幕を取得中..."):
                            try:
                                text = fetch_transcript_text(item["video_id"], languages=["ja", "en"])
                                st.session_state.transcript_to_copy = text
                            except TranscriptError as e:
                                st.session_state.transcript_error = str(e)
                        st.rerun()

                st.link_button("YouTubeで見る", video_url, use_container_width=True)
                st.markdown("---")
