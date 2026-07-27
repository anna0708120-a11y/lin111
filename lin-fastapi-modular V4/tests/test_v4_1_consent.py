"""
V4.1 測試：Consent 動態調整
"""

from app.state import AppState
from app.intimacy.consent_dynamics import (
    ConsentDynamics,
    ConsentAdjustment,
    detect_behavior_and_adjust,
    get_consent_with_dynamics
)
from app.intimacy.consent import calculate_consent
from datetime import datetime, timedelta


def test_adjustment_decay():
    """測試調整的衰減機制"""
    print("=" * 50)
    print("測試 1: 調整衰減機制")
    print("=" * 50)
    
    now = datetime.now()
    
    # 創建一個調整
    adj = ConsentAdjustment(
        delta=10.0,
        reason="溫柔回應",
        timestamp=now - timedelta(hours=12),
        decay_hours=24.0
    )
    
    # 12 小時後應該剩 50%
    effect_12h = adj.get_current_effect(now)
    print(f"\n12 小時後效果: {effect_12h:.2f} (預期 ~5.0)")
    assert 4.5 <= effect_12h <= 5.5, "12 小時應該衰減到約 50%"
    
    # 24 小時後應該完全消失
    effect_24h = adj.get_current_effect(now + timedelta(hours=12))
    print(f"24 小時後效果: {effect_24h:.2f} (預期 0.0)")
    assert effect_24h == 0.0, "24 小時應該完全衰減"
    
    print("\n✅ 衰減機制測試通過")


def test_consent_dynamics_basic():
    """測試基本的動態調整功能"""
    print("\n" + "=" * 50)
    print("測試 2: 基本動態調整")
    print("=" * 50)
    
    dynamics = ConsentDynamics()
    
    # 添加幾個調整
    dynamics.add_adjustment(8, "溫柔回應", decay_hours=12)
    dynamics.add_adjustment(6, "主動關心", decay_hours=18)
    dynamics.add_adjustment(-10, "冷淡回應", decay_hours=24)
    
    # 計算總調整
    total = dynamics.get_total_adjustment()
    print(f"\n總調整量: {total:.2f}")
    print(f"預期範圍: 0 ~ 10 (8 + 6 - 10)")
    
    assert -5 <= total <= 10, "總調整應該在合理範圍內"
    
    # 獲取有效調整列表
    active = dynamics.get_active_adjustments()
    print(f"\n有效調整數量: {len(active)}")
    assert len(active) == 3, "應該有 3 個有效調整"
    
    print("\n✅ 基本功能測試通過")


def test_behavior_detection():
    """測試行為檢測"""
    print("\n" + "=" * 50)
    print("測試 3: 行為檢測")
    print("=" * 50)
    
    dynamics = ConsentDynamics()
    
    # 測試溫柔回應
    behavior1 = detect_behavior_and_adjust("謝謝你，辛苦了", dynamics)
    print(f"\n「謝謝你，辛苦了」→ {behavior1}")
    assert behavior1 == "温柔回應", "應該檢測為溫柔回應"
    
    # 測試主動關心
    behavior2 = detect_behavior_and_adjust("你還好嗎？需要幫忙嗎？", dynamics)
    print(f"「你還好嗎？需要幫忙嗎？」→ {behavior2}")
    assert behavior2 == "主動關心", "應該檢測為主動關心"
    
    # 測試冷淡回應
    behavior3 = detect_behavior_and_adjust("嗯", dynamics)
    print(f"「嗯」→ {behavior3}")
    assert behavior3 == "冷淡回應", "應該檢測為冷淡回應"
    
    # 測試親密互動
    behavior4 = detect_behavior_and_adjust("想你了，抱抱", dynamics)
    print(f"「想你了，抱抱」→ {behavior4}")
    assert behavior4 == "親密互動", "應該檢測為親密互動"
    
    # 檢查調整是否生效
    total = dynamics.get_total_adjustment()
    print(f"\n累積調整量: {total:.2f}")
    print(f"預期: 正值（因為正向行為多於負向）")
    
    print("\n✅ 行為檢測測試通過")


def test_consent_with_dynamics():
    """測試 Consent 與動態調整的整合"""
    print("\n" + "=" * 50)
    print("測試 4: Consent 整合")
    print("=" * 50)
    
    # 基礎狀態（降低初始值，避免達到上限）
    mood = {"attachment": 0.5, "possessiveness": 0.3, "stress": 0.3, "fatigue": 0.2}
    body_values = {"tension": 30, "heat": 25, "sensitivity": 20, "control": 70}
    relationship = {"safety": 50, "rapport": 45, "temperature": 40}
    
    # 計算基礎 Consent
    base_consent = calculate_consent(mood, body_values, relationship)
    print(f"\n基礎 Consent: {base_consent:.2f}")
    
    # 添加動態調整
    dynamics = ConsentDynamics()
    dynamics.add_adjustment(10, "溫柔回應")
    dynamics.add_adjustment(6, "主動關心")
    
    # 計算含動態調整的 Consent
    final_consent = get_consent_with_dynamics(base_consent, dynamics)
    print(f"動態調整後 Consent: {final_consent:.2f}")
    print(f"調整量: +{final_consent - base_consent:.2f}")
    
    assert final_consent > base_consent, "正向行為應該提升 Consent"
    assert final_consent - base_consent <= 20, "調整量應該在合理範圍內"
    
    print("\n✅ Consent 整合測試通過")


def test_state_integration():
    """測試與 State 的整合"""
    print("\n" + "=" * 50)
    print("測試 5: State 整合")
    print("=" * 50)
    
    state = AppState()
    
    # 檢查 consent_dynamics 是否初始化
    assert hasattr(state, 'consent_dynamics'), "State 應該有 consent_dynamics 屬性"
    assert isinstance(state.consent_dynamics, ConsentDynamics), "consent_dynamics 應該是 ConsentDynamics 實例"
    
    # 測試行為檢測
    detect_behavior_and_adjust("謝謝你", state.consent_dynamics)
    
    total = state.consent_dynamics.get_total_adjustment()
    print(f"\n調整量: {total:.2f}")
    assert total > 0, "溫柔回應應該產生正向調整"
    
    print("\n✅ State 整合測試通過")


def test_serialization():
    """測試序列化與反序列化"""
    print("\n" + "=" * 50)
    print("測試 6: 序列化與反序列化")
    print("=" * 50)
    
    dynamics = ConsentDynamics()
    
    # 添加調整
    dynamics.add_adjustment(8, "溫柔回應", decay_hours=12)
    dynamics.add_adjustment(-10, "冷淡回應", decay_hours=24)
    
    # 序列化
    data = dynamics.to_dict_list()
    print(f"\n序列化結果: {len(data)} 條記錄")
    
    # 反序列化
    restored = ConsentDynamics.from_dict_list(data)
    print(f"反序列化結果: {len(restored.adjustments)} 條記錄")
    
    assert len(restored.adjustments) == 2, "反序列化後應該有 2 條記錄"
    
    # 驗證數值一致
    original_total = dynamics.get_total_adjustment()
    restored_total = restored.get_total_adjustment()
    print(f"\n原始總調整: {original_total:.2f}")
    print(f"恢復後總調整: {restored_total:.2f}")
    
    assert abs(original_total - restored_total) < 0.1, "序列化後數值應該一致"
    
    print("\n✅ 序列化測試通過")


def test_consent_prompt_integration():
    """測試 Prompt 整合"""
    print("\n" + "=" * 50)
    print("測試 7: Prompt 整合")
    print("=" * 50)
    
    from app.intimacy.prompt import build_intimacy_prompt
    
    state = AppState()
    
    # 設置狀態
    state.body_values = {"tension": 80, "heat": 70, "sensitivity": 60, "control": 40}
    state.mood = {"attachment": 0.8, "possessiveness": 0.6, "stress": 0.2, "fatigue": 0.3}
    state.relationship = {"safety": 70, "rapport": 65, "temperature": 60}
    
    # 添加動態調整
    state.consent_dynamics.add_adjustment(10, "溫柔回應", decay_hours=12)
    state.consent_dynamics.add_adjustment(6, "主動關心", decay_hours=18)
    state.consent_dynamics.add_adjustment(-8, "冷淡回應", decay_hours=24)
    
    # 生成 Prompt
    prompt = build_intimacy_prompt(state, datetime.now())
    
    print("\n生成的 Prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    
    # 檢查是否包含互動意願區塊
    assert "【互動意願】" in prompt, "應該包含互動意願區塊"
    
    print("\n✅ Prompt 整合測試通過")


if __name__ == "__main__":
    try:
        test_adjustment_decay()
        test_consent_dynamics_basic()
        test_behavior_detection()
        test_consent_with_dynamics()
        test_state_integration()
        test_serialization()
        test_consent_prompt_integration()
        
        print("\n" + "=" * 50)
        print("🎉 所有 V4.1 Consent Dynamics 測試通過！")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        raise
