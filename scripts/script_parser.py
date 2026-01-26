"""
台本パーサーモジュール
JSON台本のパース処理
"""
import json
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from scripts.script_validator import ScriptValidator

logger = get_logger(__name__)


class ScriptParser:
    """台本パーサークラス"""
    
    @staticmethod
    def parse_json(json_string: str) -> dict:
        """
        JSON文字列をパース
        
        Args:
            json_string: JSON文字列
        
        Returns:
            dict: 台本データ
        """
        try:
            script_data = json.loads(json_string)
            logger.info("JSONのパースが成功しました")
            return script_data
        except json.JSONDecodeError as e:
            logger.error(f"JSONのパースに失敗しました: {e}")
            raise ValueError(f"無効なJSON形式です: {e}")
    
    @staticmethod
    def parse_file(filepath: Path) -> dict:
        """
        ファイルから台本を読み込み
        
        Args:
            filepath: ファイルパス
        
        Returns:
            dict: 台本データ
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            
            logger.info(f"ファイルから台本を読み込みました: {filepath}")
            return script_data
        except Exception as e:
            logger.error(f"ファイルの読み込みに失敗しました: {e}")
            raise
    
    @staticmethod
    def validate_and_normalize(script_data: dict) -> dict:
        """
        台本を検証して正規化
        
        Args:
            script_data: 台本データ
        
        Returns:
            dict: 検証済み・正規化された台本データ
        """
        # 検証
        is_valid, error_message = ScriptValidator.validate(script_data)
        if not is_valid:
            raise ValueError(f"台本の検証に失敗しました: {error_message}")
        
        # 正規化
        normalized = ScriptValidator.normalize(script_data)
        
        return normalized
