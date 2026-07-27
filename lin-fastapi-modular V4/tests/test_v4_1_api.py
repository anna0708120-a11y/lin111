"""
V4.1 API 端點測試
測試 Consent Dynamics 的 HTTP 接口
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_consent_api():
    """測試 /intimacy/consent API"""
    print("=" * 50)
    print("測試 /intimacy/consent API")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/intimacy/consent")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ API 回應成功")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 驗證必要欄位
            assert "base_consent" in data, "缺少 base_consent"
            assert "total_adjustment" in data, "缺少 total_adjustment"
            assert "final_consent" in data, "缺少 final_consent"
            assert "level" in data, "缺少 level"
            assert "description" in data, "缺少 description"
            assert "adjustments" in data, "缺少 adjustments"
            
            print("\n✅ 所有必要欄位都存在")
        else:
            print(f"\n❌ API 請求失敗: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 無法連接到服務器")
        print("請先啟動服務器: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()


def test_watch_with_behavior():
    """測試 /watch 端點的行為檢測"""
    print("\n" + "=" * 50)
    print("測試 /watch 端點的行為檢測")
    print("=" * 50)
    
    test_messages = [
        "謝謝你，辛苦了",
        "你還好嗎？",
        "嗯",
        "想你了，抱抱"
    ]
    
    try:
        for msg in test_messages:
            print(f"\n發送消息: {msg}")
            
            response = requests.post(
                f"{BASE_URL}/watch",
                json={"activity": msg}
            )
            
            if response.status_code == 200:
                print(f"✅ 回應成功")
                # SSE 回應，先不解析
            else:
                print(f"❌ 請求失敗: {response.status_code}")
        
        # 查看 Consent 調整
        print("\n查看累積的 Consent 調整:")
        response = requests.get(f"{BASE_URL}/intimacy/consent")
        if response.status_code == 200:
            data = response.json()
            print(f"總調整量: {data['total_adjustment']}")
            print(f"最終 Consent: {data['final_consent']}")
            print(f"\n調整列表:")
            for adj in data['adjustments']:
                print(f"  • {adj['reason']}: {adj['effect']:+.1f} ({adj['hours_ago']:.1f}h 前)")
                
    except requests.exceptions.ConnectionError:
        print("\n❌ 無法連接到服務器")
        print("請先啟動服務器: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("開始測試 V4.1 Consent Dynamics API...\n")
    
    test_consent_api()
    # test_watch_with_behavior()  # 暫時註解，避免影響對話歷史
    
    print("\n" + "=" * 50)
    print("測試完成")
    print("=" * 50)
