import json
import os
import pandas as pd
from collections import defaultdict

# --- 定数 --- #
INPUT_NORMALIZED_ENTITIES_PATH = "output/step4_normalized_entities.json"
INPUT_NORMALIZED_RELATIONS_PATH = "output/step4_normalized_relations.jsonl"
INPUT_NORMALIZATION_MAP_PATH = "output/step4_normalization_map.json"
OUTPUT_NODES_PATH = "output/step5_nodes.csv"
OUTPUT_EDGES_PATH = "output/step5_edges.csv"
OUTPUT_NORMALIZATION_NODES_PATH = "output/step5_normalization_nodes.csv"
OUTPUT_NORMALIZATION_EDGES_PATH = "output/step5_normalization_edges.csv"

PDF_FILENAME = "c00543.pdf"

CATEGORY_PREFIX_MAP = {
    "Disease": "DISEASE",
    "Symptom": "SYMPTOM",
    "Drug": "DRUG",
    "Treatment": "TREATMENT",
}

# 標準的なオントロジーへのリレーション名マッピング
RELATION_MAP = {
    "is_a": "rdfs:subClassOf",
    "causes": "biolink:causes",
    "is_caused_by": "biolink:caused_by",
    "is_symptom_of": "biolink:is_symptom_of",
    "is_effective_for": "biolink:treats",
    "is_not_effective_for": "biolink:does_not_treat",
    "is_associated_with": "skos:related",
    "is_diagnosed_by": "biolink:diagnosed_by",
}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_jsonl(path):
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def export_normalization_graph():
    print("--- 正規化マップのグラフエクスポートを開始します ---")
    if not os.path.exists(INPUT_NORMALIZATION_MAP_PATH):
        print(f"エラー: {INPUT_NORMALIZATION_MAP_PATH} が見つかりません。")
        return

    normalization_map = load_json(INPUT_NORMALIZATION_MAP_PATH)
    node_list, edge_list = [], []
    term_to_node_id = {}
    node_counter = 0

    all_terms = set(normalization_map.keys()) | set(normalization_map.values())
    for term in all_terms:
        if term not in term_to_node_id:
            node_id = f"TERM_{node_counter:04d}"
            term_to_node_id[term] = node_id
            node_list.append({"NodeID": node_id, "Label": term})
            node_counter += 1

    for alias, normalized_name in normalization_map.items():
        if alias != normalized_name:
            source_id = term_to_node_id[alias]
            target_id = term_to_node_id[normalized_name]
            edge_list.append({
                "SourceID": source_id,
                "TargetID": target_id,
                "Relation": "skos:exactMatch"  # is_normalized_to から変更
            })

    pd.DataFrame(node_list).to_csv(OUTPUT_NORMALIZATION_NODES_PATH, index=False, encoding='utf-8-sig')
    print(f"正規化ノードリストを {OUTPUT_NORMALIZATION_NODES_PATH} に保存しました。 ({len(node_list)}件)")

    pd.DataFrame(edge_list).to_csv(OUTPUT_NORMALIZATION_EDGES_PATH, index=False, encoding='utf-8-sig')
    print(f"正規化エッジリストを {OUTPUT_NORMALIZATION_EDGES_PATH} に保存しました。 ({len(edge_list)}件)")
    print("--- 正規化マップのグラフエクスポートが完了しました ---")

def main():
    print("--- ステップ5: CSVへのエクスポートを開始します ---")

    if not os.path.exists(INPUT_NORMALIZED_ENTITIES_PATH) or not os.path.exists(INPUT_NORMALIZED_RELATIONS_PATH):
        print(f"エラー: 入力ファイルが見つかりません。")
        return

    entities = load_json(INPUT_NORMALIZED_ENTITIES_PATH)
    relations = load_jsonl(INPUT_NORMALIZED_RELATIONS_PATH)

    node_list = []
    entity_to_node_id = {}
    category_counters = defaultdict(int)

    for entity in entities:
        term = entity['term']
        category = entity['category']
        prefix = CATEGORY_PREFIX_MAP.get(category, "UNKNOWN")
        category_counters[prefix] += 1
        node_id = f"{prefix}_{category_counters[prefix]:03d}"
        node_list.append({"NodeID": node_id, "Label": term, "Category": category})
        entity_to_node_id[term] = node_id

    nodes_df = pd.DataFrame(node_list)
    nodes_df.to_csv(OUTPUT_NODES_PATH, index=False, encoding='utf-8-sig')
    print(f"ノードリストを {OUTPUT_NODES_PATH} に保存しました。 ({len(nodes_df)}件)")

    edge_list = []
    for rel in relations:
        source_term = rel.get('source')
        target_term = rel.get('target')
        original_relation = rel.get('relation')

        if not all([source_term, target_term, original_relation]) or source_term not in entity_to_node_id or target_term not in entity_to_node_id:
            continue

        source_id = entity_to_node_id[source_term]
        target_id = entity_to_node_id[target_term]
        
        # 標準的なリレーション名に変換
        standard_relation = RELATION_MAP.get(original_relation, original_relation)

        source_page = f"_p{min(rel['source_pages'])}" if rel.get('source_pages') else ""
        datasource = f"{PDF_FILENAME}{source_page}"

        edge_list.append({
            "SourceID": source_id,
            "TargetID": target_id,
            "Relation": standard_relation,
            "DataSource": datasource
        })

    edges_df = pd.DataFrame(edge_list).drop_duplicates()
    edges_df.to_csv(OUTPUT_EDGES_PATH, index=False, encoding='utf-8-sig')
    print(f"エッジリストを {OUTPUT_EDGES_PATH} に保存しました。 ({len(edges_df)}件)")

    print("--- ステップ5: CSVへのエクスポートが完了しました ---")

    export_normalization_graph()

if __name__ == "__main__":
    main()
