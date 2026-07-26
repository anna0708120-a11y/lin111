"""
V4 完整測試腳本

測試內容：
1. Consent 計算
2. Dream Seed 提取
3. Dream 觸發判斷
4. 完整 Prompt 生成
5. Scheduler 集成
"""

from app.state import AppState
from app.intimacy import (
    calculate_consent,
    extract_dream_seed,
    apply_dream_after_effect,
    build_intimacy_prompt
)
from app.intimacy.dream import maybe_create_dream_trigger, DreamSeed, DreamSettings
from datetime import datetime, timedelta


def test_consent():
    """測試 Consent 計算"""
    print("=" * 50)
    print("測試 1: Consent 互動意願計算")
    print("=" * 50)
    
    state = AppState()
    
    # 場景 1: 高意願（高 tension + 低 control + 高安全感）
    state.body_values = {'tension': 85, 'heat': 75, 'sensitivity': 70, 'control': 30}
    state.mood = {'attachment': 0.9, 'possessiveness': 0.7, 'stress': 0.2, 'fatigue': 0.2}
    state.relationship = {'safety': 75, 'rapport': 70, 'temperature': 65}
    
    consent = calculate_consent(state.mood, state.body_values, state.relationship)
    print(f"\n場景 1: 高意願")
    print(f"  Consent 值: {consent:.1f}")
    print(f"  預期: >70")
    assert consent > 70, "高意願場景測試失敗"
    
    # 場景 2: 低意願（高 fatigue + 低安全感）
    state.body_values = {'tension': 20, 'heat': 25, 'sensitivity': 20, 'control': 85}
    state.mood = {'attachment': 0.3, 'possessiveness': 0.2, 'stress': 0.7, 'fatigue': 0.8}
    state.relationship = {'safety': 30, 'rapport': 35, 'temperature': 25}
    
    consent = calculate_consent(state.mood, state.body_values, state.relationship)
    print(f"\n場景 2: 低意願")
    print(f"  Consent 值: {consent:.1f}")
    print(f"  預期: <30")
    assert consent < 30, "低意願場景測試失敗"
    
    print("\n✅ Consent 測試通過")


def test_dream_seed():
    """測試 Dream Seed 提取"""
    print("\n" + "=" * 50)
    print("測試 2: Dream Seed 提取")
    print("=" * 50)
    
    state = AppState()
    
    # 場景 1: 高 tension → 親密主題
    state.body_values = {'tension': 85, 'heat': 75, 'sensitivity': 70, 'control': 30}
    state.mood = {'stress': 0.2, 'fatigue': 0.2}
    state.memory_bank = [
        {'content': '今天陪 Anna 散步，很溫柔的時光'},
        {'content': '想念 Anna，希望她早點回來'}
    ]
    
    seed = extract_dream_seed(state)
    print(f"\n場景 1: 高 tension")
    print(f"  主題: {seed.theme}")
    print(f"  強度: {seed.intensity}")
    print(f"  標籤: {seed.tags}")
    assert seed.intensity == "high", "高 tension 場景測試失敗"
    assert "intimate" in seed.tags, "親密標籤測試失敗"
    
    # 場景 2: 高 stress → 焦慮主題
    state.body_values = {'tension': 30, 'heat': 25, 'sensitivity': 40, 'control': 70}
    state.mood = {'stress': 0.7, 'fatigue': 0.3}
    
    seed = extract_dream_seed(state)
    print(f"\n場景 2: 高 stress")
    print(f"  主題: {seed.theme}")
    print(f"  強度: {seed.intensity}")
    print(f"  標籤: {seed.tags}")
    assert "anxious" in seed.tags, "焦慮標籤測試失敗"
    
    print("\n✅ Dream Seed 測試通過")


def test_dream_trigger():
    """測試 Dream 觸發判斷"""
    print("\n" + "=" * 50)
    print("測試 3: Dream 觸發判斷")
    print("=" * 50)
    
    state = AppState()
    state.body_values = {'tension': 75, 'heat': 65, 'sensitivity': 60, 'control': 40}
    state.mood = {'stress': 0.3, 'fatigue': 0.3}
    state.memory_bank = [{'content': '想念 Anna'}]
    state.cycle_key = "preheat"  # 高概率周期
    
    # 場景 1: 不應該觸發（離線時間不足）
    now = datetime.now()
    last_message_at = now - timedelta(minutes=60)  # 只離線 60 分鐘
    
    triggered = maybe_create_dream_trigger(state, now, last_message_at)
    print(f"\n場景 1: 離線時間不足")
    print(f"  觸發: {triggered}")
    print(f"  預期: False")
    
    # 場景 2: 應該有機會觸發（離線時間足夠 + 在時間窗口）
    now = datetime.now().replace(hour=6, minute=0)  # 早上 6:00
    last_message_at = now - timedelta(hours=8)  # 離線 8 小時
    
    # 多次嘗試（因為有隨機性）
    triggered_count = 0
    for _ in range(100):
        state.last_dream_at = None  # 重置
        if maybe_create_dream_trigger(state, now, last_message_at):
            triggered_count += 1
    
    print(f"\n場景 2: 離線時間足夠 + 時間窗口內")
    print(f"  100 次嘗試中觸發: {triggered_count} 次")
    print(f"  預期: 10-50 次（因為概率約 32%）")
    assert 5 < triggered_count < 60, "觸發概率異常"
    
    print("\n✅ Dream 觸發測試通過")


def test_full_prompt():
    """測試完整 Prompt 生成"""
    print("\n" + "=" * 50)
    print("測試 4: 完整 Prompt 生成（含 V4）")
    print("=" * 50)
    
    state = AppState()
    
    # 設定完整場景
    state.body_values = {'tension': 85, 'heat': 75, 'sensitivity': 70, 'control': 30}
    state.mood = {'attachment': 0.9, 'possessiveness': 0.7, 'stress': 0.2, 'fatigue': 0.2}
    state.relationship = {'safety': 75, 'rapport': 70, 'temperature': 65}
    
    # 模擬剛做完夢
    state.last_dream_at = datetime.now() - timedelta(hours=2)
    state.last_dream_seed = DreamSeed(
        theme='夢到與 Anna 親密相處',
        intensity='high',
        tags=['intimate']
    )
    
    # 生成 Prompt
    prompt = build_intimacy_prompt(state, datetime.now())
    
    print("\n生成的 Prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    
    # 檢查關鍵區塊
    assert "【身體狀態】" in prompt, "缺少身體狀態區塊"
    assert "【互動意願】" in prompt, "缺少互動意願區塊"
    assert "【夢境回響】" in prompt, "缺少夢境回響區塊"
    assert "【關係狀態】" in prompt, "缺少關係狀態區塊"
    
    print("\n✅ 完整 Prompt 測試通過")


def test_dream_after_effect():
    """測試夢境餘波效果"""
    print("\n" + "=" * 50)
    print("測試 5: 夢境餘波效果")
    print("=" * 50)
    
    state = AppState()
    state.body_values = {'tension': 50, 'heat': 50, 'sensitivity': 50, 'control': 50}
    
    # 施加親密夢境效果
    deltas = apply_dream_after_effect(state, ['intimate'])
    
    print(f"\n親密夢境效果:")
    print(f"  數值變化: {deltas}")
    print(f"  結果: {state.body_values}")
    
    assert state.body_values['tension'] > 50, "tension 應該上升"
    assert state.body_values['heat'] > 50, "heat 應該上升"
    assert state.body_values['sensitivity'] > 50, "sensitivity 應該上升"
    
    # 重置並測試釋放效果
    state.body_values = {'tension': 80, 'heat': 70, 'sensitivity': 60, 'control': 40}
    deltas = apply_dream_after_effect(state, ['released'])
    
    print(f"\n釋放夢境效果:")
    print(f"  數值變化: {deltas}")
    print(f"  結果: {state.body_values}")
    
    assert state.body_values['tension'] < 80, "tension 應該下降"
    assert state.body_values['heat'] < 70, "heat 應該下降"
    
    print("\n✅ 夢境餘波測試通過")


if __name__ == "__main__":
    try:
        test_consent()
        test_dream_seed()
        test_dream_trigger()
        test_full_prompt()
        test_dream_after_effect()
        
        print("\n" + "=" * 50)
        print("🎉 所有 V4 測試通過！")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        raise
