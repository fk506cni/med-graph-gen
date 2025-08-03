import json
import spacy
from spacy.matcher import Matcher

def main():
    # GiNZAのロード
    # Load GiNZA
    nlp = spacy.load("ja_core_news_lg")

    # ファイルの読み込み
    # Load files
    with open("output/cleaned_text.json", "r", encoding="utf-8") as f:
        cleaned_text = json.load(f)

    with open("output/entities.json", "r", encoding="utf-8") as f:
        entities = json.load(f)

    # エンティティのリストをセットに変換（高速なルックアップのため）
    # Convert the list of entities to a set (for faster lookup)
    entity_terms = {entity["term"] for entity in entities}

    relations = []
    for item in cleaned_text:
        paragraph = item["paragraph"]
        source_pages = item["source_pages"]
        doc = nlp(paragraph)

        # CQから関係を抽出するロジック
        # Logic to extract relationships from CQs
        if paragraph.strip().startswith("CQ"):
            # 段落に含まれるエンティティを特定
            # Identify entities contained in the paragraph
            found_entities = [entity for entity in entities if entity["term"] in paragraph]
            
            # 疾患と治療法が1つずつ含まれ、「有効か」という文字列があれば関係を抽出
            # Extract relationship if one disease and one treatment are included and the string "有効か" (is it effective) is present
            if len(found_entities) >= 2 and "有効か" in paragraph:
                diseases = [e for e in found_entities if e["category"] == "Disease"]
                treatments = [e for e in found_entities if e["category"] == "Treatment"]

                if len(diseases) > 0 and len(treatments) > 0:
                    for disease in diseases:
                        for treatment in treatments:
                            relations.append({
                                "source": treatment["term"],
                                "target": disease["term"],
                                "relation": "is_effective_for",
                                "source_pages": source_pages
                            })

        # 係り受け解析と関係抽出のロジック
        # Dependency parsing and relationship extraction logic
        for sent in doc.sents:
            for token in sent:
                # 例：「原因はAである」のような単純な関係を抽出
                # Example: Extract simple relationships like "The cause is A"
                if token.dep_ == "nsubj" and token.head.text == "原因":
                    subject = token.text
                    if subject in entity_terms:
                        # 「原因」の述語を探す
                        # Find the predicate of "原因" (cause)
                        for child in token.head.children:
                            if child.dep_ == "cop": # "である"
                                obj_token = None
                                for child_of_head in token.head.children:
                                    if child_of_head.dep_ == "obl":
                                        obj_token = child_of_head
                                        break
                                if obj_token and obj_token.text in entity_terms:
                                    relations.append({
                                        "source": subject,
                                        "target": obj_token.text,
                                        "relation": "is_cause_of",
                                        "source_pages": source_pages
                                    })

    # 結果の出力
    # Output the results
    with open("output/relations.json", "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()