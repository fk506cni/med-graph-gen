# med-graph-gen
medical graph generater


# **PDFからのナレッジグラフCSV生成 実装計画書**

## **1\. 概要**

本計画書は、提供されたPDFファイル『非歯原性歯痛の診療ガイドライン』から、医学用語の関連性（原因、症状、治療法など）を構造化したナレッジグラフを構築するためのCSVファイルを、人手による注釈なしで自動生成するシステムの実装計画を定義する。

ローカルでの実行環境はDockerコンテナ上に構築し、環境差異による影響を排除し、再現性を担保する。

## **2\. プロジェクト構成**

プロジェクトのディレクトリ構造を以下のように定義する。

knowledge-graph-generator/  
│  
├── Dockerfile              \# コンテナの構成を定義  
├── requirements.txt        \# Pythonの依存ライブラリ一覧  
│  
├── input/  
│   └── c00543.pdf          \# 入力となるPDFファイル  
│  
├── output/                 \# 生成されたCSVファイルが格納される  
│   ├── nodes.csv  
│   └── edges.csv  
│  
└── src/  
    ├── main.py             \# 全ての処理を統括するメインスクリプト  
    ├── step1\_extract.py    \# テキスト抽出・構造化モジュール  
    ├── step2\_entities.py   \# エンティティ（ノード）抽出モジュール  
    ├── step3\_relations.py  \# リレーション（エッジ）抽出モジュール  
    ├── step4\_normalize.py  \# 正規化・拡充モジュール  
    └── step5\_export.py     \# CSV出力モジュール

## **3\. 開発環境構築 (Dockerfile)**

Pythonの実行環境と必要なライブラリを内包したDockerイメージを定義する。

**Dockerfile予定**

\# ベースイメージとして公式のPython 3.10 を使用  
FROM python:3.10-slim

\# 作業ディレクトリを設定  
WORKDIR /app

\# 必要なシステムライブラリをインストール  
\# (SudachiPyやGiNZAのビルドに必要な場合がある)  
RUN apt-get update && apt-get install \-y \--no-install-recommends \\  
    build-essential \\  
    && rm \-rf /var/lib/apt/lists/\*

\# 依存ライブラリ定義ファイルをコピー  
COPY requirements.txt .

\# Pythonライブラリをインストール  
RUN pip install \--no-cache-dir \-r requirements.txt

\# GiNZAの学習済みモデルをダウンロード  
RUN python \-m spacy download ja\_ginza\_electra

\# プロジェクトのソースコードをコピー  
COPY src/ ./src/  
COPY input/ ./input/

\# メインスクリプトを実行するコマンド  
CMD \["python", "src/main.py"\]

**requirements.txt**

\# PDF操作  
PyMuPDF

\# 自然言語処理 (NLP)  
spacy==3.7.2  
ginza==5.1.2  
ja-ginza-electra==5.1.2 \# GiNZAのモデル

\# データ操作  
pandas

## **4\. 実装ステップ**

処理は以下の5つのステップに分割し、それぞれを独立したPythonモジュールとして実装する。

### **ステップ1: テキスト抽出と構造化 (step1\_extract.py)**

* **目的:** PDFからテキストを抽出し、後の処理で扱いやすいようにCQ（Clinical Question）などの構造を維持したJSON形式に変換する。  
* **使用ライブラリ:** PyMuPDF  
* **処理フロー:**  
  1. input/c00543.pdf を読み込む。  
  2. ページごとにテキストを抽出する。  
  3. 正規表現を用いて CQ(\\d+): (.+) のようなパターンを検出し、CQとその回答部分を紐付ける。  
  4. 抽出したテキストをページ番号やセクション情報と共にJSONオブジェクトとして構成する。  
  5. 中間ファイル structured\_text.json として一時保存する。

### **ステップ2: エンティティ（ノード）抽出 (step2\_entities.py)**

* **目的:** 構造化されたテキストから、ナレッジグラフのノードとなる医学用語（疾患、症状、薬剤、治療法など）を抽出する。  
* **使用ライブラリ:** GiNZA (ja\_ginza\_electra モデル)  
* **処理フロー:**  
  1. structured\_text.json を読み込む。  
  2. テキスト全体にGiNZAの固有表現抽出（NER）を適用する。  
  3. Disease (疾患), Symptom (症状), Drug (薬剤), Treatment (治療法) などのラベルが付与されたエンティティを収集する。  
  4. 重複を除いたユニークなエンティティのリストを作成し、ノード候補とする。

### **ステップ3: リレーション（エッジ）抽出 (step3\_relations.py)**

* **目的:** エンティティ間の関係性を特定し、エッジ（関係性のトリプレット）を生成する。  
* **使用ライブラリ:** GiNZA (依存構造解析)  
* **処理フロー:**  
  1. **CQ構造に基づくルール:**  
     * CQ8: 非歯原性歯痛に有効な薬物療法は何か？ の回答から、薬剤エンティティを抽出し、(薬剤, is\_effective\_for, 非歯原性歯痛) という関係を生成する。  
     * CQ10: ...抜髄・抜歯は有効か？ の回答が否定的であれば、(抜髄, is\_not\_effective\_for, 非歯原性歯痛) を生成する。  
  2. **依存構造解析に基づくルール:**  
     * 文中で2つのエンティティが含まれるものを対象とする。  
     * GiNZAで係り受け解析を行い、「AがBを**引き起こす**」「CはDの**原因**」といった構文パターンに合致する場合、(A, causes, B) のような関係を抽出する。  
  3. 抽出した関係トリプレット（Source, Relation, Target）のリストを作成する。

### **ステップ4: ナレッジの正規化 (step4\_normalize.py)**

* **目的:** 抽出したエンティティの表記ゆれ（略語など）を統一する。  
* **使用ライブラリ:** pandas  
* **処理フロー:**  
  1. 既知の同義語・略語辞書を定義する（例: {'AO': '非定型歯痛', 'PDAP': '持続性歯槽痛'}）。  
  2. ステップ2で抽出したノードリストとステップ3で抽出したエッジリストを走査し、辞書に基づいてエンティティ名を正規化（統一）する。

### **ステップ5: CSVへのエクスポート (step5\_export.py)**

* **目的:** 最終的なノードとエッジのリストをCSVファイルとして出力する。  
* **使用ライブラリ:** pandas  
* **処理フロー:**  
  1. 正規化されたノードリストから output/nodes.csv を生成する。  
     * カラム: NodeID (一意のID), Label (エンティティ名), Category (カテゴリ)  
  2. 正規化されたエッジリストから output/edges.csv を生成する。  
     * カラム: SourceID (始点ノードID), TargetID (終点ノードID), Relation (関係ラベル), DataSource (出典元ページなど)

## **5\. 実行手順**

以下のコマンドをターミナルで実行する。

1. Dockerイメージのビルド:  
   プロジェクトのルートディレクトリで以下のコマンドを実行し、Dockerfileに基づいてコンテナイメージを構築する。  
   docker build \-t knowledge-graph-builder .

2. Dockerコンテナの実行:  
   ビルドしたイメージを実行する。-v オプションでローカルの output ディレクトリをコンテナ内の output ディレクトリにマウントし、生成されたファイルをローカルで確認できるようにする。  
   docker run \--rm \-v "$(pwd)/output":/app/output knowledge-graph-builder

   実行が完了すると、ローカルの output ディレクトリに nodes.csv と edges.csv が生成される。

## **6\. 生成されるCSVの例**

**output/nodes.csv**

NodeID,Label,Category  
DISEASE\_001,非歯原性歯痛,疾患  
DISEASE\_002,筋・筋膜痛,疾患  
DRUG\_001,カルバマゼピン,薬剤  
TREATMENT\_001,抜髄,治療法

**output/edges.csv**

SourceID,TargetID,Relation,DataSource  
DISEASE\_001,DISEASE\_002,has\_underlying\_disease,c00543.pdf\_p12  
DRUG\_001,DISEASE\_001,is\_effective\_for,c00543.pdf\_p40  
TREATMENT\_001,DISEASE\_001,is\_not\_effective\_for,c00543.pdf\_p49  
