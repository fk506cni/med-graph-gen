import json
from collections import defaultdict
import time
from .llm_utils import get_gemini_model, llm_generate_with_retry

def load_cleaned_data(file_path):
    """クレンジングされた段落と出典情報のリストを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_prompt_template(file_path):
    """プロンプトテンプレートを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_entities_with_llm_batch(cleaned_data, prompt_template, model, wait=60, retries=3, batch_size=5):
    """LLMを使用してエンティティを抽出する（バッチ処理＆リトライ機能付き）"""
    entity_sources = defaultdict(set)
    paragraphs_to_process = [item['paragraph'] for item in cleaned_data]

    for i in range(0, len(paragraphs_to_process), batch_size):
        batch_paragraphs = paragraphs_to_process[i:i + batch_size]
        batch_source_info = cleaned_data[i:i + batch_size]
        
        batch_text = "\n\n".join(batch_paragraphs)
        prompt = prompt_template.replace("{{JSON_INPUT}}", json.dumps(batch_text, ensure_ascii=False))
        
        try:
            print(f"エンティティ抽出バッチ {i // batch_size + 1} を開始... ({len(batch_paragraphs)}段落)")
            response = llm_generate_with_retry(model, prompt, retries=retries)
            
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_json_str = response_text[len("```json"):-len("```")].strip()
            else:
                response_json_str = response_text

            extracted_data = json.loads(response_json_str)
            
            for entity in extracted_data.get('entities', []):
                if 'term' in entity and 'category' in entity:
                    for item in batch_source_info:
                        if entity['term'] in item['paragraph']:
                            entity_key = (entity['term'], entity['category'])
                            for page_num in item['source_pages']:
                                entity_sources[entity_key].add(page_num)

            print(f"エンティティ抽出バッチ {i // batch_size + 1} が完了しました。")

        except Exception as e:
            print(f"バッチ処理中に致命的なエラーが発生しました: {e}")
            continue
        finally:
            if i + batch_size < len(paragraphs_to_process):
                print(f"{wait}秒待機します...")
                time.sleep(wait)
            
    final_entities = []
    for (term, category), pages in entity_sources.items():
        final_entities.append({
            "term": term,
            "category": category,
            "source_pages": sorted(list(pages))
        })
    
    return final_entities

def main(model_name='gemini-1.5-flash-latest', wait=60, retries=3):
    """メイン処理"""
    input_path = "output/step2a_cleaned_text.json"
    prompt_template_path = "entity_extraction_prompt.md"
    output_entities_path = "output/step2b_entities.json"

    print("クレンジングされた段落データを読み込み中...")
    cleaned_data = load_cleaned_data(input_path)

    print("プロンプトテンプレートを読み込み中...")
    prompt_template = load_prompt_template(prompt_template_path)

    print("LLMモデルを初期化中...")
    model = get_gemini_model(model_name)

    print("LLMを使用してエンティティを抽出中（バッチ処理）...")
    entities = extract_entities_with_llm_batch(
        cleaned_data, 
        prompt_template, 
        model, 
        wait=wait, 
        retries=retries
    )

    print(f"抽出されたエンティティを {output_entities_path} に保存中...")
    with open(output_entities_path, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    print("処理が完了しました。")


if __name__ == "__main__":
    main()
