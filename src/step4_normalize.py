import json
import os
import time
from collections import Counter, defaultdict
from tqdm import tqdm
from .llm_utils import get_gemini_model, llm_generate_with_retry

# --- 定数 --- #
INPUT_ENTITIES_PATH = "output/step2b_entities.json"
INPUT_RELATIONS_PATH = "output/step3b_relations.jsonl"
OUTPUT_NORMALIZED_ENTITIES_PATH = "output/step4_normalized_entities.json"
OUTPUT_NORMALIZED_RELATIONS_PATH = "output/step4_normalized_relations.jsonl"
NORMALIZATION_MAP_PATH = "output/step4_normalization_map.json"
PROMPT_TEMPLATE_PATH = "entity_normalization_prompt.md"
LLM_REQUEST_BATCH_SIZE = 100  # 一度にLLMに送るエンティティの数

def load_json(path):
    """JSONファイルを読み込む
    Loads a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    """JSONファイルに保存する
    Saves data to a JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_jsonl(path):
    """JSON Linesファイルを読み込む
    Loads a JSON Lines file."""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def save_jsonl(data, path):
    """JSON Linesファイルに保存する
    Saves data to a JSON Lines file."""
    with open(path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def get_normalization_map_from_llm(entities, model, wait=60, retries=3):
    """LLMを使用して正規化マッピングを取得し、多数決で最終版を生成する
    Gets a normalization map using an LLM and generates the final version by majority vote."""
    print("LLMを呼び出してエンティティの正規化マッピングを生成します... / Calling LLM to generate entity normalization mapping...")
    with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    all_suggestions = defaultdict(list)
    entity_terms = [entity['term'] for entity in entities]

    for i in tqdm(range(0, len(entity_terms), LLM_REQUEST_BATCH_SIZE), desc="正規化マッピング生成 / Generating normalization mapping"):
        batch = entity_terms[i:i + LLM_REQUEST_BATCH_SIZE]
        entities_json_str = json.dumps(batch, ensure_ascii=False, indent=2)
        prompt = prompt_template.format(entities_json=entities_json_str)

        try:
            response = llm_generate_with_retry(model, prompt, retries=retries)
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
                print(f"警告: バッチ {i//LLM_REQUEST_BATCH_SIZE + 1} の応答からJSONを抽出できませんでした。 / Warning: Could not extract JSON from the response of batch {i//LLM_REQUEST_BATCH_SIZE + 1}.")

        except Exception as e:
            print(f"エラー: LLM呼び出し中に致命的なエラーが発生しました: {e} / Error: A fatal error occurred during the LLM call: {e}")

        if i + LLM_REQUEST_BATCH_SIZE < len(entity_terms):
            time.sleep(wait)

    final_normalization_map = {}
    print("\n正規化マッピングを統合しています... / Consolidating normalization mapping...")
    for alias, suggestions in tqdm(all_suggestions.items(), desc="マッピング統合 / Consolidating mapping"):
        if not suggestions:
            continue
        counts = Counter(suggestions)
        most_common_name = counts.most_common(1)[0][0]
        final_normalization_map[alias] = most_common_name

    return final_normalization_map

def normalize_entities(entities, normalization_map):
    """エンティティリストを正規化する
    Normalizes the entity list."""
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
    """リレーションリストを正規化する
    Normalizes the relation list."""
    normalized_relations = []
    for rel in relations:
        new_rel = rel.copy()
        new_rel['source'] = normalization_map.get(rel['source'], rel['source'])
        new_rel['target'] = normalization_map.get(rel['target'], rel['target'])
        if new_rel['source'] != new_rel['target']:
            normalized_relations.append(new_rel)
    return normalized_relations

def main(model_name='gemini-1.5-flash-latest', wait=60, retries=3):
    """
    エンティティとリレーションを正規化するメイン関数
    Main function to normalize entities and relations
    """
    print("--- ステップ4: ナレッジの正規化を開始します --- / --- Step 4: Starting knowledge normalization ---")

    if not os.path.exists(INPUT_ENTITIES_PATH):
        print(f"エラー: {INPUT_ENTITIES_PATH} が見つかりません。 / Error: {INPUT_ENTITIES_PATH} not found.")
        return
    if not os.path.exists(INPUT_RELATIONS_PATH):
        print(f"エラー: {INPUT_RELATIONS_PATH} が見つかりません。 / Error: {INPUT_RELATIONS_PATH} not found.")
        return

    entities = load_json(INPUT_ENTITIES_PATH)
    relations = load_jsonl(INPUT_RELATIONS_PATH)

    model = get_gemini_model(model_name)

    normalization_map = get_normalization_map_from_llm(entities, model, wait=wait, retries=retries)
    save_json(normalization_map, NORMALIZATION_MAP_PATH)
    print(f"正規化マッピングを {NORMALIZATION_MAP_PATH} に保存しました。 / Saved normalization map to {NORMALIZATION_MAP_PATH}.")

    normalized_entities = normalize_entities(entities, normalization_map)
    normalized_relations = normalize_relations(relations, normalization_map)

    save_json(normalized_entities, OUTPUT_NORMALIZED_ENTITIES_PATH)
    save_jsonl(normalized_relations, OUTPUT_NORMALIZED_RELATIONS_PATH)

    print(f"正規化されたエンティティを {OUTPUT_NORMALIZED_ENTITIES_PATH} に保存しました。 / Saved normalized entities to {OUTPUT_NORMALIZED_ENTITIES_PATH}.")
    print(f"正規化されたリレーションを {OUTPUT_NORMALIZED_RELATIONS_PATH} に保存しました。 / Saved normalized relations to {OUTPUT_NORMALIZED_RELATIONS_PATH}.")
    print("--- ステップ4: ナレッジの正規化が完了しました --- / --- Step 4: Knowledge normalization completed ---")

if __name__ == "__main__":
    main()
