"""
画像生成モジュール
DALL-E 3を使用して画像を生成
"""
from typing import Optional
from pathlib import Path
from openai import OpenAI
from PIL import Image
import io
import requests
import base64

from config.config import config
from config.constants import (
    OPENAI_MODEL,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_SIZE,
    OPENAI_IMAGE_QUALITY,
    OPENAI_IMAGE_STYLE,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    IMAGE_FORMAT
)
from utils.file_manager import file_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """画像生成クラス"""
    
    def __init__(self):
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")
        
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = OPENAI_IMAGE_MODEL
        self.size = OPENAI_IMAGE_SIZE
        self.quality = OPENAI_IMAGE_QUALITY
        self.style = OPENAI_IMAGE_STYLE  # 実写風画像生成用
        self.text_model = OPENAI_MODEL  # GPT-4o（画像分析用）
    
    def sanitize_prompt(self, prompt: str) -> str:
        """
        プロンプトを安全フィルタに引っかからないようにサニタイズ
        
        Args:
            prompt: 元のプロンプト
        
        Returns:
            str: サニタイズされたプロンプト
        """
        logger.info("プロンプトのサニタイズを開始")
        
        try:
            response = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {
                        "role": "system",
                        "content": """あなたは画像生成プロンプトの専門家です。与えられたプロンプトを、DALL-E 3のコンテンツポリシーに準拠しつつ、意図を最大限に保った形で書き換えてください。

以下の点に注意してください：
- 暴力的、性的、違法な内容を含む表現は、安全で適切な表現に置き換える
- 具体的な人物名やブランド名は、一般的な表現に置き換える
- 意図や雰囲気は可能な限り保持する
- 絵画、イラスト、写真などの表現スタイルは維持する
- 色彩、構図、ムードなどの視覚的要素は保持する
- **重要**: 「写真」「実写」「フォト」「フォトリアリスティック」「photorealistic」「photo」「realistic」などの写真・実写に関するキーワードは必ず保持してください。これらは削除や置換をしてはいけません。

出力は、サニタイズされたプロンプトのみを返してください。説明やコメントは不要です。"""
                    },
                    {
                        "role": "user",
                        "content": f"以下のプロンプトをサニタイズしてください：\n\n{prompt}"
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            sanitized_prompt = response.choices[0].message.content.strip()
            logger.info(f"プロンプトのサニタイズが完了しました（元: {len(prompt)}文字 → 新: {len(sanitized_prompt)}文字）")
            return sanitized_prompt
        
        except Exception as e:
            logger.warning(f"プロンプトのサニタイズに失敗しました。元のプロンプトを使用します: {e}")
            return prompt
    
    def analyze_reference_image(self, image_path: Path) -> str:
        """
        参考画像を分析して、トンマナやタッチを言語化
        
        Args:
            image_path: 参考画像のパス
        
        Returns:
            str: 言語化されたトンマナ・タッチの説明
        """
        logger.info(f"参考画像の分析を開始: {image_path}")
        
        try:
            # 画像をbase64エンコード
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # GPT-4oで画像を分析
            response = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは画像分析の専門家です。画像のトンマナ（トーン&マナー）、タッチ、スタイル、色彩、構図などを詳しく分析し、言語化してください。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """以下の画像を詳しく分析して、以下の観点からトンマナやタッチを言語化してください：

1. **色彩**: 色調、彩度、明度、配色パレット
2. **タッチ**: 描画スタイル、筆触、質感
3. **構図**: レイアウト、構図の特徴
4. **トーン**: 全体的な雰囲気、ムード
5. **スタイル**: アートスタイル、ジャンル

これらの情報を、画像生成プロンプトに活用できるように、具体的で詳細な形で記述してください。"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            analysis = response.choices[0].message.content
            logger.info("参考画像の分析が完了しました")
            return analysis
        
        except Exception as e:
            logger.error(f"参考画像の分析に失敗しました: {e}")
            raise
    
    def generate_image(
        self,
        prompt: str,
        scene_number: Optional[int] = None,
        size: Optional[str] = None,
        style_description: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> Image.Image:
        """
        プロンプトから画像を生成
        
        Args:
            prompt: 画像生成用プロンプト
            scene_number: シーン番号（ログ用）
            size: 画像サイズ（デフォルトは設定値）
            style_description: 参考画像から抽出したスタイル説明（オプション）
            instruction: 追加の画像生成指示（オプション）
        
        Returns:
            Image.Image: 生成された画像（PIL Image）
        """
        logger.info(f"画像生成を開始: シーン={scene_number}, プロンプト長={len(prompt)}文字")
        
        image_size = size or self.size
        
        # プロンプトを構築（参考画像のスタイル説明は含めない - 参考のみ）
        final_prompt = prompt
        
        # 追加指示がある場合はプロンプトに追加（余計な装飾テキストなし）
        if instruction:
            final_prompt = f"{final_prompt}\n{instruction}"
        
        # プロンプトをサニタイズ（安全フィルタ回避）- 一時的に無効化
        # final_prompt = self.sanitize_prompt(final_prompt)
        
        try:
            # DALL-E 3で画像を生成
            response = self.client.images.generate(
                model=self.model,
                prompt=final_prompt,
                size=image_size,
                quality=self.quality,
                style=self.style,  # 実写風画像生成用（natural）
                n=1
            )
            
            # 画像URLを取得
            image_url = response.data[0].url
            
            # URLから画像をダウンロード
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # PIL Imageに変換
            image = Image.open(io.BytesIO(image_response.content))
            
            logger.info(f"画像生成が完了しました: シーン={scene_number}")
            return image
        
        except Exception as e:
            logger.error(f"画像生成に失敗しました: {e}")
            raise
    
    def generate_image_file(
        self,
        prompt: str,
        scene_number: Optional[int] = None,
        filename: Optional[str] = None,
        resize_to_video_size: bool = True,
        style_description: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> Path:
        """
        プロンプトから画像ファイルを生成して保存
        
        Args:
            prompt: 画像生成用プロンプト
            scene_number: シーン番号（ファイル名生成用）
            filename: ファイル名（Noneの場合は自動生成）
            resize_to_video_size: 動画サイズ（1080x1920）にリサイズするか
            style_description: 参考画像から抽出したスタイル説明（オプション）
            instruction: 追加の画像生成指示（オプション）
        
        Returns:
            Path: 保存された画像ファイルのパス
        """
        # 画像を生成
        image = self.generate_image(prompt, scene_number, style_description=style_description, instruction=instruction)
        
        # 動画サイズにリサイズ（必要に応じて）
        if resize_to_video_size:
            image = self._resize_to_video_size(image)
        
        # ファイル名を生成
        if filename is None:
            filename = file_manager.generate_filename(
                prefix="image",
                extension=IMAGE_FORMAT,
                scene_number=scene_number
            )
        
        # ファイルパスを取得
        filepath = file_manager.get_image_path(filename)
        
        # ファイルに保存
        try:
            image.save(filepath, format=IMAGE_FORMAT.upper())
            logger.info(f"画像ファイルを保存しました: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"画像ファイルの保存に失敗しました: {e}")
            raise
    
    def _resize_to_video_size(self, image: Image.Image) -> Image.Image:
        """
        画像を動画サイズ（1080x1920）にリサイズ
        
        Args:
            image: 元の画像
        
        Returns:
            Image.Image: リサイズされた画像
        """
        target_size = (VIDEO_WIDTH, VIDEO_HEIGHT)
        
        # アスペクト比を維持しながらリサイズ
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # 背景を黒で埋める（9:16形式）
        resized_image = Image.new("RGB", target_size, (0, 0, 0))
        
        # 画像を中央に配置
        x_offset = (target_size[0] - image.size[0]) // 2
        y_offset = (target_size[1] - image.size[1]) // 2
        resized_image.paste(image, (x_offset, y_offset))
        
        return resized_image
    
    def generate_script_images(
        self,
        script_data: dict,
        resize_to_video_size: bool = True,
        style_description: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> dict[str, Path]:
        """
        台本の全シーンの画像を生成
        
        Args:
            script_data: 台本データ（JSON形式）
            resize_to_video_size: 動画サイズにリサイズするか
            style_description: 参考画像から抽出したスタイル説明（オプション）
            instruction: 追加の画像生成指示（オプション）
        
        Returns:
            dict[str, Path]: {シーン番号: ファイルパス}の辞書
        """
        logger.info("台本全体の画像生成を開始")
        
        image_files = {}
        scenes = script_data.get("scenes", [])
        
        for scene in scenes:
            scene_number = scene.get("scene_number")
            image_prompt = scene.get("image_prompt", "")
            
            if not image_prompt:
                logger.warning(f"シーン{scene_number}のimage_promptが空です。スキップします。")
                continue
            
            try:
                filepath = self.generate_image_file(
                    prompt=image_prompt,
                    scene_number=scene_number,
                    resize_to_video_size=resize_to_video_size,
                    style_description=style_description,
                    instruction=instruction
                )
                image_files[str(scene_number)] = filepath
                logger.info(f"シーン{scene_number}の画像生成が完了しました")
            
            except Exception as e:
                logger.error(f"シーン{scene_number}の画像生成に失敗しました: {e}")
                raise
        
        logger.info(f"台本全体の画像生成が完了しました: {len(image_files)}個のファイル")
        return image_files
