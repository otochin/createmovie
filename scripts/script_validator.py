"""
台本検証モジュール
台本の形式と内容を検証
"""
from typing import Optional
import json

from utils.logger import get_logger

logger = get_logger(__name__)


class ScriptValidator:
    """台本検証クラス"""
    
    @staticmethod
    def validate(script_data: dict) -> tuple[bool, Optional[str]]:
        """
        台本データを検証
        
        Args:
            script_data: 台本データ
        
        Returns:
            tuple[bool, Optional[str]]: (検証成功か, エラーメッセージ)
        """
        try:
            # 必須フィールドのチェック
            if "title" not in script_data:
                return False, "titleフィールドがありません"
            
            if "scenes" not in script_data:
                return False, "scenesフィールドがありません"
            
            if not isinstance(script_data["scenes"], list):
                return False, "scenesは配列である必要があります"
            
            if len(script_data["scenes"]) == 0:
                return False, "scenesが空です"
            
            # 各シーンの検証
            for i, scene in enumerate(script_data["scenes"]):
                scene_num = i + 1
                
                if "scene_number" not in scene:
                    return False, f"シーン{scene_num}: scene_numberフィールドがありません"
                
                if "dialogue" not in scene:
                    return False, f"シーン{scene_num}: dialogueフィールドがありません"
                
                if "image_prompt" not in scene:
                    return False, f"シーン{scene_num}: image_promptフィールドがありません"
                
                if "duration" not in scene:
                    return False, f"シーン{scene_num}: durationフィールドがありません"
                
                if "subtitle" not in scene:
                    return False, f"シーン{scene_num}: subtitleフィールドがありません"
                
                # 値の検証
                if not isinstance(scene["dialogue"], str) or len(scene["dialogue"]) == 0:
                    return False, f"シーン{scene_num}: dialogueが空です"
                
                if not isinstance(scene["image_prompt"], str) or len(scene["image_prompt"]) == 0:
                    return False, f"シーン{scene_num}: image_promptが空です"
                
                if not isinstance(scene["duration"], (int, float)) or scene["duration"] <= 0:
                    return False, f"シーン{scene_num}: durationが無効です"
            
            logger.info("台本の検証が成功しました")
            return True, None
        
        except Exception as e:
            logger.error(f"台本の検証中にエラーが発生しました: {e}")
            return False, str(e)
    
    @staticmethod
    def normalize(script_data: dict) -> dict:
        """
        台本データを正規化（型の統一など）
        
        Args:
            script_data: 台本データ
        
        Returns:
            dict: 正規化された台本データ
        """
        normalized = script_data.copy()
        
        # 各シーンの正規化
        for scene in normalized.get("scenes", []):
            # durationをfloatに統一
            if "duration" in scene:
                scene["duration"] = float(scene["duration"])
            
            # scene_numberをintに統一
            if "scene_number" in scene:
                scene["scene_number"] = int(scene["scene_number"])
        
        # total_durationを計算
        total_duration = sum(scene.get("duration", 0) for scene in normalized.get("scenes", []))
        normalized["total_duration"] = total_duration
        
        return normalized
