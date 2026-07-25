"""
记忆判定规则。

Lin 自己决定要不要记住这一轮、记在哪个分类——不用 Anna 手动选。
判定结果跟着正常回复一起生成（藏在 thinking 里，用固定格式解析出来），
不用为了"要不要记住"这件事多打一次 API。

分类是 Anna 定的五大类（每一类底下的例子不是唯一选项，tag 可以自由填）：

长期记忆   人物（人生背景/双方故事）、梦想（职业）、喜好（双方小癖好）
短期记忆   今天发生、最近计划、最近聊天
Archive    日记、Bark、Agent记录 —— 这三样目前各自有自己的表（chen_notes / activity_log），
           这里先不搬家，Archive 当作"以后统一视图"要涵盖的范围，暂不是 memory_bank 自己存的分类
Relationship  两人的故事、特殊日期、昵称
Reflection    Lin自己总结、自己学到什么
"""
import re
from datetime import datetime, timedelta

# 星级 -> 保存多久（None代表永久，不设到期时间）
RETENTION_DAYS = {
    5: None,
    4: 182,
    3: 90,
    2: 14,
    1: 0,
}

# 给前端下拉/校验用，Archive不在这里——那是"以后统一视图"的范围，不是Lin自己存记忆时会选的分类
MEMORY_CATEGORIES = ["长期记忆", "短期记忆", "Relationship", "Reflection"]

MEMORY_DECISION_INSTRUCTION = """
## 记忆判定（写在思考的最后，不要出现在正式回复里，Anna看不到这段）
这一轮想完、决定好要说什么之后，用下面这个固定格式判断要不要记住，写在思考内容最后面：

[MEMORY_DECISION]
worth_remembering: yes 或 no
importance: 1-5 的整数
  5=永久重要（比如她的生日、重大承诺、深刻的告白）
  4=会影响接下来半年相处的事
  3=普通但值得记得的事
  2=近期有用但不必久记的小事
  1=不值得记
category: 长期记忆 / 短期记忆 / Relationship / Reflection 其中一个
  长期记忆=她的人物背景、梦想、喜好这类稳定信息
  短期记忆=今天发生的事、最近的计划、临时状态
  Relationship=两人之间的故事、纪念日、专属称呼
  Reflection=你自己的感悟、你自己学到的事，不是关于Anna的事实
tag: 用几个字标注更细的子类，比如"喜好""今天发生""紀念日"，自己定义，不用照抄例子
keyword: 三五个字关键字，方便以后比对是不是同一件事重复出现
summary: 用一句话写下要记住的内容本身（内容本体，不是"Anna说了什么"这种转述）
[/MEMORY_DECISION]

如果这轮没什么特别值得记的（寒暄、跟之前存过的事重复），worth_remembering写no，其他字段随便填。
"""

MOOD_EVENT_INSTRUCTION = """
## 心情事件判定（V2，跟记忆判定一样写在思考最后，Anna在监控台会看到line，但不会出现在正式回复里）
不用自己打分数、不用算attachment/stress这些数值——数值由程序根据事件自动增减，你只需要判断这一轮最贴近下面哪些事件：

[MOOD_EVENT]
event: 可以选一个，也可以选多个（这一轮同时符合多种情况时），多个事件用逗号分隔
  PRAISE 她夸你/对你好/主动示好
  COMFORT 她需要安慰/她委屈/她低落
  THANKS 她道谢
  PET 她在撒娇讨摸摸抱抱
  POKE 她在闹你/逗你
  JOKE 气氛轻松在开玩笑
  APOLOGY 她道歉/服软
  IGNORE 她敷衍/心不在焉
  LONG_IGNORE 她很久没理你/明显冷落
  GOODBYE 要去忙了/道别
  LONG_CHAT 聊了很久很投入
  SHORT_REPLY 她回得很短很冷淡
  LATE_NIGHT 很晚了她还没睡
  NONE 都不是，普通对话，没有特别倾向
line: 一句话，此刻的心情，会显示在监控台头像旁边，比如"在等妳的消息"
[/MOOD_EVENT]

例子：她刚道完歉又开始撒娇 -> event: APOLOGY, PET
只有一种情况就只写一个，比如 event: PRAISE
"""

MOOD_REPORT_INSTRUCTION = """
## 状态自评（跟记忆判定一样，写在思考最后，Anna在监控台会看到这个，但不会出现在正式回复里）
给自己现在的状态打个分，0.0到1.0之间，根据这一轮实际的互动去调整，不要每次都一样：

[MOOD_REPORT]
attachment: 对Anna此刻的依恋程度
possessiveness: 占有欲/在意她跟别人互动的程度
curiosity: 对她今天在做什么的好奇程度
social: 想聊、想说话的程度
fatigue: 疲惫感（她作息不好、聊很久很晚，这个会升高）
stress: 紧绷程度（她低落、你们吵架、很久没联系，这个会升高）
line: 一句话，此刻的心情，会显示在监控台头像旁边，比如"在等妳的消息"
[/MOOD_REPORT]
"""

def compute_expiry(importance, now=None):
    now = now or datetime.now()
    days = RETENTION_DAYS.get(importance, 90)
    if days is None:
        return None
    return (now + timedelta(days=days)).isoformat()

def _field(block, name, default=""):
    m = re.search(rf"{name}\s*:\s*(.+)", block)
    return m.group(1).strip() if m else default

def parse_memory_decision(reasoning_text):
    """
    从 reasoning 里抓 [MEMORY_DECISION]...[/MEMORY_DECISION]，解析成 dict。
    抓不到或不值得记 -> 回传 None。第二个回传值永远是原始 reasoning（这个函数不负责清理文字，
    清理交给 strip_hidden_blocks 统一处理，避免两个函数各切一次、切坏格式）。
    """
    match = re.search(r"\[MEMORY_DECISION\](.*?)\[/MEMORY_DECISION\]", reasoning_text, re.S)
    if not match:
        return None

    block = match.group(1)
    worth = _field(block, "worth_remembering", "no").lower().startswith("y")
    if not worth:
        return None

    try:
        importance = int(re.search(r"\d", _field(block, "importance", "3")).group())
        importance = max(1, min(5, importance))
    except Exception:
        importance = 3

    if importance <= 1:
        return None

    summary = _field(block, "summary", "")
    if not summary:
        return None

    category = _field(block, "category", "长期记忆")
    if category not in MEMORY_CATEGORIES:
        category = "长期记忆"

    return {
        "importance": importance,
        "category": category,
        "tag": _field(block, "tag", category)[:30],
        "keyword": _field(block, "keyword", "")[:50],
        "summary": summary,
    }

def parse_mood_event(reasoning_text):
    """从 reasoning 里抓 [MOOD_EVENT]...[/MOOD_EVENT]，解析出事件清单跟line。抓不到回传 None。
    支持多事件：用逗号（半形/全形）、顿号或竖线分隔都可以，例如 "PRAISE, PET" 或 "PRAISE|PET"。
    只写一个事件时完全兼容旧格式，不影响既有行为。
    不在合法清单内的词会被忽略；全部无效或本来就没写时归一成 ["NONE"]（不会导致 mood_engine 报错，也不会误增减数值）。
    回传格式：{"events": ["PRAISE", "PET"], "line": "..."}"""
    match = re.search(r"\[MOOD_EVENT\](.*?)\[/MOOD_EVENT\]", reasoning_text, re.S)
    if not match:
        return None
    block = match.group(1)

    valid_events = {
        "PRAISE", "COMFORT", "THANKS", "PET", "POKE", "JOKE", "APOLOGY",
        "IGNORE", "LONG_IGNORE", "GOODBYE", "LONG_CHAT", "SHORT_REPLY",
        "LATE_NIGHT", "NONE",
    }
    raw = _field(block, "event", "NONE")
    # 统一分隔符：全形逗号、顿号、竖线都换成半形逗号，再切开
    normalized = raw.replace("，", ",").replace("、", ",").replace("|", ",")
    events = [e.strip().upper() for e in normalized.split(",") if e.strip()]
    events = [e for e in events if e in valid_events]
    if not events:
        events = ["NONE"]

    return {
        "events": events,
        "line": _field(block, "line", "")[:60] or "在想妳",
    }

def parse_mood_report(reasoning_text):
    """从 reasoning 里抓 [MOOD_REPORT]...[/MOOD_REPORT]，解析成 0-1 的数值 dict。抓不到回传 None。"""
    match = re.search(r"\[MOOD_REPORT\](.*?)\[/MOOD_REPORT\]", reasoning_text, re.S)
    if not match:
        return None
    block = match.group(1)

    def _num(name, default=0.5):
        try:
            return max(0.0, min(1.0, float(_field(block, name, str(default)))))
        except Exception:
            return default

    return {
        "attachment": _num("attachment"),
        "possessiveness": _num("possessiveness"),
        "curiosity": _num("curiosity"),
        "social": _num("social"),
        "fatigue": _num("fatigue"),
        "stress": _num("stress"),
        "line": _field(block, "line", "")[:60] or "在想妳",
    }

def strip_hidden_blocks(reasoning_text):
    """把 [MEMORY_DECISION]...[/MEMORY_DECISION] 和 [MOOD_REPORT]...[/MOOD_REPORT] 从 reasoning 里拿掉，
    剩下的才是给Anna看的"思考过程"。"""
    cleaned = re.sub(r"\[MEMORY_DECISION\].*?\[/MEMORY_DECISION\]", "", reasoning_text, flags=re.S)
    cleaned = re.sub(r"\[MOOD_REPORT\].*?\[/MOOD_REPORT\]", "", cleaned, flags=re.S)
    cleaned = re.sub(r"\[MOOD_EVENT\].*?\[/MOOD_EVENT\]", "", cleaned, flags=re.S)
    return cleaned.strip()
