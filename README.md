# med-graph-gen

## **はじめに**

`med-graph-gen`は、医学系PDFドキュメント（例：診療ガイドライン）を解析し、そこに含まれる専門用語（疾患、薬剤、治療法など）とその関係性を抽出して、ナレッジグラフ形式のCSVファイル（ノードリストとエッジリスト）を自動生成するツールです。

これにより、人手を介さずに、文献情報から構造化された知識データを構築することを目指します。

## **概要**

本プロジェクトは、提供されたPDFファイル『非歯原性歯痛の診療ガイドライン』から、医学用語の関連性（原因、症状、治療法など）を構造化したナレッジグラフを構築するためのCSVファイルを、人手による注釈なしで自動生成するシステムの実装計画を定義します。

ローカルでの実行環境はDockerコンテナ上に構築し、環境差異による影響を排除し、再現性を担保します。

## **プロジェクト構成**

### **ディレクトリ構造**

```
med-graph-gen/
│
├── build/                  # Dockerビルド関連のファイルを格納
│   ├── Dockerfile
│   └── requirements.txt
│
├── input/
│   └── c00543.pdf          # 入力となるPDFファイル
│
├── output/                 # 生成されたCSVファイルが格納される
│   ├── nodes.csv
│   └── edges.csv
│
└── src/                    # Pythonソースコード
    ├── main.py
    ├── step1_extract.py
    ├── step2_entities.py
    ├── step3a_rule_based_relations.py
    ├── step3b_llm_based_relations.py
    ├── step4_normalize.py
    └── step5_export.py
```

### **処理フロー**

```mermaid
graph TD;
    A[input/c00543.pdf] --> B(step1_extract.py);
    B --> C[structured_text.json];
    C --> D(step2_entities.py);
    C --> E1(step3a_rule_based_relations.py);
    C --> E2(step3b_llm_based_relations.py);
    D --> F(step4_normalize.py);
    E1 --> F;
    E2 --> F;
    F --> G(step5_export.py);
    G --> H[output/nodes.csv];
    G --> I[output/edges.csv];

    subgraph "処理フロー"
        B
        D
        E1
        E2
        F
        G
    end

    subgraph "データ"
        A
        C
        H
        I
    end
```

## **開発環境**

コンテナの構成は `build/Dockerfile` と `build/requirements.txt` を参照してください。

## **実装ステップ**

処理は以下の5つのステップに分割し、それぞれを独立したPythonモジュールとして実装します。
モジュール内で利用する主なライブラリは記載していますが、要件に沿って実装するために必要なライブラリがあれば適宜追加してください。
requirements.txtに追加ライブラリを記載する場合はライブラリのバージョンを指定し、依存ライブラリも極力記載してください。再現性担保のためにご協力ください。
それぞれのステップで実行結果をマニュアルで確認しやすいように、jsonやcsvなどのテキスト形式の中間データを保管するようにしてください。

### **ステップ1: テキスト抽出 (step1_extract.py)**

* **目的:** PDFから全てのテキストをページ単位で抽出します。後のステップで出典を明記できるように、ページ番号と共に保存します。
* **使用ライブラリ:** PyMuPDF
* **処理フロー:**
  1. `input/c00543.pdf` を読み込みます。
  2. ページごとにテキストを抽出します。
  3. 抽出したテキストをページ番号と共にJSONオブジェクトのリストとして構成します。
  4. 中間ファイル `structured_text.json` として一時保存します。

### **ステップ2: テキストクレンジングとエンティティ（ノード）抽出 (step2_entities.py)**

* **目的:** 抽出されたテキストから医学的に無関係な情報（参考文献、引用番号、目次など）をLLMを用いて除去し、クリーンなテキストからナレッジグラフのノードとなる医学用語（疾患、症状、薬剤、治療法など）を抽出します。
* **使用ライブラリ:** google-generativeai, GiNZA (`ja_ginza_electra` モデル)
* **処理フロー:**
  1. `structured_text.json` を読み込みます。
  2. LLM（Gemini）に各ページのテキストを送信し、参考文献、引用番号、目次、著者情報などの不要な情報を除去します。この際、APIのレートリミットを考慮し、バッチ処理と適切なウェイトを設けます。
  3. クレンジングされたテキストを `output/cleaned_text.json` として一時保存します。
  4. クレンジングされたテキスト全体にGiNZAの固有表現抽出（NER）を適用します。
  5. `Disease` (疾患), `Symptom` (症状), `Drug` (薬剤), `Treatment` (治療法) などのラベルが付与されたエンティティを収集します。
  6. 重複を除いたユニークなエンティティのリストを作成し、ノード候補とします。
  7. 抽出したエンティティのリストを `output/entities.json` として一時保存します。


### **ステップ3a: ルールベースのリレーション抽出 (step3a_rule_based_relations.py)**

* **目的:** CQ構造や係り受け解析に基づき、明確なパターンに合致する関係性を抽出します。
* **使用ライブラリ:** GiNZA (依存構造解析)
* **処理フロー:**
  1. `structured_text.json` と、ステップ2で生成されたエンティティリストを読み込みます。
  2. **前処理:** 本文中の引用番号を除去します。
  3. 文ごとに、含まれているエンティティのペアをすべてリストアップします。
  4. **CQ構造に基づくルール:**
     * 「CQ8: 非歯原性歯痛に有効な薬物療法は何か？」 の回答から、薬剤エンティティを抽出し、(薬剤, is_effective_for, 非歯原性歯痛) という関係を生成します。
     * 「CQ10: ...抜髄・抜歯は有効か？」 の回答が否定的であれば、(抜髄, is_not_effective_for, 非歯原性歯痛) を生成します。
  5. **依存構造解析に基づくルール:**
     * GiNZAで係り受け解析を行い、「AがBを引き起こす」「CはDの原因」といった明確な構文パターンに合致する場合、(A, causes, B) のような関係を抽出します。
  6. 抽出した関係トリプレットのリストを中間ファイルとして保存します。

### **ステップ3b: LLMベースのリレーション抽出 (step3b_llm_based_relations.py)**

* **目的:** ルールベースでは捉えきれない、より複雑で多様な関係性をLLM（Gemini）を用いて抽出します。
* **使用ライブラリ:** google-generativeai
* **処理フロー:**
  1. `structured_text.json` と、ステップ2で生成されたエンティティリストを読み込みます。
  2. **前処理:** 本文中の引用番号を除去します。
  3. すべてのエンティティペアを対象とします。
  4. 対象となるエンティティペアと、そのペアが含まれる文（コンテキスト）をセットにします。
  5. 各セットをインプットとして、後述するプロンプトを用いてGemini APIにリクエストを送信します。
  6. プロンプト案を`prompt_plan.md`に記載しています。
  7. APIからのレスポンス（JSON形式）を解析し、(Source, Relation, Target) の関係トリプレットを生成します。
  8. 抽出した関係トリプレットのリストを中間ファイルとして保存します。


### **ステップ4: ナレッジの正規化 (step4_normalize.py)**

* **目的:** 抽出したエンティティの表記ゆれ（略語など）を統一します。
* **使用ライブラリ:** pandas
* **処理フロー:**
  1. 既知の同義語・略語辞書を定義します（例: `{'AO': '非定型歯痛', 'PDAP': '持続性歯槽痛'}`）。
  2. ステップ2で抽出したノードリストとステップ3で抽出したエッジリストを走査し、辞書に基づいてエンティティ名を正規化（統一）します。

### **ステップ5: CSVへのエクスポート (step5_export.py)**

* **目的:** 最終的なノードとエッジのリストをCSVファイルとして出力します。
* **使用ライブラリ:** pandas
* **処理フロー:**
  1. 正規化されたノードリストから `output/nodes.csv` を生成します。
     * カラム: `NodeID` (一意のID), `Label` (エンティティ名), `Category` (カテゴリ)
  2. 正規化されたエッジリストから `output/edges.csv` を生成します。
     * カラム: `SourceID` (始点ノードID), `TargetID` (終点ノードID), `Relation` (関係ラベル), `DataSource` (出典元ページなど)

## **前提条件**

*   [Docker](https://www.docker.com/) がインストールされていること。
*   Gemini APIキーが取得済みであること。

## **実行手順**

以下のコマンドをターミナルで実行します。

1.  **Gemini APIキーの設定:**
    プロジェクトのルートディレクトリに `.env` ファイルを作成し、以下の形式でAPIキーを記述します。
    ```
    GEMINI_API_KEY=YOUR_API_KEY_HERE
    ```
    `YOUR_API_KEY_HERE` を実際のAPIキーに置き換えてください。

2.  **Dockerイメージのビルド:**
    プロジェクトのルートディレクトリをコンテキストとして、コンテナイメージを構築します。
    ```bash
    docker build -t knowledge-graph-builder .
    ```

3.  **Dockerコンテナの実行:**
    ビルドしたイメージを実行します。`-v` オプションでローカルの `output` ディレクトリをコンテナ内の `output` ディリクトリにマウントし、`--env-file .env` オプションでAPIキーをコンテナに渡します。これにより、生成されたファイルをローカルで確認できるようになります。
    ```bash
    docker run --rm -v "$(pwd)/output":/app/output --env-file .env knowledge-graph-builder
    ```

    実行が完了すると、ローカルの `output` ディレクトリに `nodes.csv` と `edges.csv` が生成されます。

## **生成されるCSVの例**

**output/nodes.csv**

```csv
NodeID,Label,Category
DISEASE_001,非歯原性歯痛,疾患
DISEASE_002,筋・筋膜痛,疾患
DRUG_001,カルバマゼピン,薬剤
TREATMENT_001,抜髄,治療法
```

**output/edges.csv**

```csv
SourceID,TargetID,Relation,DataSource
DISEASE_001,DISEASE_002,has_underlying_disease,c00543.pdf_p12
DRUG_001,DISEASE_001,is_effective_for,c00543.pdf_p40
TREATTMENT_001,DISEASE_001,is_not_effective_for,c00543.pdf_p49
```
