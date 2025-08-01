# ベースイメージとして公式のPython 3.10 を使用
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なシステムライブラリをインストール
# (SudachiPyやGiNZAのビルドに必要な場合がある)
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     && rm -rf /var/lib/apt/lists/*

# 依存ライブラリ定義ファイルをコピー
COPY requirements.txt .

# Pythonライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# GiNZAの学習済みモデルをダウンロード
RUN python -m spacy download ja_ginza_electra

# プロジェクトのソースコードをコピー
COPY src/ ./src/
COPY input/ ./input/

# メインスクリプトを実行するコマンド
CMD ["python", "src/main.py"]

