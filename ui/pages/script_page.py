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
    
    # セッションステートの初期化（インサイト用）
    if "extracted_insights" not in st.session_state:
        st.session_state.extracted_insights = None
    
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
        
        instruction = st.text_area(
            "台本生成指示",
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
                value=60,
                step=5,
                help="YouTubeショートは60秒以内が推奨です"
            )
        
        with col2:
            num_scenes = st.number_input(
                "シーン数",
                min_value=3,
                max_value=20,
                value=5,
                step=1,
                help="シーン数を指定してください"
            )
        
        style = st.selectbox(
            "スタイル",
            ["エンターテイメント", "教育", "ニュース", "コメディ", "ドキュメンタリー", "その他"],
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
            
            # 参考台本がある場合は、まずインサイトを抽出
            if reference_script and reference_script.strip():
                with st.spinner("参考台本から視聴者インサイトを抽出中..."):
                    try:
                        extracted_insights = generator.extract_insights(reference_script)
                        st.session_state.extracted_insights = extracted_insights
                        st.success(f"✅ {len(extracted_insights)}個のインサイトを抽出しました")
                    except Exception as e:
                        st.error(f"❌ インサイト抽出に失敗しました: {e}")
                        logger.error(f"インサイト抽出エラー: {e}")
                        return
            else:
                st.session_state.extracted_insights = None
            
            # 台本を生成
            with st.spinner("台本を生成中..."):
                script_data = generator.generate_script(
                    topic=topic,
                    duration=duration,
                    num_scenes=num_scenes,
                    style=style,
                    reference_script=reference_script if reference_script and reference_script.strip() else None,
                    insights=st.session_state.extracted_insights,
                    instruction=instruction if instruction and instruction.strip() else None
                )
                
                # 検証と正規化
                script_data = ScriptParser.validate_and_normalize(script_data)
                
                # セッションステートに保存
                st.session_state.script_data = script_data
                
                st.success("✅ 台本の生成が完了しました！")
                logger.info("台本生成が成功しました")
        
        except Exception as e:
            st.error(f"❌ 台本の生成に失敗しました: {e}")
            logger.error(f"台本生成エラー: {e}")
    
    # 抽出されたインサイトの表示
    if st.session_state.extracted_insights:
        st.markdown("---")
        st.subheader("💡 抽出された視聴者インサイト")
        for i, insight in enumerate(st.session_state.extracted_insights, 1):
            st.markdown(f"{i}. {insight}")
    
    # 生成された台本の表示
    if st.session_state.script_data:
        st.markdown("---")
        st.subheader("📄 生成された台本")
        
        script_data = st.session_state.script_data
        
        # タイトルと説明
        st.markdown(f"### {script_data.get('title', 'タイトルなし')}")
        if "description" in script_data:
            st.info(script_data["description"])
        
        # 台本の詳細表示
        st.markdown("---")
        st.markdown(f"**総時間**: {script_data.get('total_duration', 0):.1f}秒")
        st.markdown(f"**シーン数**: {len(script_data.get('scenes', []))}")
        
        # 各シーンの表示
        st.markdown("---")
        st.markdown("### シーン詳細")
        
        for scene in script_data.get("scenes", []):
            with st.expander(f"シーン {scene.get('scene_number', 0)} - {scene.get('duration', 0):.1f}秒"):
                st.markdown(f"**セリフ**: {scene.get('dialogue', '')}")
                st.markdown(f"**字幕**: {scene.get('subtitle', '')}")
                st.markdown(f"**画像プロンプト**: {scene.get('image_prompt', '')}")
        
        # アクションボタン
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 台本を保存", use_container_width=True):
                try:
                    filename = file_manager.generate_filename("script", "json")
                    filepath = file_manager.save_script(script_data, filename)
                    st.success(f"✅ 台本を保存しました: {filepath.name}")
                except Exception as e:
                    st.error(f"❌ 保存に失敗しました: {e}")
        
        with col2:
            if st.button("🔄 再生成", use_container_width=True):
                st.session_state.script_data = None
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
