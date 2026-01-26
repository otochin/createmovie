"""
定数定義
"""
from pathlib import Path

# プロジェクトルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent

# 出力ディレクトリ
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_SCRIPTS_DIR = OUTPUT_DIR / "scripts"
OUTPUT_AUDIO_DIR = OUTPUT_DIR / "audio"
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"
OUTPUT_VIDEOS_DIR = OUTPUT_DIR / "videos"

# 動画設定
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_BITRATE = 8000000  # 8Mbps
VIDEO_ASPECT_RATIO = (9, 16)  # 9:16

# OpenAI設定
OPENAI_MODEL = "gpt-4o"
OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_IMAGE_SIZE = "1024x1792"  # 9:16形式に近いサイズ（DALL-E 3の最大サイズ）
OPENAI_IMAGE_QUALITY = "standard"

# ElevenLabs設定
ELEVENLABS_DEFAULT_VOICE_ID = None  # .envから読み込む
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"  # 日本語対応モデル
ELEVENLABS_STABILITY = 0.5
ELEVENLABS_SIMILARITY_BOOST = 0.75

# ファイル形式
SCRIPT_FORMAT = "json"
AUDIO_FORMAT = "mp3"
IMAGE_FORMAT = "png"
VIDEO_FORMAT = "mp4"

# ログ設定
LOG_DIR = PROJECT_ROOT / "logs"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
