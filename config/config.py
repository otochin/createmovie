"""
設定管理モジュール
環境変数の読み込みとアプリケーション設定の管理
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from .constants import (
    PROJECT_ROOT,
    OUTPUT_DIR,
    OUTPUT_SCRIPTS_DIR,
    OUTPUT_AUDIO_DIR,
    OUTPUT_IMAGES_DIR,
    OUTPUT_VIDEOS_DIR,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    VIDEO_BITRATE,
    LOG_DIR,
    LOG_LEVEL,
)


class Config:
    """アプリケーション設定クラス"""
    
    def __init__(self):
        # .envファイルを読み込む
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # .envファイルが存在しない場合は警告を出す
            print(f"警告: .envファイルが見つかりません。{env_path} を作成してください。")
        
        # APIキー
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id: Optional[str] = os.getenv("ELEVENLABS_VOICE_ID")
        
        # ElevenLabsモデルID（環境変数から読み込む、なければデフォルト値）
        from .constants import ELEVENLABS_MODEL_ID
        self.elevenlabs_model_id: str = os.getenv("ELEVENLABS_MODEL_ID", ELEVENLABS_MODEL_ID)
        
        # 動画設定（環境変数から読み込む、なければデフォルト値）
        self.video_width: int = int(os.getenv("VIDEO_WIDTH", VIDEO_WIDTH))
        self.video_height: int = int(os.getenv("VIDEO_HEIGHT", VIDEO_HEIGHT))
        self.video_fps: int = int(os.getenv("VIDEO_FPS", VIDEO_FPS))
        self.video_bitrate: int = int(os.getenv("VIDEO_BITRATE", VIDEO_BITRATE))
        
        # 出力ディレクトリ（環境変数から読み込む、なければデフォルト値）
        output_base_dir = os.getenv("OUTPUT_BASE_DIR", str(OUTPUT_DIR))
        self.output_dir = Path(output_base_dir)
        self.output_scripts_dir = self.output_dir / "scripts"
        self.output_audio_dir = self.output_dir / "audio"
        self.output_images_dir = self.output_dir / "images"
        self.output_videos_dir = self.output_dir / "videos"
        self.output_stock_images_dir = self.output_dir / "stock_images"
        
        # ログ設定
        self.log_dir = Path(os.getenv("LOG_DIR", str(LOG_DIR)))
        self.log_level = os.getenv("LOG_LEVEL", LOG_LEVEL)
        
        # 出力ディレクトリを作成
        self._create_output_directories()
    
    def _create_output_directories(self):
        """出力ディレクトリを作成"""
        directories = [
            self.output_dir,
            self.output_scripts_dir,
            self.output_audio_dir,
            self.output_images_dir,
            self.output_videos_dir,
            self.output_stock_images_dir,
            self.log_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate_api_keys(self) -> tuple[bool, list[str]]:
        """
        APIキーの検証
        
        Returns:
            tuple[bool, list[str]]: (すべてのキーが設定されているか, 不足しているキーのリスト)
        """
        missing_keys = []
        
        if not self.openai_api_key:
            missing_keys.append("OPENAI_API_KEY")
        
        if not self.elevenlabs_api_key:
            missing_keys.append("ELEVENLABS_API_KEY")
        
        if not self.elevenlabs_voice_id:
            missing_keys.append("ELEVENLABS_VOICE_ID")
        
        return len(missing_keys) == 0, missing_keys
    
    def get_video_config(self) -> dict:
        """動画設定を辞書形式で取得"""
        return {
            "width": self.video_width,
            "height": self.video_height,
            "fps": self.video_fps,
            "bitrate": self.video_bitrate,
        }


# グローバル設定インスタンス
config = Config()
