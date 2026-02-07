"""
動画編集モジュール
MoviePyを使用して動画を生成
"""
from typing import Optional, Dict, Callable
from pathlib import Path
import random

# Pillow 10.0.0以降との互換性パッチ
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# editor 経由だと audio.fx.all → decorators の読み込みで環境によってはエラーになるため、
# 必要最小限をサブモジュールから直接インポート
from moviepy.video.VideoClip import ImageClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.AudioClip import CompositeAudioClip, concatenate_audioclips
from moviepy.audio.fx.volumex import volumex
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.fx.resize import resize as _resize_fx


def resize_fx(clip, *args, **kwargs):
    """resize を適用。clip に ismask がない場合の AttributeError を防ぐ。"""
    if not hasattr(clip, "ismask"):
        clip.ismask = False
    return _resize_fx(clip, *args, **kwargs)
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# アニメーション効果の定義
ANIMATION_TYPES = [
    "zoom_in",      # ゆっくりズームアップ
    "slide_left",   # 右から左へスライド
    "slide_right",  # 左から右へスライド
    "slide_up",     # 下から上へスライド
    "slide_down",   # 上から下へスライド
]

from config.config import config
from config.constants import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_WIDTH_LONG,
    VIDEO_HEIGHT_LONG,
    VIDEO_FPS,
    VIDEO_BITRATE,
    VIDEO_FORMAT
)
from utils.file_manager import file_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def _ensure_ismask(clip):
    """MoviePy の blit/resize で参照される ismask が無い場合に付与する。"""
    if clip is not None and not hasattr(clip, "ismask"):
        clip.ismask = False
    return clip


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
        bg_video_path: Optional[Path] = None,
        enable_animation: bool = False,
        animation_scale: float = 1.2,
        animation_types: Optional[Dict[str, str]] = None,
        bgm_path: Optional[Path] = None,
        bgm_volume: float = 0.1,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        video_width: Optional[int] = None,
        video_height: Optional[int] = None
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
            enable_animation: 画像アニメーションを有効にするか
            animation_scale: アニメーションのスケール（ズーム/移動量）
            animation_types: {シーン番号: アニメーションタイプ}の辞書（Noneの場合はランダム）
            bgm_path: BGMファイルのパス（Noneの場合はBGMなし）
            bgm_volume: BGMの音量（0.0-1.0、デフォルト: 0.1）
            video_width: 出力動画の幅（Noneの場合はショート 1080、長尺時は 1920）
            video_height: 出力動画の高さ（Noneの場合はショート 1920、長尺時は 1080）
        
        Returns:
            Path: 生成された動画ファイルのパス
        """
        logger.info("動画生成を開始")
        # 動画サイズの設定（長尺指定時は 1920x1080、未指定時はショート 1080x1920）
        if video_width is not None and video_height is not None:
            self.width, self.height = video_width, video_height
        else:
            self.width, self.height = VIDEO_WIDTH, VIDEO_HEIGHT

        scenes = script_data.get("scenes", [])
        if not scenes:
            raise ValueError("台本にシーンがありません")

        # 進捗管理
        # ステップ数の計算：シーン数 + 結合(1) + 背景動画(条件付き1) + BGM(条件付き1) + 書き出し(1)
        base_steps = len(scenes) + 1 + 1  # シーン数 + 結合 + 書き出し
        if bg_video_path and bg_video_path.exists():
            base_steps += 1  # 背景動画
        if bgm_path and bgm_path.exists():
            base_steps += 1  # BGM
        total_steps = base_steps
        current_step = 0
        
        def update_progress(message: str, step_increment: int = 1):
            """進捗を更新"""
            nonlocal current_step
            current_step += step_increment
            progress = min(current_step / total_steps, 1.0)  # 1.0を超えないように制限
            if progress_callback:
                progress_callback(message, progress)
        
        # 字幕スタイルのデフォルト設定
        if subtitle_style is None:
            subtitle_style = {
                "fontsize": 60,
                "color": "white",
                "font": "Arial-Bold",
                "stroke_color": "black",
                "stroke_width": 2,
                "method": "caption",
                "size": (self.width - 100, None),
                "align": "center"
            }
        
        video_clips = []
        previous_animation_type = None  # 前のシーンのアニメーションタイプを記録
        
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
                # 音声クリップの読み込み（先に読み込んでdurationを取得）
                audio_clip = AudioFileClip(str(audio_path))
                actual_duration = audio_clip.duration
                
                # 画像クリップの作成
                image_clip = ImageClip(str(image_path))
                
                # アニメーションの適用
                animation_type = None
                if enable_animation:
                    # アニメーションタイプの決定
                    if animation_types is not None:
                        # 個別指定モード：animation_types辞書に含まれているシーンのみアニメーションを適用
                        if scene_key in animation_types:
                            animation_type = animation_types[scene_key]
                            if animation_type:  # None（「なし」）の場合はアニメーションを適用しない
                                previous_animation_type = animation_type  # 次のシーンのために記録
                                logger.info(f"シーン{scene_number}にアニメーション適用: {animation_type}")
                                # アニメーション付きクリップを作成
                                image_clip = self._apply_animation(
                                    image_clip,
                                    animation_type,
                                    actual_duration,
                                    animation_scale
                                )
                            else:
                                # 「なし」が選択された場合はアニメーションなし（前のアニメーションは保持）
                                image_clip = resize_fx(image_clip, (self.width, self.height))
                        else:
                            # 個別指定モードで設定されていないシーンはアニメーションなし（前のアニメーションは保持）
                            image_clip = resize_fx(image_clip, (self.width, self.height))
                    else:
                        # ランダムモード：ランダムにアニメーションタイプを選択（前のシーンと異なるものを選択）
                        available_animations = [
                            anim for anim in ANIMATION_TYPES 
                            if anim != previous_animation_type
                        ]
                        # 前のシーンと同じアニメーションしか残っていない場合は全種類から選択
                        if not available_animations:
                            available_animations = ANIMATION_TYPES
                        
                        animation_type = random.choice(available_animations)
                        previous_animation_type = animation_type  # 次のシーンのために記録
                        logger.info(f"シーン{scene_number}にアニメーション適用: {animation_type}")
                        # アニメーション付きクリップを作成
                        image_clip = self._apply_animation(
                            image_clip,
                            animation_type,
                            actual_duration,
                            animation_scale
                        )
                else:
                    # アニメーションなしの場合は通常のリサイズ
                    image_clip = resize_fx(image_clip, (self.width, self.height))
                    previous_animation_type = None  # アニメーションなしの場合はリセット
                
                # 音声の長さに合わせて画像の長さを調整
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
                        _ensure_ismask(video_clip)
                        _ensure_ismask(subtitle_clip)
                        video_clip = CompositeVideoClip([video_clip, subtitle_clip])
                
                video_clips.append(video_clip)
                animation_info = f", アニメーション: {animation_type}" if enable_animation and animation_type else ""
                logger.info(f"シーン{scene_number}の動画クリップを作成しました（長さ: {actual_duration:.2f}秒{animation_info}）")
                update_progress(f"シーン{scene_number}/{len(scenes)}の処理が完了しました", 1)
            
            except Exception as e:
                logger.error(f"シーン{scene_number}の動画クリップ作成に失敗しました: {e}")
                raise
        
        if not video_clips:
            raise ValueError("動画クリップが作成されませんでした")
        
        # すべてのクリップを結合
        logger.info(f"{len(video_clips)}個のクリップを結合します")
        update_progress("動画クリップを結合中...", 0)
        final_video = concatenate_videoclips(video_clips, method="compose")
        update_progress("動画クリップの結合が完了しました", 1)
        
        # 背景動画の合成
        bg_video_clip = None
        if bg_video_path and bg_video_path.exists():
            try:
                logger.info(f"背景動画を読み込みます: {bg_video_path}")
                update_progress("背景動画を処理中...", 0)
                bg_video_clip = VideoFileClip(str(bg_video_path))
                
                # 背景動画をリサイズ
                bg_video_clip = resize_fx(bg_video_clip, (self.width, self.height))
                
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
                update_progress("背景動画の合成が完了しました", 1)
                
            except Exception as e:
                logger.error(f"背景動画の処理に失敗しました: {e}")
                # 背景動画の処理に失敗しても、元の動画は生成する
                logger.warning("背景動画なしで動画を生成します")
        
        # BGMの追加
        if bgm_path and bgm_path.exists():
            try:
                logger.info(f"BGMを読み込みます: {bgm_path}")
                update_progress("BGMを処理中...", 0)
                bgm_clip = AudioFileClip(str(bgm_path))
                
                # 最終動画の長さを取得
                total_duration = final_video.duration
                
                # BGMをループさせて必要な長さにする（音声クリップは concatenate_audioclips を使用）
                if bgm_clip.duration < total_duration:
                    # ループ回数を計算
                    loop_count = int(total_duration / bgm_clip.duration) + 1
                    logger.info(f"BGMをループします（{loop_count}回）")
                    
                    # ループさせたBGMを作成（音声クリップ用の結合）
                    bgm_clips = [bgm_clip] * loop_count
                    bgm_looped = concatenate_audioclips(bgm_clips)
                    bgm_looped = bgm_looped.subclip(0, total_duration)
                else:
                    # BGMが十分長い場合はそのまま使用
                    bgm_looped = bgm_clip.subclip(0, total_duration)
                
                # BGMの音量を調整（サブモジュール直接利用のため volumex を関数で適用）
                bgm_looped = volumex(bgm_looped, bgm_volume)
                
                # 元の音声とBGMを合成
                logger.info(f"BGMを合成します（音量: {bgm_volume}）")
                if final_video.audio is not None:
                    # 元の音声とBGMを合成
                    final_audio = CompositeAudioClip([final_video.audio, bgm_looped])
                    final_video = final_video.set_audio(final_audio)
                else:
                    # 元の音声がない場合はBGMのみ
                    final_video = final_video.set_audio(bgm_looped)
                
                logger.info("BGMの合成が完了しました")
                update_progress("BGMの合成が完了しました", 1)
                
            except Exception as e:
                logger.error(f"BGMの処理に失敗しました: {e}")
                # BGMの処理に失敗しても、元の動画は生成する
                logger.warning("BGMなしで動画を生成します")
        
        # 出力ファイル名の生成
        if output_filename is None:
            output_filename = file_manager.generate_filename(
                prefix="video",
                extension=VIDEO_FORMAT
            )
        
        output_path = file_manager.get_video_path(output_filename)
        
        # 動画を書き出し
        try:
            update_progress("動画ファイルを書き出し中...（この処理には時間がかかります）", 0)
            final_video.write_videofile(
                str(output_path),
                fps=self.fps,
                bitrate=f"{self.bitrate // 1000000}M",
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                logger=None  # MoviePyのログを無効化
            )
            
            update_progress("動画の生成が完了しました！", 1)
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
    
    def _apply_animation(
        self,
        clip: ImageClip,
        animation_type: str,
        duration: float,
        scale: float = 1.2
    ) -> ImageClip:
        """
        画像クリップにアニメーション効果を適用
        
        Args:
            clip: 元の画像クリップ
            animation_type: アニメーションの種類
            duration: 動画の長さ（秒）
            scale: スケール係数（ズーム量や移動量に影響）
        
        Returns:
            ImageClip: アニメーション適用後のクリップ
        """
        # スケール係数（ズームや移動のために少し大きくする）
        scaled_width = int(self.width * scale)
        scaled_height = int(self.height * scale)
        
        # 画像を拡大（アニメーション用の余白を確保）
        clip = resize_fx(clip, (scaled_width, scaled_height))
        
        # 移動量の計算
        move_x = (scaled_width - self.width) // 2
        move_y = (scaled_height - self.height) // 2
        
        # 出力サイズ（クロップ後のサイズ）
        output_width = self.width
        output_height = self.height
        
        if animation_type == "zoom_in":
            # ゆっくりズームアップ（中央から拡大）
            def zoom_effect(get_frame, t):
                # 時間に応じてズーム量を計算（1.0 -> scale）
                progress = t / duration
                current_scale = 1.0 + (scale - 1.0) * progress
                
                # 現在のフレームを取得
                frame = get_frame(t)
                
                # フレームをPIL Imageに変換
                img = Image.fromarray(frame)
                
                # 現在のスケールに応じてクロップ
                crop_w = int(output_width / current_scale * scale)
                crop_h = int(output_height / current_scale * scale)
                
                # 中央からクロップ
                left = (scaled_width - crop_w) // 2
                top = (scaled_height - crop_h) // 2
                right = left + crop_w
                bottom = top + crop_h
                
                img = img.crop((left, top, right, bottom))
                img = img.resize((output_width, output_height), Image.LANCZOS)
                
                return np.array(img)
            
            return clip.fl(zoom_effect, apply_to=['mask'])
        
        elif animation_type == "slide_left":
            # 右から左へスライド（フレームごとにクロップ）
            def slide_left_effect(get_frame, t):
                progress = t / duration
                offset_x = int(move_x * (1 - 2 * progress))  # 右から左へ
                
                frame = get_frame(t)
                img = Image.fromarray(frame)
                
                # オフセットに基づいてクロップ
                left = move_x - offset_x
                top = move_y
                right = left + output_width
                bottom = top + output_height
                
                img = img.crop((left, top, right, bottom))
                return np.array(img)
            
            return clip.fl(slide_left_effect, apply_to=['mask'])
        
        elif animation_type == "slide_right":
            # 左から右へスライド（フレームごとにクロップ）
            def slide_right_effect(get_frame, t):
                progress = t / duration
                offset_x = int(-move_x + move_x * 2 * progress)  # 左から右へ
                
                frame = get_frame(t)
                img = Image.fromarray(frame)
                
                # オフセットに基づいてクロップ
                left = move_x - offset_x
                top = move_y
                right = left + output_width
                bottom = top + output_height
                
                img = img.crop((left, top, right, bottom))
                return np.array(img)
            
            return clip.fl(slide_right_effect, apply_to=['mask'])
        
        elif animation_type == "slide_up":
            # 下から上へスライド（フレームごとにクロップ）
            def slide_up_effect(get_frame, t):
                progress = t / duration
                offset_y = int(move_y * (1 - 2 * progress))  # 下から上へ
                
                frame = get_frame(t)
                img = Image.fromarray(frame)
                
                # オフセットに基づいてクロップ
                left = move_x
                top = move_y - offset_y
                right = left + output_width
                bottom = top + output_height
                
                img = img.crop((left, top, right, bottom))
                return np.array(img)
            
            return clip.fl(slide_up_effect, apply_to=['mask'])
        
        elif animation_type == "slide_down":
            # 上から下へスライド（フレームごとにクロップ）
            def slide_down_effect(get_frame, t):
                progress = t / duration
                offset_y = int(-move_y + move_y * 2 * progress)  # 上から下へ
                
                frame = get_frame(t)
                img = Image.fromarray(frame)
                
                # オフセットに基づいてクロップ
                left = move_x
                top = move_y - offset_y
                right = left + output_width
                bottom = top + output_height
                
                img = img.crop((left, top, right, bottom))
                return np.array(img)
            
            return clip.fl(slide_down_effect, apply_to=['mask'])
        
        else:
            # デフォルト：アニメーションなし
            return resize_fx(clip, (self.width, self.height))
    
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
            # 折り返し幅：動画幅から余白と縁取り分を引く（はみ出し防止）
            margin = 100  # 左右の余白（ピクセル）
            stroke_margin = 2 * max(stroke_width, 1)
            max_width = style.get("size", (self.width - 100, None))[0]
            max_width = min(max_width, self.width - margin - stroke_margin)
            
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
            
            # 画像のサイズを計算（動画幅に合わせる：ショート1080 / 長尺1920）
            line_height = int(fontsize * 1.2)
            padding = 20
            img_height = len(lines) * line_height + padding * 2
            img_width = self.width
            
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
            _ensure_ismask(subtitle_clip)
            
            logger.info(f"字幕クリップを作成しました（テキスト: {text[:30]}...）")
            return subtitle_clip
        
        except Exception as e:
            logger.error(f"字幕クリップの作成に失敗しました（テキスト: {text}）: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
