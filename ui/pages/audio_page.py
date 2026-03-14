"""
音声生成ページ
"""
import streamlit as st
import json

from audio.audio_generator import AudioGenerator
from audio.audio_processor import AudioProcessor
from utils.file_manager import file_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def show_audio_page():
    """音声生成ページを表示"""
    st.header("🎤 音声生成")
    st.markdown("---")
    
    # セッションステートの初期化
    if "generated_audios" not in st.session_state:
        st.session_state.generated_audios = {}
    
    if "elevenlabs_model_id" not in st.session_state:
        from config.config import config
        st.session_state.elevenlabs_model_id = config.elevenlabs_model_id
    
    # AudioGeneratorの初期化（モデルIDが変更された場合は再作成）
    try:
        if "audio_generator" not in st.session_state or st.session_state.get("current_model_id") != st.session_state.elevenlabs_model_id:
            st.session_state.audio_generator = AudioGenerator(model_id=st.session_state.elevenlabs_model_id)
            st.session_state.current_model_id = st.session_state.elevenlabs_model_id
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.info("`.env`ファイルに`ELEVENLABS_API_KEY`と`ELEVENLABS_VOICE_ID`を設定してください。")
        return
    
    # 台本の読み込み
    st.subheader("📝 台本の選択")
    
    # 保存された台本のリストを取得
    script_files = file_manager.list_scripts()
    
    if not script_files:
        st.warning("保存された台本がありません。まず「📝 台本生成」ページで台本を生成・保存してください。")
        return
    
    # 台本ファイルの選択
    script_file_options = {f.name: f for f in script_files}
    selected_script_name = st.selectbox(
        "台本を選択",
        options=list(script_file_options.keys()),
        help="音声を生成する台本を選択してください"
    )
    
    if selected_script_name:
        selected_script_path = script_file_options[selected_script_name]
        
        # 台本を読み込み
        try:
            script_data = file_manager.load_script(selected_script_path)
            st.session_state.current_script = script_data
            
            # 台本情報を表示（タイトル・概要説明・タグ・シーン数）
            title = script_data.get("title", "タイトルなし")
            scene_count = len(script_data.get("scenes", []))
            st.info(f"**タイトル**: {title} | **シーン数**: {scene_count}")
            description = (script_data.get("description") or "").strip()
            if description:
                with st.expander("📄 概要説明", expanded=False):
                    st.write(description)
            suggested_tags = script_data.get("suggested_tags") or []
            if suggested_tags:
                tags_str = ", ".join(str(t).strip() for t in suggested_tags if str(t).strip())
                if tags_str:
                    st.caption(f"**タグ**: {tags_str}")
            # 台本ファイルに保存された追加項目の表示
            _topic = (script_data.get("topic") or "").strip()
            if _topic:
                st.caption(f"**トピック・テーマ**: {_topic}")
            _ref_script = (script_data.get("reference_script_normalized") or "").strip()
            if _ref_script:
                with st.expander("📋 整形後の参考台本", expanded=False):
                    st.text_area("", value=_ref_script, height=120, disabled=True, key="audio_ref_script", label_visibility="collapsed")
            _ref_core = (script_data.get("reference_script_core_normalized") or "").strip()
            if _ref_core:
                with st.expander("📋 整形後の参考台本核心部", expanded=False):
                    st.text_area("", value=_ref_core, height=80, disabled=True, key="audio_ref_core", label_visibility="collapsed")
            _ref_meta = (script_data.get("reference_metadata") or "").strip()
            if _ref_meta:
                with st.expander("📋 人気動画のタイトル・概要（参考）", expanded=False):
                    st.text_area("", value=_ref_meta, height=100, disabled=True, key="audio_ref_metadata", label_visibility="collapsed")
            # 人気動画を参考にしたタイトル・概要案
            _st_ref = (script_data.get("suggested_title_from_reference") or "").strip()
            _sd_ref = (script_data.get("suggested_description_from_reference") or "").strip()
            if _st_ref or _sd_ref:
                with st.expander("📌 人気動画を参考にしたタイトル・概要案", expanded=False):
                    if _st_ref:
                        st.caption("**タイトル案**")
                        st.text_area("", value=_st_ref, height=40, disabled=True, key="audio_title_ref", label_visibility="collapsed")
                    if _sd_ref:
                        st.caption("**概要案**")
                        st.text_area("", value=_sd_ref, height=80, disabled=True, key="audio_desc_ref", label_visibility="collapsed")
        
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
    st.subheader("🎚️ 音声生成設定")
    
    # モデル選択
    model_options = {
        "eleven_turbo_v2_5": "Eleven Turbo V2.5 (V3 - 推奨)",
        "eleven_multilingual_v2": "Eleven Multilingual V2",
        "eleven_multilingual_v3": "Eleven Multilingual V3 (利用可能な場合)"
    }
    
    selected_model = st.selectbox(
        "音声モデル",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,
        help="使用するElevenLabsの音声モデルを選択してください"
    )
    
    # セッションステートにモデルIDを保存
    if "elevenlabs_model_id" not in st.session_state:
        st.session_state.elevenlabs_model_id = selected_model
    else:
        st.session_state.elevenlabs_model_id = selected_model
    
    col1, col2 = st.columns(2)
    with col1:
        stability = st.slider(
            "安定性 (Stability)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="音声の安定性を調整します（高いほど安定、低いほど表現豊か）"
        )
    
    with col2:
        similarity_boost = st.slider(
            "類似度ブースト (Similarity Boost)",
            min_value=0.0,
            max_value=1.0,
            value=0.75,
            step=0.1,
            help="音声の類似度を調整します（高いほど元の声に近い）"
        )
    
    st.markdown("---")
    st.subheader("🎵 音声生成")
    
    # 全シーン一括生成
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🚀 全シーンの音声を生成", use_container_width=True):
            with st.spinner("音声を生成中..."):
                try:
                    generator = st.session_state.audio_generator
                    audio_files = generator.generate_script_audios(
                        script_data=script_data,
                        stability=stability,
                        similarity_boost=similarity_boost
                    )
                    st.session_state.generated_audios = audio_files
                    st.success(f"✅ {len(audio_files)}個の音声ファイルを生成しました！")
                    logger.info(f"音声生成が成功しました: {len(audio_files)}個のファイル")
                
                except Exception as e:
                    st.error(f"❌ 音声生成に失敗しました: {e}")
                    logger.error(f"音声生成エラー: {e}")
    
    with col2:
        if st.button("🔄 クリア", use_container_width=True):
            st.session_state.generated_audios = {}
            st.rerun()
    
    st.markdown("---")
    st.subheader("📋 シーン別音声生成")
    
    # 各シーンの音声生成
    for scene in scenes:
        scene_number = scene.get("scene_number")
        dialogue = scene.get("dialogue", "")
        subtitle = scene.get("subtitle", "")
        
        with st.expander(f"シーン {scene_number} - {subtitle[:50] if subtitle else dialogue[:50]}..."):
            st.markdown(f"**セリフ**: {dialogue}")
            # dialogue_for_ttsがある場合は表示
            dialogue_for_tts = scene.get("dialogue_for_tts", "")
            if dialogue_for_tts:
                st.markdown(f"**音声読み上げ用テキスト（ひらがな）**: {dialogue_for_tts}")
            
            # 既に生成されているかチェック
            scene_key = str(scene_number)
            is_generated = scene_key in st.session_state.generated_audios
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if is_generated:
                    audio_path = st.session_state.generated_audios[scene_key]
                    st.audio(str(audio_path))
                    st.success(f"✅ 音声が生成されています: {audio_path.name}")
                else:
                    st.info("まだ音声が生成されていません")
            
            with col2:
                if st.button(f"生成", key=f"generate_{scene_number}", use_container_width=True):
                    with st.spinner(f"シーン{scene_number}の音声を生成中..."):
                        try:
                            generator = st.session_state.audio_generator
                            # dialogue_for_ttsがあればそれを使用、なければdialogueを使用
                            dialogue_for_tts = scene.get("dialogue_for_tts", "")
                            text_for_tts = dialogue_for_tts if dialogue_for_tts else dialogue
                            
                            audio_path = generator.generate_audio_file(
                                text=text_for_tts,
                                scene_number=scene_number,
                                stability=stability,
                                similarity_boost=similarity_boost
                            )
                            st.session_state.generated_audios[scene_key] = audio_path
                            st.success(f"✅ 音声を生成しました！")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ 音声生成に失敗しました: {e}")
                            logger.error(f"音声生成エラー: {e}")
    
    # 生成された音声の一覧
    if st.session_state.generated_audios:
        st.markdown("---")
        st.subheader("📁 生成された音声ファイル")
        
        for scene_key, audio_path in st.session_state.generated_audios.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**シーン {scene_key}**: {audio_path.name}")
                st.audio(str(audio_path))
            
            with col2:
                # 音声の長さを表示
                processor = AudioProcessor()
                duration = processor.get_audio_duration(audio_path)
                if duration > 0:
                    st.caption(f"⏱️ {duration:.1f}秒")
            
            with col3:
                # ダウンロードボタン
                with open(audio_path, "rb") as f:
                    st.download_button(
                        label="⬇️",
                        data=f.read(),
                        file_name=audio_path.name,
                        mime="audio/mpeg",
                        key=f"download_{scene_key}"
                    )
