"""
ファイル管理モジュール
ファイルの保存・読み込み管理
"""
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from config.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """ファイル管理クラス"""
    
    def __init__(self):
        self.output_dir = config.output_dir
        self.scripts_dir = config.output_scripts_dir
        self.audio_dir = config.output_audio_dir
        self.images_dir = config.output_images_dir
        self.videos_dir = config.output_videos_dir
        self.stock_images_dir = config.output_stock_images_dir
    
    def save_script(self, script_data: dict, filename: Optional[str] = None) -> Path:
        """
        台本をJSON形式で保存
        
        Args:
            script_data: 台本データ（辞書形式）
            filename: ファイル名（Noneの場合は自動生成）
        
        Returns:
            Path: 保存されたファイルのパス
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"script_{timestamp}.json"
        
        filepath = self.scripts_dir / filename
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"台本を保存しました: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"台本の保存に失敗しました: {e}")
            raise
    
    def load_script(self, filepath: Path) -> dict:
        """
        台本をJSON形式で読み込み
        
        Args:
            filepath: ファイルパス
        
        Returns:
            dict: 台本データ
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            
            logger.info(f"台本を読み込みました: {filepath}")
            return script_data
        except Exception as e:
            logger.error(f"台本の読み込みに失敗しました: {e}")
            raise
    
    def get_audio_path(self, filename: str) -> Path:
        """
        音声ファイルのパスを取得
        
        Args:
            filename: ファイル名
        
        Returns:
            Path: 音声ファイルのパス
        """
        return self.audio_dir / filename
    
    def get_image_path(self, filename: str) -> Path:
        """
        画像ファイルのパスを取得
        
        Args:
            filename: ファイル名
        
        Returns:
            Path: 画像ファイルのパス
        """
        return self.images_dir / filename
    
    def get_video_path(self, filename: str) -> Path:
        """
        動画ファイルのパスを取得
        
        Args:
            filename: ファイル名
        
        Returns:
            Path: 動画ファイルのパス
        """
        return self.videos_dir / filename
    
    def generate_filename(self, prefix: str, extension: str, scene_number: Optional[int] = None) -> str:
        """
        ファイル名を生成
        
        Args:
            prefix: プレフィックス（例: "audio", "image"）
            extension: 拡張子（例: "mp3", "png"）
            scene_number: シーン番号（オプション）
        
        Returns:
            str: 生成されたファイル名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if scene_number is not None:
            filename = f"{prefix}_scene{scene_number:03d}_{timestamp}.{extension}"
        else:
            filename = f"{prefix}_{timestamp}.{extension}"
        
        return filename
    
    def list_scripts(self) -> list[Path]:
        """
        保存されている台本ファイルのリストを取得
        
        Returns:
            list[Path]: 台本ファイルのパスのリスト
        """
        return sorted(self.scripts_dir.glob("*.json"), reverse=True)
    
    def list_audio_files(self) -> list[Path]:
        """
        保存されている音声ファイルのリストを取得
        
        Returns:
            list[Path]: 音声ファイルのパスのリスト
        """
        extensions = ["*.mp3", "*.wav"]
        files = []
        for ext in extensions:
            files.extend(self.audio_dir.glob(ext))
        return sorted(files, reverse=True)
    
    def list_image_files(self) -> list[Path]:
        """
        保存されている画像ファイルのリストを取得
        
        Returns:
            list[Path]: 画像ファイルのパスのリスト
        """
        extensions = ["*.png", "*.jpg", "*.jpeg"]
        files = []
        for ext in extensions:
            files.extend(self.images_dir.glob(ext))
        return sorted(files, reverse=True)
    
    def list_video_files(self) -> list[Path]:
        """
        保存されている動画ファイルのリストを取得
        
        Returns:
            list[Path]: 動画ファイルのパスのリスト
        """
        return sorted(self.videos_dir.glob("*.mp4"), reverse=True)
    
    def list_stock_images(self) -> list[Path]:
        """
        ストック画像ファイルのリストを取得
        
        Returns:
            list[Path]: ストック画像ファイルのパスのリスト
        """
        extensions = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
        files = []
        for ext in extensions:
            files.extend(self.stock_images_dir.glob(ext))
        return sorted(files)
    
    def ensure_directory_exists(self, directory: Path):
        """
        ディレクトリが存在することを確認（存在しない場合は作成）
        
        Args:
            directory: ディレクトリのパス
        """
        directory.mkdir(parents=True, exist_ok=True)


# グローバルファイルマネージャーインスタンス
file_manager = FileManager()
