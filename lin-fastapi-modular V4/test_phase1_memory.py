"""
Phase 1 Memory Management - 測試腳本

測試項目：
1. Keyword normalization
2. Conflict detection
3. Memory CRUD with conflict check
4. API endpoints

執行方式：
    python test_phase1_memory.py
"""
import sys
sys.path.insert(0, '.')

from app.keyword_normalizer import normalize_keyword, get_synonym_map
from app.memory_conflict import detect_conflict, _content_similarity


def test_keyword_normalization():
    """測試關鍵字正規化"""
    print("\n=== Test 1: Keyword Normalization ===")
    
    test_cases = [
        ("朱古力", "chocolate"),
        ("巧克力", "chocolate"),
        ("巧ke力", "chocolate"),
        ("雪糕", "ice_cream"),
        ("冰淇淋", "ice_cream"),
        ("開心", "happy"),
        ("高興", "happy"),
        ("COFFEE", "coffee"),
        ("  咖啡  ", "coffee"),
    ]
    
    for raw, expected in test_cases:
        normalized = normalize_keyword(raw)
        status = "✓" if normalized == expected else "✗"
        print(f"{status} {raw:15} -> {normalized:15} (expected: {expected})")


def test_content_similarity():
    """測試內容相似度計算"""
    print("\n=== Test 2: Content Similarity ===")
    
    test_cases = [
        ("Anna 喜歡吃朱古力", "Anna 喜歡吃朱古力", 1.0),
        ("Anna 喜歡吃朱古力", "Anna 最愛吃朱古力", 0.7),
        ("Anna 喜歡吃朱古力", "Anna 不喜歡吃朱古力", 0.6),
        ("Anna 喜歡吃朱古力", "Anna 喜歡喝咖啡", 0.4),
    ]
    
    for text1, text2, expected_min in test_cases:
        sim = _content_similarity(text1, text2)
        status = "✓" if sim >= expected_min - 0.15 else "✗"  # 允許 15% 誤差
        print(f"{status} Similarity: {sim:.2f} (expected >= {expected_min:.2f})")
        print(f"   Text1: {text1}")
        print(f"   Text2: {text2}")


def test_conflict_detection():
    """測試衝突偵測（需要資料庫連接）"""
    print("\n=== Test 3: Conflict Detection ===")
    print("⚠ 此測試需要資料庫連接，跳過")
    print("手動測試步驟：")
    print("1. 先插入一條記憶：keyword='chocolate', content='Anna 喜歡吃朱古力'")
    print("2. 再插入衝突記憶：keyword='巧克力', content='Anna 不喜歡吃朱古力'")
    print("3. 檢查第二條是否被標記為 pending_review=True")


def test_api_endpoints():
    """測試 API endpoints（需要伺服器運行）"""
    print("\n=== Test 4: API Endpoints ===")
    print("⚠ 此測試需要伺服器運行，跳過")
    print("手動測試步驟：")
    print("1. 啟動伺服器：uvicorn app.main:app --reload")
    print("2. 測試 GET /api/memory/pending")
    print("3. 測試 POST /api/memory/approve/:id")
    print("4. 測試 POST /api/memory/reject/:id")
    print("5. 測試 GET /api/memory/conflicts/summary")


def test_synonym_map():
    """測試同義詞表"""
    print("\n=== Test 5: Synonym Map ===")
    
    synonym_map = get_synonym_map()
    print(f"同義詞表共 {len(synonym_map)} 項")
    
    # 顯示部分內容
    categories = {
        "食物": ["朱古力", "巧克力", "雪糕", "薯片"],
        "情緒": ["開心", "難過", "緊張"],
        "活動": ["運動", "跑步", "游泳"],
    }
    
    for cat, words in categories.items():
        print(f"\n{cat}:")
        for word in words:
            normalized = normalize_keyword(word)
            print(f"  {word:10} -> {normalized}")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1 Memory Management - 測試腳本")
    print("=" * 60)
    
    test_keyword_normalization()
    test_content_similarity()
    test_conflict_detection()
    test_api_endpoints()
    test_synonym_map()
    
    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)
