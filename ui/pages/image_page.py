"""
画像生成ページ
"""
import streamlit as st
import shutil
import random
from pathlib import Path
from datetime import datetime

from images.image_generator import ImageGenerator
from images.image_processor import ImageProcessor
from utils.file_manager import file_manager
from utils.logger import get_logger
from ui.pages.video_page import get_cookie_manager, load_video_settings_from_cookie, save_video_settings_to_cookie

logger = get_logger(__name__)


def _normalize_image_path(image_path):  # str | Path -> Path
    """セッションやマッピングで str になっている場合に Path に統一する"""
    if image_path is None:
        return None
    return Path(image_path) if not isinstance(image_path, Path) else image_path


def _read_image_bytes(image_path):
    """画像をバイト列で読み込む。表示の安定性のためファイルから直接読む。存在しない場合は None"""
    path = _normalize_image_path(image_path)
    if path is None or not path.exists():
        return None
    try:
        return path.read_bytes()
    except Exception:
        return None


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
    
    # 動画フォーマット（ショート / 長尺）。動画編集画面と共通の session_state.video_format を使用
    if "video_format" not in st.session_state:
        cookie_manager = get_cookie_manager()
        saved = load_video_settings_from_cookie(cookie_manager)
        st.session_state.video_format = saved.get("video_format", "short")
    video_format_label = st.radio(
        "動画フォーマット",
        options=["ショート（9:16, 1080×1920）", "長尺（16:9, 1920×1080）"],
        index=0 if st.session_state.video_format == "short" else 1,
        horizontal=True,
        key="image_format_radio",
        help="ショートはYouTubeショート用、長尺は横型動画用です。動画編集画面と連動します。長尺時は output/stock_images_long/ の画像を紐づけ、output/images_long/ に保存します。"
    )
    new_format = "short" if "ショート" in video_format_label else "long"
    if new_format != st.session_state.video_format:
        st.session_state.video_format = new_format
        # 動画編集画面のクッキーにも反映（ブラウザ再起動後も同じフォーマットになる）
        cookie_manager = get_cookie_manager()
        settings = load_video_settings_from_cookie(cookie_manager)
        settings["video_format"] = st.session_state.video_format
        save_video_settings_to_cookie(cookie_manager, settings)
    is_long_format = st.session_state.video_format == "long"

    # 画像生成指示の入力
    image_instruction = st.text_area(
        "画像生成指示（オプション）",
        placeholder="例：明るい雰囲気で、カラフルな配色を使用してください。",
        help="画像生成時に追加で考慮してほしい指示を入力できます。全シーンに適用されます。",
        height=100
    )
    
    resize_to_video_size = st.checkbox(
        "動画サイズにリサイズ",
        value=True,
        help="生成された画像を動画サイズに自動リサイズします（ショート: 1080×1920、長尺: 1920×1080）"
    )
    
    st.markdown("---")
    st.subheader("🖼️ 画像生成")
    
    # 全シーン一括生成
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("🚀 全シーンの画像を生成", use_container_width=True):
            with st.spinner("画像を生成中..."):
                try:
                    generator = st.session_state.image_generator
                    image_files = generator.generate_script_images(
                        script_data=script_data,
                        resize_to_video_size=resize_to_video_size,
                        style_description=None,  # 参考画像の分析結果はプロンプトに含めない（参考のみ）
                        instruction=image_instruction if image_instruction.strip() else None,
                        is_long=is_long_format
                    )
                    st.session_state.generated_images = image_files
                    
                    # 画像マッピング情報を保存（台本ファイル名をキーとして、長尺時は別ファイル）
                    try:
                        script_name = selected_script_name.replace(".json", "")
                        file_manager.save_image_mapping(script_name, image_files, is_long=is_long_format)
                    except Exception as e:
                        logger.warning(f"画像マッピングの保存に失敗しました: {e}")
                    
                    st.success(f"✅ {len(image_files)}個の画像ファイルを生成しました！")
                    logger.info(f"画像生成が成功しました: {len(image_files)}個のファイル")
                
                except Exception as e:
                    st.error(f"❌ 画像生成に失敗しました: {e}")
                    logger.error(f"画像生成エラー: {e}")
    
    with col2:
        if st.button("📂 ストック画像を紐づける", use_container_width=True):
            # ストック画像の取得（フォーマットに応じてショート用 or 長尺用フォルダ）
            if is_long_format:
                stock_images = file_manager.list_stock_images_long()
                stock_folder = "output/stock_images_long/"
                images_output_dir = file_manager.images_long_dir
            else:
                stock_images = file_manager.list_stock_images()
                stock_folder = "output/stock_images/"
                images_output_dir = file_manager.images_dir
            
            if not stock_images:
                st.error(f"❌ ストック画像がありません。{stock_folder} フォルダに画像を配置してください。")
            else:
                # 既に割り当て済みのストック画像を取得（フォーマット別に追跡）
                used_key = "used_stock_images_long" if is_long_format else "used_stock_images"
                if used_key not in st.session_state:
                    st.session_state[used_key] = set()
                used_set = st.session_state[used_key]
                
                # 既に割り当て済みの画像を除外
                available_images = [img for img in stock_images if img not in used_set]
                
                if len(available_images) < len(scenes):
                    st.error(
                        f"❌ 未使用のストック画像が足りません。\n"
                        f"シーン数: {len(scenes)}、未使用のストック画像数: {len(available_images)}\n"
                        f"（既に {len(used_set)} 個の画像が使用済みです）"
                    )
                else:
                    with st.spinner("ストック画像を紐づけ中..."):
                        try:
                            # 出力先ディレクトリを確保
                            file_manager.ensure_directory_exists(images_output_dir)
                            # 未使用の画像からランダムに選択（重複なし）
                            shuffled_images = random.sample(available_images, len(scenes))
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            assigned_images = {}
                            
                            for i, scene in enumerate(scenes):
                                scene_number = scene.get("scene_number")
                                stock_image_path = shuffled_images[i]
                                
                                # 使用済みとしてマーク
                                used_set.add(stock_image_path)
                                
                                # 新しいファイル名を生成（拡張子は小文字に統一）
                                extension = stock_image_path.suffix.lower()
                                new_filename = f"image_scene{scene_number:03d}_{timestamp}{extension}"
                                new_path = (images_output_dir / new_filename).resolve()
                                
                                # 画像をコピー
                                shutil.copy2(stock_image_path, new_path)
                                
                                assigned_images[str(scene_number)] = new_path
                            
                            st.session_state.generated_images = assigned_images
                            
                            # 画像マッピング情報を保存（台本ファイル名をキーとして、長尺時は別ファイル）
                            try:
                                script_name = selected_script_name.replace(".json", "")
                                file_manager.save_image_mapping(script_name, assigned_images, is_long=is_long_format)
                            except Exception as e:
                                logger.warning(f"画像マッピングの保存に失敗しました: {e}")
                            
                            st.success(f"✅ {len(assigned_images)}個のストック画像を紐づけました！")
                            logger.info(f"ストック画像の紐づけが成功しました: {len(assigned_images)}個のファイル")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ ストック画像の紐づけに失敗しました: {e}")
                            logger.error(f"ストック画像紐づけエラー: {e}")
    
    with col3:
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
                    image_path = _normalize_image_path(st.session_state.generated_images[scene_key])
                    image_bytes = _read_image_bytes(image_path)
                    if image_bytes is not None:
                        st.image(image_bytes, use_container_width=True)
                        processor = ImageProcessor()
                        width, height = processor.get_image_size(image_path)
                        st.caption(f"✅ 画像が生成されています: {image_path.name} ({width}x{height})")
                    else:
                        st.warning(f"画像ファイルを読み込めません: {image_path}")
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
                                instruction=image_instruction if image_instruction.strip() else None,
                                is_long=is_long_format
                            )
                            st.session_state.generated_images[scene_key] = image_path
                            
                            # 画像マッピング情報を更新（台本ファイル名をキーとして、長尺時は別ファイル）
                            try:
                                script_name = selected_script_name.replace(".json", "")
                                existing_mapping = file_manager.load_image_mapping(script_name, is_long=is_long_format) or {}
                                existing_mapping[scene_key] = image_path
                                file_manager.save_image_mapping(script_name, existing_mapping, is_long=is_long_format)
                            except Exception as e:
                                logger.warning(f"画像マッピングの更新に失敗しました: {e}")
                            
                            st.success(f"✅ 画像を生成しました！")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ 画像生成に失敗しました: {e}")
                            logger.error(f"画像生成エラー: {e}")
    
    # 生成された画像の一覧（シーン番号でソートして表示）
    if st.session_state.generated_images:
        st.markdown("---")
        st.subheader("📁 生成された画像ファイル")
        sorted_items = sorted(
            st.session_state.generated_images.items(),
            key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0
        )
        cols = st.columns(3)
        for idx, (scene_key, image_path) in enumerate(sorted_items):
            path = _normalize_image_path(image_path)
            image_bytes = _read_image_bytes(path)
            with cols[idx % 3]:
                st.markdown(f"**シーン {scene_key}**")
                if image_bytes is not None:
                    st.image(image_bytes, width=200)
                    processor = ImageProcessor()
                    width, height = processor.get_image_size(path)
                    st.caption(f"{path.name}\n({width}x{height})")
                    with st.expander("🔍 拡大表示"):
                        st.image(image_bytes, use_container_width=True)
                    ext = (path.suffix or ".png").lower().lstrip(".")
                    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
                    st.download_button(
                        label="⬇️ ダウンロード",
                        data=image_bytes,
                        file_name=path.name,
                        mime=mime,
                        key=f"download_{scene_key}",
                        use_container_width=True
                    )
                else:
                    st.warning(f"画像を読み込めません: {path}")
                    st.caption(f"パス: {path}")
