# YouTubeショート動画生成ツール - システム定義書

## 1. プロジェクト概要

### 1.1 目的
インプット（テキストやトピック）から「台本・音声・画像・動画」を自動生成するGUIツールを開発します。
YouTubeショート（9:16形式、1080x1920）向けの高品質な動画を効率的に作成できることを目指します。

### 1.2 実行環境
- **OS**: macOS (MacBook Pro Mシリーズ対応)
- **Python**: 3.9以上推奨
- **ブラウザ**: Chrome, Safari, Firefox等（Streamlit対応）

### 1.3 主要技術スタック
- **GUIフレームワーク**: Streamlit
- **AI API**:
  - OpenAI API (GPT-4o) - 台本生成、画像生成（DALL-E 3）
  - ElevenLabs API - 音声生成（日本語・高品質）
- **動画編集**: MoviePy
- **動画処理**: FFmpeg
- **データ形式**: JSON（台本）、MP4（動画）、MP3/WAV（音声）、PNG/JPG（画像）

---

## 2. 機能要件

### 2.1 台本作成機能
- **入力**: ユーザーがテキストやトピックを入力
- **処理**: GPT-4oを使用して台本を生成
- **出力形式**: JSON形式
  ```json
  {
    "title": "動画タイトル",
    "scenes": [
      {
        "scene_number": 1,
        "dialogue": "セリフテキスト",
        "image_prompt": "画像生成用プロンプト",
        "duration": 3.5,
        "subtitle": "字幕テキスト"
      }
    ],
    "total_duration": 60.0
  }
  ```
- **機能**:
  - 台本のプレビュー表示
  - 台本の編集・修正機能
  - 再生成機能

### 2.2 音声生成機能
- **API**: ElevenLabs API
- **言語**: 日本語
- **品質**: 高品質（premium voice推奨）
- **出力**: MP3またはWAV形式
- **機能**:
  - 各シーンの音声を個別生成
  - 音声のプレビュー再生
  - 音声の再生成機能
  - 音声ファイルの保存管理

### 2.3 画像生成機能
- **API**: OpenAI DALL-E 3
- **出力サイズ**: 1080x1920（9:16形式）
- **機能**:
  - 各シーン用の画像を自動生成
  - 画像のプレビュー表示
  - 画像の再生成機能
  - 画像ファイルの保存管理

### 2.4 動画編集機能
- **ライブラリ**: MoviePy
- **出力形式**: MP4（H.264）
- **解像度**: 1080x1920（9:16）
- **機能**:
  - 画像と音声の同期
  - 字幕の自動追加（各シーンのセリフ）
  - トランジション効果
  - 動画のプレビュー
  - 動画のエクスポート

### 2.5 GUI機能（Streamlit）
- **ワークフロー**:
  1. 入力画面：テキスト/トピック入力
  2. 台本生成：生成とプレビュー
  3. 音声生成：各シーンの音声生成とプレビュー
  4. 画像生成：各シーンの画像生成とプレビュー
  5. 動画編集：動画生成とプレビュー
  6. エクスポート：最終動画のダウンロード
- **UI要素**:
  - ステップごとの進捗表示
  - 各ステップでのプレビュー機能
  - 再生成ボタン（各ステップで利用可能）
  - 設定パネル（APIキー、音声設定等）

---

## 3. ディレクトリ構成

```
createmovie/
├── README.md                    # プロジェクト説明書
├── requirements.txt            # Python依存パッケージ
├── .env.example                # 環境変数テンプレート
├── .gitignore                  # Git除外設定
│
├── docs/                       # ドキュメント
│   ├── README_PLAN.md         # システム定義書（本ファイル）
│   ├── DEVELOPMENT_LOG.md     # 開発ログ
│   ├── CHANGELOG.md           # 変更履歴
│   └── TODO.md                # TODOリスト
│
├── main.py                     # Streamlitアプリのエントリーポイント
│
├── config/                     # 設定管理
│   ├── __init__.py
│   ├── config.py              # アプリケーション設定
│   └── constants.py           # 定数定義
│
├── scripts/                    # 台本関連
│   ├── __init__.py
│   ├── script_generator.py    # GPT-4oを使用した台本生成
│   ├── script_validator.py    # 台本の検証・整形
│   └── script_parser.py       # JSON台本のパース処理
│
├── audio/                      # 音声関連
│   ├── __init__.py
│   ├── audio_generator.py     # ElevenLabs APIを使用した音声生成
│   └── audio_processor.py     # 音声ファイルの処理・変換
│
├── images/                     # 画像関連
│   ├── __init__.py
│   ├── image_generator.py     # DALL-E 3を使用した画像生成
│   └── image_processor.py     # 画像のリサイズ・加工
│
├── video/                      # 動画関連
│   ├── __init__.py
│   ├── video_editor.py        # MoviePyを使用した動画編集
│   ├── subtitle_generator.py  # 字幕の生成・配置
│   └── video_processor.py     # 動画の後処理
│
├── utils/                      # ユーティリティ
│   ├── __init__.py
│   ├── file_manager.py        # ファイルの保存・読み込み管理
│   ├── api_client.py          # APIクライアントの共通処理
│   ├── logger.py              # ログ管理
│   └── validators.py          # 入力値検証
│
├── ui/                         # UIコンポーネント
│   ├── __init__.py
│   ├── components.py          # Streamlitコンポーネント
│   ├── pages/                 # マルチページ構成（必要に応じて）
│   │   ├── __init__.py
│   │   ├── input_page.py     # 入力画面
│   │   ├── script_page.py    # 台本生成画面
│   │   ├── audio_page.py     # 音声生成画面
│   │   ├── image_page.py     # 画像生成画面
│   │   └── video_page.py     # 動画編集画面
│   └── styles.py             # CSSスタイル定義
│
└── output/                     # 生成物の保存先
    ├── scripts/               # 生成された台本JSON
    ├── audio/                 # 生成された音声ファイル
    ├── images/                # 生成された画像ファイル
    └── videos/                # 生成された動画ファイル
```

---

## 4. 技術仕様

### 4.1 API仕様

#### OpenAI API
- **モデル**: GPT-4o
- **用途**: 台本生成、画像生成プロンプト作成
- **画像生成**: DALL-E 3
- **設定**: 温度、最大トークン数等を設定可能

#### ElevenLabs API
- **用途**: 日本語音声生成
- **品質**: Premium Voice推奨
- **設定**: 音声ID、安定性、類似度等を設定可能

### 4.2 ファイル形式
- **台本**: JSON（UTF-8）
- **音声**: MP3（推奨）またはWAV
- **画像**: PNG（推奨）またはJPG
- **動画**: MP4（H.264、AAC）

### 4.3 動画仕様
- **解像度**: 1080x1920（縦型）
- **フレームレート**: 30fps
- **ビットレート**: 5-10Mbps（推奨）
- **アスペクト比**: 9:16

---

## 5. 開発フェーズ

### Phase 1: 基盤構築
- [ ] プロジェクト構造の作成
- [ ] 依存パッケージのインストール
- [ ] 設定管理システムの実装
- [ ] ログシステムの実装

### Phase 2: 台本生成機能
- [ ] OpenAI API連携
- [ ] 台本生成ロジックの実装
- [ ] JSON形式での台本出力
- [ ] 台本プレビュー機能

### Phase 3: 音声生成機能
- [ ] ElevenLabs API連携
- [ ] 音声生成ロジックの実装
- [ ] 音声プレビュー機能

### Phase 4: 画像生成機能
- [ ] DALL-E 3 API連携
- [ ] 画像生成ロジックの実装
- [ ] 画像プレビュー機能

### Phase 5: 動画編集機能
- [ ] MoviePy統合
- [ ] 画像・音声の同期処理
- [ ] 字幕生成・配置機能
- [ ] 動画エクスポート機能

### Phase 6: GUI実装
- [ ] Streamlit UIの構築
- [ ] ワークフロー実装
- [ ] プレビュー機能の統合
- [ ] 再生成機能の実装

### Phase 7: テスト・最適化
- [ ] エラーハンドリングの強化
- [ ] パフォーマンス最適化
- [ ] UI/UXの改善
- [ ] ドキュメント整備

---

## 6. セキュリティ・運用

### 6.1 APIキー管理
- 環境変数（`.env`）を使用
- `.env`ファイルは`.gitignore`に追加
- `.env.example`でテンプレートを提供

### 6.2 エラーハンドリング
- API呼び出しのエラーハンドリング
- ファイル操作のエラーハンドリング
- ユーザーフレンドリーなエラーメッセージ

### 6.3 ログ管理
- 開発用：詳細ログ
- 本番用：エラーログ中心

---

## 7. 今後の拡張可能性

- 複数言語対応
- 音声の感情表現調整
- 動画テンプレート機能
- バッチ処理機能
- クラウドストレージ連携
- 動画の自動アップロード機能

---

## 8. 参考資料

- [Streamlit Documentation](https://docs.streamlit.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [ElevenLabs API Documentation](https://elevenlabs.io/docs)
- [MoviePy Documentation](https://zulko.github.io/moviepy/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
