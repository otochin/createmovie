"""
音声処理モジュール
音声ファイルの処理・変換
"""
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class AudioProcessor:
    """音声処理クラス"""
    
    @staticmethod
    def get_audio_duration(filepath: Path) -> float:
        """
        音声ファイルの長さを取得
        
        Args:
            filepath: 音声ファイルのパス
        
        Returns:
            float: 音声の長さ（秒）
        """
        try:
            # pydubを使用して音声の長さを取得
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(str(filepath))
            duration = len(audio) / 1000.0  # ミリ秒から秒に変換
            
            logger.debug(f"音声ファイルの長さを取得: {filepath.name} = {duration:.2f}秒")
            return duration
        
        except ImportError:
            logger.warning("pydubがインストールされていません。音声の長さを取得できません。")
            return 0.0
        
        except Exception as e:
            logger.error(f"音声ファイルの長さ取得に失敗しました: {e}")
            return 0.0
    
    @staticmethod
    def validate_audio_file(filepath: Path) -> bool:
        """
        音声ファイルが有効かどうかを検証
        
        Args:
            filepath: 音声ファイルのパス
        
        Returns:
            bool: ファイルが有効な場合True
        """
        if not filepath.exists():
            logger.error(f"音声ファイルが存在しません: {filepath}")
            return False
        
        if filepath.stat().st_size == 0:
            logger.error(f"音声ファイルが空です: {filepath}")
            return False
        
        # 拡張子のチェック
        valid_extensions = [".mp3", ".wav", ".m4a"]
        if filepath.suffix.lower() not in valid_extensions:
            logger.warning(f"サポートされていない音声形式です: {filepath.suffix}")
        
        return True
