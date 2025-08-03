import argparse
from . import step1_extract
from . import step2a_clean_text
from . import step2b_extract_entities
# from . import step3a_rule_based_relations
from . import step3b_llm_based_relations
from . import step4_normalize
from . import step5_export
from . import step6_import_to_neo4j

def main():
    # 利用可能なステップとそれに対応する関数をマッピング
    steps = {
        'step1': step1_extract.main,
        'step2a': step2a_clean_text.main,
        'step2b': step2b_extract_entities.main,
        # 'step3a': step3a_rule_based_relations.main,
        'step3b': step3b_llm_based_relations.main,
        'step4': step4_normalize.main,
        'step5': step5_export.main,
        'step6': step6_import_to_neo4j.main,
    }
    step_order = list(steps.keys())

    parser = argparse.ArgumentParser(description="ナレッジグラフ生成パイプライン")
    parser.add_argument(
        '--start-step',
        type=str,
        default=step_order[0],
        choices=step_order,
        help='パイプラインを開始するステップを指定します'
    )
    parser.add_argument(
        '--end-step',
        type=str,
        default=step_order[-1],
        choices=step_order,
        help='パイプラインを終了するステップを指定します'
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
        '--retries',
        type=int,
        default=3,
        help='API呼び出しの最大リトライ回数'
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

    # 指定された開始ステップと終了ステップから処理範囲を決定
    start_index = step_order.index(args.start_step)
    end_index = step_order.index(args.end_step)

    if start_index > end_index:
        parser.error("--start-step は --end-step より前のステップでなければなりません。")

    for i in range(start_index, end_index + 1):
        current_step = step_order[i]
        print(f"\n--- ステップ: {current_step} を開始します ---")
        
        kwargs = {}
        if current_step == 'step1':
            kwargs['start_page'] = args.start_page
            kwargs['end_page'] = args.end_page
        elif current_step in llm_steps:
            kwargs['model_name'] = args.model
            kwargs['wait'] = args.wait
            kwargs['retries'] = args.retries
            print(f"使用モデル: {args.model}")
            print(f"待機時間: {args.wait}秒")
            print(f"リトライ回数: {args.retries}回")

        steps[current_step](**kwargs)
        print(f"--- ステップ: {current_step} が完了しました ---")

if __name__ == "__main__":
    main()


