"""
台本生成モジュール
GPT-4oを使用して台本を生成
"""
import json
from typing import Optional
from openai import OpenAI
import pykakasi

from config.config import config
from config.constants import OPENAI_MODEL
from utils.logger import get_logger

logger = get_logger(__name__)


def normalize_reference_scripts_with_openai(
    client,
    model: str,
    topic: str,
    reference_script: str,
    reference_script_core: Optional[str] = None
) -> dict:
    """
    OpenAIで参考台本・参考台本核心部を性教育動画の台本として整える。
    誤字脱字の修正、タイムスタンプ・[音楽]などの不要テキストの除去を行う。

    Args:
        client: OpenAI クライアント
        model: モデル名
        topic: トピック・テーマ
        reference_script: 参考台本の生テキスト
        reference_script_core: 参考台本核心部の生テキスト（オプション）

    Returns:
        dict: {"reference_script": str, "reference_script_core": str or None}
    """
    if not reference_script or not reference_script.strip():
        return {"reference_script": "", "reference_script_core": (reference_script_core or "").strip() or None}

    has_core = reference_script_core and reference_script_core.strip()
    core_section = ""
    if has_core:
        core_section = f"""
【参考台本核心部（ユーザー入力）】
以下も同様に、性教育動画の台本として整え、誤字脱字・タイムスタンプ・[音楽]等の不要表記を除去したテキストに修正してください。

{reference_script_core.strip()}
"""

    prompt = f"""
【トピック・テーマ】
{topic}

【タスク】
「参考台本」のテキストを、上記トピックに合わせた「性教育動画の台本」として整えてください。
{core_section}

【参考台本（ユーザー入力）】
{reference_script.strip()}

【整える際のルール】
1. 誤字脱字を修正する
2. タイムスタンプ（例: 0:00、1:23、(0:15) など）をすべて削除する
3. [音楽]、[BGM]、[効果音] など、括弧で囲まれた演出指示・不要なテキストを削除する
4. 内容は変えず、読みやすい台本テキストのみを残す
5. 性教育動画として不自然でない言い回しに微修正してよい（事実は変えない）
6. 出力は「整えた参考台本」と「整えた参考台本核心部」（核心部がある場合のみ）の2つ

【出力形式】
以下のJSON形式で出力してください。
- reference_script: 整えた参考台本（1本のテキスト）
- reference_script_core: 核心部を入力していた場合のみ、整えた参考台本核心部。なければ null

{{
  "reference_script": "整えた参考台本の全文",
  "reference_script_core": "整えた参考台本核心部の全文"
}}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "あなたは動画台本の編集者です。誤字脱字の修正と、タイムスタンプ・演出表記の除去を行い、正確な台本テキストに整えてください。"
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    data = json.loads(response.choices[0].message.content)
    out_script = (data.get("reference_script") or "").strip()
    out_core = data.get("reference_script_core")
    if out_core is not None:
        out_core = (out_core or "").strip() or None
    if not has_core:
        out_core = (reference_script_core or "").strip() or None
    logger.info("参考台本の正規化が完了しました")
    return {"reference_script": out_script, "reference_script_core": out_core}


class ScriptGenerator:
    """台本生成クラス"""
    
    def __init__(self):
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")
        
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = OPENAI_MODEL
        # pykakasiの初期化（漢字→ひらがな変換用）
        self.kks = pykakasi.kakasi()

    def normalize_reference_scripts(
        self,
        topic: str,
        reference_script: str,
        reference_script_core: Optional[str] = None
    ) -> dict:
        """
        参考台本と参考台本核心部を、トピックに合わせた性教育動画の台本として整える前処理。
        OpenAI で誤字脱字の修正、タイムスタンプ・[音楽]などの不要テキストの除去を行う。

        Returns:
            dict: {"reference_script": str, "reference_script_core": str or None}
        """
        return normalize_reference_scripts_with_openai(
            self.client,
            self.model,
            topic,
            reference_script,
            reference_script_core
        )

    
    def extract_insights_and_knowledge(self, reference_script: str, reference_core_hint: Optional[str] = None) -> dict:
        """
        参考台本から視聴者のインサイトと知識と核心部分を抽出
        
        Args:
            reference_script: 参考台本のテキスト
            reference_core_hint: ユーザーが「参考台本核心部」として指定したテキスト（オプション）。核心部分の抽出の手がかりとして利用する
        
        Returns:
            dict: {"insights": [...], "knowledge": [...], "core_part": str}の形式
        """
        logger.info("視聴者インサイト・知識・核心部分の抽出を開始")
        
        core_hint_section = ""
        if reference_core_hint and reference_core_hint.strip():
            core_hint_section = f"""
【ユーザーが指定した「参考台本核心部」】
ユーザーが、参考台本のうち核心部分だと思うとして以下のテキストを指定しています。この内容を手がかりに、参考台本全体を踏まえて「核心部分」を1文で要約してください。

{reference_core_hint.strip()}

"""
        
        prompt = f"""
以下の参考台本を分析して、以下の3つを抽出してください：

1. 視聴者がこの動画から得たいと考えている「インサイト」や「価値」
2. この台本から学べる「知識」や「情報」（事実、データ、専門知識、ノウハウなど）
3. この台本の「核心部分」：動画全体のなかで最も重要なメッセージ・結論・オチ（一番伝えたいこと）
{core_hint_section}
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

3. 核心部分の抽出：
   - この台本の「一番言いたいこと」「結論」「オチ」を1つに要約する
   - 動画の後半で語られていることが多い、本題の中心となる内容
   - 「参考台本核心部」が指定されている場合は、その内容を反映した要約にすること
   - 新しい台本を生成する際に「核心パート」として後半で必ず反映させるべき内容

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
  ],
  "core_part": "この台本の核心部分（一番重要なメッセージ・結論を1文で要約）"
}}

【注意事項】
- インサイトは具体的で、行動可能な形で記述してください
- 知識は具体的な事実や情報として記述してください（例：「〇〇は△△である」「〇〇の方法は△△である」など）
- core_partは1文で、動画の「本題の核心」を要約してください。新しい台本ではこの内容を後半の核心パートで必ず反映させます
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
            
            result = json.loads(response.choices[0].message.content)
            insights = result.get("insights", [])
            knowledge = result.get("knowledge", [])
            core_part = result.get("core_part", "") or ""
            if isinstance(core_part, list):
                core_part = core_part[0] if core_part else ""
            core_part = str(core_part).strip()
            
            logger.info(f"インサイト・知識・核心部分の抽出が完了: インサイト{len(insights)}個、知識{len(knowledge)}個、核心部分1件")
            return {"insights": insights, "knowledge": knowledge, "core_part": core_part}
        
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
    
    def generate_thumbnail_text_suggestions(self, script_data: dict) -> list[str]:
        """
        台本をもとに、サムネイルに載せる短いテキストを3案生成する。
        Canvaなどでサムネを作る際の文言候補として使える。
        
        Args:
            script_data: 台本データ（title, description, scenes を含む）
        
        Returns:
            list[str]: サムネイル用テキストの候補（最大3件）
        """
        title = script_data.get("title", "") or "タイトルなし"
        description = script_data.get("description", "") or ""
        scenes = script_data.get("scenes", [])
        first_subtitle = ""
        first_dialogue = ""
        if scenes:
            first_subtitle = scenes[0].get("subtitle", "") or ""
            first_dialogue = (scenes[0].get("dialogue", "") or "")[:200]
        
        prompt = f"""
以下の動画台本の内容を踏まえ、YouTubeのサムネイルに載せる「短いキャッチコピー」を3案考えてください。
サムネイルは一覧で目を引く必要があるため、短く・印象的で・つい衝動的にクリックしたくなるような文言にしてください。

【動画タイトル】
{title}

【動画の説明】
{description}

【冒頭の字幕】
{first_subtitle}

【冒頭のセリフ（抜粋）】
{first_dialogue}

【条件】
- 各案は日本語で、サムネイルに収まる長さにすること（目安：5〜15文字程度。長くても20文字以内）
- 疑問形・数字・驚き・共感など、クリックしたくなる表現を推奨
- 3案はなるべくトーンや切り口を変えて、バリエーションをつける

【出力形式】
以下のJSON形式のみで出力してください。説明や余計な文字は不要です。
{{"suggestions": ["案1のテキスト", "案2のテキスト", "案3のテキスト"]}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはYouTubeのサムネイル・タイトル設計の専門家です。短く印象的で、クリック率が高くなるキャッチコピーを考えてください。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            suggestions = result.get("suggestions", [])
            if not isinstance(suggestions, list):
                suggestions = []
            # 最大3件、文字列のみ
            out = [str(s).strip() for s in suggestions[:3] if s]
            logger.info(f"サムネイル用テキスト案を生成しました: {len(out)}件")
            return out
        except Exception as e:
            logger.error(f"サムネイル用テキスト案の生成に失敗しました: {e}")
            raise

    def generate_title_description_suggestions(
        self,
        script_data: dict,
        reference_metadata: str
    ) -> dict:
        """
        人気動画のタイトル・概要（reference_metadata）だけを参考に、
        表現を少し変えたタイトル案・概要案を1件ずつ生成する。本編の内容は参照しない。

        Args:
            script_data: 呼び出し互換用（プロンプトでは使用しない）
            reference_metadata: 人気動画のタイトル・概要テキスト

        Returns:
            dict: {"suggested_title_from_reference": str, "suggested_description_from_reference": str}
        """
        if not (reference_metadata and reference_metadata.strip()):
            return {"suggested_title_from_reference": "", "suggested_description_from_reference": ""}

        prompt = f"""
【人気動画のタイトル・概要（参考）】
以下は、人気動画のタイトル・概要です。このテキスト**だけ**を材料にしてください。

{reference_metadata.strip()}

【タスク】
上記「人気動画のタイトル・概要」の**内容のみ**を参考に、「タイトル案」と「概要案」を1つずつ作成してください。

【重要なルール】
- 本編の台本や動画の具体的な内容には一切触れないでください。参考にするのは上記のテキストのみです。
- そのまま写すとパクリになるため、言い回し・語順・表現を必ず変えてください（意図やトーンは似せてよい）。
- 同じキーワードやテーマは活かしつつ、別の言い方・言い換えにすること。

【出力形式】
以下のJSON形式のみで出力してください。
{{"suggested_title_from_reference": "タイトル案（1本）", "suggested_description_from_reference": "概要案（1〜3文程度）"}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはYouTubeのタイトル・説明文の設計の専門家です。与えられた人気動画のタイトル・概要の「内容だけ」を参考に、表現を少し変えたタイトル案と概要案を作成してください。本編の内容は参照せず、パクリにならないよう言い回しを変えてください。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            out_title = (result.get("suggested_title_from_reference") or "").strip()
            out_desc = (result.get("suggested_description_from_reference") or "").strip()
            logger.info("人気動画を参考にしたタイトル・概要案を生成しました")
            return {"suggested_title_from_reference": out_title, "suggested_description_from_reference": out_desc}
        except Exception as e:
            logger.error(f"タイトル・概要案の生成に失敗しました: {e}")
            raise

    def extract_tags_from_reference_metadata(self, reference_metadata: str) -> list:
        """
        「人気動画のタイトル・概要（参考）」のテキストのみからタグを抽出する。
        本編の内容は参照しない。

        Args:
            reference_metadata: 人気動画のタイトル・概要テキスト

        Returns:
            list: タグ文字列のリスト（10〜15個程度）
        """
        if not (reference_metadata and reference_metadata.strip()):
            return []
        prompt = f"""
【人気動画のタイトル・概要（参考）】
以下のテキスト**だけ**を材料にしてください。本編の台本や動画の内容は参照しないでください。

{reference_metadata.strip()}

【タスク】
上記のテキストから、動画のアップロード時に使える「タグ」を 10〜15 個程度抽出してください。
- キーワード・テーマ・検索されそうな語をタグにすること
- 日本語中心、必要に応じて英語も可
- 重複や冗長な表現は避ける
- そのままの文言でも、少し言い換えた表現でもよい（パクリにならない程度に）

【出力形式】
以下のJSON形式のみで出力してください。
{{"suggested_tags": ["タグ1", "タグ2", "タグ3", ...]}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは動画のメタデータ設計の専門家です。与えられた「人気動画のタイトル・概要」のテキストのみから、タグ候補を抽出してください。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            tags = result.get("suggested_tags", [])
            if not isinstance(tags, list):
                tags = []
            out = [str(t).strip() for t in tags if str(t).strip()][:20]
            logger.info(f"人気動画のタイトル・概要からタグを抽出しました: {len(out)}件")
            return out
        except Exception as e:
            logger.error(f"タグの抽出に失敗しました: {e}")
            raise

    def generate_script(
        self,
        topic: str,
        duration: int = 60,
        num_scenes: int = 5,
        style: str = "エンターテイメント",
        reference_script: Optional[str] = None,
        insights: Optional[list[str]] = None,
        knowledge: Optional[list[str]] = None,
        core_part: Optional[str] = None,
        reference_core_hint: Optional[str] = None,
        instruction: Optional[str] = None,
        reference_metadata: Optional[str] = None
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
            core_part: 抽出済みの核心部分（オプション、参考台本の核心を新しい台本の後半で反映）
            reference_core_hint: ユーザーが「参考台本核心部」として指定したテキスト（オプション）。抽出時に核心部分の手がかりとして利用
            instruction: 台本生成指示（オプション）
        
        Returns:
            dict: 台本データ（JSON形式、insights, knowledge, core_part を含む場合あり）
        """
        logger.info(f"台本生成を開始: トピック={topic}, 時間={duration}秒, シーン数={num_scenes}")
        
        # 参考台本がある場合はインサイト・知識・核心部分を抽出
        extracted_insights = None
        extracted_knowledge = None
        extracted_core_part = None
        if reference_script and reference_script.strip():
            if insights is None:
                # インサイト・知識・核心部分をまとめて抽出
                extraction_result = self.extract_insights_and_knowledge(
                    reference_script,
                    reference_core_hint=reference_core_hint
                )
                extracted_insights = extraction_result.get("insights", [])
                extracted_knowledge = extraction_result.get("knowledge", [])
                extracted_core_part = extraction_result.get("core_part") or None
            else:
                extracted_insights = insights
                if knowledge is None:
                    extraction_result = self.extract_insights_and_knowledge(
                        reference_script,
                        reference_core_hint=reference_core_hint
                    )
                    extracted_knowledge = extraction_result.get("knowledge", [])
                    extracted_core_part = extraction_result.get("core_part") or None
                else:
                    extracted_knowledge = knowledge
                    extracted_core_part = (core_part or "").strip() or None
        
        # プロンプトの作成
        prompt = self._create_prompt(
            topic=topic,
            duration=duration,
            num_scenes=num_scenes,
            style=style,
            insights=extracted_insights,
            knowledge=extracted_knowledge,
            core_part=extracted_core_part,
            instruction=instruction,
            reference_metadata=reference_metadata
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
            
            # インサイト・知識・核心部分を台本データに追加
            if extracted_insights:
                script_data["insights"] = extracted_insights
            if extracted_knowledge:
                script_data["knowledge"] = extracted_knowledge
            if extracted_core_part:
                script_data["core_part"] = extracted_core_part
            
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
        core_part: Optional[str] = None,
        instruction: Optional[str] = None,
        reference_metadata: Optional[str] = None
    ) -> str:
        """
        プロンプトを作成
        
        Args:
            topic: トピック
            duration: 動画の総時間（秒）
            num_scenes: シーン数
            style: スタイル
            insights: 視聴者のインサイト（オプション）
            knowledge: 参考台本から学んだ知識（オプション）
            core_part: 参考台本の核心部分（オプション、新しい台本の後半で核心パートとして反映）
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
        
        # 核心部分がある場合の追加指示
        core_part_instruction = ""
        if core_part and core_part.strip():
            core_part_instruction = f"""

【重要：核心パート】
参考台本から抽出した「核心部分」を、新しい台本の**後半（最後の1〜2シーン付近）**で必ず核心パートとして反映させてください。
動画の結論・オチ・一番伝えたいメッセージとして扱い、視聴者が最後まで見たくなるように構成してください。

【抽出された核心部分】
{core_part.strip()}

上記の内容を、新しいトピック（{topic}）に合わせた形で、台本の後半で必ず説明・伝達してください。
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

        # 人気動画のタイトル・概要（参考メタデータ）がある場合の追加指示
        reference_metadata_text = ""
        if reference_metadata and reference_metadata.strip():
            reference_metadata_text = f"""

【参考：人気動画のタイトル・概要（参考メタデータ）】
以下は、参考として貼り付けられた「人気動画のタイトル・概要（冒頭）」です。
この内容を参考に、同じテーマ・検索意図として認識されやすいように、重要キーワードや論点をあなたの台本（title/description）に自然に反映してください。

【重要ルール】
- 文言をそのままコピーしない（表現は必ず言い換える）
- 重要キーワードは「title」と「description」の両方に自然に含める
- スパムっぽくならないよう、不自然なキーワード羅列は避ける

【参考メタデータ】
{reference_metadata.strip()}
"""
        
        prompt = f"""
以下の条件でYouTubeショート動画の台本を作成してください。

【条件】
- トピック: {topic}
- 動画の総時間: {duration}秒
- シーン数: {num_scenes}シーン
- 1シーンあたりの時間: 約{scene_duration:.1f}秒
- スタイル: {style}
{insights_instruction}{knowledge_instruction}{core_part_instruction}{instruction_text}{reference_metadata_text}

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画のタイトル",
  "description": "動画の説明（最初の1〜2文で、テーマと重要キーワードを明確に書いた後、補足説明を続ける）",
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
- 読点「、」はこまめに入れてください。短いフレーズの区切り（例：「〇〇が」「〇〇を」「〇〇も」の後、修飾の切れ目など）に「、」を入れ、音声が一息で読み上げすぎないようにします。例：「実は、日常のストレスが影響していることも多いんです。」→「じつは、にちじょうの、ストレスが、えいきょうしていることも、おおいんです。」
- dialogue と意味・内容は同一にし、句読点の追加と表記の変換のみ行ってください。

【注意事項】
- 各シーンのdialogueは、視聴者の興味を引く内容にしてください
- title は短く強く、検索意図が一目で分かるようにしてください（重要キーワードを自然に含める）
- description は「最初の1〜2文」でテーマ・重要キーワード・視聴者の得られる価値を明確に書き、その後に補足や詳細を続けてください
- 各シーンのdialogueは、指定されたduration（{scene_duration:.1f}秒）に合わせて、適切な長さのセリフにしてください。目安として、1秒あたり約12〜16文字程度のセリフ量を目指してください（例：{scene_duration:.1f}秒のシーンなら約{int(scene_duration * 14)}〜{int(scene_duration * 16)}文字程度）。情報量を多めにし、詳細で具体的な説明を入れてください。
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
