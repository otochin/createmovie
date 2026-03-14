"""
台本生成ページ
"""
import streamlit as st
import json

from scripts.script_generator import ScriptGenerator
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
    
    # 入力フォーム
    with st.form("script_generation_form"):
        st.subheader("台本生成設定")
        
        topic = st.text_input(
            "トピック・テーマ",
            placeholder="例: 人工知能の最新動向",
            help="動画のテーマやトピックを入力してください"
        )
        
        reference_script = st.text_area(
            "参考台本",
            placeholder="参考にしたい台本を貼り付けてください（オプション）\n\n例:\nシーン1: 今日はAIの最新技術についてお話しします...",
            help="参考にしたい台本を入力すると、視聴者のインサイトを抽出して、そのインサイトを満足させる台本を生成します",
            height=150
        )
        
        reference_script_core = st.text_area(
            "参考台本核心部",
            placeholder="参考台本のうち、核心部分だと思うセリフ・パートを貼り付けてください（オプション）\n\n例:\nつまり〇〇ということが言えるんです。...",
            help="ここに入れた内容を手がかりに、参考台本から「核心部分」を抽出します。空欄の場合は参考台本全体から自動で抽出します。",
            height=80
        )
        
        instruction = st.text_area(
            "台本生成指示",
            value="- かわいい女性が読み上げるセリフにすること\n- 最初にオープニングと、最後にエンディングもつけること\n- 最初のシーン（冒頭3〜5秒）では、問いかけ・驚き・共感の一言など、視聴者が離脱しないよう必ずフックを入れること\n- 雑学の根拠や理由を深堀りして視聴者に教えてあげること\n- 今回のテーマの核心部分は動画の最後のほうで説明すること。動画の前半はできるだけ興味を引かせることに留めておき、核心部分は動画の後半で説明することで、なるべく動画を最後まで見てもらえるような台本構成にすること",
            placeholder="台本生成時の特別な指示を入力してください（オプション）\n\n例:\n- 専門用語は避けて、わかりやすい言葉で説明してください\n- 冒頭で視聴者の注意を引くフックを入れてください\n- 各シーンで具体的な例を1つずつ挙げてください",
            help="台本生成時に考慮してほしい特別な指示や要件を入力できます",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            duration = st.number_input(
                "動画の総時間（秒）",
                min_value=15,
                max_value=300,
                value=180,
                step=5,
                help="YouTubeショートは60秒以内が推奨です"
            )
        
        with col2:
            num_scenes = st.number_input(
                "シーン数",
                min_value=3,
                max_value=20,
                value=18,
                step=1,
                help="シーン数を指定してください"
            )
        
        style = st.selectbox(
            "スタイル",
            ["エンターテイメント", "教育", "ニュース", "コメディ", "ドキュメンタリー", "その他"],
            index=1,
            help="動画のスタイルを選択してください"
        )
        
        submitted = st.form_submit_button("🚀 台本を生成", use_container_width=True)
    
    # 台本生成処理
    if submitted:
        if not topic:
            st.error("トピックを入力してください。")
            return
        
        try:
            generator = st.session_state.script_generator
            
            # 参考台本がある場合は、まずインサイトと知識を抽出
            if reference_script and reference_script.strip():
                with st.spinner("参考台本から視聴者インサイトと知識を抽出中..."):
                    try:
                        extraction_result = generator.extract_insights_and_knowledge(
                            reference_script,
                            reference_core_hint=reference_script_core.strip() if reference_script_core and reference_script_core.strip() else None
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
            
            # 台本を生成
            with st.spinner("台本を生成中..."):
                script_data = generator.generate_script(
                    topic=topic,
                    duration=duration,
                    num_scenes=num_scenes,
                    style=style,
                    reference_script=reference_script if reference_script and reference_script.strip() else None,
                    insights=st.session_state.extracted_insights,
                    knowledge=st.session_state.extracted_knowledge,
                    core_part=st.session_state.extracted_core_part,
                    reference_core_hint=reference_script_core.strip() if reference_script_core and reference_script_core.strip() else None,
                    instruction=instruction if instruction and instruction.strip() else None
                )
                
                # 検証と正規化
                script_data = ScriptParser.validate_and_normalize(script_data)
                
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
