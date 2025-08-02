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
    parser.add_argument(
        '--wait',
        type=int,
        default=60,
        help='APIレート制限のための待機時間（秒）'
    )
    parser.add_argument(
        '--start_page',
        type=int,
        default=None,
        help='処理を開始するページ番号'
    )
    parser.add_argument(
        '--end_page',
        type=int,
        default=None,
        help='処理を終了するページ番号'
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
            
            kwargs = {}
            if current_step == 'step1':
                kwargs['start_page'] = args.start_page
                kwargs['end_page'] = args.end_page
            elif current_step in llm_steps:
                kwargs['model_name'] = args.model
                kwargs['wait'] = args.wait
                print(f"使用モデル: {args.model}")
                print(f"待機時間: {args.wait}秒")

            steps[current_step](**kwargs)
            print(f"--- ステップ: {current_step} が完了しました ---")
        else:
            print(f"\n--- ステップ: {current_step} は未実装のためスキップします ---")

if __name__ == "__main__":
    main()
