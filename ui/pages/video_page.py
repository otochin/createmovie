"""
動画編集ページ
"""
import streamlit as st
from pathlib import Path
from typing import Dict

from video.video_editor import VideoEditor
from utils.file_manager import file_manager
from utils.logger import get_logger
from config.constants import VIDEO_WIDTH

logger = get_logger(__name__)


def show_video_page():
    """動画編集ページを表示"""
    st.header("🎬 動画編集")
    st.markdown("---")
    
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
            st.session_state.current_script = script_data
            
            # 台本情報を表示
            st.info(f"**タイトル**: {script_data.get('title', 'タイトルなし')} | **シーン数**: {len(script_data.get('scenes', []))}")
        
        except Exception as e:
            st.error(f"台本の読み込みに失敗しました: {e}")
            return
    
    # セッションステートに台本がない場合は終了
    if "current_script" not in st.session_state:
        return
    
    script_data = st.session_state.current_script
    scenes = script_data.get("scenes", [])
    
    if not scenes:
        st.warning("台本にシーンがありません。")
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
        
        # 画像ファイルの検索
        image_patterns = [
            f"image_scene{scene_number:03d}_*.png",
            f"image_scene{scene_number:03d}_*.jpg",
            f"image_scene{scene_number:03d}_*.jpeg"
        ]
        
        found_image = None
        for pattern in image_patterns:
            matches = list(file_manager.images_dir.glob(pattern))
            if matches:
                found_image = matches[0]
                break
        
        if found_image:
            image_files[scene_key] = found_image
        else:
            missing_images.append(scene_number)
        
        # 音声ファイルの検索
        audio_patterns = [
            f"audio_scene{scene_number:03d}_*.mp3",
            f"audio_scene{scene_number:03d}_*.wav"
        ]
        
        found_audio = None
        for pattern in audio_patterns:
            matches = list(file_manager.audio_dir.glob(pattern))
            if matches:
                found_audio = matches[0]
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
    
    add_subtitles = st.checkbox(
        "字幕を追加",
        value=True,
        help="各シーンの字幕を動画に追加します"
    )
    
    # 字幕スタイル設定
    if add_subtitles:
        with st.expander("字幕スタイル設定"):
            subtitle_fontsize = st.slider("フォントサイズ", 30, 100, 60)
            subtitle_color = st.color_picker("文字色", "#FFFFFF")
            subtitle_stroke_color = st.color_picker("縁取り色", "#000000")
            subtitle_stroke_width = st.slider("縁取りの太さ", 0, 5, 2)
            
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
    else:
        subtitle_style = None
    
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
                    subtitle_style=subtitle_style
                )
                
                st.success(f"✅ 動画を生成しました！")
                st.session_state.generated_video = video_path
                logger.info(f"動画生成が成功しました: {video_path}")
                
                # 動画を表示（サイズを30%に縮小）
                # Streamlitのst.video()にはwidthパラメータがないため、HTMLで表示
                with open(video_path, "rb") as video_file:
                    video_bytes = video_file.read()
                    import base64
                    video_base64 = base64.b64encode(video_bytes).decode()
                    video_html = f"""
                    <div style="display: flex; justify-content: center; margin: 20px 0;">
                        <video width="30%" controls style="max-width: 324px;">
                            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                        </video>
                    </div>
                    """
                    st.markdown(video_html, unsafe_allow_html=True)
                
                # ダウンロードボタン
                with open(video_path, "rb") as f:
                    st.download_button(
                        label="⬇️ 動画をダウンロード",
                        data=f.read(),
                        file_name=video_path.name,
                        mime="video/mp4",
                        use_container_width=True
                    )
            
            except Exception as e:
                st.error(f"❌ 動画生成に失敗しました: {e}")
                logger.error(f"動画生成エラー: {e}")
    
    # 生成済み動画の表示
    if "generated_video" in st.session_state:
        st.markdown("---")
        st.subheader("📁 生成された動画")
        
        video_path = st.session_state.generated_video
        if video_path.exists():
            # 動画を表示（サイズを30%に縮小）
            with open(video_path, "rb") as video_file:
                video_bytes = video_file.read()
                import base64
                video_base64 = base64.b64encode(video_bytes).decode()
                video_html = f"""
                <div style="display: flex; justify-content: center; margin: 20px 0;">
                    <video width="30%" controls style="max-width: 324px;">
                        <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                    </video>
                </div>
                """
                st.markdown(video_html, unsafe_allow_html=True)
            
            # 動画情報を表示
            file_size = video_path.stat().st_size / (1024 * 1024)  # MB
            st.caption(f"ファイル名: {video_path.name} | サイズ: {file_size:.2f} MB")
            
            # ダウンロードボタン
            with open(video_path, "rb") as f:
                st.download_button(
                    label="⬇️ 動画をダウンロード",
                    data=f.read(),
                    file_name=video_path.name,
                    mime="video/mp4",
                    use_container_width=True
                )
    
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
