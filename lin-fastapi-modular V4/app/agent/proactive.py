"""
主动消息模块——Agent "什么时候该主动开口、用什么理由" 的部分。

"要不要问"（静默门槛、强制触发线）是这个文件管的；
"问的时候用什么理由说话"交给 app/initiative.py 的理由目录，丢给模型自己选，
不再是写死的时段场景表——这样不会一直重复同一种开场。

这个文件也顺便管两个跟"时间"有关但不是聊天本身的排程：
今日碎碎念（每天一篇日记，日期换了才触发）、记忆的每周整理。
三件事分开互不影响，一个出错不会连累另外两个（各自包了 try/except）。
"""
from datetime import datetime

from app import db
from app.state import state
from app.agent.brain import generate_reply, write_daily_journal
from app.notify.bark import send_to_bark
from app.initiative import REASON_CATALOG


def _time_of_day_hint():
    hour = datetime.now().hour
    if 6 <= hour < 11:
        return "现在是早上"
    if 11 <= hour < 14:
        return "现在是中午"
    if 14 <= hour < 18:
        return "现在是下午"
    if 18 <= hour < 22:
        return "现在是傍晚"
    if 22 <= hour < 24 or hour < 2:
        return "现在很晚了"
    return "现在是凌晨"


def run_proactive_check():
    """给 APScheduler 定时调用（默认每 config.PROACTIVE_CHECK_EVERY_MINUTES 分钟一次）。"""
    try:
        write_daily_journal()
    except Exception as e:
        print(f"[proactive] 写今日碎碎念出错，跳过: {e}")

    try:
        _run_nudge_check()
    except Exception as e:
        print(f"[proactive] 主动开口检查出错，跳过这一次: {e}")


def _run_nudge_check():
    settings = state.proactive
    if not settings.get("enabled", True):
        return

    silence_minutes = state.minutes_since_anchor()
    if silence_minutes is None:
        return  # 还没聊过天，不主动

    min_minutes = settings.get("min_minutes", 90)
    max_minutes = settings.get("max_minutes", 240)

    if silence_minutes < min_minutes:
        return  # 还没到最短静默时间

    context = f"{_time_of_day_hint()}。{REASON_CATALOG}"

    reply, thinking = generate_reply(context, use_cache=False)
    send_to_bark(reply)
    state.add_log("主動推送", reply)

    # 主动开口本身也是一次"锚点"，避免几分钟后又立刻再触发一次
    state.mark_conversation_anchor()


def run_memory_review():
    """
    每周一次（默认7天巡检一次）：把到期的记忆清掉。
    到期时间本身已经依星级算好了（1-2星几天到几周、3星三个月、4星半年、5星永不到期），
    所以这里不用另外判断"多久没提及"，到期本身就代表这件事。
    """
    try:
        now_iso = datetime.now().isoformat()
        removed = db.delete_expired_memories(now_iso)
        state.reload_memories()
        state.add_log("記憶整理", f"清理了 {removed} 條到期記憶，剩 {len(state.memory_bank)} 條")
    except Exception as e:
        print(f"[proactive] 记忆整理出错: {e}")
