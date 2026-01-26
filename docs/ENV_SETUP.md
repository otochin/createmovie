# .envファイル設定ガイド

このガイドでは、`.env`ファイルの設定方法を詳しく説明します。

## 📋 目次

1. [.envファイルの作成](#1-envファイルの作成)
2. [OpenAI APIキーの取得と設定](#2-openai-apiキーの取得と設定)
3. [ElevenLabs APIキーの取得と設定](#3-elevenlabs-apiキーの取得と設定)
4. [ElevenLabs Voice IDの取得と設定](#4-elevenlabs-voice-idの取得と設定)
5. [動画設定（オプション）](#5-動画設定オプション)
6. [設定の確認](#6-設定の確認)

---

## 1. .envファイルの作成

### ステップ1: テンプレートファイルをコピー

プロジェクトのルートディレクトリで、以下のコマンドを実行します：

```bash
cd /Users/arie-yoshiaki/createmovie
cp .env.example .env
```

### ステップ2: .envファイルを編集

お好みのテキストエディタで`.env`ファイルを開きます：

```bash
# VS Codeの場合
code .env

# nanoエディタの場合
nano .env

# vimエディタの場合
vim .env
```

---

## 2. OpenAI APIキーの取得と設定

### OpenAI APIキーの取得方法

1. **OpenAIアカウントの作成**
   - [OpenAI Platform](https://platform.openai.com/) にアクセス
   - アカウントを作成（まだの場合）

2. **APIキーの生成**
   - ログイン後、右上のプロフィールアイコンをクリック
   - 「View API keys」を選択
   - 「Create new secret key」をクリック
   - キー名を入力（例: "createmovie"）
   - 「Create secret key」をクリック
   - **重要**: 表示されたキーをコピー（この画面を閉じると再表示できません）

3. **.envファイルに設定**
   ```env
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   `sk-`で始まる文字列をそのまま貼り付けます。

### 💡 ヒント
- APIキーは機密情報です。絶対にGitにコミットしないでください（`.gitignore`に含まれています）
- APIキーが漏洩した場合は、すぐにOpenAIのダッシュボードで削除してください

---

## 3. ElevenLabs APIキーの取得と設定

### ElevenLabs APIキーの取得方法

1. **ElevenLabsアカウントの作成**
   - [ElevenLabs](https://elevenlabs.io/) にアクセス
   - 「Sign Up」でアカウントを作成

2. **APIキーの生成**
   - ログイン後、右上のプロフィールアイコンをクリック
   - 「Profile」→「API Keys」を選択
   - 「Create API Key」をクリック
   - キー名を入力（例: "createmovie"）
   - 「Create」をクリック
   - 表示されたキーをコピー

3. **.envファイルに設定**
   ```env
   ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   コピーしたキーをそのまま貼り付けます。

### 💡 ヒント
- ElevenLabsの無料プランには月間の文字数制限があります
- 有料プランにアップグレードすると、より多くの文字数が利用できます

---

## 4. ElevenLabs Voice IDの取得と設定

### Voice IDの取得方法

1. **ElevenLabsのVoice Libraryにアクセス**
   - [ElevenLabs Voice Library](https://elevenlabs.io/voice-library) にアクセス
   - または、ダッシュボードから「Voices」→「Voice Library」を選択

2. **日本語音声を検索**
   - 検索バーで「Japanese」または「日本語」で検索
   - または、フィルターで「Japanese」を選択

3. **Voice IDをコピー**
   - お気に入りの音声を選択
   - 音声の詳細ページで「Voice ID」をコピー
   - 例: `21m00Tcm4TlvDq8ikWAM` のような文字列

4. **.envファイルに設定**
   ```env
   ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
   ```
   コピーしたVoice IDをそのまま貼り付けます。

### おすすめの日本語音声

以下は日本語対応の音声の例です（Voice IDは変更される可能性があります）：

- **女性の声**: 検索で「Japanese Female」で探す
- **男性の声**: 検索で「Japanese Male」で探す
- **カスタム音声**: 自分で作成した音声も使用可能

### 💡 ヒント
- Voice IDは音声ごとに異なります
- 音声のサンプルを聞いてから選択することをおすすめします
- カスタム音声を作成する場合は、ElevenLabsの「Voice Cloning」機能を使用できます

---

## 5. 動画設定（オプション）

動画設定は既にデフォルト値が設定されているため、変更する必要はありませんが、カスタマイズすることもできます：

```env
# 動画設定（デフォルト値）
VIDEO_WIDTH=1080        # 幅（ピクセル）
VIDEO_HEIGHT=1920       # 高さ（ピクセル）- YouTubeショートは9:16形式
VIDEO_FPS=30            # フレームレート
VIDEO_BITRATE=8000000   # ビットレート（8Mbps）

# 出力ディレクトリ設定（オプション）
OUTPUT_BASE_DIR=./output
```

### 設定の説明

- **VIDEO_WIDTH/HEIGHT**: YouTubeショートは1080x1920（9:16）が推奨
- **VIDEO_FPS**: 30fpsが標準的
- **VIDEO_BITRATE**: 8Mbpsが高品質な動画に適しています
- **OUTPUT_BASE_DIR**: 生成されたファイルの保存先（変更可能）

---

## 6. 設定の確認

### ステップ1: .envファイルの内容を確認

```bash
cat .env
```

以下のような内容になっているはずです：

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
VIDEO_FPS=30
VIDEO_BITRATE=8000000
OUTPUT_BASE_DIR=./output
```

### ステップ2: アプリケーションで確認

Streamlitアプリを起動して、設定が正しく読み込まれているか確認します：

```bash
streamlit run main.py
```

- ホームページで「✅ すべてのAPIキーが設定されています。」と表示されれば成功です
- 「⚠️ 以下のAPIキーが設定されていません」と表示される場合は、`.env`ファイルを確認してください

### ステップ3: エラーが発生する場合

#### よくあるエラーと対処法

1. **「.envファイルが見つかりません」**
   - `.env`ファイルがプロジェクトルートに存在するか確認
   - ファイル名が`.env`（先頭のドットを含む）になっているか確認

2. **「OPENAI_API_KEYが設定されていません」**
   - `.env`ファイルに`OPENAI_API_KEY=`の行があるか確認
   - 値が正しく設定されているか確認（余分なスペースがないか）

3. **「無効なAPIキー」エラー**
   - APIキーが正しくコピーされているか確認
   - APIキーに余分なスペースや改行が含まれていないか確認
   - APIキーが有効かどうか、各サービスのダッシュボードで確認

---

## 📝 設定例（完成形）

以下は、すべての設定が完了した`.env`ファイルの例です：

```env
# OpenAI API設定
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ElevenLabs API設定
ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ElevenLabs Voice ID（日本語音声）
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# 動画設定
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
VIDEO_FPS=30
VIDEO_BITRATE=8000000

# 出力ディレクトリ設定（オプション）
OUTPUT_BASE_DIR=./output
```

---

## 🔒 セキュリティに関する注意事項

1. **.envファイルは絶対にGitにコミットしない**
   - `.gitignore`に`.env`が含まれていることを確認
   - 誤ってコミットした場合は、すぐにGit履歴から削除してください

2. **APIキーを他人と共有しない**
   - APIキーは個人のアカウントに紐づいています
   - 共有すると、不正利用される可能性があります

3. **定期的にAPIキーをローテーション**
   - セキュリティのため、定期的に新しいAPIキーを生成してください
   - 古いキーは削除してください

---

## 📚 参考リンク

- [OpenAI Platform](https://platform.openai.com/)
- [ElevenLabs Documentation](https://elevenlabs.io/docs)
- [ElevenLabs Voice Library](https://elevenlabs.io/voice-library)

---

## ❓ よくある質問（FAQ）

### Q: APIキーは無料で取得できますか？
A: 
- OpenAI: アカウント作成時に無料クレジットが付与されますが、使用量に応じて課金されます
- ElevenLabs: 無料プランがありますが、月間の文字数制限があります

### Q: Voice IDはどこで見つけられますか？
A: ElevenLabsのVoice Libraryで検索できます。日本語音声を検索して、お気に入りの音声のVoice IDをコピーしてください。

### Q: 設定を変更した後、アプリを再起動する必要がありますか？
A: はい、`.env`ファイルを変更した後は、Streamlitアプリを再起動してください。

---

設定が完了したら、アプリケーションを起動して台本生成機能を試してみてください！
