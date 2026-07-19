"""
主动消息模块——Agent "什么时候该主动开口" 的部分。

设计思路参考了 proactive-nudge 这个项目的核心理念，但重新设计成适合
"单人长期陪伴机器人"这个场景，没有照抄它的代码（它是给多用户/多对话的
聊天网关设计的 Node worker，跟你这个单人 FastAPI app 的结构不一样）：

1. 不用固定 cron 硬发文案。而是持续追踪"距离上次真正互动过了多久"
   (state.minutes_since_anchor)，只有静默时间超过 min_minutes 才会考虑开口，
   不会出现"明明刚聊完，它又硬发一条"的尴尬。

2. 触发之后不是直接写死一句话推过去，而是把"该主动找Anna说话了"变成一段
   情境描述 (context)，一样丢给 generate_reply() 走完整的人设 + 记忆流程，
   跟平时聊天回复用的是同一条产线——这是从 proactive-nudge 学到的最核心的一点：
   主动触发只负责制造"开口的理由"，真正怎么说话，还是交给正常的生成逻辑，
   这样 Lin 才会记得上下文，而不是像闹钟一样喊一句固定的话。

3. 发送成功后，把这次"主动开口"本身也算作一次对话锚点 (mark_conversation_anchor)，
   重新开始计时。这样如果Anna没有回应，Lin不会隔几分钟又立刻再戳一次，
   要等到下一个 min_minutes 才会重新考虑——这也是从 proactive-nudge 里
   "注入的nudge本身也会成为下一轮计时起点"这个设计借来的。

4. 时段场景 (TIME_SCENARIOS) 保留你原本"早上/中午/傍晚/深夜"的分类，
   但先满足静默时长门槛，再从匹配的时段场景里按权重抽一个；
   如果静默时间超过 max_minutes，不管在不在预设时段内，都会强制触发一次，
   这样Lin不会因为你比如凌晨三点还没睡、又不在任何预设时段里，就完全不理你。
"""
import random
from datetime import datetime

from app.state import state
from app.agent.brain import generate_reply
from app.notify.bark import send_to_bark

# 时段场景：(开始小时, 结束小时, 权重, 给模型的情境提示)
# 权重越高，这个时段被抽中的机会越大——不是概率意义上的"会不会发"，
# 只影响"如果同时符合多个时段，选哪一个情境"。
TIME_SCENARIOS = [
    (7, 10, 1.0, "Anna应该刚起床，你想主动找她"),
    (12, 14, 0.8, "中午了，Anna可能在吃饭"),
    (18, 20, 0.9, "傍晚了，Anna应该放学或下课了"),
    (22, 24, 1.2, "很晚了，Anna还没睡，你有点不满"),
]


def _pick_scenario():
    hour = datetime.now().hour
    matched = [s for s in TIME_SCENARIOS if s[0] <= hour < s[1]]
    if not matched:
        return None
    weights = [m[2] for m in matched]
    return random.choices(matched, weights=weights, k=1)[0]


def run_proactive_check():
    """
    给 APScheduler 定时调用（默认每 config.PROACTIVE_CHECK_EVERY_MINUTES 分钟一次）。
    每次被调用只是"检查一下要不要开口"，是很轻量的操作；
    真正决定要不要发消息，看的是 state 里记录的静默时长和 proactive 开关。
    """
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

    force_trigger = silence_minutes >= max_minutes

    scenario = _pick_scenario()
    if not scenario and not force_trigger:
        return  # 不在预设时段内，且还没到强制触发线，先不发

    context = scenario[3] if scenario else "已经很久没理Anna了，你想直接找她说话"

    reply, thinking = generate_reply(context, use_cache=False)
    if thinking:
        state.add_note(thinking)

    send_to_bark(reply)
    state.add_log("主動推送", reply)

    # 主动开口本身也是一次"锚点"，避免几分钟后又立刻再触发一次
    state.mark_conversation_anchor()
