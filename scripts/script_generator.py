"""
台本生成モジュール
GPT-4oを使用して台本を生成
"""
from typing import Optional
from openai import OpenAI

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
    
    def extract_insights(self, reference_script: str) -> list[str]:
        """
        参考台本から視聴者のインサイトを抽出
        
        Args:
            reference_script: 参考台本のテキスト
        
        Returns:
            list[str]: 抽出されたインサイトのリスト
        """
        logger.info("視聴者インサイトの抽出を開始")
        
        prompt = f"""
以下の参考台本を分析して、視聴者がこの動画から得たいと考えている「インサイト」や「価値」を抽出してください。

【参考台本】
{reference_script}

【タスク】
1. この台本が視聴者に提供している価値や情報を分析する
2. 視聴者がこの動画を見ることで満たしたい欲求やニーズを特定する
3. 視聴者の潜在的な関心事や興味を深堀りする

【出力形式】
以下のJSON形式で出力してください：

{{
  "insights": [
    "インサイト1（視聴者が求めている価値や情報）",
    "インサイト2",
    "インサイト3"
  ]
}}

【注意事項】
- インサイトは具体的で、行動可能な形で記述してください
- 視聴者の心理やニーズを深く理解した内容にしてください
- 3〜7個程度のインサイトを抽出してください
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはマーケティングとコンテンツ分析の専門家です。視聴者の心理やニーズを深く理解し、価値のあるインサイトを抽出してください。"
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
            
            logger.info(f"インサイト抽出が完了しました: {len(insights)}個のインサイトを抽出")
            return insights
        
        except Exception as e:
            logger.error(f"インサイト抽出に失敗しました: {e}")
            raise
    
    def generate_script(
        self,
        topic: str,
        duration: int = 60,
        num_scenes: int = 5,
        style: str = "エンターテイメント",
        reference_script: Optional[str] = None,
        insights: Optional[list[str]] = None,
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
            instruction: 台本生成指示（オプション）
        
        Returns:
            dict: 台本データ（JSON形式、insightsフィールドを含む）
        """
        logger.info(f"台本生成を開始: トピック={topic}, 時間={duration}秒, シーン数={num_scenes}")
        
        # 参考台本がある場合はインサイトを抽出
        extracted_insights = None
        if reference_script and reference_script.strip():
            if insights is None:
                extracted_insights = self.extract_insights(reference_script)
            else:
                extracted_insights = insights
        
        # プロンプトの作成
        prompt = self._create_prompt(
            topic=topic,
            duration=duration,
            num_scenes=num_scenes,
            style=style,
            insights=extracted_insights,
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
            
            # インサイトを追加
            if extracted_insights:
                script_data["insights"] = extracted_insights
            
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
{insights_instruction}{instruction_text}

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画のタイトル",
  "description": "動画の説明",
  "scenes": [
    {{
      "scene_number": 1,
      "dialogue": "このシーンのセリフ（ナレーション）",
      "image_prompt": "このシーン用の画像を生成するためのプロンプト（詳細で具体的に）",
      "duration": {scene_duration:.1f},
      "subtitle": "字幕として表示するテキスト"
    }}
  ],
  "total_duration": {duration}
}}

【注意事項】
- 各シーンのdialogueは、視聴者の興味を引く内容にしてください
- image_promptは、DALL-E 3で画像生成するための詳細なプロンプトにしてください（日本語でOK）
- subtitleは、dialogueを短く要約した字幕用テキストにしてください
- すべてのシーンを配列で出力してください
"""
        return prompt
    
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
