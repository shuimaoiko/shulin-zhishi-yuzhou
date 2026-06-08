# -*- coding: utf-8 -*-
"""
解析「树成林」全部内容 -> 结构化数据 + 分组，供「树林知识宇宙」可视化使用。

两层结构：
  系统(system)  ── 知乎 / 公众号 / B站动态 / B站视频
    └ 分组(group) ── 知乎=13 内容维度；公众号=两个号(对木同学 / 树成林Light)；B站动态=动态类型；B站视频=9 主题
        └ 内容(item)

数据源：
  知乎  回答/文章  <- 知乎/树成林-知乎数据.md
  知乎  想法        <- 知乎/树成林-想法合集.md（带链接+评论数）
  公众号 两个号     <- 公众号/对木同学/*.md  公众号/树成林Light/*.md（每篇一文件）
  B站   动态        <- b站动态/树林同学_B站动态_完整版(1).md
  B站   视频文案    <- b站视频/树林同学_B站视频文案.md（标题+简介为文案，58 个投稿）

输出：
  - 数据/data.json + 数据/data.js  （供 index.html）
  - 数据/分类文档/知乎/*.md  数据/分类文档/公众号/*.md  数据/分类文档/B站动态/*.md （保底文档）
  - _build/stats.txt
"""
import re, json, os, collections, shutil

ROOT      = "/Users/水猫/文档/树林/树林知识宇宙"
ZHIHU_SRC = "/Users/水猫/文档/树林/知乎/树成林-知乎数据.md"
THINK_SRC = "/Users/水猫/文档/树林/知乎/树成林-想法合集.md"
MP_ROOT   = "/Users/水猫/文档/树林/公众号"
BILI_SRC  = "/Users/水猫/文档/树林/b站动态/树林同学_B站动态_完整版(1).md"
BILI_VIDEO_SRC = "/Users/水猫/文档/树林/b站视频/树林同学_B站视频文案.md"
MOMENTS_SRC = "/Users/水猫/文档/树林/树林朋友圈/timeline.json"

# 公众号账号：(id, 名称, emoji, 颜色, 文件夹)
MP_ACCOUNTS = [
    ("duimu", "对木同学",     "✍️", "#F4A261", os.path.join(MP_ROOT, "对木同学")),
    ("light", "树成林Light",  "🌳", "#2A9D8F", os.path.join(MP_ROOT, "树成林Light")),
]

# 公众号内容类型：短标签，前端用于「按类型 / 类型+时间」查看
MP_TYPES = [
    ("course", "课程", "📣", "#E9C46A", ["报名","课程","直播","训练营","成长营","践行群","规划课","特训营","系统课","答疑","招生","开营","优惠","营","课"]),
    ("subject","学科", "📚", "#2E86AB", ["英语","数学","语文","物理","化学","生物","历史","文综","理综","作文","阅读理解","阅读","完形","错题","刷题","教材","知识体系","题型","拆题","审题","推理","论证","全科"]),
    ("exam",   "高考", "🎯", "#4361EE", ["高考","高三","高二","高一","准高三","一模","二模","三模","倒计时","百天","100天","一百天","复读","志愿","出分","冲刺","考前","月考"]),
    ("eff",    "效率", "⏱️", "#06A77D", ["效率","高效","低效","自律","早起","睡眠","起床","作息","时间","计划","习惯","注意力","专注","摆烂","状态","拖延","复盘","打卡"]),
    ("mind2",  "心态", "🧠", "#F77F00", ["焦虑","内耗","情绪","压力","崩溃","难受","发疯","摆烂","自卑","痛苦","开心","抱怨","厌恶","低落","燃点","相信","勇气","心态"]),
    ("growth", "成长", "🌱", "#588157", ["人生","成长","认知","选择","自由","价值","清醒","成熟","世界","生活","努力","相信改变","优越","幸运","孤独","普通","热爱","自我","密度"]),
    ("univ2",  "大学", "🎓", "#7209B7", ["大学","准大学生","考研","职场","大厂","面试","职业","毕业","专业","工作","求职","规划","预备营","浪前"]),
    ("love2",  "情感", "❤️", "#E63946", ["恋爱","爱情","脱单","婚姻","喜欢","亲密关系","朋友","父母","家族","社交","人际","女孩子","男生","女生"]),
    ("create", "创作", "💡", "#FFB703", ["IP","ip","公众号","写作","创作者","自媒体","流量","粉丝","视频","商业","赚钱","收入","项目","产品","变现","AI","Ai","ai"]),
    ("daily",  "日常", "🪐", "#8D99AE", ["分享图片","家族群","歌单","见面会","杭州","每天一遍","好久不见","随便","照片","图片"]),
]
MP_TYPE_ORDER = [t[0] for t in MP_TYPES]
MP_TYPE_META = {t[0]: {"id": t[0], "name": t[1], "emoji": t[2], "color": t[3]} for t in MP_TYPES}

BILI_GROUPS = [
    ("bili_text",    "纯文字", "💬", "#79B8FF", "纯文字动态"),
    ("bili_image",   "图片",   "🖼️", "#B9855B", "图片动态"),
    ("bili_video",   "视频",   "🎬", "#E9C46A", "视频动态"),
    ("bili_repost",  "转发",   "🔁", "#9DA6C8", "转发动态"),
    ("bili_article", "文章",   "📰", "#67B8A7", "文章动态"),
]
BILI_SECTION_TO_GROUP = {section: gid for gid, _name, _emoji, _color, section in BILI_GROUPS}
BILI_GROUP_META = {gid: {"id": gid, "name": name, "emoji": emoji, "color": color}
                   for gid, name, emoji, color, _section in BILI_GROUPS}

# B站视频 主题分组（归纳分类，关键词命中；顺序即优先级，人生·认知兜底）
BV_CATS = [
    ("bv_study",  "学科·工具",   "📚", "#06A77D", ["数学","英语","物理","化学","deepseek","ai","做题家","出题家","合法作弊","内卷方案","刷题","错题","题"]),
    ("bv_method", "提分·方法",   "🚀", "#EF476F", ["提分","提高","逆袭","复习","六轮","三轮","计划","自学","效率","学习机器","记忆","方法","指南","压榨","榨干","极限","450","650","684","学渣","卷王","自律","规划","顶300天","时间账","睡四个小时","睡4"]),
    ("bv_exam",   "高考·冲刺",   "🎯", "#4361EE", ["高考","高三","高二","高一","一百天","100天","百天","冲刺","考试","考前","十考九崩","网课","出分","赢最后","幻想","最后一百天"]),
    ("bv_repeat", "复读·决策",   "🔁", "#9D4EDD", ["复读","复了","高四"]),
    ("bv_univ",   "大学·未来",   "🎓", "#7209B7", ["大学","面试","躺赢","躺","脱层皮","大学四年","删减内容","专业","职场"]),
    ("bv_love",   "情感·人际",   "❤️", "#E63946", ["恋爱","爱情","爱在","日落黄昏","适合恋爱","空心人","洁癖式孤独","人际关系","孤独"]),
    ("bv_mind",   "心态·情绪",   "🧠", "#F77F00", ["焦虑","情绪","emo","自卑","黑洞","陷阱","压力","发病","难受","力气","卷了","清醒一点","正常了","原动力","破防","内耗"]),
    ("bv_daily",  "日常·随笔",   "🪐", "#8D99AE", ["包场","海底捞","哪吒","雪国列车","见面会","初一","可爱","杭州","everything","alright","老王","见面","歌单"]),
    ("bv_life",   "人生·认知",   "🌱", "#588157", ["人生","独立","人格","精神独立","自由","普通人","被成为","现实","认知","成长","圈","百年","尽兴","道理","清醒","站起来","竹杖芒鞋","一蓑烟雨","被忘掉"]),
]
BV_ORDER = [c[0] for c in BV_CATS]
BV_META = {c[0]: {"id": c[0], "name": c[1], "emoji": c[2], "color": c[3]} for c in BV_CATS}

# ---- 朋友圈 主题分组（归纳分类，关键词命中；顺序即优先级，生活·日常兜底）----
PYQ_CATS = [
    ("pyq_study",  "学习·高考", "🎯", "#4361EE", ["高考","高三","高二","高一","复读","学习","复习","考试","提分","刷题","做题","数学","英语","物理","化学","生物","作文","背书","知识","上岸","录取","分数","学渣","学霸","学生","上课","期末","考研","成绩","老师","教育","出题","课程","训练营","成长营"]),
    ("pyq_create", "创作·表达", "💡", "#FFB703", ["公众号","写作","文字","表达","创作","视频号","直播","见面会","粉丝","读者","作品","更新","文章","内容","出书","采访","合作","树成林","对木","老王","项目","商业","赚钱","流量","ip","品牌","媒体","写下","录","发朋友圈","安利"]),
    ("pyq_love",   "情感·关系", "❤️", "#E63946", ["爸","妈","父母","家人","阿嬷","恋","喜欢一个人","想念","姜禹","哥哥","姐姐","在一起","想你","拥抱","陪我","陪伴","朋友","闺蜜","亲爱","暗恋","分手","告白","女孩","男孩","爱人","结婚","婚礼","小孩","孩子","宝贝","爱你","爱我"]),
    ("pyq_music",  "音乐·歌单", "🎵", "#9D4EDD", ["好听","歌","音乐","声音","旋律","循环","单曲","翻译","drunk","唱","这首","专辑","耳机","bgm","纯音乐","刘聪","旋","听这"]),
    ("pyq_mind",   "心态·情绪", "🧠", "#F77F00", ["难受","焦虑","emo","难过","情绪","崩溃","压力","治愈","哭","丧","累","平静","勇气","害怕","紧张","委屈","破防","内耗","心态","释怀","痛苦","开心","快乐","幸福","温暖","温柔","感动","舒服","释然","坦然","心安","治好"]),
    ("pyq_life",   "人生·认知", "🌱", "#588157", ["人生","世界","成长","认知","选择","自由","众生","意义","相信","改变","清醒","成熟","价值","道理","命运","坚持","努力","勇敢","格局","热爱","活着","成为","时间","年轻","配得","值得","珍惜","长大","记得","明白","懂得","人间","信念","信仰","活成"]),
    ("pyq_daily",  "生活·日常", "🪐", "#8D99AE", []),  # 兜底：吃喝玩乐 / 生活切片
]
PYQ_ORDER = [c[0] for c in PYQ_CATS]

# 朋友圈 内容形态（辅轴：按微信 content_type 客观归类）
PYQ_FORMS = [
    ("text",  "纯文本",   "📝", "#79B8FF"),
    ("photo", "图文",     "🖼️", "#67B8A7"),
    ("video", "视频",     "🎬", "#E9C46A"),
    ("music", "音乐分享", "🎵", "#9D4EDD"),
    ("link",  "链接分享", "🔗", "#9DA6C8"),
    ("live",  "直播",     "📍", "#EF476F"),
    ("note",  "笔记·其他","📒", "#B9855B"),
]
PYQ_FORM_META = {f[0]: {"id": f[0], "name": f[1], "emoji": f[2], "color": f[3]} for f in PYQ_FORMS}
# 微信 content_type -> 形态
CT_TO_FORM = {
    2: "text", 1: "photo", 15: "video", 28: "video",
    42: "music", 5: "link", 3: "link", 54: "live",
    34: "note", 4: "note", 7: "note",
}

items = []
audit_stats = collections.Counter()

# ================================================================ 知乎
with open(ZHIHU_SRC, encoding="utf-8") as f:
    lines = f.readlines()
n = len(lines)

# --- 回答：来自「全部回答」汇总表 ---
row_re = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*👍\s*([\d,]+)\s*\|\s*⭐\s*([\d,]+)\s*\|\s*(.*?)\s*\|\s*$"
)
for ln in lines:
    m = row_re.match(ln.strip())
    if m:
        items.append({
            "type": "回答", "idx": int(m.group(1)),
            "title": m.group(2).strip(), "url": m.group(3).strip(),
            "likes": int(m.group(4).replace(",", "")),
            "collects": int(m.group(5).replace(",", "")),
            "excerpt": m.group(6).strip().rstrip("."),
        })

# --- 文章：## N. [title](url) · 👍X  + 正文直到下一个 ## / # ---
art_hdr = re.compile(r"^##\s+(\d+)\.\s+\[([^\]]+)\]\(([^)]+)\)\s*·\s*👍\s*([\d,]+)")
for i, ln in enumerate(lines):
    m = art_hdr.match(ln)
    if not m:
        continue
    body = []
    for j in range(i + 1, n):
        if re.match(r"^#{1,2}\s", lines[j]):
            break
        body.append(lines[j])
    btxt = re.sub(r"\s+", " ", "".join(body)).strip()
    items.append({
        "type": "文章", "idx": int(m.group(1)),
        "title": m.group(2).strip(), "url": m.group(3).strip(),
        "likes": int(m.group(4).replace(",", "")), "collects": 0,
        "excerpt": btxt[:160], "body": btxt[:1200],
    })

# --- 想法：### N. [🔗 查看原文](URL) · 👍X · 💬Y  正文直到 --- 或下一个 ### ---
with open(THINK_SRC, encoding="utf-8") as f:
    tlines = f.readlines()
tn = len(tlines)
think_hdr = re.compile(
    r"^###\s+(\d+)\.\s+\[🔗[^\]]*\]\((https?://[^)]+)\)\s*·\s*👍\s*([\d,]+)(?:\s*·\s*💬\s*([\d,]+))?"
)
for i in range(tn):
    m = think_hdr.match(tlines[i])
    if not m:
        continue
    body = []
    for j in range(i + 1, tn):
        if tlines[j].strip() == "---" or re.match(r"^###\s", tlines[j]):
            break
        body.append(tlines[j])
    clean = re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", "".join(body))).strip()
    if not clean:
        continue
    title = re.split(r"[。！？\n]", clean)[0][:30]
    items.append({
        "type": "想法", "idx": int(m.group(1)),
        "title": title or f"想法 #{m.group(1)}", "url": m.group(2).strip(),
        "likes": int(m.group(3).replace(",", "")), "collects": 0,
        "comments": int(m.group(4).replace(",", "")) if m.group(4) else 0,
        "excerpt": clean[:160], "body": clean[:1200],
    })

# 标记来源系统
for it in items:
    it["sys"] = "zhihu"

# ---- 知乎内容维度（关键词自动归类）：顺序即优先级（学科最先，人生兜底）----
CATS = [
    ("chem",   "化学",        "🧪", "#2E86AB", ["化学","氧化还原","氧还","原电池","电解池","化学平衡","勒夏特列","方程式","离子反应","元素周期"]),
    ("math",   "数学",        "📐", "#A23B72", ["数学","130","函数","导数","圆锥曲线","解析几何"]),
    ("phys",   "物理",        "⚛️", "#F18F01", ["物理","力学","受力","电磁","模型分解"]),
    ("bio",    "生物",        "🧬", "#3B8C4E", ["生物"]),
    ("sci",    "理综·综合",   "🔬", "#6A994E", ["理综","理科综合","三科","副科"]),
    ("love",   "情感·人际",   "❤️", "#E63946", ["恋爱","爱情","谈恋爱","暗恋","亲密关系","男朋友","女朋友","单身","男孩子","男生","女生","喜欢一个人","分手","告白"]),
    ("repeat", "复读·决策",   "🔁", "#9D4EDD", ["复读","高四","复不复读","要不要复读"]),
    ("univ",   "大学·未来",   "🎓", "#4361EE", ["大学","大一","准大学生","大学生","毕业","专业","考研","期末","上岸","职场","资本家"]),
    ("comeback","逆袭·提分",  "🚀", "#EF476F", ["逆袭","大幅度","提高成绩","提分","快速提高","质变","90+","130+","提了","涨分","黑马","从400","从500","逼到"]),
    ("method", "学习方法·策略","📚","#06A77D", ["刷题","效率","高效","计划","一轮复习","复习","学习习惯","自学","笔记","错题","学习方法","背书","记忆","时间管理","作息","睡眠","睡4","睡几个","技巧","提高学习效率","制定"]),
    ("mind",   "心态·情绪",   "🧠", "#F77F00", ["心态","焦虑","情绪","压力","敏感","发挥失常","紧张","自卑","低落","抑郁","信心","压抑","熬过","骂醒","下定决心","不想学","原动力","动力","坚持不下去","破防","内耗","emo","勇气","平静"]),
    ("plan",   "高三·规划冲刺","📅","#118AB2", ["高三","高二","高一","倒计时","最后","100天","60天","40天","二百多天","高考前","冲刺","一轮","新高三","入高三","高中三年","给高中生","暑假","寒假","临考","出分","志愿"]),
    ("ip",     "内容·IP创业", "💡", "#FFB703", ["公众号","直播","ip","收割","挣钱","做课","粉丝","流量","财报","商业","视频号","树成林","万木行","地瓜","老王","备课","创业","变现","赚钱"]),
    ("life",   "人生·认知成长","🌱","#588157", ["人生","经验","道理","认知","成长","越早知道","明白的事","格局","选择","自由","价值","世界","勇敢","成熟","清醒"]),
]
CAT_ORDER = [c[0] for c in CATS]

def classify(it):
    hay = (it["title"] + " " + it.get("excerpt","") + " " + it.get("body","")).lower()
    tags = [cid for cid, name, emoji, color, kws in CATS if any(k.lower() in hay for k in kws)]
    if not tags:
        tags = ["life"]
    primary = sorted(tags, key=lambda t: CAT_ORDER.index(t))[0]
    return primary, tags

for it in items:                      # 此时 items 全是知乎
    p, tags = classify(it)
    it["group"], it["tags"] = p, tags

print("知乎：", collections.Counter(it["type"] for it in items if it["sys"] == "zhihu"))

# ================================================================ 公众号
title_re = re.compile(r"^#\s+\[([^\]]+)\]\(([^)]+)\)")
date_re  = re.compile(r"\*(\d{4}-\d{2}-\d{2})(?:[\sT][\d:]+)?\*")

def parse_mp_file(path, fn):
    with open(path, encoding="utf-8") as f:
        flines = f.readlines()
    title, url = None, ""
    for ln in flines[:4]:
        m = title_re.match(ln.strip())
        if m:
            title, url = m.group(1).strip(), m.group(2).strip()
            break
    if not title:                     # 兜底：用文件名（去日期前缀、还原换行标记）
        title = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", fn[:-3]).replace("n", " ").strip()
    dm = date_re.search("".join(flines[:6]))
    if dm:
        date = dm.group(1)
    else:
        fm = re.match(r"(\d{4}-\d{2}-\d{2})_", fn)
        date = fm.group(1) if fm else ""
    body = []
    for ln in flines:
        s = ln.strip()
        if not s: continue
        if title_re.match(s):            continue   # 标题行
        if "javascript:void" in s:       continue   # 作者/账号/日期 元信息行
        if s.startswith("!["):           continue   # 图片
        if s in ("* * *", "---", "***"): continue   # 分隔线
        if s.startswith("[阅读原文]"):    continue   # 阅读原文链接
        body.append(s)
    text = re.sub(r"[*#>`>]", "", " ".join(body))
    text = re.sub(r"\s+", " ", text).strip()
    return {"title": title, "url": url, "date": date,
            "excerpt": text[:160], "body": text[:800]}

def classify_mp(d):
    title = d.get("title", "").lower()
    excerpt = d.get("excerpt", "").lower()
    body = d.get("body", "").lower()
    scores = collections.Counter()
    for tid, _name, _emoji, _color, kws in MP_TYPES:
        for kw in kws:
            k = kw.lower()
            if k in title:
                scores[tid] += 4
            if k in excerpt:
                scores[tid] += 2
            if k in body:
                scores[tid] += 1
    if not scores:
        return "daily"
    return sorted(scores, key=lambda tid: (-scores[tid], MP_TYPE_ORDER.index(tid)))[0]

for aid, aname, emoji, color, folder in MP_ACCOUNTS:
    if not os.path.isdir(folder):
        print("⚠️ 缺少公众号文件夹：", folder); continue
    cnt = 0
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".md"):
            continue
        d = parse_mp_file(os.path.join(folder, fn), fn)
        mp_type = classify_mp(d)
        items.append({
            "type": "公众号", "sys": "mp", "group": aid, "account": aname,
            "title": d["title"], "url": d["url"], "date": d["date"],
            "likes": 0, "collects": 0,
            "excerpt": d["excerpt"], "body": d["body"], "tags": [aid, mp_type],
            "mp_type": mp_type, "mp_type_name": MP_TYPE_META[mp_type]["name"],
        })
        cnt += 1
    print(f"公众号 · {aname}：{cnt} 篇")

# ================================================================ B站动态
def clean_bili_text(raw):
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            lines.append("")
            continue
        s = re.sub(r"^>\s?", "", s).strip()
        if not s or s.startswith("!["):
            continue
        if s.lower() in ("none", "null", "nan"):
            continue
        if re.match(r"^🖼️\s*图片\d*[:：]\s*!\[[^\]]*\]\([^)]+\)\s*$", s):
            continue
        if re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", s):
            continue
        if re.match(r"^❤️\s*\*\*", s):
            continue
        s = re.sub(r"\*\*", "", s)
        lines.append(s)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def data_audit_agent_accept_bili(clean_text, group):
    """最底层数据审核：只清掉确定无信息量的 B站动态，不做主观提炼。"""
    normalized = re.sub(r"\s+", "", clean_text or "").lower()
    if not normalized:
        return False, "empty_after_media_strip"
    if normalized in ("none", "null", "nan"):
        return False, "none_body"
    if group == "bili_image" and not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", clean_text):
        return False, "pure_image"
    return True, ""

def bili_title_from_body(text, idx):
    one_line = re.sub(r"\s+", " ", text).strip()
    one_line = re.sub(r"^#\d+\s*", "", one_line)
    first = re.split(r"[。！？!?]", one_line)[0].strip()
    if not first:
        return f"B站动态 #{idx}"
    return first[:42]

if os.path.isfile(BILI_SRC):
    with open(BILI_SRC, encoding="utf-8") as f:
        blines = f.readlines()
    current_group = None
    section_re = re.compile(r"^##\s+.*?(纯文字动态|图片动态|视频动态|转发动态|文章动态)")
    bili_hdr = re.compile(r"^###\s+(\d+)\.\s+\[(.+)\]\((https?://[^)]+)\)")
    stats_re = re.compile(r"❤️\s*\*\*([\d,]+)\*\*.*?💬\s*\*\*([\d,]+)\*\*.*?🔄\s*\*\*([\d,]+)\*\*")
    i = 0
    while i < len(blines):
        sm = section_re.match(blines[i].strip())
        if sm:
            current_group = BILI_SECTION_TO_GROUP.get(sm.group(1))
            i += 1
            continue
        m = bili_hdr.match(blines[i].strip())
        if not m or not current_group:
            i += 1
            continue
        idx = int(m.group(1))
        header_title = m.group(2).strip()
        url = m.group(3).strip()
        likes = comments = reposts = 0
        body = []
        j = i + 1
        while j < len(blines):
            s = blines[j].strip()
            if re.match(r"^###\s+\d+\.", s) or section_re.match(s):
                break
            if s == "---":
                j += 1
                break
            st = stats_re.search(s)
            if st:
                likes = int(st.group(1).replace(",", ""))
                comments = int(st.group(2).replace(",", ""))
                reposts = int(st.group(3).replace(",", ""))
            else:
                body.append(blines[j])
            j += 1
        clean = clean_bili_text("".join(body))
        ok, reject_reason = data_audit_agent_accept_bili(clean, current_group)
        if not ok:
            audit_stats[f"bili_removed_{reject_reason}"] += 1
        if ok:
            gm = BILI_GROUP_META[current_group]
            title = bili_title_from_body(clean, idx)
            if not header_title.startswith("🔗") and not header_title.startswith("查看"):
                title = header_title[:42]
            body_text = clean
            if current_group == "bili_video" and title and title not in clean:
                body_text = f"{title}\n\n{clean}"
            items.append({
                "type": "B站动态", "sys": "bili", "group": current_group,
                "platform": "B站", "bili_type": current_group, "bili_type_name": gm["name"],
                "idx": idx, "title": title, "url": url,
                "likes": likes, "collects": 0, "comments": comments, "reposts": reposts,
                "excerpt": re.sub(r"\s+", " ", body_text)[:160], "body": body_text[:1200],
                "tags": [current_group],
            })
        i = max(j, i + 1)
    print("B站动态：", collections.Counter(it["group"] for it in items if it["sys"] == "bili"))
else:
    print("⚠️ 缺少 B站动态文件：", BILI_SRC)

# ================================================================ B站视频（文案）
def classify_bv(title, body):
    hay = (title + " " + (body or "")).lower()
    for cid, name, emoji, color, kws in BV_CATS:
        if any(k.lower() in hay for k in kws):
            return cid
    return "bv_life"

if os.path.isfile(BILI_VIDEO_SRC):
    with open(BILI_VIDEO_SRC, encoding="utf-8") as f:
        vtext = f.read()
    blocks = re.split(r"\n(?=##\s+\d+\.)", vtext)
    bv_cnt = 0
    for blk in blocks:
        hm = re.match(r"##\s+(\d+)\.\s+(.+)", blk)
        if not hm:
            continue
        idx = int(hm.group(1))
        title = hm.group(2).strip()
        um = re.search(r"🔗\s*\*\*链接:\*\*\s*(\S+)", blk)
        bm = re.search(r"`(BV\w+)`", blk)
        pm = re.search(r"🕐\s*\*\*发布时间:\*\*\s*([0-9:\s\-]+)", blk)
        dm = re.search(r"📋\s*\*\*简介:\*\*\s*(.+)", blk)
        url  = um.group(1).strip() if um else ""
        bvid = bm.group(1) if bm else ""
        date = pm.group(1).strip() if pm else ""
        desc = dm.group(1).strip() if dm else ""
        like = comment = repost = 0
        sm = re.search(r"📊\s*\*\*数据:\*\*\s*(.+)", blk)
        if sm:
            sline = sm.group(1)
            lm = re.search(r"❤️\s*([\d,]+)", sline)
            cm = re.search(r"💬\s*([\d,]+)", sline)
            rm = re.search(r"🔄\s*([\d,]+)", sline)
            if lm: like = int(lm.group(1).replace(",", ""))
            if cm: comment = int(cm.group(1).replace(",", ""))
            if rm: repost = int(rm.group(1).replace(",", ""))
        copy_lines = []
        after = blk.split("**📝 文案：**", 1)
        if len(after) == 2:
            for ln in after[1].splitlines():
                s = ln.strip()
                if s == "---":
                    break
                if s.startswith(">"):
                    s = s[1:].strip()
                    if not s or s.startswith("（视频无额外简介"):
                        continue
                    copy_lines.append(s)
        copy_text = "\n".join(copy_lines).strip()
        if copy_text and copy_text not in title and title not in copy_text:
            body_text = f"{title}\n{copy_text}"
        else:
            body_text = copy_text or title
        # 用「标题+简介」分类(主题信号干净)，不用全文转写——否则学习类关键词会在每篇都命中、塌成一类
        group = classify_bv(title, desc)
        items.append({
            "type": "B站视频", "sys": "biliv", "group": group,
            "platform": "B站", "idx": idx,
            "title": title, "url": url, "date": date, "bvid": bvid,
            "likes": like, "collects": 0, "comments": comment, "reposts": repost,
            "excerpt": re.sub(r"\s+", " ", body_text)[:160],
            "body": body_text[:4000],
            "tags": [group],
        })
        bv_cnt += 1
    print("B站视频：", collections.Counter(it["group"] for it in items if it["sys"] == "biliv"), f"共{bv_cnt}")
else:
    print("⚠️ 缺少 B站视频文件：", BILI_VIDEO_SRC)

# ================================================================ 朋友圈（微信 Moments）
PYQ_EMOJI_RE = re.compile(r"\[[一-鿿A-Za-z]{1,4}\]")   # 微信表情符 [微笑]/[doge]/[OK]

def clean_moment_text(raw):
    t = PYQ_EMOJI_RE.sub("", raw or "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t

def moment_title(text, idx):
    one = re.sub(r"\s+", " ", text).strip()
    first = re.split(r"[。！？!?\n]", one)[0].strip()
    if not first:
        first = one
    return (first[:30] or f"朋友圈 #{idx}")

def classify_moment(text, form):
    hay = (text or "").lower()
    for cid, _name, _emoji, _color, kws in PYQ_CATS:
        if kws and any(k.lower() in hay for k in kws):
            return cid
    # 无主题关键词命中：小程序基本是音乐分享，归音乐；否则生活·日常兜底
    if form == "music":
        return "pyq_music"
    return "pyq_daily"

if os.path.isfile(MOMENTS_SRC):
    with open(MOMENTS_SRC, encoding="utf-8") as f:
        moments_raw = json.load(f).get("posts", [])
    seen_moment = set()
    pyq_cnt = 0
    # 时间正序解析、去重保留最早，再统一倒序展示
    for idx, p in enumerate(sorted(moments_raw, key=lambda x: x.get("create_time", 0))):
        raw = (p.get("content_desc") or "").strip()
        if not raw:                                   # 数据审核：空文本无信息量
            audit_stats["pyq_removed_empty"] += 1
            continue
        clean = clean_moment_text(raw)
        if not clean:                                 # 纯表情符，清洗后为空
            audit_stats["pyq_removed_emoji_only"] += 1
            continue
        dedup_key = re.sub(r"\s+", "", clean)
        if dedup_key in seen_moment:                  # 精确去重
            audit_stats["pyq_removed_duplicate"] += 1
            continue
        seen_moment.add(dedup_key)
        ct = p.get("content_type")
        form = CT_TO_FORM.get(ct, "note")
        group = classify_moment(clean, form)
        date = (p.get("create_time_str") or "")[:10]
        media = p.get("media") or []
        fm = PYQ_FORM_META[form]
        items.append({
            "type": "朋友圈", "sys": "pyq", "group": group,
            "platform": "微信", "pyq_form": form, "pyq_form_name": fm["name"],
            "idx": idx, "title": moment_title(clean, idx), "url": "",
            "date": date, "create_time": p.get("create_time", 0),
            "likes": 0, "collects": 0,
            "has_media": bool(media), "media_count": len(media),
            "excerpt": re.sub(r"\s+", " ", clean)[:160], "body": clean[:1200],
            "tags": [group],
        })
        pyq_cnt += 1
    print("朋友圈：", collections.Counter(it["group"] for it in items if it["sys"] == "pyq"), f"共{pyq_cnt}")
else:
    print("⚠️ 缺少 朋友圈文件：", MOMENTS_SRC)

# ================================================================ 系统/分组元数据
SYSTEMS = [
    {"id": "zhihu", "name": "知乎",   "emoji": "📕", "color": "#4361EE"},
    {"id": "mp",    "name": "公众号", "emoji": "📗", "color": "#2A9D8F"},
    {"id": "bili",  "name": "B站动态", "emoji": "📡", "color": "#79B8FF"},
    {"id": "biliv", "name": "B站视频", "emoji": "🎬", "color": "#E9C46A"},
    {"id": "pyq",   "name": "朋友圈", "emoji": "📘", "color": "#b0859a"},
]
GROUPS = [{"id": c[0], "sys": "zhihu", "name": c[1], "emoji": c[2], "color": c[3]} for c in CATS] \
       + [{"id": a[0], "sys": "mp",    "name": a[1], "emoji": a[2], "color": a[3]} for a in MP_ACCOUNTS] \
       + [{"id": g[0], "sys": "bili",  "name": g[1], "emoji": g[2], "color": g[3]} for g in BILI_GROUPS] \
       + [{"id": c[0], "sys": "biliv", "name": c[1], "emoji": c[2], "color": c[3]} for c in BV_CATS] \
       + [{"id": c[0], "sys": "pyq",   "name": c[1], "emoji": c[2], "color": c[3]} for c in PYQ_CATS]
GROUP_META = {g["id"]: g for g in GROUPS}
GROUP_ORDER = [g["id"] for g in GROUPS]

# ---------------------------------------------------------------- stats
sys_cnt   = collections.Counter(it["sys"] for it in items)
group_cnt = collections.Counter(it["group"] for it in items)
mp_type_cnt = collections.Counter(it.get("mp_type") for it in items if it["sys"] == "mp")
with open(os.path.join(ROOT, "_build", "stats.txt"), "w", encoding="utf-8") as f:
    f.write("树林知识宇宙 · 分组统计\n\n")
    for s in SYSTEMS:
        f.write(f"{s['emoji']} {s['name']}  （{sys_cnt.get(s['id'],0)} 条）\n")
        for g in GROUPS:
            if g["sys"] != s["id"]:
                continue
            f.write(f"    {g['emoji']} {g['name']:10s} : {group_cnt.get(g['id'],0)}\n")
        f.write("\n")
    f.write("公众号内容类型\n")
    for tid, name, emoji, _color, _kws in MP_TYPES:
        f.write(f"    {emoji} {name:4s} : {mp_type_cnt.get(tid,0)}\n")
    f.write("\n")
    pyq_form_cnt = collections.Counter(it.get("pyq_form") for it in items if it["sys"] == "pyq")
    f.write("朋友圈内容形态（辅轴）\n")
    for fid, name, emoji, _color in PYQ_FORMS:
        f.write(f"    {emoji} {name:6s} : {pyq_form_cnt.get(fid,0)}\n")
    f.write("\n")
    f.write("数据审核 Agent\n")
    if audit_stats:
        reason_names = {
            "bili_removed_empty_after_media_strip": "B站：剔除纯图片/媒体占位/空内容",
            "bili_removed_none_body": "B站：剔除 None 空内容",
            "bili_removed_pure_image": "B站：剔除纯图片",
            "pyq_removed_empty": "朋友圈：剔除空文本",
            "pyq_removed_emoji_only": "朋友圈：剔除纯表情符",
            "pyq_removed_duplicate": "朋友圈：剔除精确重复",
        }
        for key, cnt in sorted(audit_stats.items()):
            f.write(f"    {reason_names.get(key,key)} : {cnt}\n")
    else:
        f.write("    本次没有剔除项\n")
    f.write("\n")
    f.write(f"总计 {len(items)} 条\n")
print(open(os.path.join(ROOT, "_build", "stats.txt"), encoding="utf-8").read())

# ---------------------------------------------------------------- 输出 JSON / JS
data = {
    "meta": {
        "title": "树林知识宇宙",
        "subtitle": "树成林 · 知乎 + 公众号 + B站动态 + B站视频 + 朋友圈全集",
        "total": len(items),
        "crawl_date": "2026-06-06",
    },
    "systems": SYSTEMS,
    "groups": GROUPS,
    "mp_types": [MP_TYPE_META[t[0]] for t in MP_TYPES],
    "pyq_forms": [PYQ_FORM_META[f[0]] for f in PYQ_FORMS],
    "items": items,
}
DATA_ROOT = os.path.join(ROOT, "数据")
os.makedirs(DATA_ROOT, exist_ok=True)
with open(os.path.join(DATA_ROOT, "data.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA_ROOT, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.ZHIHU_DATA = ")
    json.dump(data, f, ensure_ascii=False, indent=1)
    f.write(";\n")
print("已写 数据/data.json + data.js")

def source_doc_path(it):
    g = GROUP_META.get(it.get("group"), {})
    if not g:
        return ""
    if it.get("sys") == "zhihu":
        return f"数据/分类文档/知乎/{g['emoji']}{g['name'].replace('·','-')}.md"
    if it.get("sys") == "mp":
        return f"数据/分类文档/公众号/{g['emoji']}{g['name']}.md"
    if it.get("sys") == "bili":
        return f"数据/分类文档/B站动态/{g['emoji']}{g['name']}.md"
    if it.get("sys") == "biliv":
        return f"数据/分类文档/B站视频/{g['emoji']}{g['name'].replace('·','-')}.md"
    if it.get("sys") == "pyq":
        return f"数据/分类文档/朋友圈/{g['emoji']}{g['name'].replace('·','-')}.md"
    return ""

def agent_search_text(it):
    g = GROUP_META.get(it.get("group"), {})
    s = next((x for x in SYSTEMS if x["id"] == it.get("sys")), {})
    tag_names = [GROUP_META.get(t, {}).get("name", t) for t in it.get("tags", [])]
    parts = [
        it.get("title"), it.get("excerpt"), it.get("body"), it.get("type"),
        it.get("account"), it.get("mp_type_name"), it.get("bili_type_name"),
        it.get("pyq_form_name"),
        it.get("platform"), g.get("name"), s.get("name"), *tag_names
    ]
    return " ".join(str(x) for x in parts if x).lower()

agent_items = []
for i, it in enumerate(items):
    g = GROUP_META.get(it.get("group"), {})
    s = next((x for x in SYSTEMS if x["id"] == it.get("sys")), {})
    agent_id = f"{it.get('sys','item')}-{i+1}"
    it["agent_id"] = agent_id
    agent_items.append({
        "id": agent_id,
        "title": it.get("title", ""),
        "platform": s.get("name", it.get("sys", "")),
        "sys": it.get("sys", ""),
        "group": it.get("group", ""),
        "group_name": g.get("name", ""),
        "type": it.get("type", ""),
        "content_type": it.get("mp_type_name") or it.get("bili_type_name") or it.get("pyq_form_name") or it.get("type", ""),
        "account": it.get("account", ""),
        "date": it.get("date", ""),
        "url": it.get("url", ""),
        "source_doc": source_doc_path(it),
        "likes": it.get("likes", 0),
        "comments": it.get("comments", 0),
        "reposts": it.get("reposts", 0),
        "excerpt": it.get("excerpt", ""),
        "body": it.get("body", it.get("excerpt", "")),
        "search_text": agent_search_text(it),
    })

agent_index = {
    "meta": {
        "title": data["meta"]["title"],
        "total": len(agent_items),
        "updated": data["meta"]["crawl_date"],
        "usage": "读取 agent-index.json 后，用关键词在 search_text 中匹配；或访问 agent.html?q=关键词&platform=all&format=md。",
        "entry": "agent.html",
        "query_params": {
            "q": "关键词，支持任意文本",
            "platform": "all | zhihu | mp | bili | biliv",
            "format": "md | json",
            "limit": "返回条数上限，默认 80",
            "id": "直接读取单条内容的 agent_id"
        }
    },
    "systems": SYSTEMS,
    "groups": GROUPS,
    "items": agent_items,
}
with open(os.path.join(DATA_ROOT, "agent-index.json"), "w", encoding="utf-8") as f:
    json.dump(agent_index, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA_ROOT, "agent-index.js"), "w", encoding="utf-8") as f:
    f.write("window.AGENT_INDEX = ")
    json.dump(agent_index, f, ensure_ascii=False, indent=1)
    f.write(";\n")
print("已写 数据/agent-index.json + agent-index.js")

# ---------------------------------------------------------------- 分类文档（按来源分子目录）
DOC_ROOT = os.path.join(DATA_ROOT, "分类文档")
if os.path.isdir(DOC_ROOT):
    shutil.rmtree(DOC_ROOT)
os.makedirs(DOC_ROOT, exist_ok=True)

by_group = collections.defaultdict(list)
for it in items:
    by_group[it["group"]].append(it)

type_emoji = {"回答": "📝", "文章": "📰", "想法": "💭", "公众号": "📰", "B站动态": "📡"}

# 知乎：按维度，按点赞排序
zdir = os.path.join(DOC_ROOT, "知乎"); os.makedirs(zdir, exist_ok=True)
for g in GROUPS:
    if g["sys"] != "zhihu":
        continue
    arr = sorted(by_group.get(g["id"], []), key=lambda x: -x["likes"])
    if not arr:
        continue
    fn = os.path.join(zdir, f"{g['emoji']}{g['name'].replace('·','-')}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {g['emoji']} {g['name']}\n\n> 共 **{len(arr)}** 条（按点赞排序）｜来源：知乎\n\n---\n\n")
        for it in arr:
            te = type_emoji.get(it["type"], "")
            head = f"[{it['title']}]({it['url']})" if it["url"] else it["title"]
            f.write(f"### {te} {head}\n\n")
            ml = f"**{it['type']}** · 👍 {it['likes']:,}"
            if it["collects"]: ml += f" · ⭐ {it['collects']:,}"
            if it.get("comments"): ml += f" · 💬 {it['comments']:,}"
            others = [GROUP_META[t]['name'] for t in it["tags"] if t != it["group"] and t in GROUP_META]
            if others: ml += "  ｜ 关联：" + "、".join(others)
            f.write(ml + "\n\n" + it["excerpt"] + ("…" if len(it["excerpt"]) >= 150 else "") + "\n\n---\n\n")

# 公众号：按账号，按日期倒序
mdir = os.path.join(DOC_ROOT, "公众号"); os.makedirs(mdir, exist_ok=True)
for g in GROUPS:
    if g["sys"] != "mp":
        continue
    arr = sorted(by_group.get(g["id"], []), key=lambda x: x.get("date",""), reverse=True)
    if not arr:
        continue
    fn = os.path.join(mdir, f"{g['emoji']}{g['name']}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {g['emoji']} {g['name']}\n\n> 共 **{len(arr)}** 篇（按日期倒序）｜来源：公众号\n\n---\n\n")
        for it in arr:
            head = f"[{it['title']}]({it['url']})" if it["url"] else it["title"]
            f.write(f"### 📰 {head}\n\n")
            f.write(f"*{it.get('date','')}*\n\n")
            f.write(it["excerpt"] + ("…" if len(it["excerpt"]) >= 150 else "") + "\n\n---\n\n")

typed_dir = os.path.join(mdir, "按类型"); os.makedirs(typed_dir, exist_ok=True)
by_mp_type = collections.defaultdict(list)
for it in items:
    if it["sys"] == "mp":
        by_mp_type[it.get("mp_type", "daily")].append(it)
for tid, name, emoji, _color, _kws in MP_TYPES:
    arr = sorted(by_mp_type.get(tid, []), key=lambda x: x.get("date",""), reverse=True)
    if not arr:
        continue
    fn = os.path.join(typed_dir, f"{emoji}{name}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {emoji} {name}\n\n> 共 **{len(arr)}** 篇（按日期倒序）｜来源：公众号\n\n---\n\n")
        for it in arr:
            head = f"[{it['title']}]({it['url']})" if it["url"] else it["title"]
            f.write(f"### 📰 {head}\n\n")
            f.write(f"*{it.get('date','')}* ｜ {it.get('account','')}\n\n")
            f.write(it["excerpt"] + ("…" if len(it["excerpt"]) >= 150 else "") + "\n\n---\n\n")

# B站动态：按动态类型，按源文件顺序
bdir = os.path.join(DOC_ROOT, "B站动态"); os.makedirs(bdir, exist_ok=True)
for g in GROUPS:
    if g["sys"] != "bili":
        continue
    arr = sorted(by_group.get(g["id"], []), key=lambda x: x.get("idx", 0))
    if not arr:
        continue
    fn = os.path.join(bdir, f"{g['emoji']}{g['name']}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {g['emoji']} {g['name']}\n\n> 共 **{len(arr)}** 条（按源文件顺序）｜来源：B站动态\n\n---\n\n")
        for it in arr:
            head = f"[{it['title']}]({it['url']})" if it["url"] else it["title"]
            f.write(f"### 📡 {head}\n\n")
            ml = f"❤️ {it.get('likes',0):,} · 💬 {it.get('comments',0):,} · 🔄 {it.get('reposts',0):,}"
            f.write(ml + "\n\n" + it["excerpt"] + ("…" if len(it["excerpt"]) >= 150 else "") + "\n\n---\n\n")

# B站视频：按主题，按发布时间倒序，输出文案
vdir = os.path.join(DOC_ROOT, "B站视频"); os.makedirs(vdir, exist_ok=True)
for g in GROUPS:
    if g["sys"] != "biliv":
        continue
    arr = sorted(by_group.get(g["id"], []), key=lambda x: x.get("date", ""), reverse=True)
    if not arr:
        continue
    fn = os.path.join(vdir, f"{g['emoji']}{g['name'].replace('·','-')}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {g['emoji']} {g['name']}\n\n> 共 **{len(arr)}** 个视频（按发布时间倒序）｜来源：B站视频文案\n\n---\n\n")
        for it in arr:
            head = f"[{it['title']}]({it['url']})" if it["url"] else it["title"]
            f.write(f"### 🎬 {head}\n\n")
            ml = f"*{it.get('date','')}* ｜ ❤️ {it.get('likes',0):,} · 💬 {it.get('comments',0):,} · 🔄 {it.get('reposts',0):,}"
            f.write(ml + "\n\n" + it["excerpt"] + ("…" if len(it["excerpt"]) >= 150 else "") + "\n\n---\n\n")

# 朋友圈：按主题分组，按时间倒序，正文附内容形态（辅轴）
pdir = os.path.join(DOC_ROOT, "朋友圈"); os.makedirs(pdir, exist_ok=True)
for g in GROUPS:
    if g["sys"] != "pyq":
        continue
    arr = sorted(by_group.get(g["id"], []), key=lambda x: x.get("create_time", 0), reverse=True)
    if not arr:
        continue
    fn = os.path.join(pdir, f"{g['emoji']}{g['name'].replace('·','-')}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {g['emoji']} {g['name']}\n\n> 共 **{len(arr)}** 条（按时间倒序）｜来源：微信朋友圈\n\n---\n\n")
        for it in arr:
            fm = PYQ_FORM_META.get(it.get("pyq_form"), {})
            f.write(f"### 📘 {it['title']}\n\n")
            f.write(f"*{it.get('date','')}* ｜ {fm.get('emoji','')} {fm.get('name','')}\n\n")
            f.write(it["excerpt"] + ("…" if len(it["excerpt"]) >= 150 else "") + "\n\n---\n\n")

print("已写 数据/分类文档/知乎/*.md + 数据/分类文档/公众号/*.md + 数据/分类文档/B站动态/*.md + 数据/分类文档/B站视频/*.md + 数据/分类文档/朋友圈/*.md")
print("总计：", len(items), "条")
