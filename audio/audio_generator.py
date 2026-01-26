"""
音声生成モジュール
ElevenLabs APIを使用して音声を生成
"""
from typing import Optional
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings

from config.config import config
from config.constants import (
    ELEVENLABS_MODEL_ID,
    ELEVENLABS_STABILITY,
    ELEVENLABS_SIMILARITY_BOOST,
    AUDIO_FORMAT
)
from utils.file_manager import file_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class AudioGenerator:
    """音声生成クラス"""
    
    def __init__(self):
        if not config.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEYが設定されていません。.envファイルを確認してください。")
        
        if not config.elevenlabs_voice_id:
            raise ValueError("ELEVENLABS_VOICE_IDが設定されていません。.envファイルを確認してください。")
        
        self.client = ElevenLabs(api_key=config.elevenlabs_api_key)
        self.voice_id = config.elevenlabs_voice_id
        self.model_id = ELEVENLABS_MODEL_ID
    
    def generate_audio(
        self,
        text: str,
        scene_number: Optional[int] = None,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None
    ) -> bytes:
        """
        テキストから音声を生成
        
        Args:
            text: 音声化するテキスト
            scene_number: シーン番号（ファイル名生成用）
            stability: 安定性（0.0-1.0、デフォルトは設定値）
            similarity_boost: 類似度ブースト（0.0-1.0、デフォルトは設定値）
        
        Returns:
            bytes: 音声データ（MP3形式）
        """
        logger.info(f"音声生成を開始: テキスト長={len(text)}文字, シーン={scene_number}")
        
        try:
            # VoiceSettingsの作成
            voice_settings = VoiceSettings(
                stability=stability if stability is not None else ELEVENLABS_STABILITY,
                similarity_boost=similarity_boost if similarity_boost is not None else ELEVENLABS_SIMILARITY_BOOST
            )
            
            # 音声を生成
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                voice_settings=voice_settings
            )
            
            # バイトデータに変換
            audio_data = b"".join(audio_generator)
            
            logger.info("音声生成が完了しました")
            return audio_data
        
        except Exception as e:
            logger.error(f"音声生成に失敗しました: {e}")
            raise
    
    def generate_audio_file(
        self,
        text: str,
        scene_number: Optional[int] = None,
        filename: Optional[str] = None,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None
    ) -> Path:
        """
        テキストから音声ファイルを生成して保存
        
        Args:
            text: 音声化するテキスト
            scene_number: シーン番号（ファイル名生成用）
            filename: ファイル名（Noneの場合は自動生成）
            stability: 安定性（0.0-1.0）
            similarity_boost: 類似度ブースト（0.0-1.0）
        
        Returns:
            Path: 保存された音声ファイルのパス
        """
        # 音声データを生成
        audio_data = self.generate_audio(
            text=text,
            scene_number=scene_number,
            stability=stability,
            similarity_boost=similarity_boost
        )
        
        # ファイル名を生成
        if filename is None:
            filename = file_manager.generate_filename(
                prefix="audio",
                extension=AUDIO_FORMAT,
                scene_number=scene_number
            )
        
        # ファイルパスを取得
        filepath = file_manager.get_audio_path(filename)
        
        # ファイルに保存
        try:
            with open(filepath, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"音声ファイルを保存しました: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"音声ファイルの保存に失敗しました: {e}")
            raise
    
    def generate_script_audios(
        self,
        script_data: dict,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None
    ) -> dict[str, Path]:
        """
        台本の全シーンの音声を生成
        
        Args:
            script_data: 台本データ（JSON形式）
            stability: 安定性（0.0-1.0）
            similarity_boost: 類似度ブースト（0.0-1.0）
        
        Returns:
            dict[str, Path]: {シーン番号: ファイルパス}の辞書
        """
        logger.info("台本全体の音声生成を開始")
        
        audio_files = {}
        scenes = script_data.get("scenes", [])
        
        for scene in scenes:
            scene_number = scene.get("scene_number")
            dialogue = scene.get("dialogue", "")
            
            if not dialogue:
                logger.warning(f"シーン{scene_number}のdialogueが空です。スキップします。")
                continue
            
            try:
                filepath = self.generate_audio_file(
                    text=dialogue,
                    scene_number=scene_number,
                    stability=stability,
                    similarity_boost=similarity_boost
                )
                audio_files[str(scene_number)] = filepath
                logger.info(f"シーン{scene_number}の音声生成が完了しました")
            
            except Exception as e:
                logger.error(f"シーン{scene_number}の音声生成に失敗しました: {e}")
                raise
        
        logger.info(f"台本全体の音声生成が完了しました: {len(audio_files)}個のファイル")
        return audio_files
