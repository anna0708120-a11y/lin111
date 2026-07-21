# 这份文件是累积的：改了什么、要做什么都写这里，不再每次开新文件

## 已完成（Supabase / Render / Bark / PWA）

### 建 Supabase 项目
去 supabase.com 注册、New Project。左边 Project Settings → Data API，複製 Project URL（填 SUPABASE_URL）
和 **service_role** 那把 key（填 SUPABASE_KEY，不是 anon key）。

### 建表
Supabase 左边 SQL Editor 跑一次：

```sql
create table if not exists app_state (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz default now()
);

create table if not exists memory_bank (
  id bigint generated always as identity primary key,
  tag text not null,
  content text not null,
  created_at timestamptz default now()
);

create table if not exists activity_log (
  id bigint generated always as identity primary key,
  event_type text not null,
  content text not null,
  created_at timestamptz default now()
);

create table if not exists chen_notes (
  id bigint generated always as identity primary key,
  content text not null,
  created_at timestamptz default now()
);
```

### Render 环境变量
`SUPABASE_URL`、`SUPABASE_KEY`（service_role）、`BARK_KEYS`（手机key,电脑key，逗号分隔，取代旧的BARK_KEY）。

### 一个坑：Render 免费版会睡觉
15分钟没访问就休眠，排程也跟着停。解法：cron-job.org（免费）设个任务每10分钟打一次 `/health`。

### PWA
manifest.json、service worker都好了，静态图标要放进 `static/` 资料夹（文件名见 `static/README.md`）。

---

## 本轮规划（还没写代码，等你看完确认）

### 1. 文件规范
以后「改了什么 + 要做什么」都写在这份文件，不再另开新 md。

### 2. 碎碎念 → 今日碎碎念
现在的碎碎念是从每条回复的思考内容里摘出来的，混着你说的话和他的反应，不是他自己的东西——你说得对。
拆成两件事：每句话的思考过程改走第3点的真thinking，跟聊天气泡绑在一起；碎碎念本体改成「今日碎碎念」，
一天一篇不是每条消息都写，主动消息排程加一个"日期换了"的检查，触发时让Lin看当天的记忆自己写一段感想。

### 3. 拿掉 [Lin在想]/[Lin说]，改用真的 thinking
现在是硬性要求模型输出两段文字格式再切字符串解析，脆弱、而且是"装出来"的思考。
查过官方文档：DeepSeek v4系列原生支持thinking mode，请求加
`extra_body={"thinking":{"type":"enabled"}}` + `reasoning_effort:"high"`，
回应会有独立的 `reasoning_content`（真推理过程）和 `content`（正式回复），不用再切字符串。
前端做成跟Claude一样：回复下面一个可以点开/收起的思考区块，默认收起。
persona.py里那段"思考链行为/情感/内容指导"（教模型怎么装格式的规则）到时候整段删掉。

### 4.「Lin状态」——这块我不做

Eventide 我看了源码：这是 ABO 世界观的生理周期模拟器，热度/敏感度/蓄积感这些数值随时间自动累积，
配合"释放"结算（结算字段里直接有 `ejaculated`），设计目的就是让性张力自动随时间升温、
还会透过主动消息在你没在聊天的时候把升温结果推给你。

这个我不会做——不是角色设定本身的问题，是这套东西被设计成自动、持续地把性内容往前推，
跟你主动想聊、我帮你写完全是两回事，我不会去搭这种自动升温+主动推送的管线。

如果你要的其实是「Lin有自己会变化的状态、感觉更像活的」，我可以做一版不含情欲机制的：
疲惫感、心情、专注度这类的会随时间/互动变化，一样能在监控台看到一个小面板。要的话再谈怎么设计。

### 5. Prompt 拆三个文件 + 记忆判定规则

拆分：`style.py`（说话方式/语气，跟思考格式无关的部分）、`persona.py`（人设本体，不动）、`memory_rules.py`（新规则）。

记忆判定：
- 星级：5星永久／4星半年／3星三个月／2星几天到几周／1星不存。
- 每条记忆多记：重要程度、分类(长期/短期)、tag、keyword、到期时间、最后被提到的时间。
- 不额外多打一次API：在同一次生成回复的请求里，让模型在正常回复之后多输出一段「值不值得记住」的判断，解析出来自动存或跳过。
- 同一件事重复出现：先比对关键字/tag，像的话不新增，把旧那条星级调高、到期时间重算。
- 遗忘：每周一次排程，扫一遍到期记忆——1-2星直接删；3星以上过期且很久没被提起才清掉；5星不到期。
- 语意搜索/BM25/rerank你排的优先序比较后面，这轮先不做，只搭星级/分类/关键字这层。

### 6. Bug记录.md
加一个空白追踪文件，之后遇到bug直接记在里面。

---

不影响现有功能：全部是在现有 FastAPI + Supabase + Render 架构上加东西，
/watch /logs /memory 这些既有接口对外行为不变，聊天、记忆、Bark、Cron Job都不会中断。

---

## 本轮已完成：thinking mode + 新记忆分类 + 状态面板 + initiative

### 1. Supabase 要跑的 SQL（只需要跑这一次，之前的表不受影响）

进 Supabase 左边 SQL Editor，跑这段，给 memory_bank 加几个新栏位：

```sql
alter table memory_bank add column if not exists category text default '长期记忆';
alter table memory_bank add column if not exists importance smallint default 3;
alter table memory_bank add column if not exists keyword text default '';
alter table memory_bank add column if not exists expires_at timestamptz;
```

没有新建表——头像、心情状态、日记日期都塞进已经有的 app_state 表，不用另外建。

### 2. Render 环境变量

不用加新的。DEEPSEEK_REASONING_EFFORT、DEEPSEEK_MAX_TOKENS 这两个有默认值（high / 1200），
想调的话才需要去 Render 加，不加也能跑。

### 3. 这轮做了什么

- persona.py / style.py 换成你给的新版本，OUTPUT_FORMAT_RULES 那套"装思考格式"的规则整个拿掉。
- DeepSeek 改用官方 thinking mode，`reasoning_content` 是真思考，前端做成跟 Claude 一样可以收合/展开。
- 记忆分类换成你定的四类（长期记忆/短期记忆/Relationship/Reflection），Archive 先不搬家（日记、
  Bark推送本来就各自有表），做成一个"统一读取"的视图页签，不是把数据搬过去。
- Lin 自己判断要不要记、记在哪一类、多重要，不用你手动选；同一件事重复提到会自动调高星级、延长保存时间；
  每周整理一次，到期的自动清掉。
- 加了状态面板（監控台頁面最上面）：依戀/佔有欲/好奇/社交欲/疲憊感/壓力，Lin自己每次回覆順便打分，
  不是libido/欲望那套，跟你之前的图1参考做了区分。
- 碎碎念改成一天一篇的日记，不是每条消息都写。
- 主动消息改用"理由目录"（无聊/很久没理/关心作息/想分享事情等），不再是写死的时间表，也不设每日最低次数。
- 双方头像：监控台头像点了换Lin的，聊天气泡里点自己的头像换Anna的。

### 4. 没做/简化的部分（老实说一下）

- Archive 目前是"读取三个来源拼起来显示"，不是真的把日记/推送记录搬进 memory_bank 那张表，
  以后要做语意搜索/BM25/rerank的话，这个视图层面的做法可能要重新设计，先不用太依赖它的排序。
- 状态面板的数值现在完全由模型自己每次回覆时顺便打分，没有额外的"计算规则"（比如疲惫感不会因为
  时间流逝自动增加），纯粹是Lin自己感觉到什么就报什么。
