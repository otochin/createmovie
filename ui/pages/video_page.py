"""
動画編集ページ
"""
import streamlit as st
import json
import random
from pathlib import Path
from typing import Dict

import extra_streamlit_components as stx

from video.video_editor import VideoEditor
from utils.file_manager import file_manager
from utils.logger import get_logger
from config.constants import VIDEO_WIDTH

logger = get_logger(__name__)


def get_cookie_manager():
    """クッキーマネージャーを取得"""
    # セッションステートでCookieManagerを管理
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="video_settings_cookie_manager")
    return st.session_state.cookie_manager


def load_video_settings_from_cookie(cookie_manager):
    """クッキーから設定値を読み込む"""
    settings = {}
    try:
        # クッキーを取得（getAllでまとめて取得）
        all_cookies = cookie_manager.get_all()
        if all_cookies and "video_settings" in all_cookies:
            cookie_value = all_cookies["video_settings"]
            if cookie_value:
                settings = json.loads(cookie_value) if isinstance(cookie_value, str) else cookie_value
                logger.debug(f"クッキーから設定を読み込みました: {settings}")
    except Exception as e:
        logger.debug(f"クッキー読み込みエラー: {e}")
    return settings


def save_video_settings_to_cookie(cookie_manager, settings):
    """クッキーに設定値を保存"""
    try:
        cookie_manager.set("video_settings", json.dumps(settings), key="video_settings_set")
    except Exception as e:
        logger.debug(f"クッキー保存エラー: {e}")


def show_video_page():
    """動画編集ページを表示"""
    st.header("🎬 動画編集")
    st.markdown("---")
    
    # クッキーマネージャーの初期化
    cookie_manager = get_cookie_manager()
    
    # クッキーから設定を読み込み
    # 注意: CookieManagerは非同期なので、最初のレンダリングでは値が取得できないことがある
    saved_settings = load_video_settings_from_cookie(cookie_manager)
    
    # クッキーから読み込んだ設定をセッションステートに反映（初回のみ）
    if "video_settings_loaded" not in st.session_state:
        # デフォルト値の設定（仕様書に基づく）
        default_bg_video = "なし（背景動画を使用しない）"
        bg_videos = file_manager.list_bgvideos()
        if bg_videos:
            # 最新のファイルを選択（更新日時でソート済み）
            latest_bg = sorted(bg_videos, key=lambda x: x.stat().st_mtime, reverse=True)[0]
            default_bg_video = latest_bg.name
        
        if saved_settings:
            st.session_state.video_add_subtitles = saved_settings.get("add_subtitles", True)
            st.session_state.video_subtitle_source_idx = saved_settings.get("subtitle_source_idx", 1)  # デフォルト：セリフ
            st.session_state.video_subtitle_fontsize = saved_settings.get("fontsize", 60)
            st.session_state.video_subtitle_color = saved_settings.get("color", "#FFFFFF")
            st.session_state.video_subtitle_stroke_color = saved_settings.get("stroke_color", "#000000")
            st.session_state.video_subtitle_stroke_width = saved_settings.get("stroke_width", 3)  # デフォルト：3
            st.session_state.video_subtitle_bottom_offset = saved_settings.get("bottom_offset", 500)  # デフォルト：500
            st.session_state.video_bg_video_selected = saved_settings.get("bg_video", default_bg_video)
            st.session_state.video_enable_animation = saved_settings.get("enable_animation", True)  # デフォルト：オン
            st.session_state.video_animation_scale = saved_settings.get("animation_scale", 1.1)  # デフォルト：1.1
            st.session_state.video_animation_mode = saved_settings.get("animation_mode", "individual")  # デフォルト：個別指定
            st.session_state.video_animation_types = saved_settings.get("animation_types", {})  # 個別アニメーション設定
        else:
            # クッキーが読み込まれていない場合は、デフォルト値を設定
            st.session_state.video_add_subtitles = True
            st.session_state.video_subtitle_source_idx = 1  # デフォルト：セリフ
            st.session_state.video_subtitle_fontsize = 60
            st.session_state.video_subtitle_color = "#FFFFFF"
            st.session_state.video_subtitle_stroke_color = "#000000"
            st.session_state.video_subtitle_stroke_width = 3  # デフォルト：3
            st.session_state.video_subtitle_bottom_offset = 500  # デフォルト：500
            st.session_state.video_bg_video_selected = default_bg_video
            st.session_state.video_enable_animation = True  # デフォルト：オン
            st.session_state.video_animation_scale = 1.1  # デフォルト：1.1
            st.session_state.video_animation_mode = "individual"  # デフォルト：個別指定
            st.session_state.video_animation_types = {}  # 個別アニメーション設定
        st.session_state.video_settings_loaded = True
    
    # セッションステートの初期化
    if "video_editor" not in st.session_state:
        try:
            st.session_state.video_editor = VideoEditor()
        except Exception as e:
            st.error(f"⚠️ 動画エディタの初期化に失敗しました: {e}")
            st.info("MoviePyとFFmpegが正しくインストールされているか確認してください。")
            return
    
    # 台本の読み込み
    st.subheader("📝 台本の選択")
    
    script_files = file_manager.list_scripts()
    
    if not script_files:
        st.warning("保存された台本がありません。まず「📝 台本生成」ページで台本を生成・保存してください。")
        return
    
    # 台本ファイルの選択
    script_file_options = {f.name: f for f in script_files}
    selected_script_name = st.selectbox(
        "台本を選択",
        options=list(script_file_options.keys()),
        help="動画を生成する台本を選択してください"
    )
    
    if selected_script_name:
        selected_script_path = script_file_options[selected_script_name]
        
        # 台本を読み込み
        try:
            script_data = file_manager.load_script(selected_script_path)
            
            # 台本データの検証
            if not isinstance(script_data, dict):
                st.error(f"❌ 台本データの形式が正しくありません。型: {type(script_data)}")
                logger.error(f"台本データの型が不正です: {type(script_data)}")
                return
            
            # scenesキーの存在確認
            if "scenes" not in script_data:
                st.error("❌ 台本データに'scenes'キーがありません。")
                st.info(f"**デバッグ情報**: 台本データのキー: {list(script_data.keys())}")
                logger.error(f"台本データに'scenes'キーがありません。キー: {list(script_data.keys())}")
                return
            
            scenes_list = script_data.get("scenes", [])
            if not isinstance(scenes_list, list):
                st.error(f"❌ 'scenes'の型が正しくありません。型: {type(scenes_list)}")
                logger.error(f"'scenes'の型が不正です: {type(scenes_list)}")
                return
            
            if len(scenes_list) == 0:
                st.warning("⚠️ 台本にシーンが含まれていません。")
                logger.warning("台本にシーンが含まれていません")
                return
            
            st.session_state.current_script = script_data
            
            # 画像マッピング情報を読み込み（存在する場合）
            script_name = selected_script_name.replace(".json", "")
            image_mapping = file_manager.load_image_mapping(script_name)
            if image_mapping:
                st.session_state.image_mapping = image_mapping
            else:
                st.session_state.image_mapping = None
            
            # 台本情報を表示
            st.info(f"**タイトル**: {script_data.get('title', 'タイトルなし')} | **シーン数**: {len(scenes_list)}")
        
        except Exception as e:
            st.error(f"❌ 台本の読み込みに失敗しました: {e}")
            logger.error(f"台本の読み込みエラー: {e}", exc_info=True)
            return
    
    # セッションステートに台本がない場合は終了
    if "current_script" not in st.session_state:
        return
    
    script_data = st.session_state.current_script
    
    # デバッグ情報：台本データの構造を確認
    if not isinstance(script_data, dict):
        st.error(f"❌ 台本データの形式が正しくありません。型: {type(script_data)}")
        logger.error(f"台本データの型が不正です: {type(script_data)}")
        return
    
    scenes = script_data.get("scenes", [])
    
    if not scenes:
        # より詳細なエラーメッセージを表示
        st.warning("⚠️ 台本にシーンがありません。")
        st.info(f"**デバッグ情報**: 台本データのキー: {list(script_data.keys())}")
        if "scenes" in script_data:
            st.info(f"**デバッグ情報**: scenesの値: {script_data['scenes']} (型: {type(script_data['scenes'])})")
        logger.warning(f"台本にシーンがありません。台本データのキー: {list(script_data.keys())}")
        return
    
    st.markdown("---")
    st.subheader("📦 必要なファイルの確認")
    
    # 画像ファイルと音声ファイルの確認
    image_files: Dict[str, Path] = {}
    audio_files: Dict[str, Path] = {}
    
    missing_images = []
    missing_audio = []
    
    for scene in scenes:
        scene_number = scene.get("scene_number")
        scene_key = str(scene_number)
        
        # まず画像マッピング情報から検索（画像生成画面で割り当てた画像を優先）
        found_image = None
        if st.session_state.get("image_mapping") and scene_key in st.session_state.image_mapping:
            mapped_image_path = st.session_state.image_mapping[scene_key]
            if mapped_image_path.exists():
                found_image = mapped_image_path
        
        # マッピング情報にない場合は、ファイル検索で探す
        if not found_image:
            image_patterns = [
                f"image_scene{scene_number:03d}_*.png",
                f"image_scene{scene_number:03d}_*.PNG",
                f"image_scene{scene_number:03d}_*.jpg",
                f"image_scene{scene_number:03d}_*.JPG",
                f"image_scene{scene_number:03d}_*.jpeg",
                f"image_scene{scene_number:03d}_*.JPEG"
            ]
            
            for pattern in image_patterns:
                matches = list(file_manager.images_dir.glob(pattern))
                if matches:
                    # 最新のファイルを使用（複数ある場合）
                    found_image = sorted(matches, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                    break
        
        if found_image:
            image_files[scene_key] = found_image
        else:
            missing_images.append(scene_number)
        
        # 音声ファイルの検索（大文字・小文字両方に対応）
        audio_patterns = [
            f"audio_scene{scene_number:03d}_*.mp3",
            f"audio_scene{scene_number:03d}_*.MP3",
            f"audio_scene{scene_number:03d}_*.wav",
            f"audio_scene{scene_number:03d}_*.WAV"
        ]
        
        found_audio = None
        for pattern in audio_patterns:
            matches = list(file_manager.audio_dir.glob(pattern))
            if matches:
                # 最新のファイルを使用（複数ある場合）
                found_audio = sorted(matches, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                break
        
        if found_audio:
            audio_files[scene_key] = found_audio
        else:
            missing_audio.append(scene_number)
    
    # ファイルの存在確認結果を表示
    col1, col2 = st.columns(2)
    
    with col1:
        if missing_images:
            st.error(f"❌ 画像ファイルが見つかりません: シーン {', '.join(map(str, missing_images))}")
        else:
            st.success(f"✅ 画像ファイル: {len(image_files)}個")
    
    with col2:
        if missing_audio:
            st.error(f"❌ 音声ファイルが見つかりません: シーン {', '.join(map(str, missing_audio))}")
        else:
            st.success(f"✅ 音声ファイル: {len(audio_files)}個")
    
    if missing_images or missing_audio:
        st.warning("⚠️ 不足しているファイルがあります。画像生成または音声生成ページでファイルを生成してください。")
        return
    
    st.markdown("---")
    st.subheader("🎨 動画生成設定")
    
    # セッションステートの初期化（設定値の保持用）
    # 注意: クッキー読み込み部分で既に設定されている場合は、その値を使用
    if "video_add_subtitles" not in st.session_state:
        st.session_state.video_add_subtitles = True  # デフォルト：オン
    if "video_subtitle_source_idx" not in st.session_state:
        st.session_state.video_subtitle_source_idx = 1  # 0=見出し, 1=セリフ（デフォルト：セリフ）
    if "video_subtitle_fontsize" not in st.session_state:
        st.session_state.video_subtitle_fontsize = 60
    if "video_subtitle_color" not in st.session_state:
        st.session_state.video_subtitle_color = "#FFFFFF"
    if "video_subtitle_stroke_color" not in st.session_state:
        st.session_state.video_subtitle_stroke_color = "#000000"
    if "video_subtitle_stroke_width" not in st.session_state:
        st.session_state.video_subtitle_stroke_width = 3  # デフォルト：3
    if "video_subtitle_bottom_offset" not in st.session_state:
        st.session_state.video_subtitle_bottom_offset = 500  # デフォルト：500px
    if "video_bg_video_selected" not in st.session_state:
        # デフォルト：最新の背景動画を選択
        bg_videos = file_manager.list_bgvideos()
        if bg_videos:
            # 最新のファイルを選択（更新日時でソート済み）
            latest_bg = sorted(bg_videos, key=lambda x: x.stat().st_mtime, reverse=True)[0]
            st.session_state.video_bg_video_selected = latest_bg.name
        else:
            st.session_state.video_bg_video_selected = "なし（背景動画を使用しない）"
    if "video_enable_animation" not in st.session_state:
        st.session_state.video_enable_animation = True  # デフォルト：オン
    if "video_animation_scale" not in st.session_state:
        st.session_state.video_animation_scale = 1.1  # デフォルト：1.1
    if "video_animation_mode" not in st.session_state:
        st.session_state.video_animation_mode = "individual"  # デフォルト：個別指定
    if "video_animation_types" not in st.session_state:
        st.session_state.video_animation_types = {}  # {シーン番号: アニメーションタイプ}
    
    add_subtitles = st.checkbox(
        "字幕を追加",
        value=st.session_state.video_add_subtitles,
        key="video_add_subtitles",
        help="各シーンの字幕を動画に追加します"
    )
    
    # 字幕設定
    subtitle_source = "subtitle"
    subtitle_bottom_offset = st.session_state.video_subtitle_bottom_offset
    subtitle_style = None
    
    if add_subtitles:
        # 字幕内容の選択
        subtitle_options = ["見出し（subtitle）", "セリフ（dialogue）"]
        subtitle_source_option = st.radio(
            "字幕の内容",
            options=subtitle_options,
            index=st.session_state.video_subtitle_source_idx,
            horizontal=True,
            help="字幕に表示するテキストの種類を選択します"
        )
        # 選択結果を保存
        st.session_state.video_subtitle_source_idx = subtitle_options.index(subtitle_source_option)
        subtitle_source = "subtitle" if "見出し" in subtitle_source_option else "dialogue"
        
        with st.expander("字幕スタイル設定"):
            subtitle_fontsize = st.slider(
                "フォントサイズ",
                30, 100,
                key="video_subtitle_fontsize"
            )
            subtitle_color = st.color_picker(
                "文字色",
                key="video_subtitle_color"
            )
            subtitle_stroke_color = st.color_picker(
                "縁取り色",
                key="video_subtitle_stroke_color"
            )
            subtitle_stroke_width = st.slider(
                "縁取りの太さ",
                0, 5,
                key="video_subtitle_stroke_width"
            )
            
            st.markdown("---")
            st.markdown("**字幕の位置**")
            subtitle_bottom_offset = st.slider(
                "下からの位置（ピクセル）",
                min_value=0,
                max_value=500,
                step=10,
                key="video_subtitle_bottom_offset",
                help="値が大きいほど字幕が上に移動します（0=画面最下部）"
            )
            
            subtitle_style = {
                "fontsize": subtitle_fontsize,
                "color": subtitle_color,
                "font": "Arial-Bold",
                "stroke_color": subtitle_stroke_color,
                "stroke_width": subtitle_stroke_width,
                "method": "caption",
                "size": (VIDEO_WIDTH - 100, None),
                "align": "center"
            }
    
    st.markdown("---")
    st.subheader("🎥 背景動画設定")
    
    # 背景動画の選択
    bg_video_files = file_manager.list_bgvideos()
    bg_video_path = None
    
    if bg_video_files:
        bg_video_options = ["なし（背景動画を使用しない）"] + [f.name for f in bg_video_files]
        
        # 保存された選択が有効か確認
        saved_selection = st.session_state.video_bg_video_selected
        if saved_selection not in bg_video_options:
            saved_selection = "なし（背景動画を使用しない）"
            st.session_state.video_bg_video_selected = saved_selection
        
        selected_bg_video = st.selectbox(
            "背景動画を選択",
            options=bg_video_options,
            index=bg_video_options.index(saved_selection),
            help="動画の背景でループ再生する動画を選択します。`output/bgvideos/`フォルダに動画を配置してください。"
        )
        # 選択結果を保存
        st.session_state.video_bg_video_selected = selected_bg_video
        
        if selected_bg_video != "なし（背景動画を使用しない）":
            bg_video_path = file_manager.bgvideos_dir / selected_bg_video
            st.info(f"✅ 背景動画: {selected_bg_video}")
    else:
        st.info("💡 背景動画を使用するには、`output/bgvideos/`フォルダに動画ファイル（MP4等）を配置してください。")
    
    st.markdown("---")
    st.subheader("🎞️ 画像アニメーション設定")
    
    enable_animation = st.checkbox(
        "画像アニメーションを有効にする",
        key="video_enable_animation",
        help="各シーンの画像にアニメーション効果（ズーム、スライド）を適用します"
    )
    
    animation_scale = 1.2
    animation_types = None
    
    if enable_animation:
        # アニメーションモードの選択
        animation_mode_options = ["ランダム", "個別指定"]
        animation_mode_idx = 0 if st.session_state.video_animation_mode == "random" else 1
        animation_mode = st.radio(
            "アニメーションの適用方法",
            options=animation_mode_options,
            index=animation_mode_idx,
            horizontal=True,
            help="ランダム：各シーンにランダムにアニメーションを適用\n個別指定：各シーンごとにアニメーションを個別に指定"
        )
        st.session_state.video_animation_mode = "random" if animation_mode == "ランダム" else "individual"
        
        animation_scale = st.slider(
            "アニメーションの強さ",
            min_value=1.1,
            max_value=1.5,
            value=st.session_state.video_animation_scale,
            step=0.05,
            key="video_animation_scale",
            help="値が大きいほどズームや移動量が大きくなります（1.1 = 10%）"
        )
        
        # 個別指定モードの場合
        if st.session_state.video_animation_mode == "individual":
            st.markdown("---")
            
            # アニメーションタイプの選択肢
            animation_type_options = {
                "なし": None,
                "ゆっくりズームアップ": "zoom_in",
                "右から左へスライド": "slide_left",
                "左から右へスライド": "slide_right",
                "上から下へスライド": "slide_up",
                "下から上へスライド": "slide_down"
            }
            
            # アニメーションタイプの値のみ（「なし」を除く）
            animation_type_values = ["zoom_in", "slide_left", "slide_right", "slide_up", "slide_down"]
            
            # 各シーンごとにアニメーションを選択
            animation_types = {}
            
            # 各シーンに対して設定がない場合のみランダムに初期値を設定（連続しないように）
            previous_animation = None
            for scene in scenes:
                scene_number = scene.get("scene_number")
                scene_key = str(scene_number)
                # 設定がない場合のみランダムにアニメーションタイプを設定
                if scene_key not in st.session_state.video_animation_types:
                    # 前のシーンのアニメーションを除外したリストから選択
                    available_animations = [
                        anim for anim in animation_type_values 
                        if anim != previous_animation
                    ]
                    # 前のシーンと同じアニメーションしか残っていない場合は全種類から選択
                    if not available_animations:
                        available_animations = animation_type_values
                    
                    random_animation = random.choice(available_animations)
                    st.session_state.video_animation_types[scene_key] = random_animation
                    previous_animation = random_animation
                else:
                    # 既に設定されている場合は、それを前のアニメーションとして記録
                    previous_animation = st.session_state.video_animation_types[scene_key]
            
            # Expanderで折りたたみ可能にする
            with st.expander("📋 各シーンのアニメーション設定", expanded=True):
                # 3列レイアウトで表示（シーンを3つずつのグループに分ける）
                num_cols = 3
                
                # シーンを3つずつのグループに分ける
                for group_start in range(0, len(scenes), num_cols):
                    group_scenes = scenes[group_start:group_start + num_cols]
                    cols = st.columns(num_cols)
                    
                    for col_idx, scene in enumerate(group_scenes):
                        scene_number = scene.get("scene_number")
                        scene_key = str(scene_number)
                        
                        with cols[col_idx]:
                            # シーン番号を表示
                            st.markdown(f"### シーン {scene_number}")
                            
                            # 画像を表示（約15%サイズ：324pxの半分 = 162px）
                            scene_image_path = image_files.get(scene_key)
                            if scene_image_path and scene_image_path.exists():
                                # 画像を読み込んで表示（約15%サイズ：1080 * 0.15 = 162px）
                                st.image(
                                    str(scene_image_path),
                                    caption=f"シーン{scene_number}の画像",
                                    width=162
                                )
                            else:
                                st.warning(f"シーン{scene_number}の画像が見つかりません")
                            
                            # 現在の設定を取得（既にランダムに設定済み）
                            current_animation = st.session_state.video_animation_types.get(scene_key, None)
                            current_option = None
                            for option_name, option_value in animation_type_options.items():
                                if option_value == current_animation:
                                    current_option = option_name
                                    break
                            if current_option is None:
                                # 設定がない場合は「なし」をデフォルトに（通常は発生しない）
                                current_option = "なし"
                            
                            # セレクトボックスで選択
                            selected_option = st.selectbox(
                                f"アニメーション",
                                options=list(animation_type_options.keys()),
                                index=list(animation_type_options.keys()).index(current_option),
                                key=f"animation_scene_{scene_number}",
                                help=f"シーン{scene_number}に適用するアニメーションを選択"
                            )
                            
                            selected_animation_type = animation_type_options[selected_option]
                            if selected_animation_type:
                                animation_types[scene_key] = selected_animation_type
                                st.session_state.video_animation_types[scene_key] = selected_animation_type
                            else:
                                # 「なし」が選択された場合は辞書から削除
                                if scene_key in st.session_state.video_animation_types:
                                    del st.session_state.video_animation_types[scene_key]
                            
                            st.markdown("---")  # 区切り線
                    
                    # グループ間にスペースを追加（最後のグループ以外）
                    if group_start + num_cols < len(scenes):
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            # ランダムモードの場合
            st.info("💡 各シーンにランダムで以下のアニメーションが適用されます：\n"
                    "- ゆっくりズームアップ\n"
                    "- 右から左へスライド\n"
                    "- 左から右へスライド\n"
                    "- 上から下へスライド\n"
                    "- 下から上へスライド")
    
    # 設定をクッキーに保存
    current_settings = {
        "add_subtitles": st.session_state.video_add_subtitles,
        "subtitle_source_idx": st.session_state.video_subtitle_source_idx,
        "fontsize": st.session_state.video_subtitle_fontsize,
        "color": st.session_state.video_subtitle_color,
        "stroke_color": st.session_state.video_subtitle_stroke_color,
        "stroke_width": st.session_state.video_subtitle_stroke_width,
        "bottom_offset": st.session_state.video_subtitle_bottom_offset,
        "bg_video": st.session_state.video_bg_video_selected,
        "enable_animation": st.session_state.video_enable_animation,
        "animation_scale": st.session_state.video_animation_scale,
        "animation_mode": st.session_state.video_animation_mode,
        "animation_types": st.session_state.video_animation_types
    }
    save_video_settings_to_cookie(cookie_manager, current_settings)
    
    st.markdown("---")
    st.subheader("🎬 動画生成")
    
    if st.button("🚀 動画を生成", use_container_width=True, type="primary"):
        with st.spinner("動画を生成中..."):
            try:
                editor = st.session_state.video_editor
                video_path = editor.create_video_from_script(
                    script_data=script_data,
                    image_files=image_files,
                    audio_files=audio_files,
                    add_subtitles=add_subtitles,
                    subtitle_style=subtitle_style,
                    subtitle_source=subtitle_source,
                    subtitle_bottom_offset=subtitle_bottom_offset,
                    bg_video_path=bg_video_path,
                    enable_animation=enable_animation,
                    animation_scale=animation_scale,
                    animation_types=animation_types if enable_animation else None
                )
                
                st.session_state.generated_video = video_path
                st.session_state.video_just_generated = True
                logger.info(f"動画生成が成功しました: {video_path}")
                
                # 動画生成完了後にリランして表示を更新
                st.rerun()
            
            except Exception as e:
                st.error(f"❌ 動画生成に失敗しました: {e}")
                logger.error(f"動画生成エラー: {e}")
    
    # 生成完了メッセージ（一度だけ表示）
    if st.session_state.get("video_just_generated", False):
        st.success(f"✅ 動画を生成しました！")
        st.session_state.video_just_generated = False
    
    # 生成済み動画の表示
    if "generated_video" in st.session_state:
        st.markdown("---")
        st.subheader("📁 生成された動画")
        
        video_path = st.session_state.generated_video
        if video_path.exists():
            # 動画情報を表示
            file_size = video_path.stat().st_size / (1024 * 1024)  # MB
            st.caption(f"ファイル名: {video_path.name} | サイズ: {file_size:.2f} MB")
            
            # 動画を表示（ファイルパスを直接渡す）
            try:
                st.video(str(video_path), format="video/mp4")
            except Exception as e:
                logger.error(f"動画表示エラー: {e}")
                st.error(f"動画の表示に失敗しました: {e}")
                # フォールバック: バイトデータで読み込み
                try:
                    with open(video_path, "rb") as f:
                        video_data = f.read()
                    st.video(video_data, format="video/mp4")
                except Exception as e2:
                    st.error(f"動画の読み込みに失敗しました: {e2}")
            
            # ダウンロードボタン（必要に応じてファイルを読み込む）
            try:
                with open(video_path, "rb") as f:
                    video_data = f.read()
                st.download_button(
                    label="⬇️ 動画をダウンロード",
                    data=video_data,
                    file_name=video_path.name,
                    mime="video/mp4",
                    use_container_width=True,
                    key="download_generated_video"
                )
            except Exception as e:
                logger.error(f"動画ダウンロードボタンの作成エラー: {e}")
                st.error(f"ダウンロードボタンの作成に失敗しました: {e}")
    
    # 保存済み動画の一覧
    st.markdown("---")
    st.subheader("📚 保存済み動画")
    
    video_files = file_manager.list_video_files()
    
    if video_files:
        for video_file in video_files[:10]:  # 最新10件を表示
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{video_file.name}**")
                file_size = video_file.stat().st_size / (1024 * 1024)  # MB
                st.caption(f"サイズ: {file_size:.2f} MB")
            with col2:
                with open(video_file, "rb") as f:
                    st.download_button(
                        label="⬇️",
                        data=f.read(),
                        file_name=video_file.name,
                        mime="video/mp4",
                        key=f"download_{video_file.name}"
                    )
    else:
        st.info("保存済みの動画がありません。")
