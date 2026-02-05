"""
台本生成モジュール
GPT-4oを使用して台本を生成
"""
from typing import Optional
from openai import OpenAI
import pykakasi

from config.config import config
from config.constants import OPENAI_MODEL
from utils.logger import get_logger

logger = get_logger(__name__)


class ScriptGenerator:
    """台本生成クラス"""
    
    def __init__(self):
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")
        
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = OPENAI_MODEL
        # pykakasiの初期化（漢字→ひらがな変換用）
        self.kks = pykakasi.kakasi()
    
    def extract_insights_and_knowledge(self, reference_script: str) -> dict:
        """
        参考台本から視聴者のインサイトと知識を抽出
        
        Args:
            reference_script: 参考台本のテキスト
        
        Returns:
            dict: {"insights": [...], "knowledge": [...]}の形式
        """
        logger.info("視聴者インサイトと知識の抽出を開始")
        
        prompt = f"""
以下の参考台本を分析して、以下の2つを抽出してください：

1. 視聴者がこの動画から得たいと考えている「インサイト」や「価値」
2. この台本から学べる「知識」や「情報」（事実、データ、専門知識、ノウハウなど）

【参考台本】
{reference_script}

【タスク】
1. インサイトの抽出：
   - この台本が視聴者に提供している価値や情報を分析する
   - 視聴者がこの動画を見ることで満たしたい欲求やニーズを特定する
   - 視聴者の潜在的な関心事や興味を深堀りする

2. 知識の抽出：
   - この台本に含まれている具体的な事実やデータを抽出する
   - 専門知識やノウハウを抽出する
   - 視聴者が学べる具体的な情報を抽出する
   - 雑学やトリビア的な知識も含める

【出力形式】
以下のJSON形式で出力してください：

{{
  "insights": [
    "インサイト1（視聴者が求めている価値や情報）",
    "インサイト2",
    "インサイト3"
  ],
  "knowledge": [
    "知識1（具体的な事実、データ、専門知識、ノウハウなど）",
    "知識2",
    "知識3"
  ]
}}

【注意事項】
- インサイトは具体的で、行動可能な形で記述してください
- 知識は具体的な事実や情報として記述してください（例：「〇〇は△△である」「〇〇の方法は△△である」など）
- インサイトは3〜7個程度、知識は5〜10個程度を抽出してください
- 知識は、新しい台本を生成する際に活用できる具体的な情報として記述してください
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはマーケティングとコンテンツ分析の専門家です。視聴者の心理やニーズを深く理解し、価値のあるインサイトと知識を抽出してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            insights = result.get("insights", [])
            knowledge = result.get("knowledge", [])
            
            logger.info(f"インサイトと知識の抽出が完了しました: {len(insights)}個のインサイト、{len(knowledge)}個の知識を抽出")
            return {"insights": insights, "knowledge": knowledge}
        
        except Exception as e:
            logger.error(f"インサイトと知識の抽出に失敗しました: {e}")
            raise
    
    def extract_insights(self, reference_script: str) -> list[str]:
        """
        参考台本から視聴者のインサイトを抽出（後方互換性のため残す）
        
        Args:
            reference_script: 参考台本のテキスト
        
        Returns:
            list[str]: 抽出されたインサイトのリスト
        """
        result = self.extract_insights_and_knowledge(reference_script)
        return result.get("insights", [])
    
    def generate_script(
        self,
        topic: str,
        duration: int = 60,
        num_scenes: int = 5,
        style: str = "エンターテイメント",
        reference_script: Optional[str] = None,
        insights: Optional[list[str]] = None,
        knowledge: Optional[list[str]] = None,
        instruction: Optional[str] = None
    ) -> dict:
        """
        台本を生成
        
        Args:
            topic: トピックまたはテーマ
            duration: 動画の総時間（秒）
            num_scenes: シーン数
            style: スタイル（エンターテイメント、教育、ニュースなど）
            reference_script: 参考台本（オプション）
            insights: 抽出済みのインサイト（オプション、reference_scriptがある場合は自動抽出）
            knowledge: 抽出済みの知識（オプション、reference_scriptがある場合は自動抽出）
            instruction: 台本生成指示（オプション）
        
        Returns:
            dict: 台本データ（JSON形式、insightsフィールドを含む）
        """
        logger.info(f"台本生成を開始: トピック={topic}, 時間={duration}秒, シーン数={num_scenes}")
        
        # 参考台本がある場合はインサイトと知識を抽出
        extracted_insights = None
        extracted_knowledge = None
        if reference_script and reference_script.strip():
            if insights is None:
                # インサイトと知識の両方を抽出
                extraction_result = self.extract_insights_and_knowledge(reference_script)
                extracted_insights = extraction_result.get("insights", [])
                extracted_knowledge = extraction_result.get("knowledge", [])
            else:
                extracted_insights = insights
                # knowledgeが指定されていない場合は抽出する
                if knowledge is None:
                    extraction_result = self.extract_insights_and_knowledge(reference_script)
                    extracted_knowledge = extraction_result.get("knowledge", [])
                else:
                    extracted_knowledge = knowledge
        
        # プロンプトの作成
        prompt = self._create_prompt(
            topic=topic,
            duration=duration,
            num_scenes=num_scenes,
            style=style,
            insights=extracted_insights,
            knowledge=extracted_knowledge,
            instruction=instruction
        )
        
        try:
            # GPT-4oで台本を生成
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはYouTubeショート動画の台本作成の専門家です。視聴者の興味を引く、エンターテイメント性の高い台本を作成してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            script_json = response.choices[0].message.content
            import json
            script_data = json.loads(script_json)
            
            # インサイトと知識を追加
            if extracted_insights:
                script_data["insights"] = extracted_insights
            if extracted_knowledge:
                script_data["knowledge"] = extracted_knowledge
            
            # APIがdialogue_for_ttsを返していないシーンがあれば、ひらがな変換で補う
            script_data = self._ensure_tts_dialogue(script_data)
            
            logger.info("台本生成が完了しました")
            return script_data
        
        except Exception as e:
            logger.error(f"台本生成に失敗しました: {e}")
            raise
    
    def _create_prompt(
        self,
        topic: str,
        duration: int,
        num_scenes: int,
        style: str,
        insights: Optional[list[str]] = None,
        knowledge: Optional[list[str]] = None,
        instruction: Optional[str] = None
    ) -> str:
        """
        プロンプトを作成
        
        Args:
            topic: トピック
            duration: 動画の総時間（秒）
            num_scenes: シーン数
            style: スタイル
            insights: 視聴者のインサイト（オプション）
            instruction: 台本生成指示（オプション）
        
        Returns:
            str: プロンプト
        """
        scene_duration = duration / num_scenes
        
        # インサイトがある場合の追加指示
        insights_instruction = ""
        if insights:
            insights_list = "\n".join([f"- {insight}" for insight in insights])
            insights_instruction = f"""

【重要：視聴者インサイト】
以下の視聴者のインサイトを満足させるような台本を作成してください。これらのインサイトを意識して、視聴者が求めている価値や情報を提供する内容にしてください。

{insights_list}

上記のインサイトを基に、視聴者のニーズや欲求を満たすような台本を作成してください。
"""
        
        # 知識がある場合の追加指示
        knowledge_instruction = ""
        if knowledge:
            knowledge_list = "\n".join([f"- {k}" for k in knowledge])
            knowledge_instruction = f"""

【重要：参考台本から学んだ知識】
以下の知識や情報を新しい台本に活用してください。これらの知識を基に、視聴者に価値のある情報を提供する台本を作成してください。

{knowledge_list}

上記の知識を参考にしながら、新しいトピック（{topic}）に関する台本を作成してください。知識をそのまま使うのではなく、新しいトピックに応用して活用してください。
"""
        
        # 台本生成指示がある場合の追加指示
        instruction_text = ""
        if instruction and instruction.strip():
            instruction_text = f"""

【台本生成指示】
以下の指示に従って台本を作成してください。この指示を優先的に考慮し、指定された要件を満たす台本にしてください。

{instruction}

上記の指示を必ず反映させてください。
"""
        
        prompt = f"""
以下の条件でYouTubeショート動画の台本を作成してください。

【条件】
- トピック: {topic}
- 動画の総時間: {duration}秒
- シーン数: {num_scenes}シーン
- 1シーンあたりの時間: 約{scene_duration:.1f}秒
- スタイル: {style}
{insights_instruction}{knowledge_instruction}{instruction_text}

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画のタイトル",
  "description": "動画の説明",
  "scenes": [
    {{
      "scene_number": 1,
      "dialogue": "このシーンのセリフ（ナレーション）",
      "dialogue_for_tts": "このシーンの音声読み上げ用テキスト（下記のルールで作成）",
      "image_prompt": "このシーン用の画像を生成するためのプロンプト（詳細で具体的に）",
      "duration": {scene_duration:.1f},
      "subtitle": "字幕として表示するテキスト"
    }}
  ],
  "total_duration": {duration}
}}

【dialogue_for_tts のルール】
- dialogue の内容を、音声AIで自然に読み上げられる形にしたテキストを必ず出力してください。
- 漢字はひらがなにしてください。固有名詞・専門用語・外来語はカタカナのままにしてください。
- 読み上げの区切りが自然になるよう、適切な位置に読点「、」と句点「。」を入れてください（接続詞の後や、息継ぎの位置など）。
- dialogue と意味・内容は同一にし、句読点の追加と表記の変換のみ行ってください。

【注意事項】
- 各シーンのdialogueは、視聴者の興味を引く内容にしてください
- 各シーンのdialogueは、指定されたduration（{scene_duration:.1f}秒）に合わせて、適切な長さのセリフにしてください。目安として、1秒あたり約6〜8文字程度のセリフ量を目指してください（例：{scene_duration:.1f}秒のシーンなら約{int(scene_duration * 7)}〜{int(scene_duration * 8)}文字程度）
- セリフは自然な話し言葉で、指定された時間内で読み上げられる長さにしてください
- セリフは詳細で具体的な内容を含め、視聴者に価値のある情報を提供してください
- image_promptは、DALL-E 3で画像生成するための詳細なプロンプトにしてください（日本語でOK）
- subtitleは、dialogueを短く要約した字幕用テキストにしてください
- すべてのシーンを配列で出力してください
"""
        return prompt
    
    def _convert_to_hiragana(self, text: str) -> str:
        """
        テキストをひらがなに変換（カタカナはそのまま保持）
        
        Args:
            text: 変換するテキスト
        
        Returns:
            str: ひらがなに変換されたテキスト（カタカナはそのまま）
        """
        try:
            result = self.kks.convert(text)
            converted_text = ""
            for item in result:
                orig = item.get("orig", "")
                hira = item.get("hira", "")
                kana = item.get("kana", "")
                
                # カタカナの場合はそのまま保持
                if orig and self._is_katakana(orig):
                    converted_text += orig
                else:
                    # それ以外はひらがなに変換
                    converted_text += hira if hira else orig
            
            return converted_text
        except Exception as e:
            logger.warning(f"ひらがな変換に失敗しました（元のテキストを使用）: {e}")
            return text

    def _is_katakana(self, text: str) -> bool:
        """
        テキストがカタカナかどうかを判定
        
        Args:
            text: 判定するテキスト
        
        Returns:
            bool: カタカナの場合はTrue
        """
        import unicodedata
        for char in text:
            if unicodedata.name(char, '').startswith('KATAKANA'):
                return True
        return False
    
    def _ensure_tts_dialogue(self, script_data: dict) -> dict:
        """
        ［APIが返した dialogue_for_tts をそのまま利用し、
        欠けているシーンのみ dialogue からひらがな変換して dialogue_for_tts を補う。

        Args:
            script_data: 台本データ（API応答。dialogue_for_tts が含まれる場合あり）

        Returns:
            dict: 全シーンに dialogue_for_tts が入った台本データ
        """
        scenes = script_data.get("scenes", [])
        for scene in scenes:
            dialogue_for_tts = scene.get("dialogue_for_tts", "").strip()
            dialogue = scene.get("dialogue", "")
            if dialogue_for_tts:
                # APIが返した読み上げ用テキストをそのまま使用
                scene["dialogue_for_tts"] = dialogue_for_tts
                logger.debug(f"シーン{scene.get('scene_number')}のdialogue_for_ttsをAPI応答のまま使用")
            elif dialogue:
                # 未返却時は従来どおりひらがな変換で補う
                scene["dialogue_for_tts"] = self._convert_to_hiragana(dialogue)
                logger.debug(f"シーン{scene.get('scene_number')}のdialogue_for_ttsをひらがな変換で補完")
        return script_data
    
    def regenerate_scene(
        self,
        script_data: dict,
        scene_number: int,
        new_topic: Optional[str] = None
    ) -> dict:
        """
        特定のシーンを再生成
        
        Args:
            script_data: 既存の台本データ
            new_topic: 新しいトピック（オプション）
        
        Returns:
            dict: 更新された台本データ
        """
        logger.info(f"シーン{scene_number}の再生成を開始")
        
        # 実装は後で追加
        # 現時点では元のデータを返す
        return script_data
