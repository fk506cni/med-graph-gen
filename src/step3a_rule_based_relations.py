import json
import spacy
from spacy.matcher import Matcher

def main():
    # GiNZAのロード
    nlp = spacy.load("ja_core_news_lg")

    # ファイルの読み込み
    with open("output/cleaned_text.json", "r", encoding="utf-8") as f:
        cleaned_text = json.load(f)

    with open("output/entities.json", "r", encoding="utf-8") as f:
        entities = json.load(f)

    relations = []
    for item in cleaned_text:
        paragraph = item["paragraph"]
        doc = nlp(paragraph)
        
        # ここに係り受け解析と関係抽出のロジックを実装
        # (今回はまず骨格のみ)

    # 結果の出力
    with open("output/relations.json", "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()