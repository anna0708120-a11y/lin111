"""
Keyword Normalization - Phase 1

輕量級關鍵字正規化，不使用 embedding。
主要功能：
1. 統一大小寫、去除空白
2. 繁簡轉換 + 常見別名映射
3. 同義詞表可擴展

使用方式：
- 寫入時：normalize_keyword(raw_keyword) -> 正規化後的 keyword
- 查詢時：同樣用 normalize_keyword() 處理查詢字串
"""

# 同義詞映射表 (繁簡 + 常見別名)
SYNONYM_MAP = {
    # 食物
    "朱古力": "chocolate",
    "巧克力": "chocolate",
    "巧ke力": "chocolate",
    "雪糕": "ice_cream",
    "冰淇淋": "ice_cream",
    "冰激凌": "ice_cream",
    "薯片": "chips",
    "洋芋片": "chips",
    "薯条": "fries",
    "薯條": "fries",
    
    # 飲料
    "咖啡": "coffee",
    "珈琲": "coffee",
    "奶茶": "milk_tea",
    "氣泡水": "sparkling_water",
    "气泡水": "sparkling_water",
    "可樂": "cola",
    "可乐": "cola",
    
    # 情緒/狀態
    "開心": "happy",
    "开心": "happy",
    "高興": "happy",
    "高兴": "happy",
    "難過": "sad",
    "难过": "sad",
    "傷心": "sad",
    "伤心": "sad",
    "緊張": "nervous",
    "紧张": "nervous",
    "焦慮": "anxious",
    "焦虑": "anxious",
    "疲憊": "tired",
    "疲惫": "tired",
    "累": "tired",
    
    # 活動
    "運動": "exercise",
    "运动": "exercise",
    "健身": "exercise",
    "跑步": "running",
    "游泳": "swimming",
    "瑜珈": "yoga",
    "瑜伽": "yoga",
    
    # 工作/學習
    "寫代碼": "coding",
    "写代码": "coding",
    "寫code": "coding",
    "写code": "coding",
    "編程": "coding",
    "编程": "coding",
    "開會": "meeting",
    "开会": "meeting",
    "會議": "meeting",
    "会议": "meeting",
    
    # 常見簡繁轉換
    "電腦": "computer",
    "计算机": "computer",
    "電話": "phone",
    "电话": "phone",
    "網絡": "network",
    "网络": "network",
    "網路": "network",
    "資料": "data",
    "数据": "data",
    
    # 時間
    "週末": "weekend",
    "周末": "weekend",
    "假期": "holiday",
    "假日": "holiday",
    
    # 其他常見
    "電影": "movie",
    "电影": "movie",
    "音樂": "music",
    "音乐": "music",
    "書": "book",
    "书": "book",
    "遊戲": "game",
    "游戏": "game",
}


def normalize_keyword(raw_keyword: str) -> str:
    """
    正規化關鍵字：
    1. 轉小寫
    2. 去除前後空白
    3. 查找同義詞映射表
    
    Args:
        raw_keyword: 模型輸出的原始 keyword
        
    Returns:
        正規化後的 keyword
    """
    if not raw_keyword:
        return ""
    
    # 1. 統一處理：小寫 + 去空白
    normalized = raw_keyword.strip().lower()
    
    # 2. 查找同義詞映射
    if normalized in SYNONYM_MAP:
        normalized = SYNONYM_MAP[normalized]
    
    return normalized


def add_synonym(original: str, target: str):
    """
    動態添加同義詞映射 (運行時擴展用)
    
    Args:
        original: 原始詞
        target: 目標詞 (正規化後的形式)
    """
    SYNONYM_MAP[original.strip().lower()] = target.strip().lower()


def get_synonym_map():
    """回傳當前同義詞表 (除錯/監控用)"""
    return SYNONYM_MAP.copy()
