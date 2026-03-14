"""
YouTubeショート動画生成ツール - メインアプリケーション
"""
import streamlit as st

from config.config import config
from utils.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

st.set_page_config(
    page_title="YouTubeショート動画生成ツール",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


def show_home_page():
    """ホームページを表示"""
    st.title("🎬 YouTubeショート動画生成ツール")
    st.markdown("---")
    
    # APIキーの検証
    is_valid, missing_keys = config.validate_api_keys()
    
    if not is_valid:
        st.warning(f"⚠️ 以下のAPIキーが設定されていません: {', '.join(missing_keys)}")
        st.info("`.env`ファイルを作成して、必要なAPIキーを設定してください。")
        st.code("""
# .envファイルの例
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
    """)
    else:
        st.success("✅ すべてのAPIキーが設定されています。")
    
    st.markdown("---")
    
    st.markdown("""
    ## ようこそ！
    
    このツールは、テキストやトピックを入力するだけで、YouTubeショート（9:16形式）向けの高品質な動画を自動生成します。
    
    ### 主な機能
    - 📝 **台本自動生成**: GPT-4oを使用した高品質な台本生成
    - 🎤 **音声生成**: ElevenLabs APIを使用した日本語音声生成
    - 🖼️ **画像生成**: DALL-E 3を使用した画像生成
    - 🎬 **動画編集**: MoviePyを使用した動画編集と字幕追加
    
    ### 使い方
    1. 左サイドバーから各ステップに進んでください
    2. テキストやトピックを入力
    3. 台本を生成
    4. 音声と画像を生成
    5. 動画を編集・エクスポート
    
    ---
    
    ### 現在の設定
    - **動画サイズ**: {width}x{height}
    - **フレームレート**: {fps} fps
    - **ビットレート**: {bitrate} bps
    """.format(
        width=config.video_width,
        height=config.video_height,
        fps=config.video_fps,
        bitrate=config.video_bitrate
    ))


# サイドバーナビゲーション
st.sidebar.title("🎬 ナビゲーション")
page = st.sidebar.radio(
    "ページを選択",
    ["🏠 ホーム", "🔍 動画検索", "📝 台本生成", "🎤 音声生成", "🖼️ 画像生成", "🎬 動画編集"]
)

# ページルーティング
if page == "🏠 ホーム":
    show_home_page()
elif page == "🔍 動画検索":
    from ui.pages.video_search_page import show_video_search_page
    show_video_search_page()
elif page == "📝 台本生成":
    from ui.pages.script_page import show_script_page
    show_script_page()
elif page == "🎤 音声生成":
    from ui.pages.audio_page import show_audio_page
    show_audio_page()
elif page == "🖼️ 画像生成":
    from ui.pages.image_page import show_image_page
    show_image_page()
elif page == "🎬 動画編集":
    from ui.pages.video_page import show_video_page
    show_video_page()

# サイドバーに設定情報を表示
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 設定")
st.sidebar.markdown(f"**出力ディレクトリ**: `{config.output_dir}`")
st.sidebar.markdown(f"**ログディレクトリ**: `{config.log_dir}`")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 システム情報")
try:
    import streamlit as st_module
    st.sidebar.markdown(f"- Streamlit: {st_module.__version__}")
except:
    st.sidebar.markdown("- Streamlit: N/A")
