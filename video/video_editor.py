"""
動画編集モジュール
MoviePyを使用して動画を生成
"""
from typing import Optional, Dict
from pathlib import Path

# Pillow 10.0.0以降との互換性パッチ
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    VideoFileClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from moviepy.video.fx import resize
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config.config import config
from config.constants import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    VIDEO_BITRATE,
    VIDEO_FORMAT
)
from utils.file_manager import file_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class VideoEditor:
    """動画編集クラス"""
    
    def __init__(self):
        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT
        self.fps = VIDEO_FPS
        self.bitrate = VIDEO_BITRATE
    
    def create_video_from_script(
        self,
        script_data: dict,
        image_files: Dict[str, Path],
        audio_files: Dict[str, Path],
        output_filename: Optional[str] = None,
        add_subtitles: bool = True,
        subtitle_style: Optional[dict] = None,
        subtitle_source: str = "subtitle",
        subtitle_bottom_offset: int = 50,
        bg_video_path: Optional[Path] = None
    ) -> Path:
        """
        台本データから動画を生成
        
        Args:
            script_data: 台本データ（JSON形式）
            image_files: {シーン番号: 画像ファイルパス}の辞書
            audio_files: {シーン番号: 音声ファイルパス}の辞書
            output_filename: 出力ファイル名（Noneの場合は自動生成）
            add_subtitles: 字幕を追加するか
            subtitle_style: 字幕のスタイル設定
            subtitle_source: 字幕のソース（"subtitle"=見出し, "dialogue"=セリフ）
            subtitle_bottom_offset: 字幕の下からのオフセット（ピクセル）
            bg_video_path: 背景動画のパス（Noneの場合は背景動画なし）
        
        Returns:
            Path: 生成された動画ファイルのパス
        """
        logger.info("動画生成を開始")
        
        scenes = script_data.get("scenes", [])
        if not scenes:
            raise ValueError("台本にシーンがありません")
        
        # 字幕スタイルのデフォルト設定
        if subtitle_style is None:
            subtitle_style = {
                "fontsize": 60,
                "color": "white",
                "font": "Arial-Bold",
                "stroke_color": "black",
                "stroke_width": 2,
                "method": "caption",
                "size": (VIDEO_WIDTH - 100, None),
                "align": "center"
            }
        
        video_clips = []
        
        for scene in scenes:
            scene_number = scene.get("scene_number")
            scene_key = str(scene_number)
            duration = scene.get("duration", 3.0)
            # 字幕のソースに応じてテキストを取得
            subtitle_text = scene.get(subtitle_source, "")
            
            # 画像ファイルの取得
            image_path = image_files.get(scene_key)
            if not image_path or not image_path.exists():
                logger.warning(f"シーン{scene_number}の画像ファイルが見つかりません: {image_path}")
                continue
            
            # 音声ファイルの取得
            audio_path = audio_files.get(scene_key)
            if not audio_path or not audio_path.exists():
                logger.warning(f"シーン{scene_number}の音声ファイルが見つかりません: {audio_path}")
                continue
            
            try:
                # 画像クリップの作成
                image_clip = ImageClip(str(image_path))
                image_clip = image_clip.resize((self.width, self.height))
                
                # 音声クリップの読み込み
                audio_clip = AudioFileClip(str(audio_path))
                
                # 音声の長さに合わせて画像の長さを調整
                actual_duration = audio_clip.duration
                image_clip = image_clip.set_duration(actual_duration)
                
                # 音声を画像に設定
                video_clip = image_clip.set_audio(audio_clip)
                
                # 字幕を追加
                if add_subtitles and subtitle_text:
                    subtitle_clip = self._create_subtitle_clip(
                        subtitle_text,
                        actual_duration,
                        subtitle_style,
                        subtitle_bottom_offset
                    )
                    # 字幕クリップが正常に作成された場合のみ合成
                    if subtitle_clip is not None:
                        video_clip = CompositeVideoClip([video_clip, subtitle_clip])
                
                video_clips.append(video_clip)
                logger.info(f"シーン{scene_number}の動画クリップを作成しました（長さ: {actual_duration:.2f}秒）")
            
            except Exception as e:
                logger.error(f"シーン{scene_number}の動画クリップ作成に失敗しました: {e}")
                raise
        
        if not video_clips:
            raise ValueError("動画クリップが作成されませんでした")
        
        # すべてのクリップを結合
        logger.info(f"{len(video_clips)}個のクリップを結合します")
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # 背景動画の合成
        bg_video_clip = None
        if bg_video_path and bg_video_path.exists():
            try:
                logger.info(f"背景動画を読み込みます: {bg_video_path}")
                bg_video_clip = VideoFileClip(str(bg_video_path))
                
                # 背景動画をリサイズ
                bg_video_clip = bg_video_clip.resize((self.width, self.height))
                
                # 最終動画の長さを取得
                total_duration = final_video.duration
                
                # 背景動画をループさせて必要な長さにする
                if bg_video_clip.duration < total_duration:
                    # ループ回数を計算
                    loop_count = int(total_duration / bg_video_clip.duration) + 1
                    logger.info(f"背景動画をループします（{loop_count}回）")
                    
                    # ループさせた背景動画を作成
                    bg_clips = [bg_video_clip] * loop_count
                    bg_video_looped = concatenate_videoclips(bg_clips)
                    bg_video_looped = bg_video_looped.subclip(0, total_duration)
                else:
                    # 背景動画が十分長い場合はそのまま使用
                    bg_video_looped = bg_video_clip.subclip(0, total_duration)
                
                # 背景動画の音声を削除（元の音声を保持するため）
                bg_video_looped = bg_video_looped.without_audio()
                
                # 背景動画の上にメイン動画を合成
                logger.info("背景動画とメイン動画を合成します")
                final_video = CompositeVideoClip([bg_video_looped, final_video])
                
            except Exception as e:
                logger.error(f"背景動画の処理に失敗しました: {e}")
                # 背景動画の処理に失敗しても、元の動画は生成する
                logger.warning("背景動画なしで動画を生成します")
        
        # 出力ファイル名の生成
        if output_filename is None:
            output_filename = file_manager.generate_filename(
                prefix="video",
                extension=VIDEO_FORMAT
            )
        
        output_path = file_manager.get_video_path(output_filename)
        
        # 動画を書き出し
        try:
            final_video.write_videofile(
                str(output_path),
                fps=self.fps,
                bitrate=f"{self.bitrate // 1000000}M",
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                logger=None  # MoviePyのログを無効化
            )
            
            logger.info(f"動画を生成しました: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"動画の書き出しに失敗しました: {e}")
            raise
        
        finally:
            # リソースを解放
            final_video.close()
            for clip in video_clips:
                clip.close()
            if bg_video_clip is not None:
                bg_video_clip.close()
    
    def _create_subtitle_clip(
        self,
        text: str,
        duration: float,
        style: dict,
        bottom_offset: int = 50
    ) -> Optional[ImageClip]:
        """
        字幕クリップを作成（PILを使用）
        
        Args:
            text: 字幕テキスト
            duration: 字幕の表示時間（秒）
            style: 字幕のスタイル設定
            bottom_offset: 下からのオフセット（ピクセル）
        
        Returns:
            ImageClip: 字幕クリップ
        """
        try:
            fontsize = style.get("fontsize", 60)
            text_color = style.get("color", "white")
            stroke_color = style.get("stroke_color", "black")
            stroke_width = style.get("stroke_width", 2)
            max_width = style.get("size", (VIDEO_WIDTH - 100, None))[0]
            
            # フォントの読み込み（日本語対応フォントを優先）
            font = None
            font_paths = [
                # macOSの日本語フォント（優先順位順）
                "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",  # 太字
                "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",  # 通常
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
            
            for font_path in font_paths:
                try:
                    if font_path.endswith('.ttc'):
                        # TTCファイルの場合はフォントインデックスを指定
                        font = ImageFont.truetype(font_path, fontsize, index=0)
                    else:
                        font = ImageFont.truetype(font_path, fontsize)
                    logger.info(f"フォントを読み込みました: {font_path}")
                    break
                except Exception as e:
                    logger.debug(f"フォント読み込み失敗: {font_path} - {e}")
                    continue
            
            if font is None:
                # デフォルトフォントを使用（日本語非対応の可能性あり）
                try:
                    font = ImageFont.load_default()
                    logger.warning("デフォルトフォントを使用します（日本語が表示されない可能性があります）")
                except:
                    font = None
            
            # テキストのサイズを計算
            if font:
                # テキストを折り返す（日本語対応）
                lines = []
                current_line = ""
                
                # 日本語は文字単位、英語は単語単位で処理
                for char in text:
                    test_line = current_line + char
                    bbox = font.getbbox(test_line)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_width <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        # 現在の文字が1文字でも幅を超える場合は強制的に追加
                        if current_line == "":
                            current_line = char
                        else:
                            current_line = char
                
                if current_line:
                    lines.append(current_line)
            else:
                lines = [text]
            
            # 画像のサイズを計算
            line_height = int(fontsize * 1.2)
            padding = 20
            img_height = len(lines) * line_height + padding * 2
            img_width = VIDEO_WIDTH
            
            # 透明な画像を作成
            img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # テキストを描画
            y_offset = padding
            for line in lines:
                if not line:
                    continue
                
                # テキストの位置を計算（中央揃え）
                if font:
                    bbox = font.getbbox(line)
                    text_width = bbox[2] - bbox[0]
                else:
                    text_width = len(line) * fontsize // 2
                
                x = (img_width - text_width) // 2
                
                # 縁取りを描画
                if stroke_width > 0:
                    for adj in range(-stroke_width, stroke_width + 1):
                        for adj2 in range(-stroke_width, stroke_width + 1):
                            if adj != 0 or adj2 != 0:
                                draw.text(
                                    (x + adj, y_offset + adj2),
                                    line,
                                    font=font,
                                    fill=stroke_color
                                )
                
                # テキストを描画
                draw.text(
                    (x, y_offset),
                    line,
                    font=font,
                    fill=text_color
                )
                
                y_offset += line_height
            
            # PIL Imageをnumpy配列に変換
            img_array = np.array(img)
            
            # ImageClipを作成
            subtitle_clip = ImageClip(img_array)
            subtitle_clip = subtitle_clip.set_duration(duration)
            # 下からのオフセットを考慮した位置を計算
            y_position = self.height - img_height - bottom_offset
            subtitle_clip = subtitle_clip.set_position(("center", y_position))
            
            logger.info(f"字幕クリップを作成しました（テキスト: {text[:30]}...）")
            return subtitle_clip
        
        except Exception as e:
            logger.error(f"字幕クリップの作成に失敗しました（テキスト: {text}）: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
