import argparse
import step1_extract
import step2a_clean_text
import step2b_extract_entities
# import step3a_rule_based_relations
import step3b_llm_based_relations
import step4_normalize
import step5_export

def main():
    parser = argparse.ArgumentParser(description="ナレッジグラフ生成パイプライン")
    parser.add_argument(
        '--start-step',
        type=str,
        default='step1',
        choices=['step1', 'step2a', 'step2b', 'step3b', 'step4', 'step5'],
        help='パイプラインを開始するステップを指定します'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gemini-2.5-flash-lite',
        help='使用するLLMモデルを指定します'
    )
    args = parser.parse_args()

    # LLMを必要とするステップのリスト
    llm_steps = ['step2a', 'step2b', 'step3b', 'step4']

    # 利用可能なステップとそれに対応する関数をマッピング
    steps = {
        'step1': step1_extract.main,
        'step2a': step2a_clean_text.main,
        'step2b': step2b_extract_entities.main,
        # 'step3a': step3a_rule_based_relations.main,
        'step3b': step3b_llm_based_relations.main,
        'step4': step4_normalize.main,
        'step5': step5_export.main,
    }

    # 実行するステップのリストを定義
    step_order = ['step1', 'step2a', 'step2b', 'step3b', 'step4', 'step5']

    # 指定された開始ステップから処理を開始
    start_index = step_order.index(args.start_step)

    for i in range(start_index, len(step_order)):
        current_step = step_order[i]
        if current_step in steps:
            print(f"\n--- ステップ: {current_step} を開始します ---")
            # LLMを使用するステップにはモデル名を渡す
            if current_step in llm_steps:
                print(f"使用モデル: {args.model}")
                steps[current_step](model_name=args.model)
            else:
                steps[current_step]()
            print(f"--- ステップ: {current_step} が完了しました ---")
        else:
            print(f"\n--- ステップ: {current_step} は未実装のためスキップします ---")

if __name__ == "__main__":
    main()
