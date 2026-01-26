"""
画像処理モジュール
画像のリサイズ・加工
"""
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

from config.constants import VIDEO_WIDTH, VIDEO_HEIGHT
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """画像処理クラス"""
    
    @staticmethod
    def resize_to_video_size(
        image_path: Path,
        output_path: Optional[Path] = None,
        target_size: Tuple[int, int] = (VIDEO_WIDTH, VIDEO_HEIGHT)
    ) -> Path:
        """
        画像を動画サイズにリサイズ
        
        Args:
            image_path: 元の画像ファイルのパス
            output_path: 出力ファイルのパス（Noneの場合は上書き）
            target_size: ターゲットサイズ（デフォルト: 1080x1920）
        
        Returns:
            Path: リサイズされた画像ファイルのパス
        """
        try:
            image = Image.open(image_path)
            
            # アスペクト比を維持しながらリサイズ
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # 背景を黒で埋める（9:16形式）
            resized_image = Image.new("RGB", target_size, (0, 0, 0))
            
            # 画像を中央に配置
            x_offset = (target_size[0] - image.size[0]) // 2
            y_offset = (target_size[1] - image.size[1]) // 2
            resized_image.paste(image, (x_offset, y_offset))
            
            # 保存
            if output_path is None:
                output_path = image_path
            
            resized_image.save(output_path)
            logger.info(f"画像をリサイズしました: {image_path.name} -> {target_size}")
            return output_path
        
        except Exception as e:
            logger.error(f"画像のリサイズに失敗しました: {e}")
            raise
    
    @staticmethod
    def get_image_size(image_path: Path) -> Tuple[int, int]:
        """
        画像のサイズを取得
        
        Args:
            image_path: 画像ファイルのパス
        
        Returns:
            Tuple[int, int]: (幅, 高さ)
        """
        try:
            image = Image.open(image_path)
            return image.size
        except Exception as e:
            logger.error(f"画像サイズの取得に失敗しました: {e}")
            return (0, 0)
    
    @staticmethod
    def validate_image_file(image_path: Path) -> bool:
        """
        画像ファイルが有効かどうかを検証
        
        Args:
            image_path: 画像ファイルのパス
        
        Returns:
            bool: ファイルが有効な場合True
        """
        if not image_path.exists():
            logger.error(f"画像ファイルが存在しません: {image_path}")
            return False
        
        if image_path.stat().st_size == 0:
            logger.error(f"画像ファイルが空です: {image_path}")
            return False
        
        try:
            image = Image.open(image_path)
            image.verify()
            return True
        except Exception as e:
            logger.error(f"画像ファイルが無効です: {e}")
            return False
