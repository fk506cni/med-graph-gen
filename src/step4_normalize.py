import json
import os
import time
from collections import Counter, defaultdict
import google.generativeai as genai
from tqdm import tqdm

# --- 定数 --- #
# APIキーを環境変数から取得
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# 入出力ファイルのパス
INPUT_ENTITIES_PATH = "output/entities.json"
INPUT_RELATIONS_PATH = "output/relations.jsonl"
OUTPUT_NORMALIZED_ENTITIES_PATH = "output/normalized_entities.json"
OUTPUT_NORMALIZED_RELATIONS_PATH = "output/normalized_relations.jsonl"
NORMALIZATION_MAP_PATH = "output/normalization_map.json"
PROMPT_TEMPLATE_PATH = "entity_normalization_prompt.md"

# LLM呼び出しのパラメータ
LLM_MODEL = "gemini-1.5-flash-latest"
LLM_REQUEST_BATCH_SIZE = 100  # 一度にLLMに送るエンティティの数
DELAY_SECONDS = 5  # APIレート制限のための待機時間

def load_json(path):
    """JSONファイルを読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    """JSONファイルに保存する"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_jsonl(path):
    """JSON Linesファイルを読み込む"""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def save_jsonl(data, path):
    """JSON Linesファイルに保存する"""
    with open(path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def get_normalization_map_from_llm(entities):
    """LLMを使用して正規化マッピングを取得し、多数決で最終版を生成する"""
    print("LLMを呼び出してエンティティの正規化マッピングを生成します...")
    model = genai.GenerativeModel(LLM_MODEL)
    with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    all_suggestions = defaultdict(list)
    entity_terms = [entity['term'] for entity in entities]

    # エンティティリストをバッチに分割して処理
    for i in tqdm(range(0, len(entity_terms), LLM_REQUEST_BATCH_SIZE), desc="正規化マッピング生成"):
        batch = entity_terms[i:i + LLM_REQUEST_BATCH_SIZE]
        entities_json_str = json.dumps(batch, ensure_ascii=False, indent=2)
        prompt = prompt_template.format(entities_json=entities_json_str)

        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            json_start = response_text.find('```json') + len('```json\n')
            json_end = response_text.rfind('```')
            if json_start != -1 and json_end != -1:
                json_content = response_text[json_start:json_end].strip()
                data = json.loads(json_content)
                batch_map = data.get("normalization_map", {})
                for alias, normalized_name in batch_map.items():
                    all_suggestions[alias].append(normalized_name)
            else:
                print(f"警告: バッチ {i//LLM_REQUEST_BATCH_SIZE + 1} の応答からJSONを抽出できませんでした。")

        except Exception as e:
            print(f"エラー: LLM呼び出し中にエラーが発生しました: {e}")

        if i + LLM_REQUEST_BATCH_SIZE < len(entity_terms):
            time.sleep(DELAY_SECONDS)

    # 多数決で最終的な正規化マッピングを決定
    final_normalization_map = {}
    print("\n正規化マッピングを統合しています...")
    for alias, suggestions in tqdm(all_suggestions.items(), desc="マッピング統合"):
        if not suggestions:
            continue
        counts = Counter(suggestions)
        most_common_name = counts.most_common(1)[0][0]
        final_normalization_map[alias] = most_common_name

    return final_normalization_map

def normalize_entities(entities, normalization_map):
    """エンティティリストを正規化する"""
    normalized_entities = []
    seen_terms = set()
    for entity in entities:
        original_term = entity['term']
        normalized_term = normalization_map.get(original_term, original_term)

        if normalized_term not in seen_terms:
            new_entity = entity.copy()
            new_entity['term'] = normalized_term
            normalized_entities.append(new_entity)
            seen_terms.add(normalized_term)
        else:
            for ne in normalized_entities:
                if ne['term'] == normalized_term:
                    ne['source_pages'] = sorted(list(set(ne['source_pages'] + entity['source_pages'])))
                    break

    return normalized_entities

def normalize_relations(relations, normalization_map):
    """リレーションリストを正規化する"""
    normalized_relations = []
    for rel in relations:
        new_rel = rel.copy()
        new_rel['source'] = normalization_map.get(rel['source'], rel['source'])
        new_rel['target'] = normalization_map.get(rel['target'], rel['target'])
        if new_rel['source'] != new_rel['target']:
            normalized_relations.append(new_rel)
    return normalized_relations

def main():
    """
    エンティティとリレーションを正規化するメイン関数
    """
    print("--- ステップ4: ナレッジの正規化を開始します ---")

    if not os.path.exists(INPUT_ENTITIES_PATH):
        print(f"エラー: {INPUT_ENTITIES_PATH} が見つかりません。")
        return
    if not os.path.exists(INPUT_RELATIONS_PATH):
        print(f"エラー: {INPUT_RELATIONS_PATH} が見つかりません。")
        return

    entities = load_json(INPUT_ENTITIES_PATH)
    relations = load_jsonl(INPUT_RELATIONS_PATH)

    normalization_map = get_normalization_map_from_llm(entities)
    save_json(normalization_map, NORMALIZATION_MAP_PATH)
    print(f"正規化マッピングを {NORMALIZATION_MAP_PATH} に保存しました。")

    normalized_entities = normalize_entities(entities, normalization_map)
    normalized_relations = normalize_relations(relations, normalization_map)

    save_json(normalized_entities, OUTPUT_NORMALIZED_ENTITIES_PATH)
    save_jsonl(normalized_relations, OUTPUT_NORMALIZED_RELATIONS_PATH)

    print(f"正規化されたエンティティを {OUTPUT_NORMALIZED_ENTITIES_PATH} に保存しました。")
    print(f"正規化されたリレーションを {OUTPUT_NORMALIZED_RELATIONS_PATH} に保存しました。")
    print("--- ステップ4: ナレッジの正規化が完了しました ---")

if __name__ == "__main__":
    main()
