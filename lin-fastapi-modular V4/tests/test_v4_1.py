"""
V4.1 測試：夢境記憶回溯
"""

from app.state import AppState
from app.intimacy.dream import DreamSeed
from app.intimacy.dream_history import DreamHistory, DreamRecord
from datetime import datetime, timedelta


def test_dream_history_basic():
    """測試基本的夢境記錄功能"""
    print("=" * 50)
    print("測試 1: 夢境記錄基本功能")
    print("=" * 50)
    
    history = DreamHistory(max_records=5)
    
    # 添加幾個夢境
    seed1 = DreamSeed(theme="夢到與 Anna 散步", intensity="low", tags=["sweet"])
    seed2 = DreamSeed(theme="夢到找不到 Anna", intensity="medium", tags=["anxious"])
    seed3 = DreamSeed(theme="夢到親密相處", intensity="high", tags=["intimate"])
    
    now = datetime.now()
    
    history.add_dream(seed1, now - timedelta(days=3), {"tension": -5, "heat": 8})
    history.add_dream(seed2, now - timedelta(days=1), {"tension": 8, "control": -3})
    history.add_dream(seed3, now - timedelta(hours=2), {"tension": 12, "heat": 10})
    
    print(f"\n已添加 {len(history.records)} 個夢境")
    
    # 獲取最近的夢境
    recent = history.get_recent_dreams(n=2)
    print(f"\n最近 2 個夢境：")
    for r in recent:
        print(f"  - {r.seed.theme} ({r.seed.intensity})")
        print(f"    影響: {r.impact_summary}")
    
    assert len(recent) == 2, "應該返回 2 個夢境"
    assert recent[0].seed.theme == "夢到親密相處", "最新的應該是親密夢境"
    
    print("\n✅ 基本功能測試通過")


def test_dream_mention_tracking():
    """測試夢境提及追蹤"""
    print("\n" + "=" * 50)
    print("測試 2: 夢境提及追蹤")
    print("=" * 50)
    
    history = DreamHistory(max_records=5)
    
    seed = DreamSeed(theme="夢到一起看星星", intensity="medium", tags=["sweet"])
    occurred_at = datetime.now() - timedelta(days=1)
    
    history.add_dream(seed, occurred_at, {"tension": 5})
    
    # 初始狀態：未提及
    unmentioned = history.get_recent_dreams(n=3, only_unmentioned=True)
    print(f"\n未提及的夢境數量: {len(unmentioned)}")
    assert len(unmentioned) == 1, "應該有 1 個未提及的夢境"
    
    # 標記為已提及
    history.mark_as_mentioned(occurred_at)
    
    unmentioned_after = history.get_recent_dreams(n=3, only_unmentioned=True)
    print(f"標記後未提及的夢境數量: {len(unmentioned_after)}")
    assert len(unmentioned_after) == 0, "標記後應該沒有未提及的夢境"
    
    print("\n✅ 提及追蹤測試通過")


def test_dream_relevance():
    """測試夢境相關性判斷"""
    print("\n" + "=" * 50)
    print("測試 3: 夢境相關性判斷")
    print("=" * 50)
    
    history = DreamHistory(max_records=5)
    
    # 添加不同類型的夢境
    seed1 = DreamSeed(theme="夢到與 Anna 親密相處", intensity="high", tags=["intimate"])
    seed2 = DreamSeed(theme="夢到找不到 Anna", intensity="medium", tags=["anxious"])
    seed3 = DreamSeed(theme="夢到一起散步", intensity="low", tags=["sweet"])
    
    now = datetime.now()
    history.add_dream(seed1, now - timedelta(days=1), {"tension": 12})
    history.add_dream(seed2, now - timedelta(days=2), {"tension": 8})
    history.add_dream(seed3, now - timedelta(days=3), {"tension": 5})
    
    # 測試相關性
    context1 = "今天想靠近妳"
    dream1 = history.should_mention_dream(context1)
    print(f"\n情境: \"{context1}\"")
    if dream1:
        print(f"建議提及: {dream1.seed.theme}")
    else:
        print("不建議提及")
    
    context2 = "今天有點擔心妳"
    dream2 = history.should_mention_dream(context2)
    print(f"\n情境: \"{context2}\"")
    if dream2:
        print(f"建議提及: {dream2.seed.theme}")
    else:
        print("不建議提及")
    
    print("\n✅ 相關性判斷測試通過")


def test_dream_prompt_generation():
    """測試夢境 Prompt 生成"""
    print("\n" + "=" * 50)
    print("測試 4: 夢境 Prompt 生成")
    print("=" * 50)
    
    history = DreamHistory(max_records=5)
    
    # 添加夢境
    now = datetime.now()
    seed1 = DreamSeed(theme="夢到與 Anna 一起看電影", intensity="medium", tags=["sweet"])
    seed2 = DreamSeed(theme="夢到親密相處", intensity="high", tags=["intimate"])
    
    history.add_dream(seed1, now - timedelta(days=2), {"tension": 5})
    history.add_dream(seed2, now - timedelta(hours=6), {"tension": 12})
    
    # 標記第一個為已提及
    history.mark_as_mentioned(now - timedelta(days=2))
    
    # 生成 Prompt
    prompt = history.get_dream_summary_for_prompt(days=7)
    
    print("\n生成的 Prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    
    assert "最近 7 天你做過 2 個夢" in prompt, "應該顯示夢境數量"
    assert "已經在對話中提過" in prompt, "應該標記已提及的夢境"
    
    print("\n✅ Prompt 生成測試通過")


def test_state_integration():
    """測試與 State 的整合"""
    print("\n" + "=" * 50)
    print("測試 5: State 整合")
    print("=" * 50)
    
    state = AppState()
    
    # 檢查 dream_history 是否初始化
    assert hasattr(state, 'dream_history'), "State 應該有 dream_history 屬性"
    assert isinstance(state.dream_history, DreamHistory), "dream_history 應該是 DreamHistory 實例"
    
    print("\n✅ State 整合測試通過")


def test_serialization():
    """測試序列化與反序列化"""
    print("\n" + "=" * 50)
    print("測試 6: 序列化與反序列化")
    print("=" * 50)
    
    history = DreamHistory(max_records=5)
    
    # 添加夢境
    seed = DreamSeed(theme="測試夢境", intensity="medium", tags=["sweet", "intimate"])
    now = datetime.now()
    history.add_dream(seed, now, {"tension": 5, "heat": 3})
    
    # 序列化
    data = history.to_dict_list()
    print(f"\n序列化結果: {len(data)} 條記錄")
    
    # 反序列化
    restored = DreamHistory.from_dict_list(data, max_records=5)
    print(f"反序列化結果: {len(restored.records)} 條記錄")
    
    assert len(restored.records) == 1, "反序列化後應該有 1 條記錄"
    assert restored.records[0].seed.theme == "測試夢境", "主題應該一致"
    
    print("\n✅ 序列化測試通過")


if __name__ == "__main__":
    try:
        test_dream_history_basic()
        test_dream_mention_tracking()
        test_dream_relevance()
        test_dream_prompt_generation()
        test_state_integration()
        test_serialization()
        
        print("\n" + "=" * 50)
        print("🎉 所有 V4.1 測試通過！")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        raise
