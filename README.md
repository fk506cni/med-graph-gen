# med-graph-gen

## **はじめに**

`med-graph-gen`は、医学系PDFドキュメント（例：診療ガイドライン）を解析し、そこに含まれる専門用語（疾患、薬剤、治療法など）とその関係性を抽出して、ナレッジグラフ形式のCSVファイル（ノードリストとエッジリスト）を自動生成するツールです。

これにより、人手を介さずに、文献情報から構造化された知識データを構築することを目指します。

## **概要**

本プロジェクトは、提供されたPDFファイルから、医学用語の関連性（原因、症状、治療法など）を構造化したナレッジグラフを構築するためのCSVファイルを、人手による注釈なしで自動生成するシステムです。

ローカルでの実行環境はDockerコンテナ上に構築し、環境差異による影響を排除し、再現性を担保します。

## **プロジェクト構成**

### **ディレクトリ構造**

```
med-graph-gen/
│
├── Dockerfile
├── .env.example            # APIキー設定用のサンプルファイル
├── ... (プロンプトファイル)
│
├── input/
│   └── c00543.pdf          # 入力となるPDFファイル
│
├── output/                 # 生成された中間ファイルやCSVが格納される
│   ├── step1_structured_text.json
│   ├── step2a_cleaned_text.json
│   ├── step2b_entities.json
│   ├── step3b_relations.jsonl
│   ├── step4_normalized_entities.json
│   ├── step4_normalized_relations.jsonl
│   ├── step4_normalization_map.json
│   ├── step5_nodes.csv
│   ├── step5_edges.csv
│   ├── step5_normalization_nodes.csv
│   └── step5_normalization_edges.csv
│
└── src/                    # Pythonソースコード
    ├── main.py
    ├── step1_extract.py
    ├── step2a_clean_text.py
    ├── step2b_extract_entities.py
    ├── step3b_llm_based_relations.py
    ├── step4_normalize.py
    └── step5_export.py
```

### **処理フロー**

```mermaid
graph TD;
    A[input/c00543.pdf] --> B(step1_extract.py);
    B --> C[output/step1_structured_text.json];
    C --> D(step2a_clean_text.py);
    D --> E[output/step2a_cleaned_text.json];
    E --> F(step2b_extract_entities.py);
    F --> G[output/step2b_entities.json];
    G --> H(step3b_llm_based_relations.py);
    H --> I[output/step3b_relations.jsonl];

    G --> J(step4_normalize.py);
    I --> J;

    J --> K[output/step4_normalized_entities.json];
    J --> L[output/step4_normalized_relations.jsonl];
    J --> P[output/step4_normalization_map.json];

    K --> M(step5_export.py);
    L --> M;
    P --> M;

    M --> N[output/step5_nodes.csv];
    M --> O[output/step5_edges.csv];
    M --> Q[output/step5_normalization_nodes.csv];
    M --> R[output/step5_normalization_edges.csv];

    subgraph "処理フロー"
        B; D; F; H; J; M;
    end

    subgraph "データ"
        A; C; E; G; I; K; L; P; N; O; Q; R;
    end
```

## **実装ステップ**

### **ステップ1: テキスト抽出 (step1_extract.py)**
*   **目的:** PDFから指定されたページ範囲のテキストを抽出します。`--start_page`と`--end_page`引数で範囲を指定できます。
*   **出力:** `output/step1_structured_text.json`

### **ステップ2a: テキストクレンジングと段落化 (step2a_clean_text.py)**
*   **目的:** LLMを用いて、抽出したテキストから不要な情報を取り除き、段落単位に分割します。APIレート制限対策として`--wait`引数で待機時間を指定できます。
*   **出力:** `output/step2a_cleaned_text.json`

### **ステップ2b: LLMによるエンティティ抽出 (step2b_extract_entities.py)**
*   **目的:** クレンジングされた段落から、LLMを用いて医学用語（エンティティ）を抽出します。
*   **出力:** `output/step2b_entities.json`

### **ステップ3b: LLMベースのリレーション抽出 (step3b_llm_based_relations.py)**
*   **目的:** 段落内のエンティティのペアに基づき、LLMを用いてそれらの関係性を抽出します。
*   **出力:** `output/step3b_relations.jsonl`

### **ステップ4: ナレッジの正規化 (step4_normalize.py)**
*   **目的:** 抽出したエンティティの表記ゆれ（例: `非歯原性歯痛`と`NTDP`）を統一します。
*   **出力:** `output/step4_normalized_entities.json`, `output/step4_normalized_relations.jsonl`, `output/step4_normalization_map.json`

### **ステップ5: CSVへのエクスポート (step5_export.py)**
*   **目的:** 正規化されたエンティティとリレーションを、グラフデータベースで扱いやすいCSV形式に変換します。また、正規化の対応関係そのものもグラフとしてCSV出力します。
*   **出力:** 
    *   `output/step5_nodes.csv`, `output/step5_edges.csv` (ナレッジグラフ)
    *   `output/step5_normalization_nodes.csv`, `output/step5_normalization_edges.csv` (正規化関係グラフ)

## **前提条件**

*   [Docker](https://www.docker.com/) がインストールされていること。
*   Gemini APIキーが取得済みであること。

## **実行手順**

1.  **Gemini APIキーの設定:**
    プロジェクトのルートディレクトリに `.env` ファイルを作成し、お持ちのAPIキーを記述します。
    ```
    GEMINI_API_KEY="<YOUR_API_KEY>"
    ```

2.  **Dockerイメージのビルド:**
    ```bash
    docker build -t knowledge-graph-builder .
    ```

3.  **Dockerコンテナの実行:**
    *   **全ステップを実行 (基本):**
        ```bash
        docker run --rm --env-file .env \
          -v "/path/to/your/med-graph-gen/output:/app/output" \
          -v "/path/to/your/med-graph-gen/paragraph_cleaning_prompt.md:/app/paragraph_cleaning_prompt.md" \
          -v "/path/to/your/med-graph-gen/entity_extraction_prompt.md:/app/entity_extraction_prompt.md" \
          -v "/path/to/your/med-graph-gen/relation_extraction_batch_prompt.md:/app/relation_extraction_batch_prompt.md" \
          -v "/path/to/your/med-graph-gen/entity_normalization_prompt.md:/app/entity_normalization_prompt.md" \
          knowledge-graph-builder python -u src/main.py
        ```
        *注意: `/path/to/your/med-graph-gen` の部分は、お使いの環境の `med-graph-gen` プロジェクトへの絶対パスに置き換えてください。*

    *   **ページ範囲と待機時間を指定して実行:**
        `--start_page`, `--end_page`, `--wait` 引数で、処理対象のページ範囲とAPI呼び出し間の待機時間（秒）を制御できます。
        ```bash
        docker run --rm --env-file .env \
          -v "/path/to/your/med-graph-gen/output:/app/output" \
          -v "/path/to/your/med-graph-gen/paragraph_cleaning_prompt.md:/app/paragraph_cleaning_prompt.md" \
          -v "/path/to/your/med-graph-gen/entity_extraction_prompt.md:/app/entity_extraction_prompt.md" \
          -v "/path/to/your/med-graph-gen/relation_extraction_batch_prompt.md:/app/relation_extraction_batch_prompt.md" \
          -v "/path/to/your/med-graph-gen/entity_normalization_prompt.md:/app/entity_normalization_prompt.md" \
          knowledge-graph-builder python -u src/main.py --start_page 12 --end_page 17 --wait 5
        ```

    *   **特定のステップから実行:**
        `--start-step`引数で開始ステップを指定できます。例えば、`step5`から実行する場合、`output`ディレクトリに依存ファイルが存在している必要があります。
        ```bash
        docker run --rm --env-file .env \
          -v "/path/to/your/med-graph-gen/output:/app/output" \
          knowledge-graph-builder python -u src/main.py --start-step step5
        ```

## **生成されるCSVの例**

**output/step5_nodes.csv**

```csv
NodeID,Label,Category
DISEASE_001,非歯原性歯痛,疾患
...
```

**output/step5_edges.csv**

```csv
SourceID,TargetID,Relation,DataSource
DISEASE_001,DISEASE_002,has_underlying_disease,c00543.pdf_p12
...
```

**output/step5_normalization_nodes.csv**

```csv
NodeID,Label
TERM_0001,非歯原性歯痛
TERM_0002,NTDP
...
```

**output/step5_normalization_edges.csv**

```csv
SourceID,TargetID,Relation
TERM_0002,TERM_0001,is_normalized_to
...
```
