import json
import os
import pandas as pd
from collections import defaultdict

# --- 定数 --- #
INPUT_NORMALIZED_ENTITIES_PATH = "output/normalized_entities.json"
INPUT_NORMALIZED_RELATIONS_PATH = "output/normalized_relations.jsonl"
OUTPUT_NODES_PATH = "output/nodes.csv"
OUTPUT_EDGES_PATH = "output/edges.csv"

# PDFのファイル名（データソースとして使用）
PDF_FILENAME = "c00543.pdf"

# カテゴリ名をNodeIDのプレフィックスに変換するマッピング
CATEGORY_PREFIX_MAP = {
    "Disease": "DISEASE",
    "Symptom": "SYMPTOM",
    "Drug": "DRUG",
    "Treatment": "TREATMENT",
    # 必要に応じて他のカテゴリも追加
}

def load_json(path):
    """JSONファイルを読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_jsonl(path):
    """JSON Linesファイルを読み込む"""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def main():
    """
    正規化されたナレッジをCSVにエクスポートするメイン関数
    """
    print("--- ステップ5: CSVへのエクスポートを開始します ---")

    # 1. ファイルの読み込み
    if not os.path.exists(INPUT_NORMALIZED_ENTITIES_PATH):
        print(f"エラー: {INPUT_NORMALIZED_ENTITIES_PATH} が見つかりません。")
        return
    if not os.path.exists(INPUT_NORMALIZED_RELATIONS_PATH):
        print(f"エラー: {INPUT_NORMALIZED_RELATIONS_PATH} が見つかりません。")
        return

    entities = load_json(INPUT_NORMALIZED_ENTITIES_PATH)
    relations = load_jsonl(INPUT_NORMALIZED_RELATIONS_PATH)

    # 2. ノードリストの作成
    node_list = []
    entity_to_node_id = {}
    category_counters = defaultdict(int)

    for entity in entities:
        term = entity['term']
        category = entity['category']
        prefix = CATEGORY_PREFIX_MAP.get(category, "UNKNOWN")
        
        category_counters[prefix] += 1
        node_id = f"{prefix}_{category_counters[prefix]:03d}"
        
        node_list.append({
            "NodeID": node_id,
            "Label": term,
            "Category": category
        })
        entity_to_node_id[term] = node_id

    nodes_df = pd.DataFrame(node_list)
    nodes_df.to_csv(OUTPUT_NODES_PATH, index=False, encoding='utf-8-sig')
    print(f"ノードリストを {OUTPUT_NODES_PATH} に保存しました。 ({len(nodes_df)}件)")

    # 3. エッジリストの作成
    edge_list = []
    for rel in relations:
        source_term = rel['source']
        target_term = rel['target']
        
        # マッピングに存在しないエンティティはスキップ
        if source_term not in entity_to_node_id or target_term not in entity_to_node_id:
            continue

        source_id = entity_to_node_id[source_term]
        target_id = entity_to_node_id[target_term]
        
        # データソースのページ番号を取得（最小ページを使用）
        source_page = f"_p{min(rel['source_pages'])}" if rel.get('source_pages') else ""
        datasource = f"{PDF_FILENAME}{source_page}"

        edge_list.append({
            "SourceID": source_id,
            "TargetID": target_id,
            "Relation": rel['relation'],
            "DataSource": datasource
        })

    edges_df = pd.DataFrame(edge_list)
    # 重複するエッジを削除
    edges_df.drop_duplicates(inplace=True)
    edges_df.to_csv(OUTPUT_EDGES_PATH, index=False, encoding='utf-8-sig')
    print(f"エッジリストを {OUTPUT_EDGES_PATH} に保存しました。 ({len(edges_df)}件)")

    print("--- ステップ5: CSVへのエクスポートが完了しました ---")

if __name__ == "__main__":
    from collections import defaultdict
    main()
