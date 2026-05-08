#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HR Agent Monitor - 人力资源相关开源项目监控脚本
监控 GitHub / Skillhub / Clawhub 三大渠道
筛选 star > 200 的项目，生成深度分析报告
"""

import os
import json
import time
import datetime
import requests
import re
from pathlib import Path

# ────────────────────────────────────────────
# 配置区
# ────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
WECHAT_WEBHOOK = os.environ.get("WECHAT_WEBHOOK", "")   # 企业微信机器人 Webhook
STAR_THRESHOLD = 200

# HR 相关 GitHub 搜索（按 HR 子领域分组）
# 覆盖：招聘、简历、培训、绩效、薪酬、劳动关系、预算、HRBP、入职、员工管理
GITHUB_SEARCH_QUERIES = [
    # ═══════════ 招聘 / 人才获取 ═══════════
    "topic:recruitment stars:>200",
    "ATS+applicant+tracking stars:>200",
    "talent+acquisition stars:>200",
    "recruitment+AI stars:>200",
    "candidate+screening stars:>200",
    "interview+AI stars:>200",
    "job+matching+AI stars:>200",
    "hiring+management stars:>200",
    "referral+program+employee stars:>200",

    # ═══════════ 简历 / CV ═══════════
    "topic:resume stars:>200",
    "resume+screening+AI stars:>200",
    "resume+builder+parser stars:>200",
    "CV+generator stars:>200",

    # ═══════════ 培训 / 学习发展 ═══════════
    "topic:training stars:>200",
    "employee+training+platform stars:>200",
    "learning+management+system stars:>200",
    "LMS+corporate+training stars:>200",
    "e-learning+course stars:>200",
    "onboarding+training stars:>200",
    "skill+assessment+employee stars:>200",
    "knowledge+base+employee stars:>200",

    # ═══════════ 绩效管理 ═══════════
    "performance+review+management stars:>200",
    "performance+evaluation+employee stars:>200",
    "OKR+goal+tracking stars:>200",
    "KPI+dashboard+employee stars:>200",
    "360+feedback+review stars:>200",
    "goal+setting+employee stars:>200",

    # ═══════════ 薪酬 / 福利 / 薪资 ═══════════
    "payroll+management stars:>200",
    "compensation+benefits stars:>200",
    "salary+calculation stars:>200",
    "leave+management+employee stars:>200",
    "expense+management+employee stars:>200",

    # ═══════════ 劳动关系 / 合规 ═══════════
    "labor+relations+management stars:>200",
    "employee+compliance stars:>200",
    "workforce+compliance stars:>200",
    "contract+management+employee stars:>200",
    "policy+management+HR stars:>200",

    # ═══════════ 预算 / 成本管控 ═══════════
    "HR+budget+management stars:>200",
    "workforce+planning+budget stars:>200",
    "headcount+planning stars:>200",
    "labor+cost+analytics stars:>200",

    # ═══════════ HRBP / 综合 HR 平台 ═══════════
    "topic:human-resources stars:>200",
    "topic:hr stars:>200",
    "HRIS+human+resource stars:>200",
    "HRMS+HR+management stars:>200",
    "HCM+human+capital stars:>200",
    "people+analytics+HR stars:>200",
    "workforce+management stars:>200",
    "employee+engagement stars:>200",
    "HR+chatbot+assistant stars:>200",
    "employee+self+service stars:>200",
    "org+chart+organization stars:>200",
    "shift+scheduling+employee stars:>200",
    "time+attendance+tracking stars:>200",
    "employee+directory stars:>200",
]

# Skillhub / Clawhub 搜索关键词（按子领域覆盖）
# 真实 API: GET https://api.skillhub.cn/api/skills?keyword=xxx&pageSize=50&pageNumber=1
SKILL_KEYWORDS = [
    "hr", "recruitment", "resume screening", "talent acquisition",
    "human resources", "ATS", "onboarding", "payroll", "performance review",
    "employee training", "learning management", "compensation", "HRIS",
    "workforce management", "labor relations", "compliance", "HRBP",
    "leave management", "OKR", "KPI", "expense management", "shift scheduling",
    "time attendance", "org chart",
]
SKILL_PAGE_SIZE = 50       # 每次请求获取数量
SKILL_MAX_PER_KW = 100     # 每个关键词最多取多少

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TODAY = datetime.date.today().isoformat()
TODAY_GITHUB_MD  = DATA_DIR / "github_today.md"
TODAY_SKILLS_MD  = DATA_DIR / "skills_today.md"
HISTORY_GITHUB_MD = DATA_DIR / "github_history.md"
HISTORY_SKILLS_MD = DATA_DIR / "skills_history.md"
HISTORY_JSON      = DATA_DIR / "history.json"


# ────────────────────────────────────────────
# 翻译函数
# ────────────────────────────────────────────
# 常见 HR/AI 领域术语缓存（避免重复翻译）
TERMINOLOGY = {
    # ── 招聘 / 简历 ──
    "resume": "简历", "cv": "简历", "cover letter": "求职信",
    "recruitment": "招聘", "recruiting": "招聘", "recruit": "招聘",
    "applicant": "求职者", "applicant tracking": "求职者追踪",
    "screening": "筛选", "candidate": "候选人", "hiring": "招聘",
    "job search": "求职", "job application": "求职申请", "job board": "招聘网站",
    "job matching": "职位匹配", "talent acquisition": "人才获取", "talent": "人才",
    "referral": "内推", "sourcing": "人才寻访",
    # ── 培训 / 学习 ──
    "training": "培训", "learning management": "学习管理", "LMS": "学习管理系统",
    "e-learning": "在线学习", "course": "课程", "onboarding": "入职",
    "skill assessment": "技能评估", "knowledge base": "知识库",
    "tutorial": "教程", "coaching": "辅导", "mentor": "导师",
    # ── 绩效管理 ──
    "performance review": "绩效评估", "performance": "绩效",
    "OKR": "OKR目标管理", "KPI": "KPI考核", "goal setting": "目标设定",
    "feedback": "反馈", "appraisal": "考核", "evaluation": "评估",
    # ── 薪酬 / 福利 ──
    "payroll": "薪资", "payroll management": "薪资管理",
    "compensation": "薪酬", "benefits": "福利", "salary": "工资",
    "leave management": "请假管理", "expense management": "费用管理",
    "reimbursement": "报销", "payslip": "工资单",
    # ── 劳动关系 / 合规 ──
    "labor relations": "劳动关系", "compliance": "合规",
    "contract management": "合同管理", "policy": "制度",
    "regulation": "法规", "dispute": "争议",
    # ── 预算 / 成本 ──
    "budget": "预算", "headcount": "编制", "workforce planning": "人力规划",
    "labor cost": "人工成本", "cost analytics": "成本分析",
    # ── 员工管理 ──
    "onboarding": "入职", "offboarding": "离职",
    "workforce": "劳动力", "workforce management": "劳动力管理",
    "employee engagement": "员工敬业度", "employee experience": "员工体验",
    "human resources": "人力资源", "HR": "HR", "HRIS": "人力资源信息系统",
    "HRMS": "人力资源管理系统", "HCM": "人力资本管理",
    "ATS": "招聘管理系统", "chatbot": "聊天机器人",
    "interview": "面试", "assessment": "评估",
    "scheduling": "排程", "shift scheduling": "排班",
    "time attendance": "考勤", "attendance": "考勤",
    "employee directory": "员工通讯录", "org chart": "组织架构图",
    "employee self-service": "员工自助服务",
    # ── 通用技术 ──
    "analytics": "数据分析", "insights": "洞察",
    "open source": "开源", "open-source": "开源",
    "AI": "AI", "artificial intelligence": "人工智能",
    "machine learning": "机器学习", "ML": "机器学习",
    "deep learning": "深度学习", "NLP": "自然语言处理",
    "LLM": "大语言模型", "GPT": "GPT", "transformer": "Transformer",
    "automation": "自动化", "pipeline": "流水线",
    "tracker": "追踪器", "dashboard": "仪表盘", "platform": "平台",
    "framework": "框架", "toolkit": "工具包", "library": "库",
    "template": "模板", "builder": "构建器", "generator": "生成器",
    "matching": "匹配", "job": "职位", "career": "职业",
    "freelance": "自由职业", "remote": "远程", "tracking": "追踪",
    "management": "管理系统", "software": "软件", "system": "系统",
    "solution": "解决方案", "service": "服务", "engine": "引擎",
    "API": "API", "SDK": "SDK", "plugin": "插件",
    "self-hosted": "自托管", "hosted": "托管",
    "privacy": "隐私", "security": "安全",
    "ethical": "伦理的", "sustainable": "可持续的",
    "powering": "赋能", "empowering": "赋能",
    "enterprise": "企业级", "scalable": "可扩展的",
    "customizable": "可定制的", "portable": "可移植的",
    "drag-and-drop": "拖拽式", "real-time": "实时",
    "natural language": "自然语言", "conversational": "对话式",
}


def _is_chinese(text: str) -> bool:
    """判断文本是否主要包含中文"""
    if not text:
        return True
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese_chars > len(text) * 0.3


def translate_description(text: str, cache: dict) -> str:
    """翻译项目简介为中文，带缓存"""
    if not text or _is_chinese(text):
        return text or "暂无简介"

    # 检查缓存
    if text in cache:
        return cache[text]

    # 先用术语替换
    translated = text
    # 按词长度倒序替换（避免短词先替换影响长词匹配）
    sorted_terms = sorted(TERMINOLOGY.items(), key=lambda x: len(x[0]), reverse=True)
    for en, zh in sorted_terms:
        translated = re.sub(re.escape(en), zh, translated, flags=re.IGNORECASE)

    # 如果替换后仍然主要是英文，调用翻译 API
    if not _is_chinese(translated):
        translated = _translate_via_api(text, cache)

    cache[text] = translated
    return translated


def _translate_via_api(text: str, cache: dict) -> str:
    """通过 MyMemory 免费翻译 API 翻译"""
    try:
        # 截断过长的文本（API 限制 500 字符）
        short_text = text[:480] if len(text) > 480 else text
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": short_text,
            "langpair": "en|zh-CN",
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("responseData", {}).get("translatedText", "")
            if result and _is_chinese(result):
                # 去掉 MyMemory 有时返回的包裹标记
                result = result.strip()
                cache[text] = result
                return result
    except Exception as e:
        print(f"[WARN] 翻译 API 调用失败: {e}")
    return text


def batch_translate_descriptions(projects: list[dict]) -> None:
    """批量翻译项目简介（原地修改）"""
    cache = {}
    for i, p in enumerate(projects):
        desc = p.get("description", "")
        if desc and not _is_chinese(desc):
            p["description"] = translate_description(desc, cache)
        if (i + 1) % 20 == 0:
            print(f"      已翻译 {i + 1}/{len(projects)} 个简介...")
    print(f"      翻译完成，共 {len(projects)} 个项目")
def gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def load_history() -> dict:
    if HISTORY_JSON.exists():
        return json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
    return {"github": {}, "skills": {}, "clawhub": {}}


def save_history(data: dict):
    HISTORY_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def send_wechat(title: str, content: str):
    """发送企业微信机器人通知"""
    if not WECHAT_WEBHOOK:
        print("[WARN] WECHAT_WEBHOOK 未配置，跳过通知")
        return
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"## {title}\n\n{content}"
        }
    }
    try:
        resp = requests.post(WECHAT_WEBHOOK, json=payload, timeout=10)
        if resp.status_code == 200:
            print("[OK] 微信通知已发送")
        else:
            print(f"[WARN] 微信通知失败: {resp.text}")
    except Exception as e:
        print(f"[ERROR] 微信通知异常: {e}")


# ────────────────────────────────────────────
# GitHub 抓取
# ────────────────────────────────────────────
def fetch_github_projects() -> list[dict]:
    """搜索 GitHub 上 HR 相关、star > 200 的项目"""
    seen = set()
    results = []

    for query in GITHUB_SEARCH_QUERIES:
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
        }
        try:
            resp = requests.get(url, headers=gh_headers(), params=params, timeout=15)
            if resp.status_code == 403:
                print(f"[WARN] GitHub API 限速，等待 60 秒...")
                time.sleep(60)
                resp = requests.get(url, headers=gh_headers(), params=params, timeout=15)
            if resp.status_code != 200:
                print(f"[WARN] GitHub API 返回 {resp.status_code}，query: {query}")
                continue
            data = resp.json()
            total = data.get("total_count", 0)
            items = data.get("items", [])
            print(f"      query '{query[:40]}...' → {total} results, fetched {len(items)}")
            for item in items:
                if item["full_name"] not in seen:
                    seen.add(item["full_name"])
                    results.append({
                        "name": item["full_name"],
                        "url": item["html_url"],
                        "description": item.get("description") or "",
                        "stars": item["stargazers_count"],
                        "forks": item["forks_count"],
                        "language": item.get("language") or "Unknown",
                        "updated_at": item["updated_at"][:10],
                        "topics": item.get("topics", []),
                        "keyword": query,
                    })
        except Exception as e:
            print(f"[ERROR] GitHub 搜索异常 ({query[:40]}): {e}")
        time.sleep(2)  # 避免触发速率限制

    # 按 star 降序
    results.sort(key=lambda x: x["stars"], reverse=True)
    return results


# ────────────────────────────────────────────
# Skillhub 抓取
# ────────────────────────────────────────────
def fetch_skillhub_projects() -> list[dict]:
    """从 Skillhub API 搜索 HR 相关 skill（真实 API）"""
    results = []
    seen = set()
    base_url = "https://api.skillhub.cn/api/skills"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://skillhub.cn/",
    }

    for kw in SKILL_KEYWORDS:
        page = 1
        fetched = 0
        try:
            while fetched < SKILL_MAX_PER_KW:
                params = {
                    "keyword": kw,
                    "pageSize": SKILL_PAGE_SIZE,
                    "pageNumber": page,
                }
                resp = requests.get(base_url, params=params, headers=headers, timeout=15)
                if resp.status_code != 200:
                    print(f"[WARN] Skillhub API 返回 {resp.status_code}，kw={kw}")
                    break

                data = resp.json()
                if data.get("code") != 0:
                    print(f"[WARN] Skillhub API 错误: {data.get('message', '未知错误')}")
                    break

                skills = data.get("data", {}).get("skills", [])
                if not skills:
                    break

                for item in skills:
                    slug = item.get("slug", "")
                    if slug and slug not in seen:
                        seen.add(slug)
                        # 优先使用中文描述
                        desc = item.get("description_zh") or item.get("description") or ""
                        results.append({
                            "name": item.get("name") or slug,
                            "slug": slug,
                            "url": item.get("homepage") or f"https://skillhub.cn/skills/{slug}",
                            "description": desc,
                            "description_zh": desc,
                            "stars": item.get("stars") or 0,
                            "downloads": item.get("downloads") or 0,
                            "installs": item.get("installs") or 0,
                            "category": item.get("category") or "",
                            "source": item.get("source") or "unknown",
                            "tags": item.get("tags") or [],
                            "ownerName": item.get("ownerName") or "",
                            "keyword": kw,
                        })

                fetched += len(skills)
                page += 1

                # 如果这一页数据不足 pageSize，说明已经是最后一页
                if len(skills) < SKILL_PAGE_SIZE:
                    break

                time.sleep(0.3)  # 避免请求过快

        except Exception as e:
            print(f"[WARN] Skillhub 搜索异常 ({kw}): {e}")

    # 按综合热度排序（downloads + installs*2 + stars*3）
    results.sort(key=lambda x: x.get("downloads", 0) + x.get("installs", 0) * 2 + x.get("stars", 0) * 3, reverse=True)
    return results


# ────────────────────────────────────────────
# Clawhub 抓取
# ────────────────────────────────────────────
def fetch_clawhub_projects() -> list[dict]:
    """从 Clawhub 搜索 HR 相关项目"""
    results = []
    seen = set()
    base_url = "https://clawhub.cn/api/mcp/search"

    for kw in SKILL_KEYWORDS:
        try:
            resp = requests.get(base_url, params={"q": kw, "limit": 30}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("items") or data.get("data") or []
                for item in items:
                    name = item.get("name") or item.get("title") or ""
                    if name and name not in seen:
                        seen.add(name)
                        results.append({
                            "name": name,
                            "url": item.get("url") or item.get("link") or f"https://clawhub.cn/mcp/{name}",
                            "description": item.get("description") or "",
                            "stars": item.get("stars") or item.get("installs") or 0,
                            "category": item.get("category") or "HR",
                            "keyword": kw,
                        })
        except Exception as e:
            print(f"[WARN] Clawhub 搜索异常 ({kw}): {e}")
        time.sleep(0.8)

    results.sort(key=lambda x: x.get("stars", 0), reverse=True)
    return results


# ────────────────────────────────────────────
# Markdown 报告生成
# ────────────────────────────────────────────
def _star_level(stars: int) -> str:
    """根据 star 数给出等级标签"""
    if stars >= 10000: return "🔥 顶级项目"
    if stars >= 5000:  return "⭐ 明星项目"
    if stars >= 1000:  return "💎 优质项目"
    if stars >= 500:   return "📈 潜力项目"
    return "🌱 新兴项目"


def _classify_project(p: dict) -> str:
    """根据描述关键词给项目分类标签（覆盖 HR 全子领域）"""
    desc_lower = (p.get("description") or "").lower()
    name_lower = (p.get("name") or "").lower()
    keyword_lower = (p.get("keyword") or "").lower()
    text = desc_lower + " " + name_lower + " " + keyword_lower
    mapping = [
        # 招聘 / 人才获取
        (["recruit", "talent acquisition", "sourc", "hiring", "referral"], "🎯 招聘/人才获取"),
        # 简历 / CV
        (["resume", "cv ", "resume screening", "resume builder", "resume parser"], "📄 简历/简历筛选"),
        # 培训 / 学习发展
        (["training", "learning", "lms", "e-learning", "course", "onboarding", "skill assessment",
          "knowledge base", "tutorial"], "📚 培训/学习发展"),
        # 绩效管理
        (["performance", "okr", "kpi", "goal", "feedback", "evaluation", "review", "appraisal"], "📝 绩效管理"),
        # 薪酬 / 福利 / 薪资
        (["payroll", "compensation", "salary", "benefit", "leave management", "expense",
          "reimbursement", "payslip"], "💰 薪酬/福利"),
        # 劳动关系 / 合规
        (["labor", "compliance", "contract", "policy", "regulation", "legal", "dispute"], "⚖️ 劳动关系/合规"),
        # 预算 / 成本管控
        (["budget", "cost", "headcount", "workforce planning", "labor cost"], "📊 预算/成本管控"),
        # ATS 招聘管理
        (["ats", "applicant track"], "📋 ATS 招聘管理"),
        # 面试 / 评估
        (["interview", "assessment", "schedule"], "🎙️ 面试/评估"),
        # HR 聊天机器人 / AI
        (["chatbot", "conversational", "assistant", "hrbot"], "🤖 HR 聊天机器人"),
        # 入职 / 员工管理
        (["onboard", "employee experience", "hcm", "employee directory", "org chart",
          "shift", "attendance", "time track", "employee self-service"], "👥 入职/员工管理"),
        # 人力数据分析
        (["analytics", "insight", "people analyt", "data-driven hr"], "📊 人力数据分析"),
        # AI/NLP 基础
        (["llm", "gpt", "transformer", "nlp"], "🧠 AI/NLP 基础"),
    ]
    for keywords, label in mapping:
        if any(kw in text for kw in keywords):
            return label
    return "🏢 综合HR平台"


def render_github_md(projects: list[dict], title: str) -> str:
    # ── 头部概览 ──
    lines = [
        f"# {title}",
        f"",
        f"> 更新时间：{TODAY}　｜　筛选条件：⭐ Star > {STAR_THRESHOLD}　｜　来源：GitHub",
        f"",
        f"## 概览",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 项目总数 | {len(projects)} |",
        f"| 平均 Star | {int(sum(p['stars'] for p in projects)/len(projects)) if projects else 0} |",
        f"| 最高 Star | {max((p['stars'] for p in projects), default=0):,} |",
        f"| 涉及编程语言 | {len(set(p['language'] for p in projects))} 种 |",
        f"",
        f"---",
        f"",
    ]

    # ── 项目列表（表格形式 - Top 20） ──
    lines += [
        f"## GitHub 新发现项目（Top 20）",
        f"",
        f"| 项目名 | ⭐ Stars | 简介 |",
        f"|--------|---------|------|",
    ]
    for p in projects[:20]:
        desc = p["description"] or "暂无简介"
        # 简介截断，避免表格过宽
        desc_short = desc[:60] + "..." if len(desc) > 60 else desc
        lines.append(f"| [{p['name']}]({p['url']}) | {p['stars']:,} | {desc_short} |")
    lines.append("")

    # ── 深度分析 ──
    lines += [f"---", f"", f"## 深度分析", f""]

    # ── 1. 重点项目分析 ──
    lines += [f"### 🔍 重点项目分析", f""]
    if projects:
        top10 = projects[:5]
        for rank, p in enumerate(top10, 1):
            category = _classify_project(p)
            desc = p["description"] or "暂无简介"
            lines += [
                f"#### {rank}. {p['name']} ⭐{p['stars']:,}",
                f"",
                f"- **分类**：{category}",
                f"- **简介**：{desc[:120]}",
                f"- **Forks**：{p['forks']:,}　|　**语言**：{p['language']}　|　**最近更新**：{p['updated_at']}",
                f"- **项目地址**：[{p['url']}]({p['url']})",
                f"",
            ]
    else:
        lines += ["> 暂无项目数据", ""]

    # ── 2. 趋势观察 ──
    lines += [f"### 📈 趋势观察", f""]

    # 按分类统计
    cat_count: dict = {}
    for p in projects:
        cat = _classify_project(p)
        cat_count[cat] = cat_count.get(cat, 0) + 1

    lines += [f"#### 子领域分布热度", f"", f"| 领域 | 项目数 | 占比 |", f"|------|--------|------|"]
    total = len(projects) or 1
    for cat, cnt in sorted(cat_count.items(), key=lambda x: -x[1]):
        pct = f"{cnt/total*100:.1f}%"
        bar = "█" * max(1, int(cnt / total * 20))
        lines.append(f"| {cat} | {cnt} | {pct} `{bar}`")
    lines.append("")

    # 最近活跃项目
    active_projects = sorted(projects, key=lambda x: x["updated_at"], reverse=True)[:5]
    lines += [f"#### 最近活跃项目", f""]
    for p in active_projects:
        category = _classify_project(p)
        lines.append(f"- [{p['name']}]({p['url']}) — ⭐{p['stars']:,}　|　更新于 {p['updated_at']}　|　{category}")
    lines.append("")

    # 高 Fork 项目（社区参与度高）
    high_fork = sorted(projects, key=lambda x: x["forks"], reverse=True)[:5]
    lines += [f"#### 社区参与度 Top 5（按 Fork）", f""]
    for p in high_fork:
        category = _classify_project(p)
        lines.append(f"- [{p['name']}]({p['url']}) — 🍴{p['forks']:,}　|　⭐{p['stars']:,}　|　{category}")
    lines.append("")

    # ── 3. 推荐优先级 ──
    lines += [f"### 🏆 推荐优先级", f""]

    # 综合评分：stars权重 + forks权重 + 更新时间权重
    max_stars = max((p["stars"] for p in projects), default=1) or 1
    max_forks = max((p["forks"] for p in projects), default=1) or 1
    scored = []
    for p in projects:
        star_score = p["stars"] / max_stars * 50
        fork_score = p["forks"] / max_forks * 30
        # 越新的项目加分越高
        try:
            days_since_update = (datetime.date.today() - datetime.date.fromisoformat(p["updated_at"])).days
        except (ValueError, TypeError):
            days_since_update = 365
        recency_score = max(0, 20 - days_since_update / 30)
        total_score = star_score + fork_score + recency_score
        scored.append((p, total_score))

    scored.sort(key=lambda x: x[1], reverse=True)

    lines += [f"#### 🔴 S 级 — 必须关注", f""]
    s_list = [s for s in scored if s[1] >= 70][:5]
    if s_list:
        for p, score in s_list:
            category = _classify_project(p)
            lines.append(f"- ⭐⭐⭐⭐⭐ **[{p['name']}]({p['url']})** — 综合分 {score:.0f}/100　|　{category}　|　⭐{p['stars']:,}")
    else:
        lines.append("> 本期暂无 S 级项目")
    lines.append("")

    lines += [f"#### 🟠 A 级 — 强烈推荐", f""]
    a_list = [s for s in scored if 50 <= s[1] < 70][:10]
    if a_list:
        for p, score in a_list:
            category = _classify_project(p)
            lines.append(f"- ⭐⭐⭐⭐ **[{p['name']}]({p['url']})** — 综合分 {score:.0f}/100　|　{category}　|　⭐{p['stars']:,}")
    else:
        lines.append("> 本期暂无 A 级项目")
    lines.append("")

    lines += [f"#### 🟡 B 级 — 值得关注", f""]
    b_list = [s for s in scored if 30 <= s[1] < 50][:10]
    if b_list:
        for p, score in b_list:
            category = _classify_project(p)
            lines.append(f"- ⭐⭐⭐ **[{p['name']}]({p['url']})** — 综合分 {score:.0f}/100　|　{category}　|　⭐{p['stars']:,}")
    else:
        lines.append("> 本期暂无 B 级项目")
    lines.append("")

    lines.append(f"\n---\n\n*由 HR Agent Monitor 自动生成 · {TODAY}*")
    return "\n".join(lines)


def render_skills_md(skillhub: list[dict], clawhub: list[dict], title: str) -> str:
    """渲染 Skills/MCP 看板 Markdown，输出结构化 JSON 供前端卡片渲染"""
    lines = [
        f"# {title}",
        f"",
        f"> 更新时间：{TODAY}　｜　Skillhub：**{len(skillhub)}** 个　｜　Clawhub：**{len(clawhub)}** 个",
        f"",
    ]

    # ── Skillhub 概览统计 ──
    if skillhub:
        total_downloads = sum(p.get("downloads", 0) for p in skillhub)
        total_installs = sum(p.get("installs", 0) for p in skillhub)
        total_stars = sum(p.get("stars", 0) for p in skillhub)
        top_skill = skillhub[0]
        top_heat = top_skill.get("downloads", 0) + top_skill.get("installs", 0) * 2 + top_skill.get("stars", 0) * 3

        lines += [
            f"## 概览",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| Skill 总数 | {len(skillhub)} |",
            f"| 总下载量 | {total_downloads:,} |",
            f"| 总安装量 | {total_installs:,} |",
            f"| 总 Star 数 | {total_stars:,} |",
            f"| 最热 Skill | [{top_skill.get('name', '—')}]({top_skill.get('url', '#')}) (热度 {top_heat:,}) |",
            f"",
            f"---",
            f"",
        ]

        # ── Skillhub 按热度分级（仿 GitHub 看板风格）──
        # 先给每个 skill 计算热度
        for p in skillhub:
            p["_heat"] = p.get("downloads", 0) + p.get("installs", 0) * 2 + p.get("stars", 0) * 3

        lines += [
            f"## 🔥 Skillhub 热门 Skills",
            f"",
        ]

        # Top 10
        lines.append(f"### 🏆 Top 10 热门")
        lines.append("")
        for i, p in enumerate(skillhub[:10], 1):
            name = p.get("name") or p.get("slug") or "—"
            url = p.get("url") or f"https://skillhub.cn/skills/{p.get('slug', '')}"
            desc = (p.get("description_zh") or p.get("description") or "—")[:80]
            heat = p.get("_heat", 0)
            source = p.get("source", "skillhub")
            tags = p.get("tags") or []
            tag_str = " ".join(f"`{t}`" for t in tags[:3])
            meta = f"⬇️{p.get('downloads', 0):,}　📥{p.get('installs', 0):,}　⭐{p.get('stars', 0):,}　📦{source}"
            lines.append(f"#### {i}. [{name}]({url})")
            lines.append(f"- **热度**：{heat:,}　|　{meta}")
            if desc != "—":
                lines.append(f"- **简介**：{desc}")
            if tag_str:
                lines.append(f"- **标签**：{tag_str}")
            lines.append("")

        # 完整列表表格（前 50）
        lines += [
            f"### 📋 完整列表（Top 50）",
            f"",
            f"| # | Skill | 热度 | ⬇️ 下载 | 📥 安装 | ⭐ Stars | 来源 | 标签 |",
            f"|---|-------|------|---------|---------|---------|------|------|",
        ]
        for i, p in enumerate(skillhub[:50], 1):
            name = p.get("name") or p.get("slug") or "—"
            url = p.get("url") or f"https://skillhub.cn/skills/{p.get('slug', '')}"
            heat = p.get("_heat", 0)
            tags = p.get("tags") or []
            tag_str = "、".join(tags[:2]) if tags else "—"
            lines.append(
                f"| {i} | [{name}]({url}) | {heat:,} | {p.get('downloads', 0):,} | {p.get('installs', 0):,} | {p.get('stars', 0):,} | {p.get('source', '—')} | {tag_str} |"
            )
        lines.append("")

    # ── Clawhub 部分 ──
    if clawhub:
        lines += [
            f"## 📦 Clawhub HR MCP",
            f"",
            f"共 **{len(clawhub)}** 个匹配项",
            f"",
            f"| # | MCP 名称 | 描述 | 分类 | 关键词 |",
            f"|---|---------|------|------|-------|",
        ]
        for i, p in enumerate(clawhub[:50], 1):
            desc = p["description"][:50].replace("|", "｜") if p["description"] else "—"
            lines.append(f"| {i} | [{p['name']}]({p['url']}) | {desc} | {p.get('category','—')} | {p.get('keyword','—')} |")
        lines.append("")

    # ── 嵌入结构化 JSON 供前端卡片渲染 ──
    import json as _json
    # 只保留前端需要的字段，减少体积
    skillhub_light = []
    for p in skillhub[:100]:
        skillhub_light.append({
            "name": p.get("name") or p.get("slug") or "",
            "slug": p.get("slug", ""),
            "url": p.get("url") or f"https://skillhub.cn/skills/{p.get('slug', '')}",
            "desc": (p.get("description_zh") or p.get("description") or "")[:120],
            "downloads": p.get("downloads", 0),
            "installs": p.get("installs", 0),
            "stars": p.get("stars", 0),
            "heat": p.get("_heat", 0),
            "source": p.get("source", ""),
            "tags": (p.get("tags") or [])[:5],
            "keyword": p.get("keyword", ""),
        })
    json_block = _json.dumps({"skillhub": skillhub_light, "clawhub": clawhub[:50]}, ensure_ascii=False)
    lines.append(f"<!-- SKILL_DATA:{json_block}:SKILL_DATA -->")

    lines.append(f"\n---\n\n*由 HR Agent Monitor 自动生成 · {TODAY}*")
    return "\n".join(lines)


def render_history_github_md(history: dict) -> str:
    lines = [
        "# 📚 GitHub HR 项目历史记录",
        "",
        "> 每日快照归档，按日期倒序",
        "",
    ]
    for date in sorted(history.get("github", {}).keys(), reverse=True):
        projects = history["github"][date]
        lines += [
            f"## {date}",
            f"",
            f"共 {len(projects)} 个项目，最高 Star：{max((p['stars'] for p in projects), default=0):,}",
            f"",
            f"| 项目 | ⭐ Stars | 语言 |",
            f"|------|---------|------|",
        ]
        for p in sorted(projects, key=lambda x: x["stars"], reverse=True)[:20]:
            lines.append(f"| [{p['name']}]({p['url']}) | {p['stars']:,} | {p['language']} |")
        lines.append("")
    lines.append(f"\n---\n\n*由 HR Agent Monitor 自动生成*")
    return "\n".join(lines)


def render_history_skills_md(history: dict) -> str:
    lines = [
        "# 📋 Skills/MCP 历史记录",
        "",
        "> 每日快照归档，按日期倒序",
        "",
    ]
    for date in sorted(history.get("skills", {}).keys(), reverse=True):
        entry = history["skills"][date]
        skillhub = entry.get("skillhub", [])
        clawhub  = entry.get("clawhub", [])
        lines += [
            f"## {date}",
            f"",
            f"Skillhub：{len(skillhub)} 个　｜　Clawhub：{len(clawhub)} 个",
            f"",
        ]
    lines.append(f"\n---\n\n*由 HR Agent Monitor 自动生成*")
    return "\n".join(lines)


# ────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────
def main():
    print(f"[{TODAY}] 开始 HR 项目监控抓取...")

    # 1. 抓取数据
    print("  → 抓取 GitHub 数据...")
    gh_projects = fetch_github_projects()
    print(f"     GitHub: {len(gh_projects)} 个项目 (star>{STAR_THRESHOLD})")

    # 2. 翻译简介为中文
    if gh_projects:
        print("  → 翻译项目简介为中文...")
        batch_translate_descriptions(gh_projects)

    print("  → 抓取 Skillhub 数据...")
    sh_projects = fetch_skillhub_projects()
    print(f"     Skillhub: {len(sh_projects)} 个")

    print("  → 抓取 Clawhub 数据...")
    ch_projects = fetch_clawhub_projects()
    print(f"     Clawhub: {len(ch_projects)} 个")

    # 2. 生成今日 Markdown
    gh_md = render_github_md(gh_projects, f"⭐ GitHub HR 项目监控 · {TODAY}")
    sk_md = render_skills_md(sh_projects, ch_projects, f"🛠️ Skills/MCP HR 监控 · {TODAY}")

    TODAY_GITHUB_MD.write_text(gh_md, encoding="utf-8")
    TODAY_SKILLS_MD.write_text(sk_md, encoding="utf-8")
    print("  → 今日报告已写入")

    # 3. 更新历史
    history = load_history()
    history.setdefault("github", {})[TODAY] = gh_projects
    history.setdefault("skills", {})[TODAY] = {"skillhub": sh_projects, "clawhub": ch_projects}
    save_history(history)

    # 4. 生成历史 Markdown
    HISTORY_GITHUB_MD.write_text(render_history_github_md(history), encoding="utf-8")
    HISTORY_SKILLS_MD.write_text(render_history_skills_md(history), encoding="utf-8")
    print("  → 历史记录已更新")

    # 5. 微信通知
    top5 = "\n".join(
        f"> {i+1}. [{p['name']}]({p['url']}) — ⭐{p['stars']:,}"
        for i, p in enumerate(gh_projects[:5])
    ) if gh_projects else "> 暂无数据"

    send_wechat(
        f"🧑‍💼 HR Agent Monitor 日报 {TODAY}",
        f"**GitHub** 共发现 **{len(gh_projects)}** 个 HR 相关项目（star>{STAR_THRESHOLD}）\n"
        f"**Skillhub** {len(sh_projects)} 个 | **Clawhub** {len(ch_projects)} 个\n\n"
        f"**🏆 GitHub Top 5**\n{top5}\n\n"
        f"[查看完整报告](https://ffff.avazhang1224.workers.dev/)"
    )

    print("[DONE] 所有任务完成！")


if __name__ == "__main__":
    main()
