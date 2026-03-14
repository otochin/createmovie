"""
台本生成ページ
"""
import streamlit as st
import json

from scripts.script_generator import ScriptGenerator, normalize_reference_scripts_with_openai
from scripts.script_validator import ScriptValidator
from scripts.script_parser import ScriptParser
from utils.file_manager import file_manager
from utils.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)


def show_script_page():
    """台本生成ページを表示"""
    st.header("📝 台本生成")
    st.markdown("---")
    
    # セッションステートの初期化
    if "script_data" not in st.session_state:
        st.session_state.script_data = None
    if "script_generator" not in st.session_state:
        try:
            st.session_state.script_generator = ScriptGenerator()
        except ValueError as e:
            st.error(f"⚠️ {e}")
            st.info("`.env`ファイルに`OPENAI_API_KEY`を設定してください。")
            return
    
    # セッションステートの初期化（インサイトと知識用）
    if "extracted_insights" not in st.session_state:
        st.session_state.extracted_insights = None
    if "extracted_knowledge" not in st.session_state:
        st.session_state.extracted_knowledge = None
    if "extracted_core_part" not in st.session_state:
        st.session_state.extracted_core_part = None
    if "script_edit_mode" not in st.session_state:
        st.session_state.script_edit_mode = False
    if "editing_script_path" not in st.session_state:
        st.session_state.editing_script_path = None
    if "selected_script_for_edit" not in st.session_state:
        st.session_state.selected_script_for_edit = "選択してください..."

    # 台本生成フォームの初期値（キーが無いときだけ初期化）
    _default_instruction = "- かわいい女性が読み上げるセリフにすること\n- 最初にオープニングと、最後にエンディングもつけること\n- 最初のシーン（冒頭3〜5秒）では、問いかけ・驚き・共感の一言など、視聴者が離脱しないよう必ずフックを入れること\n- 雑学の根拠や理由を深堀りして視聴者に教えてあげること\n- 今回のテーマの核心部分は動画の最後のほうで説明すること。動画の前半はできるだけ興味を引かせることに留めておき、核心部分は動画の後半で説明することで、なるべく動画を最後まで見てもらえるような台本構成にすること"
    _style_options = ["エンターテイメント", "教育", "ニュース", "コメディ", "ドキュメンタリー", "その他"]
    if "script_page_topic" not in st.session_state:
        st.session_state.script_page_topic = ""
    if "script_page_reference_script" not in st.session_state:
        st.session_state.script_page_reference_script = ""
    if "script_page_reference_script_core" not in st.session_state:
        st.session_state.script_page_reference_script_core = ""
    if "script_page_reference_metadata" not in st.session_state:
        st.session_state.script_page_reference_metadata = ""
    if "script_page_instruction" not in st.session_state:
        st.session_state.script_page_instruction = _default_instruction
    if "script_page_duration" not in st.session_state:
        st.session_state.script_page_duration = 180
    if "script_page_num_scenes" not in st.session_state:
        st.session_state.script_page_num_scenes = 18
    if "script_page_style" not in st.session_state:
        st.session_state.script_page_style = "教育"

    # 動画検索から渡されたメタデータがあれば reference_metadata の初期値に使う（未入力時のみ）
    if st.session_state.get("reference_metadata_from_search") and not st.session_state.script_page_reference_metadata:
        st.session_state.script_page_reference_metadata = st.session_state.reference_metadata_from_search

    # 入力欄
    st.subheader("台本生成設定")
    
    topic = st.text_input(
        "トピック・テーマ",
        value=st.session_state.script_page_topic,
        placeholder="例: 人工知能の最新動向",
        help="動画のテーマやトピックを入力してください",
        key="script_page_topic",
    )
    
    reference_script = st.text_area(
        "参考台本",
        value=st.session_state.script_page_reference_script,
        placeholder="参考にしたい台本を貼り付けてください（オプション）\n\n例:\nシーン1: 今日はAIの最新技術についてお話しします...",
        help="参考にしたい台本を入力すると、視聴者のインサイトを抽出して、そのインサイトを満足させる台本を生成します",
        height=150,
        key="script_page_reference_script",
    )
    
    reference_script_core = st.text_area(
        "参考台本核心部",
        value=st.session_state.script_page_reference_script_core,
        placeholder="参考台本のうち、核心部分だと思うセリフ・パートを貼り付けてください（オプション）\n\n例:\nつまり〇〇ということが言えるんです。...",
        help="ここに入れた内容を手がかりに、参考台本から「核心部分」を抽出します。空欄の場合は参考台本全体から自動で抽出します。",
        height=80,
        key="script_page_reference_script_core",
    )

    reference_metadata = st.text_area(
        "人気動画のタイトル・概要（参考・オプション）",
        value=st.session_state.script_page_reference_metadata,
        placeholder="動画検索で「タイトル・概要をコピー」→「クリップボードにコピー」した内容をここに貼り付けてください（オプション）",
        help="関連動画として認識されやすいように、重要キーワードや論点を title / description に自然に反映します（文言の丸ごとコピーはしません）。動画検索でコピーした場合はここに貼り付けてください。",
        height=100,
        key="script_page_reference_metadata",
    )
    
    instruction = st.text_area(
        "台本生成指示",
        value=st.session_state.script_page_instruction,
        placeholder="台本生成時の特別な指示を入力してください（オプション）\n\n例:\n- 専門用語は避けて、わかりやすい言葉で説明してください\n- 冒頭で視聴者の注意を引くフックを入れてください\n- 各シーンで具体的な例を1つずつ挙げてください",
        help="台本生成時に考慮してほしい特別な指示や要件を入力できます",
        height=100,
        key="script_page_instruction",
    )
    
    col1, col2 = st.columns(2)
    with col1:
        duration = st.number_input(
            "動画の総時間（秒）",
            min_value=15,
            max_value=300,
            value=st.session_state.script_page_duration,
            step=5,
            help="YouTubeショートは60秒以内が推奨です",
            key="script_page_duration",
        )
    
    with col2:
        num_scenes = st.number_input(
            "シーン数",
            min_value=3,
            max_value=20,
            value=st.session_state.script_page_num_scenes,
            step=1,
            help="シーン数を指定してください",
            key="script_page_num_scenes",
        )
    
    _style_index = _style_options.index(st.session_state.script_page_style) if st.session_state.script_page_style in _style_options else 1
    style = st.selectbox(
        "スタイル",
        _style_options,
        index=_style_index,
        help="動画のスタイルを選択してください",
        key="script_page_style",
    )
    
    submitted = st.button("🚀 台本を生成", use_container_width=True)
    
    # ボタン押下時は session_state の最新値を変数に反映（key 付きウィジェットは既に session_state を更新済み）
    if submitted:
        topic = st.session_state.script_page_topic
        reference_script = st.session_state.script_page_reference_script
        reference_script_core = st.session_state.script_page_reference_script_core
        reference_metadata = st.session_state.script_page_reference_metadata
        instruction = st.session_state.script_page_instruction
        duration = st.session_state.script_page_duration
        num_scenes = st.session_state.script_page_num_scenes
        style = st.session_state.script_page_style
    
    # 台本生成処理
    if submitted:
        if not topic:
            st.error("トピックを入力してください。")
            return
        
        try:
            generator = st.session_state.script_generator
            cleaned_reference_script = reference_script.strip() if reference_script and reference_script.strip() else ""
            cleaned_reference_script_core = reference_script_core.strip() if reference_script_core and reference_script_core.strip() else None

            # 整えた参考台本の表示用（今回参考台本が無い場合はクリア）
            st.session_state.normalized_reference_script = None
            st.session_state.normalized_reference_script_core = None

            # 参考台本がある場合: OpenAIで性教育動画台本として整える前処理（誤字脱字・タイムスタンプ・[音楽]等除去）
            if cleaned_reference_script:
                with st.spinner("参考台本を整えています（誤字脱字・不要表記の除去）..."):
                    try:
                        normalizer = getattr(generator, "normalize_reference_scripts", None)
                        if callable(normalizer):
                            normalized = normalizer(
                                topic=topic,
                                reference_script=cleaned_reference_script,
                                reference_script_core=cleaned_reference_script_core
                            )
                        else:
                            normalized = normalize_reference_scripts_with_openai(
                                generator.client,
                                generator.model,
                                topic,
                                cleaned_reference_script,
                                cleaned_reference_script_core
                            )
                        cleaned_reference_script = normalized.get("reference_script", "").strip()
                        cleaned_reference_script_core = normalized.get("reference_script_core")
                        if cleaned_reference_script_core is not None:
                            cleaned_reference_script_core = cleaned_reference_script_core.strip() or None
                        st.session_state.normalized_reference_script = cleaned_reference_script
                        st.session_state.normalized_reference_script_core = cleaned_reference_script_core
                        st.success("✅ 参考台本を整えました")
                    except Exception as e:
                        st.error(f"❌ 参考台本の整えに失敗しました: {e}")
                        logger.error(f"参考台本正規化エラー: {e}")
                        return

            # 参考台本がある場合は、整えたテキストでインサイトと知識を抽出
            if cleaned_reference_script:
                with st.spinner("参考台本から視聴者インサイトと知識を抽出中..."):
                    try:
                        extraction_result = generator.extract_insights_and_knowledge(
                            cleaned_reference_script,
                            reference_core_hint=cleaned_reference_script_core
                        )
                        extracted_insights = extraction_result.get("insights", [])
                        extracted_knowledge = extraction_result.get("knowledge", [])
                        extracted_core_part = extraction_result.get("core_part", "") or ""
                        st.session_state.extracted_insights = extracted_insights
                        st.session_state.extracted_knowledge = extracted_knowledge
                        st.session_state.extracted_core_part = extracted_core_part
                        st.success(f"✅ {len(extracted_insights)}個のインサイトと{len(extracted_knowledge)}個の知識と核心部分を抽出しました")
                    except Exception as e:
                        st.error(f"❌ インサイトと知識の抽出に失敗しました: {e}")
                        logger.error(f"インサイトと知識の抽出エラー: {e}")
                        return
            else:
                st.session_state.extracted_insights = None
                st.session_state.extracted_knowledge = None
                st.session_state.extracted_core_part = None

            # 台本を生成（整えた参考台本・核心部を使用）
            with st.spinner("台本を生成中..."):
                script_data = generator.generate_script(
                    topic=topic,
                    duration=duration,
                    num_scenes=num_scenes,
                    style=style,
                    reference_script=cleaned_reference_script if cleaned_reference_script else None,
                    insights=st.session_state.extracted_insights,
                    knowledge=st.session_state.extracted_knowledge,
                    core_part=st.session_state.extracted_core_part,
                    reference_core_hint=cleaned_reference_script_core,
                    instruction=instruction if instruction and instruction.strip() else None,
                    reference_metadata=reference_metadata if reference_metadata and reference_metadata.strip() else None
                )
                
                # 検証と正規化
                script_data = ScriptParser.validate_and_normalize(script_data)
                # 台本ファイルに保存する追加項目（音声・画像・動画編集画面で表示するため）
                script_data["topic"] = topic
                script_data["reference_script_normalized"] = cleaned_reference_script or ""
                script_data["reference_script_core_normalized"] = (cleaned_reference_script_core or "").strip() or ""
                script_data["reference_metadata"] = (reference_metadata or "").strip() or ""
                # タグは「人気動画のタイトル・概要（参考）」のみから抽出する
                if (reference_metadata or "").strip():
                    with st.spinner("人気動画のタイトル・概要からタグを抽出中..."):
                        try:
                            script_data["suggested_tags"] = generator.extract_tags_from_reference_metadata(
                                (reference_metadata or "").strip()
                            )
                        except Exception as e:
                            logger.warning(f"タグの抽出に失敗しました: {e}")
                            script_data["suggested_tags"] = []
                else:
                    script_data["suggested_tags"] = []
                # 人気動画のタイトル・概要を参考にしたタイトル案・概要案を生成して保存
                if (reference_metadata or "").strip():
                    with st.spinner("人気動画を参考にタイトル・概要案を生成中..."):
                        try:
                            suggestions = generator.generate_title_description_suggestions(
                                script_data, (reference_metadata or "").strip()
                            )
                            script_data["suggested_title_from_reference"] = suggestions.get("suggested_title_from_reference", "") or ""
                            script_data["suggested_description_from_reference"] = suggestions.get("suggested_description_from_reference", "") or ""
                        except Exception as e:
                            logger.warning(f"タイトル・概要案の生成に失敗しました: {e}")
                            script_data["suggested_title_from_reference"] = ""
                            script_data["suggested_description_from_reference"] = ""
                else:
                    script_data["suggested_title_from_reference"] = ""
                    script_data["suggested_description_from_reference"] = ""

                # セッションステートに保存
                st.session_state.script_data = script_data
                
                # 台本を自動保存して、編集用に選択状態にする
                try:
                    filename = file_manager.generate_filename("script", "json")
                    filepath = file_manager.save_script(script_data, filename)
                    st.session_state.editing_script_path = filepath
                    st.session_state.selected_script_for_edit = filename
                    logger.info(f"台本を自動保存しました: {filename}")
                    st.success("✅ 台本の生成が完了しました！台本は自動保存されました。")
                    # 画面を更新してセレクトボックスに反映
                    st.rerun()
                except Exception as e:
                    logger.warning(f"台本の自動保存に失敗しました: {e}")
                    # 自動保存に失敗しても台本生成は成功とする
                    st.success("✅ 台本の生成が完了しました！")
                
                logger.info("台本生成が成功しました")
        
        except Exception as e:
            st.error(f"❌ 台本の生成に失敗しました: {e}")
            logger.error(f"台本生成エラー: {e}")
    
    # 整えた参考台本・参考台本核心部の表示
    if st.session_state.get("normalized_reference_script") or st.session_state.get("normalized_reference_script_core"):
        st.markdown("---")
        st.subheader("📋 整えた参考台本（性教育動画台本として整形済み）")
        if st.session_state.get("normalized_reference_script"):
            st.text_area(
                "整えた参考台本",
                value=st.session_state.normalized_reference_script,
                height=200,
                disabled=True,
                key="display_normalized_script",
                label_visibility="collapsed"
            )
        if st.session_state.get("normalized_reference_script_core"):
            st.markdown("**整えた参考台本核心部**")
            st.text_area(
                "整えた参考台本核心部",
                value=st.session_state.normalized_reference_script_core,
                height=120,
                disabled=True,
                key="display_normalized_core",
                label_visibility="collapsed"
            )

    # 抽出されたインサイト・知識・核心部分の表示
    if st.session_state.extracted_insights or st.session_state.extracted_knowledge or st.session_state.extracted_core_part:
        st.markdown("---")
        
        if st.session_state.extracted_insights:
            st.subheader("💡 抽出された視聴者インサイト")
            for i, insight in enumerate(st.session_state.extracted_insights, 1):
                st.markdown(f"{i}. {insight}")
        
        if st.session_state.extracted_knowledge:
            st.markdown("---")
            st.subheader("📚 抽出された知識")
            for i, knowledge_item in enumerate(st.session_state.extracted_knowledge, 1):
                st.markdown(f"{i}. {knowledge_item}")
        
        if st.session_state.extracted_core_part:
            st.markdown("---")
            st.subheader("🎯 抽出された核心部分")
            st.info(st.session_state.extracted_core_part)
    
    # 既存の台本を読み込んで編集
    st.markdown("---")
    st.subheader("📂 既存の台本を読み込んで編集")
    
    script_files = file_manager.list_scripts()
    if script_files:
        script_file_options = {f.name: f for f in script_files}
        options = ["選択してください..."] + list(script_file_options.keys())
        
        # デフォルト値を設定（生成した台本がある場合はそれを選択）
        default_index = 0
        if st.session_state.selected_script_for_edit != "選択してください...":
            if st.session_state.selected_script_for_edit in script_file_options:
                default_index = options.index(st.session_state.selected_script_for_edit)
        
        selected_script_name = st.selectbox(
            "編集する台本を選択",
            options=options,
            index=default_index,
            help="既存の台本を読み込んで編集できます"
        )
        
        # 選択が変更された場合はセッションステートを更新
        if selected_script_name != st.session_state.selected_script_for_edit:
            st.session_state.selected_script_for_edit = selected_script_name
        
        if selected_script_name != "選択してください...":
            if st.button("📖 台本を読み込む", use_container_width=True):
                try:
                    selected_script_path = script_file_options[selected_script_name]
                    script_data = file_manager.load_script(selected_script_path)
                    st.session_state.script_data = script_data
                    st.session_state.editing_script_path = selected_script_path
                    st.session_state.selected_script_for_edit = selected_script_name
                    st.session_state.script_edit_mode = True
                    st.success(f"✅ 台本を読み込みました: {selected_script_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 台本の読み込みに失敗しました: {e}")
                    logger.error(f"台本読み込みエラー: {e}")
    
    # 生成された台本または読み込んだ台本の表示・編集
    if st.session_state.script_data:
        st.markdown("---")
        st.subheader("📄 生成された台本")
        
        script_data = st.session_state.script_data.copy()  # 編集用にコピー
        
        # 編集モードの切り替え
        col_edit1, col_edit2 = st.columns([1, 4])
        with col_edit1:
            edit_mode = st.checkbox("✏️ 編集モード", value=st.session_state.script_edit_mode, key="edit_mode_checkbox")
            if edit_mode != st.session_state.script_edit_mode:
                st.session_state.script_edit_mode = edit_mode
                st.rerun()
        
        if st.session_state.script_edit_mode:
            # 編集モード
            st.info("💡 編集モード：台本の内容を編集できます。編集後は「💾 変更を保存」ボタンで保存してください。")
            
            # タイトルと説明の編集
            script_data["title"] = st.text_input(
                "タイトル",
                value=script_data.get('title', ''),
                key="edit_title"
            )
            
            script_data["description"] = st.text_area(
                "説明",
                value=script_data.get('description', ''),
                height=100,
                key="edit_description"
            )
            
            st.markdown("---")
            st.markdown("### シーン編集")
            
            # 各シーンの編集
            scenes = script_data.get("scenes", [])
            for idx, scene in enumerate(scenes):
                scene_number = scene.get('scene_number', idx + 1)
                with st.expander(f"シーン {scene_number} - {scene.get('duration', 0):.1f}秒", expanded=False):
                    # セリフの編集
                    dialogue = st.text_area(
                        "セリフ",
                        value=scene.get('dialogue', ''),
                        height=100,
                        key=f"edit_dialogue_{idx}"
                    )
                    scenes[idx]["dialogue"] = dialogue
                    
                    # dialogue_for_ttsの編集（手動編集可能）
                    current_dialogue_for_tts = scene.get('dialogue_for_tts', '')
                    if not current_dialogue_for_tts and dialogue:
                        # 既存のdialogue_for_ttsがない場合は自動生成
                        generator = st.session_state.script_generator
                        current_dialogue_for_tts = generator._convert_to_hiragana(dialogue)
                    
                    dialogue_for_tts = st.text_area(
                        "音声読み上げ用テキスト（ひらがな）",
                        value=current_dialogue_for_tts,
                        height=80,
                        help="音声読み上げAIが読み上げるテキストです。漢字をひらがなに変換したテキストを入力してください。空欄の場合は自動生成されます。",
                        key=f"edit_dialogue_for_tts_{idx}"
                    )
                    
                    # 自動生成ボタン
                    col_tts1, col_tts2 = st.columns([3, 1])
                    with col_tts1:
                        if not dialogue_for_tts and dialogue:
                            st.caption("💡 セリフから自動生成する場合は「自動生成」ボタンをクリックしてください")
                    with col_tts2:
                        if st.button("🔄 自動生成", key=f"auto_generate_tts_{idx}", use_container_width=True):
                            if dialogue:
                                generator = st.session_state.script_generator
                                dialogue_for_tts = generator._convert_to_hiragana(dialogue)
                                st.session_state[f"edit_dialogue_for_tts_{idx}"] = dialogue_for_tts
                                st.rerun()
                    
                    scenes[idx]["dialogue_for_tts"] = dialogue_for_tts
                    
                    # 字幕の編集
                    scenes[idx]["subtitle"] = st.text_input(
                        "字幕",
                        value=scene.get('subtitle', ''),
                        key=f"edit_subtitle_{idx}"
                    )
                    
                    # 画像プロンプトの編集
                    scenes[idx]["image_prompt"] = st.text_area(
                        "画像プロンプト",
                        value=scene.get('image_prompt', ''),
                        height=80,
                        key=f"edit_image_prompt_{idx}"
                    )
                    
                    # 時間の編集
                    col_dur1, col_dur2 = st.columns(2)
                    with col_dur1:
                        duration = st.number_input(
                            "時間（秒）",
                            min_value=0.1,
                            max_value=60.0,
                            value=float(scene.get('duration', 3.0)),
                            step=0.1,
                            key=f"edit_duration_{idx}"
                        )
                        scenes[idx]["duration"] = duration
                    
                    with col_dur2:
                        scenes[idx]["scene_number"] = st.number_input(
                            "シーン番号",
                            min_value=1,
                            max_value=100,
                            value=scene.get('scene_number', idx + 1),
                            key=f"edit_scene_number_{idx}"
                        )
            
            script_data["scenes"] = scenes
            
            # 総時間を再計算
            total_duration = sum(scene.get("duration", 0) for scene in scenes)
            script_data["total_duration"] = total_duration
            
            st.markdown("---")
            st.markdown(f"**総時間**: {total_duration:.1f}秒")
            st.markdown(f"**シーン数**: {len(scenes)}")
            
            # 保存ボタン
            col_save1, col_save2, col_save3 = st.columns(3)
            
            with col_save1:
                if st.button("💾 変更を保存", use_container_width=True, type="primary"):
                    try:
                        if st.session_state.editing_script_path:
                            # 既存ファイルを上書き
                            filepath = file_manager.save_script(script_data, st.session_state.editing_script_path.name)
                            st.session_state.editing_script_path = filepath
                            st.session_state.selected_script_for_edit = filepath.name
                            st.success(f"✅ 台本を更新しました: {filepath.name}")
                        else:
                            # 新規保存
                            filename = file_manager.generate_filename("script", "json")
                            filepath = file_manager.save_script(script_data, filename)
                            st.session_state.editing_script_path = filepath
                            st.session_state.selected_script_for_edit = filename
                            st.success(f"✅ 台本を保存しました: {filepath.name}")
                        
                        st.session_state.script_data = script_data
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 保存に失敗しました: {e}")
                        logger.error(f"台本保存エラー: {e}")
            
            with col_save2:
                if st.button("💾 別名で保存", use_container_width=True):
                    try:
                        filename = file_manager.generate_filename("script", "json")
                        filepath = file_manager.save_script(script_data, filename)
                        st.session_state.selected_script_for_edit = filename
                        st.success(f"✅ 台本を保存しました: {filepath.name}")
                    except Exception as e:
                        st.error(f"❌ 保存に失敗しました: {e}")
                        logger.error(f"台本保存エラー: {e}")
            
            with col_save3:
                if st.button("❌ 編集をキャンセル", use_container_width=True):
                    st.session_state.script_edit_mode = False
                    if st.session_state.editing_script_path:
                        # 元のファイルを再読み込み
                        script_data = file_manager.load_script(st.session_state.editing_script_path)
                        st.session_state.script_data = script_data
                    st.rerun()
        
        else:
            # 表示モード
            # タイトルと説明
            st.markdown(f"### {script_data.get('title', 'タイトルなし')}")
            if "description" in script_data and script_data["description"]:
                st.info(script_data["description"])
            
            # 台本の詳細表示
            st.markdown("---")
            st.markdown(f"**総時間**: {script_data.get('total_duration', 0):.1f}秒")
            st.markdown(f"**シーン数**: {len(script_data.get('scenes', []))}")
            
            # サムネイル用テキスト案（GPTで3案生成＋表示・コピー）
            st.markdown("---")
            st.subheader("🖼️ サムネイル用テキスト案")
            st.caption("Canvaなどでサムネを作る際に載せる短いキャッチコピーの候補です。選択してコピーできます。")
            if "thumbnail_suggestions" not in st.session_state:
                st.session_state.thumbnail_suggestions = None
            if "last_thumbnail_script_id" not in st.session_state:
                st.session_state.last_thumbnail_script_id = None
            current_script_id = f"{script_data.get('title', '')}_{len(script_data.get('scenes', []))}"
            if st.session_state.last_thumbnail_script_id != current_script_id:
                st.session_state.thumbnail_suggestions = None
                st.session_state.last_thumbnail_script_id = current_script_id
            if st.button("✨ 3案を生成", key="generate_thumbnail_suggestions", use_container_width=True):
                try:
                    generator = st.session_state.script_generator
                    with st.spinner("サムネイル用テキスト案を生成中..."):
                        st.session_state.thumbnail_suggestions = generator.generate_thumbnail_text_suggestions(script_data)
                    st.success("✅ 3案を生成しました")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成に失敗しました: {e}")
                    logger.error(f"サムネイルテキスト案生成エラー: {e}")
            if st.session_state.thumbnail_suggestions:
                for i, text in enumerate(st.session_state.thumbnail_suggestions, 1):
                    with st.container():
                        st.markdown(f"**案{i}**")
                        st.code(text, language=None)

            # タグ案（台本生成時に suggested_tags があれば表示）
            if script_data.get("suggested_tags"):
                st.markdown("---")
                st.subheader("🏷️ タグ案")
                st.caption("アップロード時のタグ候補です（選択してコピーできます）。")
                tags = script_data.get("suggested_tags") or []
                if isinstance(tags, list) and tags:
                    st.text_area(
                        "タグ（改行区切り）",
                        value="\n".join([str(t) for t in tags if str(t).strip()]),
                        height=140,
                    )

            # 人気動画を参考にしたタイトル・概要案（台本ファイルに含まれる）
            _st_ref = (script_data.get("suggested_title_from_reference") or "").strip()
            _sd_ref = (script_data.get("suggested_description_from_reference") or "").strip()
            if _st_ref or _sd_ref:
                st.markdown("---")
                st.subheader("📌 人気動画を参考にしたタイトル・概要案")
                st.caption("「人気動画のタイトル・概要」を参考に生成した案です。アップロード時の候補として利用できます。")
                if _st_ref:
                    st.markdown("**タイトル案**")
                    st.code(_st_ref, language=None)
                if _sd_ref:
                    st.markdown("**概要案**")
                    st.text_area("", value=_sd_ref, height=80, disabled=True, key="script_page_desc_ref", label_visibility="collapsed")
            
            # 各シーンの表示
            st.markdown("---")
            st.markdown("### シーン詳細")
            
            for scene in script_data.get("scenes", []):
                with st.expander(f"シーン {scene.get('scene_number', 0)} - {scene.get('duration', 0):.1f}秒"):
                    st.markdown(f"**セリフ**: {scene.get('dialogue', '')}")
                    # 音声読み上げ用テキスト（ひらがな）がある場合は表示
                    dialogue_for_tts = scene.get('dialogue_for_tts', '')
                    if dialogue_for_tts:
                        st.markdown(f"**音声読み上げ用テキスト（ひらがな）**: {dialogue_for_tts}")
                    st.markdown(f"**字幕**: {scene.get('subtitle', '')}")
                    st.markdown(f"**画像プロンプト**: {scene.get('image_prompt', '')}")
            
            # アクションボタン
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 台本を保存", use_container_width=True):
                    try:
                        filename = file_manager.generate_filename("script", "json")
                        filepath = file_manager.save_script(script_data, filename)
                        st.session_state.editing_script_path = filepath
                        st.session_state.selected_script_for_edit = filename
                        st.success(f"✅ 台本を保存しました: {filepath.name}")
                    except Exception as e:
                        st.error(f"❌ 保存に失敗しました: {e}")
            
            with col2:
                if st.button("🔄 再生成", use_container_width=True):
                    st.session_state.script_data = None
                    st.session_state.editing_script_path = None
                    st.session_state.selected_script_for_edit = "選択してください..."
                    st.rerun()
            
            with col3:
                # JSON表示
                if st.button("📋 JSON表示", use_container_width=True):
                    st.json(script_data)
        
        # JSONダウンロード
        st.download_button(
            label="⬇️ JSONをダウンロード",
            data=json.dumps(script_data, ensure_ascii=False, indent=2),
            file_name=file_manager.generate_filename("script", "json"),
            mime="application/json",
            use_container_width=True
        )
