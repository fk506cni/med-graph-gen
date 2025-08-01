import step1_extract
import step2_entities

if __name__ == "__main__":
    print("ステップ1: テキスト抽出と構造化を開始します。")
    step1_extract.main()
    print("ステップ1が完了しました。")

    print("\nステップ2: エンティティ抽出を開始します。")
    step2_entities.main()
    print("ステップ2が完了しました。")
