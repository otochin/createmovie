# YouTubeショート動画生成ツール

インプットから「台本・音声・画像・動画」を自動生成するGUIツールです。

## 概要

このツールは、テキストやトピックを入力するだけで、YouTubeショート（9:16形式）向けの高品質な動画を自動生成します。

## 主な機能

- 📝 **台本自動生成**: GPT-4oを使用した高品質な台本生成
- 🎤 **音声生成**: ElevenLabs APIを使用した日本語音声生成
- 🖼️ **画像生成**: DALL-E 3を使用した画像生成
- 🎬 **動画編集**: MoviePyを使用した動画編集と字幕追加

## 必要な環境

- macOS (MacBook Pro Mシリーズ対応)
- Python 3.9以上
- FFmpeg（動画処理用）

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd createmovie
```

### 2. 仮想環境の作成と有効化

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. FFmpegのインストール（未インストールの場合）

```bash
brew install ffmpeg
```

### 5. 環境変数の設定

`.env.example`を参考に`.env`ファイルを作成し、APIキーを設定してください。

```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

## 使用方法

### アプリケーションの起動

```bash
streamlit run main.py
```

ブラウザが自動的に開き、アプリケーションが表示されます。

## プロジェクト構造

詳細は `docs/README_PLAN.md` を参照してください。

## ライセンス

（ライセンス情報を記載してください）

## 開発者向け情報

詳細なシステム定義書は `docs/README_PLAN.md` を参照してください。

その他のドキュメント：
- `docs/DEVELOPMENT_LOG.md` - 開発ログ
- `docs/CHANGELOG.md` - 変更履歴
- `docs/TODO.md` - TODOリスト
