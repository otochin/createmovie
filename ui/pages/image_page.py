"""
画像生成ページ
"""
import streamlit as st
from pathlib import Path

from images.image_generator import ImageGenerator
from images.image_processor import ImageProcessor
from utils.file_manager import file_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def show_image_page():
    """画像生成ページを表示"""
    st.header("🖼️ 画像生成")
    st.markdown("---")
    
    # セッションステートの初期化
    if "image_generator" not in st.session_state:
        try:
            st.session_state.image_generator = ImageGenerator()
        except ValueError as e:
            st.error(f"⚠️ {e}")
            st.info("`.env`ファイルに`OPENAI_API_KEY`を設定してください。")
            return
    
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = {}
    
    if "reference_image_analysis" not in st.session_state:
        st.session_state.reference_image_analysis = None
    
    if "reference_image_path" not in st.session_state:
        st.session_state.reference_image_path = None
    
    # 参考画像のアップロード
    st.subheader("🖼️ 参考画像（オプション）")
    
    uploaded_file = st.file_uploader(
        "参考画像をアップロード",
        type=['png', 'jpg', 'jpeg'],
        help="参考にしたい画像をアップロードすると、そのトンマナやタッチを分析して反映させます"
    )
    
    if uploaded_file is not None:
        # アップロードされた画像を保存
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = Path(tmp_file.name)
            st.session_state.reference_image_path = tmp_path
        
        # 画像を表示
        st.image(uploaded_file, caption="参考画像", use_container_width=True)
        
        # 分析ボタン
        if st.button("🔍 参考画像を分析", use_container_width=True):
            with st.spinner("参考画像のトンマナ・タッチを分析中..."):
                try:
                    generator = st.session_state.image_generator
                    analysis = generator.analyze_reference_image(st.session_state.reference_image_path)
                    st.session_state.reference_image_analysis = analysis
                    st.success("✅ 参考画像の分析が完了しました！")
                    logger.info("参考画像の分析が成功しました")
                except Exception as e:
                    st.error(f"❌ 参考画像の分析に失敗しました: {e}")
                    logger.error(f"参考画像分析エラー: {e}")
        
        # 分析結果の表示
        if st.session_state.reference_image_analysis:
            st.markdown("---")
            st.subheader("📝 分析結果：トンマナ・タッチ")
            st.info(st.session_state.reference_image_analysis)
    
    elif st.session_state.reference_image_path and st.session_state.reference_image_path.exists():
        # 以前アップロードした画像がある場合
        st.image(str(st.session_state.reference_image_path), caption="参考画像", use_container_width=True)
        if st.session_state.reference_image_analysis:
            st.markdown("---")
            st.subheader("📝 分析結果：トンマナ・タッチ")
            st.info(st.session_state.reference_image_analysis)
    
    st.markdown("---")
    
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
        help="画像を生成する台本を選択してください"
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
    st.subheader("🎨 画像生成設定")
    
    # 画像生成指示の入力
    image_instruction = st.text_area(
        "画像生成指示（オプション）",
        placeholder="例：明るい雰囲気で、カラフルな配色を使用してください。",
        help="画像生成時に追加で考慮してほしい指示を入力できます。全シーンに適用されます。",
        height=100
    )
    
    resize_to_video_size = st.checkbox(
        "動画サイズ（1080x1920）にリサイズ",
        value=True,
        help="生成された画像を動画サイズに自動リサイズします"
    )
    
    st.markdown("---")
    st.subheader("🖼️ 画像生成")
    
    # 全シーン一括生成
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🚀 全シーンの画像を生成", use_container_width=True):
            with st.spinner("画像を生成中..."):
                try:
                    generator = st.session_state.image_generator
                    image_files = generator.generate_script_images(
                        script_data=script_data,
                        resize_to_video_size=resize_to_video_size,
                        style_description=None,  # 参考画像の分析結果はプロンプトに含めない（参考のみ）
                        instruction=image_instruction if image_instruction.strip() else None
                    )
                    st.session_state.generated_images = image_files
                    st.success(f"✅ {len(image_files)}個の画像ファイルを生成しました！")
                    logger.info(f"画像生成が成功しました: {len(image_files)}個のファイル")
                
                except Exception as e:
                    st.error(f"❌ 画像生成に失敗しました: {e}")
                    logger.error(f"画像生成エラー: {e}")
    
    with col2:
        if st.button("🔄 クリア", use_container_width=True):
            st.session_state.generated_images = {}
            st.rerun()
    
    st.markdown("---")
    st.subheader("📋 シーン別画像生成")
    
    # 各シーンの画像生成
    for scene in scenes:
        scene_number = scene.get("scene_number")
        image_prompt = scene.get("image_prompt", "")
        subtitle = scene.get("subtitle", "")
        
        with st.expander(f"シーン {scene_number} - {subtitle[:50] if subtitle else image_prompt[:50]}..."):
            st.markdown(f"**画像プロンプト**: {image_prompt}")
            
            # 既に生成されているかチェック
            scene_key = str(scene_number)
            is_generated = scene_key in st.session_state.generated_images
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if is_generated:
                    image_path = st.session_state.generated_images[scene_key]
                    st.image(str(image_path), use_container_width=True)
                    
                    # 画像情報を表示
                    processor = ImageProcessor()
                    width, height = processor.get_image_size(image_path)
                    st.caption(f"✅ 画像が生成されています: {image_path.name} ({width}x{height})")
                else:
                    st.info("まだ画像が生成されていません")
            
            with col2:
                if st.button(f"生成", key=f"generate_{scene_number}", use_container_width=True):
                    with st.spinner(f"シーン{scene_number}の画像を生成中..."):
                        try:
                            generator = st.session_state.image_generator
                            image_path = generator.generate_image_file(
                                prompt=image_prompt,
                                scene_number=scene_number,
                                resize_to_video_size=resize_to_video_size,
                                style_description=None,  # 参考画像の分析結果はプロンプトに含めない（参考のみ）
                                instruction=image_instruction if image_instruction.strip() else None
                            )
                            st.session_state.generated_images[scene_key] = image_path
                            st.success(f"✅ 画像を生成しました！")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ 画像生成に失敗しました: {e}")
                            logger.error(f"画像生成エラー: {e}")
    
    # 生成された画像の一覧
    if st.session_state.generated_images:
        st.markdown("---")
        st.subheader("📁 生成された画像ファイル")
        
        for scene_key, image_path in st.session_state.generated_images.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**シーン {scene_key}**: {image_path.name}")
                st.image(str(image_path), use_container_width=True)
                
                # 画像情報を表示
                processor = ImageProcessor()
                width, height = processor.get_image_size(image_path)
                st.caption(f"サイズ: {width}x{height}")
            
            with col2:
                # ダウンロードボタン
                with open(image_path, "rb") as f:
                    st.download_button(
                        label="⬇️",
                        data=f.read(),
                        file_name=image_path.name,
                        mime=f"image/{image_path.suffix[1:]}",
                        key=f"download_{scene_key}"
                    )
