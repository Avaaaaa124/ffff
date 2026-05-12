#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Office Skills Monitor - 办公通用技能监控脚本
监控 Skillhub / GitHub 两大渠道的办公通用类 AI 技能与工具
过滤纯开发代码、底层技术、硬件运维等非办公技能
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
STAR_THRESHOLD = 50  # 办公技能 star 阈值可以低一些

# ────────────────────────────────────────────
# 办公通用技能分类体系（一级分类 + 搜索关键词）
# ────────────────────────────────────────────
OFFICE_CATEGORIES = {
    "办公软件与文档处理": {
        "emoji": "📄",
        "keywords": [
            "office document", "document automation",
            "PDF tool", "PDF converter",
            "spreadsheet", "Excel",
            "powerpoint", "slide generator",
            "form builder", "electronic signature",
        ],
    },
    "数据分析与可视化": {
        "emoji": "📊",
        "keywords": [
            "data visualization", "data dashboard",
            "chart generator", "business intelligence",
            "data analysis", "report builder",
            "infographic", "analytics",
        ],
    },
    "演示与信息设计": {
        "emoji": "🎨",
        "keywords": [
            "presentation generator", "slide design",
            "pitch deck", "whiteboard",
            "diagram", "flowchart",
            "visual design",
        ],
    },
    "项目管理与协作": {
        "emoji": "📋",
        "keywords": [
            "project management", "task management",
            "kanban", "Gantt chart",
            "workflow automation", "team productivity",
            "meeting scheduler", "calendar",
        ],
    },
    "文案撰写与内容生成": {
        "emoji": "✍️",
        "keywords": [
            "AI writing", "content writing",
            "email writing", "meeting minutes",
            "document summarization", "grammar",
            "translation",
        ],
    },
    "思维导图与知识管理": {
        "emoji": "🧠",
        "keywords": [
            "mind map", "knowledge management",
            "note taking", "brainstorming",
            "wiki", "documentation",
        ],
    },
    "流程优化与自动化": {
        "emoji": "⚙️",
        "keywords": [
            "RPA", "no-code automation",
            "workflow automation", "office automation",
            "Zapier", "automation platform",
        ],
    },
    "协同办公与沟通": {
        "emoji": "💬",
        "keywords": [
            "team collaboration", "video conference",
            "CRM", "helpdesk",
            "email management", "remote work",
            "file sharing",
        ],
    },
    "表格处理与报表": {
        "emoji": "📈",
        "keywords": [
            "invoice", "survey", "timesheet",
            "expense", "budget",
            "report dashboard",
        ],
    },
    "AI 办公工具": {
        "emoji": "🤖",
        "keywords": [
            "AI assistant office", "AI productivity",
            "AI copilot", "AI secretary",
            "ChatGPT workflow",
        ],
    },
}

# 从分类中提取搜索关键词列表
OFFICE_SKILL_KEYWORDS = []
_KW_TO_CATEGORY = {}
for _cat_name, _cat_info in OFFICE_CATEGORIES.items():
    for _kw in _cat_info["keywords"]:
        OFFICE_SKILL_KEYWORDS.append(_kw)
        _KW_TO_CATEGORY[_kw] = _cat_name

# ────────────────────────────────────────────
# 办公技能相关性过滤器
# ────────────────────────────────────────────

# 白名单：名称/描述/标签中包含这些词，视为办公通用
OFFICE_WHITELIST_WORDS = [
    # 办公文档
    "document", "spreadsheet", "presentation", "slide", "PDF",
    "word", "excel", "powerpoint", "ppt", "office", "docx", "xlsx",
    "form", "template", "report", "dashboard", "chart", "graph",
    # 数据
    "data visualization", "data analysis", "analytics", "statistics",
    "pivot table", "infographic", "chart maker",
    # 项目管理
    "project management", "task management", "kanban", "gantt",
    "sprint", "workflow", "standup", "agile", "scrum", "todo",
    # 协作
    "collaboration", "team", "meeting", "calendar", "schedule",
    "communication", "messaging", "video conference", "webinar",
    # 文案
    "writing", "copywriting", "email", "newsletter", "blog",
    "meeting minutes", "meeting notes", "summarization", "summary",
    "translation", "grammar", "proofreading", "writing assistant",
    # 知识管理
    "mind map", "mind mapping", "knowledge base", "knowledge management",
    "note taking", "brainstorm", "wiki", "outline",
    # 自动化
    "automation", "RPA", "no-code", "low-code", "zapier", "workflow automation",
    "process automation", "task automation",
    # 表格/报表
    "timesheet", "invoice", "receipt", "expense", "budget",
    "survey", "questionnaire", "poll", "feedback",
    "inventory", "stock", "tracker",
    # AI办公
    "AI assistant", "AI copilot", "productivity", "office AI",
    "AI secretary", "AI scheduler",
    # 其他办公
    "whiteboard", "diagram", "flowchart", "wireframe",
    "electronic signature", "digital signature", "e-signature",
    "file converter", "PDF converter", "file sharing",
    "CRM", "helpdesk", "customer support", "ticket",
    "remote work", "virtual office", "screen sharing",
]

# 黑名单：包含这些词视为非办公技能，直接排除
OFFICE_BLACKLIST_WORDS = [
    # 编程/开发
    "code editor", "IDE", "compiler", "debugger", "code review",
    "docker", "kubernetes", "terraform", "ansible",
    "CI/CD", "devops", "infrastructure as code",
    "web framework", "backend", "frontend", "full stack",
    "API gateway", "microservice", "serverless",
    "database administration", "DBA", "SQL optimizer",
    # 底层技术
    "kernel", "driver", "firmware", "embedded system",
    "network protocol", "packet capture", "reverse engineering",
    "blockchain", "cryptocurrency", "smart contract", "defi", "NFT",
    # 硬件运维
    "hardware", "networking", "server management", "data center",
    "system admin", "linux server", "cloud infrastructure",
    "GPU driver", "CUDA", "CUDA programming",
    # 游戏/娱乐
    "gaming", "minecraft", "roblox", "game engine", "game mod",
    "streaming", "twitch", "youtube bot",
    # 金融/交易（非办公报表）
    "algorithmic trading", "day trading", "forex", "crypto trading",
    "stock trading bot", "quantitative trading", "arbitrage bot",
    "stock analysis", "stock market", "financial market", "trading",
    "investment", "portfolio", "fund", "hedge", "dividend",
    # 网络安全/渗透
    "penetration testing", "vulnerability scanner", "exploit",
    "malware analysis", "cybersecurity tool",
    # AI 基础设施（非办公场景）
    "LLM training", "model training", "fine-tuning", "dataset",
    "ollama", "local LLM", "language model management",
    "Hugging Face model", "model deployment",
    # 电商
    "amazon seller", "shopify", "dropshipping", "product sourcing",
    "SEO tool", "backlink", "serp analyzer",
    # 其他非办公
    "weather", "recipe", "cooking", "travel booking",
    "flight tracker", "hotel booking", "dating",
    "social media bot", "reddit bot", "twitter bot",
    "web scraping", "web crawler", "proxy",
    "VPN", "ad blocker",
    "HR", "human resource", "payroll", "recruit",
    "ATS", "applicant tracking", "resume parser",
]

# 模糊词（单独出现不够，需要上下文）
OFFICE_AMBIGUOUS_WORDS = {
    "tool", "platform", "system", "dashboard", "automation",
    "assistant", "generator", "builder", "manager", "converter",
    "editor", "tracker", "analyzer", "processor",
}


def _is_office_related(item: dict) -> bool:
    """判断一个 Skill/项目是否属于办公通用类"""
    name = (item.get("name") or "").lower()
    desc = (item.get("description") or item.get("description_zh") or "").lower()
    tags = " ".join(item.get("tags") or []).lower()
    text = f"{name} {desc} {tags}"

    # 1. 黑名单优先：命中任一黑名单词直接排除
    for bw in OFFICE_BLACKLIST_WORDS:
        if bw.lower() in text:
            return False

    # 2. 白名单：命中任一白名单词视为办公相关
    for ww in OFFICE_WHITELIST_WORDS:
        if ww.lower() in text:
            return True

    # 3. 模糊词：需要与办公上下文词同现
    office_context = [
        "office", "document", "spreadsheet", "slide", "presentation",
        "report", "chart", "data", "team", "meeting", "calendar",
        "task", "project", "workflow", "writing", "note", "mind map",
        "form", "email", "automation", "productivity", "schedule",
        "invoice", "survey", "collaboration", "communication",
    ]
    for aw in OFFICE_AMBIGUOUS_WORDS:
        if aw in text:
            for ctx in office_context:
                if ctx in text:
                    return True
            return False

    return False


def _classify_office_skill(item: dict) -> str:
    """根据关键词匹配给办公技能分类"""
    name = (item.get("name") or "").lower()
    desc = (item.get("description") or item.get("description_zh") or "").lower()
    tags = " ".join(item.get("tags") or []).lower()
    text = f"{name} {desc} {tags}"

    for cat_name, cat_info in OFFICE_CATEGORIES.items():
        for kw in cat_info["keywords"]:
            if kw.lower() in text:
                return cat_name
    return "AI 办公工具"  # 默认归入 AI 办公工具


# ────────────────────────────────────────────
# GitHub 搜索查询（办公通用技能）
# ────────────────────────────────────────────
GITHUB_SEARCH_QUERIES = [
    # 办公文档与 PDF
    "document+automation+tool stars:>50",
    "PDF+generator+converter stars:>50",
    "spreadsheet+automation+Excel stars:>50",
    "powerpoint+slide+generator stars:>50",
    "electronic+signature+document stars:>50",
    # 数据分析与可视化
    "data+visualization+dashboard stars:>50",
    "chart+generator+infographic stars:>50",
    "business+intelligence+report stars:>50",
    # 项目管理与协作
    "project+management+tool stars:>50",
    "kanban+task+management stars:>50",
    "workflow+automation+tool stars:>50",
    # 文案撰写
    "AI+writing+assistant stars:>50",
    "meeting+minutes+summarization stars:>50",
    # 知识管理
    "mind+map+knowledge+base stars:>50",
    "note+taking+wiki stars:>50",
    # 协同办公
    "team+collaboration+CRM stars:>50",
    "video+conference+calendar stars:>50",
    # 流程自动化
    "no-code+automation+RPA stars:>50",
    # 表格报表
    "invoice+survey+timesheet stars:>50",
    # AI办公
    "AI+office+productivity+copilot stars:>50",
]


# ────────────────────────────────────────────
# 翻译相关
# ────────────────────────────────────────────
_KNOWN_OFFICE_DESC_ZH = {
    # 常见办公项目手动翻译
}


def _is_chinese(text: str) -> bool:
    if not text:
        return True
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff') > len(text) * 0.3


def _translate_via_api(text: str) -> str:
    try:
        short_text = text[:480] if len(text) > 480 else text
        url = "https://api.mymemory.translated.net/get"
        resp = requests.get(url, params={"q": short_text, "langpair": "en|zh-CN"}, timeout=10)
        if resp.status_code == 200:
            result = resp.json().get("responseData", {}).get("translatedText", "")
            if result and _is_chinese(result) and not result.upper().startswith(("QUERY", "MYMEMORY")):
                return result.strip()
    except Exception:
        pass
    return text


_translate_cache: dict[str, str] = {}


def translate_description(text: str) -> str:
    if not text or _is_chinese(text):
        return text or ""
    if text in _translate_cache:
        return _translate_cache[text]
    result = _translate_via_api(text)
    _translate_cache[text] = result
    return result


# ────────────────────────────────────────────
# 路径配置
# ────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TODAY = datetime.date.today().isoformat()
OFFICE_SKILLS_MD = DATA_DIR / "office_skills_today.md"
OFFICE_GITHUB_MD = DATA_DIR / "office_github_today.md"
OFFICE_HISTORY_MD = DATA_DIR / "office_history.md"
OFFICE_HISTORY_JSON = DATA_DIR / "office_history.json"


# ────────────────────────────────────────────
# Skillhub 抓取（办公技能）
# ────────────────────────────────────────────
SKILL_PAGE_SIZE = 50
SKILL_MAX_PER_KW = 80


def fetch_skillhub_office() -> list[dict]:
    """从 Skillhub API 搜索办公通用技能"""
    results = []
    seen = set()
    base_url = "https://api.skillhub.cn/api/skills"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://skillhub.cn/",
    }

    total_fetched = 0
    total_filtered = 0

    for kw in OFFICE_SKILL_KEYWORDS:
        category = _KW_TO_CATEGORY.get(kw, "")
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
                    break

                data = resp.json()
                if data.get("code") != 0:
                    break

                skills = data.get("data", {}).get("skills", [])
                if not skills:
                    break

                for item in skills:
                    slug = item.get("slug", "")
                    if slug and slug not in seen:
                        seen.add(slug)
                        desc = item.get("description_zh") or item.get("description") or ""
                        skill_data = {
                            "name": item.get("name") or slug,
                            "slug": slug,
                            "url": item.get("homepage") or f"https://skillhub.cn/skills/{slug}",
                            "description": desc,
                            "description_zh": desc,
                            "stars": item.get("stars") or 0,
                            "downloads": item.get("downloads") or 0,
                            "installs": item.get("installs") or 0,
                            "category": item.get("category") or "",
                            "office_category": "",
                            "source": item.get("source") or "unknown",
                            "tags": item.get("tags") or [],
                            "ownerName": item.get("ownerName") or "",
                            "keyword": kw,
                        }
                        total_fetched += 1

                        # 二次过滤：只保留办公通用
                        if not _is_office_related(skill_data):
                            total_filtered += 1
                            continue

                        # 分类
                        skill_data["office_category"] = _classify_office_skill(skill_data)
                        results.append(skill_data)

                fetched += len(skills)
                page += 1

                if len(skills) < SKILL_PAGE_SIZE:
                    break

                time.sleep(0.3)

        except Exception as e:
            print(f"  [WARN] Skillhub 搜索异常 ({kw}): {e}")

    print(f"  Skillhub 抓取: {total_fetched} 个 → 过滤后: {len(results)} 个 (过滤掉 {total_filtered} 个非办公)")

    results.sort(key=lambda x: x.get("downloads", 0) + x.get("installs", 0) * 2 + x.get("stars", 0) * 3, reverse=True)
    return results


# ────────────────────────────────────────────
# GitHub 抓取（办公技能）
# ────────────────────────────────────────────
def fetch_github_office() -> list[dict]:
    """从 GitHub Search API 搜索办公通用工具"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    results = []
    seen = set()
    total_filtered = 0

    for query in GITHUB_SEARCH_QUERIES:
        page = 1
        for _ in range(2):  # 每个查询最多 2 页
            try:
                url = "https://api.github.com/search/repositories"
                params = {"q": query, "sort": "stars", "order": "desc", "per_page": 30, "page": page}
                resp = requests.get(url, params=params, headers=headers, timeout=15)

                if resp.status_code == 403:
                    print("  [WARN] GitHub API 速率限制，暂停 60 秒...")
                    time.sleep(60)
                    continue
                if resp.status_code != 200:
                    print(f"  [WARN] GitHub API {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    full_name = item.get("full_name", "")
                    if full_name in seen:
                        continue
                    seen.add(full_name)

                    proj = {
                        "name": full_name,
                        "url": item.get("html_url", ""),
                        "description": item.get("description") or "",
                        "desc_zh": "",
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "language": item.get("language") or "",
                        "topics": item.get("topics") or [],
                        "updated_at": item.get("updated_at", "")[:10],
                        "office_category": "",
                    }

                    # 过滤
                    if not _is_office_related(proj):
                        total_filtered += 1
                        continue

                    # 分类
                    proj["office_category"] = _classify_office_skill(proj)
                    results.append(proj)

                page += 1
                time.sleep(2)  # GitHub API 限速

            except Exception as e:
                print(f"  [WARN] GitHub 搜索异常 ({query}): {e}")
                break

    # 去重（同名项目保留 star 最高的）
    deduped = {}
    for p in results:
        key = p["name"].lower()
        if key not in deduped or p["stars"] > deduped[key]["stars"]:
            deduped[key] = p

    results = list(deduped.values())

    # 翻译描述
    print(f"  GitHub 抓取: 过滤后 {len(results)} 个 (过滤掉 {total_filtered} 个非办公)")
    print(f"  正在翻译 GitHub 项目描述...")
    for i, p in enumerate(results):
        desc = p.get("description") or ""
        if desc and not _is_chinese(desc):
            p["desc_zh"] = translate_description(desc)
        else:
            p["desc_zh"] = desc
        if i < len(results) - 1:
            time.sleep(0.6)

    results.sort(key=lambda x: x["stars"], reverse=True)
    return results


# ────────────────────────────────────────────
# 渲染函数
# ────────────────────────────────────────────
def render_office_skills_md(skills: list[dict], title: str) -> str:
    """渲染办公技能今日报告"""
    lines = [
        f"# {title}",
        "",
        f"> 更新时间：{TODAY}　|　数据来源：Skillhub",
        "",
        "---",
        "",
    ]

    # 汇总
    total_downloads = sum(s.get("downloads", 0) for s in skills)
    total_installs = sum(s.get("installs", 0) for s in skills)

    lines += [
        f"| 统计项 | 数值 |",
        f"|--------|------|",
        f"| 技能总数 | **{len(skills)}** |",
        f"| 总下载量 | {total_downloads:,} |",
        f"| 总安装量 | {total_installs:,} |",
        "",
    ]

    # 按分类分组
    for cat_name, cat_info in OFFICE_CATEGORIES.items():
        emoji = cat_info["emoji"]
        cat_items = [s for s in skills if s.get("office_category") == cat_name]
        if not cat_items:
            continue
        lines.append(f"### {emoji} {cat_name}（{len(cat_items)} 个）")
        lines.append("")
        lines.append(f"| # | 技能名称 | 描述 | 热度 | 下载 |")
        lines.append(f"|---|---------|------|------|------|")
        for i, s in enumerate(cat_items[:20], 1):
            desc = (s.get("description_zh") or s.get("description") or "—")[:60].replace("|", "｜")
            heat = s.get("downloads", 0) + s.get("installs", 0) * 2 + s.get("stars", 0) * 3
            dl = s.get("downloads", 0)
            lines.append(f"| {i} | [{s['name']}]({s['url']}) | {desc} | 🔥{heat} | ⬇️{dl} |")
        lines.append("")

    # 嵌入 JSON 供前端卡片
    import json as _json
    skills_light = []
    for s in skills[:200]:
        skills_light.append({
            "name": s.get("name") or s.get("slug") or "",
            "slug": s.get("slug", ""),
            "url": s.get("url") or "",
            "desc": (s.get("description_zh") or s.get("description") or "")[:120],
            "downloads": s.get("downloads", 0),
            "installs": s.get("installs", 0),
            "stars": s.get("stars", 0),
            "heat": s.get("downloads", 0) + s.get("installs", 0) * 2 + s.get("stars", 0) * 3,
            "source": s.get("source", ""),
            "tags": (s.get("tags") or [])[:5],
            "keyword": s.get("keyword", ""),
            "office_category": s.get("office_category", ""),
        })
    json_block = _json.dumps({"office_skills": skills_light}, ensure_ascii=False)
    lines.append(f"<!-- OFFICE_SKILL_DATA:{json_block}:OFFICE_SKILL_DATA -->")

    lines.append(f"\n---\n\n*由 Office Skills Monitor 自动生成 · {TODAY}*")
    return "\n".join(lines)


def render_office_github_md(projects: list[dict], title: str) -> str:
    """渲染办公工具 GitHub 今日报告"""
    lines = [
        f"# {title}",
        "",
        f"> 更新时间：{TODAY}　|　Star 阈值 > {STAR_THRESHOLD}",
        "",
    ]

    top_stars = max((p["stars"] for p in projects), default=0)
    lines += [
        f"| 统计项 | 数值 |",
        f"|--------|------|",
        f"| 项目总数 | **{len(projects)}** |",
        f"| 最高 Star | {top_stars:,} |",
        "",
        "---",
        "",
    ]

    # Top 20 表格
    lines += [
        f"| # | 项目 | ⭐ Stars | 简介 |",
        f"|---|------|---------|------|",
    ]
    for i, p in enumerate(projects[:20], 1):
        desc = (p.get("desc_zh") or p.get("description") or "暂无简介")[:60]
        if len(p.get("desc_zh") or p.get("description") or "") > 60:
            desc += "..."
        lines.append(f"| {i} | [{p['name']}]({p['url']}) | {p['stars']:,} | {desc} |")
    lines.append("")

    # 嵌入 JSON
    import json as _json
    projects_light = []
    for p in projects:
        projects_light.append({
            "name": p["name"],
            "url": p["url"],
            "desc": (p.get("description") or "")[:120],
            "desc_zh": (p.get("desc_zh") or "")[:120],
            "stars": p["stars"],
            "forks": p.get("forks", 0),
            "language": p.get("language", ""),
            "topics": (p.get("topics") or [])[:5],
            "updated_at": p.get("updated_at", ""),
            "office_category": p.get("office_category", ""),
        })
    json_block = _json.dumps(projects_light, ensure_ascii=False)
    lines.append(f"<!-- OFFICE_GITHUB_DATA:{json_block}:OFFICE_GITHUB_DATA -->")

    lines.append(f"\n---\n\n*由 Office Skills Monitor 自动生成 · {TODAY}*")
    return "\n".join(lines)


# ────────────────────────────────────────────
# 历史记录
# ────────────────────────────────────────────
def load_history() -> dict:
    if OFFICE_HISTORY_JSON.exists():
        return json.loads(OFFICE_HISTORY_JSON.read_text(encoding="utf-8"))
    return {}


def save_history(history: dict) -> None:
    OFFICE_HISTORY_JSON.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def render_office_history_md(history: dict) -> str:
    """渲染办公技能历史记录"""
    lines = [
        "# 📚 办公技能历史记录",
        "",
        "> 每日快照归档，按日期倒序",
        "",
    ]
    for date in sorted(history.keys(), reverse=True):
        entry = history[date]
        skills_count = len(entry.get("skillhub_skills", []))
        github_count = len(entry.get("github_projects", []))
        lines += [
            f"## {date}",
            "",
            f"Skillhub 办公技能：{skills_count} 个　|　GitHub 办公工具：{github_count} 个",
            "",
        ]

        # Skillhub Top 20
        sh = entry.get("skillhub_skills", [])
        if sh:
            sorted_sh = sorted(sh, key=lambda x: x.get("downloads", 0) + x.get("installs", 0) * 2 + x.get("stars", 0) * 3, reverse=True)[:20]
            lines.append(f"### Skillhub Top 20")
            lines.append("")
            lines.append(f"| 技能名称 | ⭐ Stars | 简介 |")
            lines.append(f"|---------|---------|------|")
            for s in sorted_sh:
                desc = (s.get("description_zh") or s.get("description") or "暂无简介")[:60]
                if len(s.get("description_zh") or s.get("description") or "") > 60:
                    desc += "..."
                lines.append(f"| [{s.get('name', '—')}]({s.get('url', '#')}) | {s.get('stars', 0)} | {desc} |")
            lines.append("")

        # GitHub Top 20
        gh = entry.get("github_projects", [])
        if gh:
            sorted_gh = sorted(gh, key=lambda x: x.get("stars", 0), reverse=True)[:20]
            lines.append(f"### GitHub Top 20")
            lines.append("")
            lines.append(f"| 项目 | ⭐ Stars | 简介 |")
            lines.append(f"|------|---------|------|")
            for p in sorted_gh:
                desc = (p.get("desc_zh") or p.get("description") or "暂无简介")[:60]
                if len(p.get("desc_zh") or p.get("description") or "") > 60:
                    desc += "..."
                lines.append(f"| [{p['name']}]({p['url']}) | {p['stars']:,} | {desc} |")
            lines.append("")

    lines.append(f"\n---\n\n*由 Office Skills Monitor 自动生成*")
    return "\n".join(lines)


# ────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────
def main():
    print(f"[{TODAY}] 开始办公技能监控抓取...")

    # 1. 抓取 Skillhub 办公技能
    print("  → 抓取 Skillhub 办公技能...")
    sh_skills = fetch_skillhub_office()
    print(f"     Skillhub: {len(sh_skills)} 个办公技能")

    # 2. 抓取 GitHub 办公工具
    print("  → 抓取 GitHub 办公工具...")
    gh_projects = fetch_github_office()
    print(f"     GitHub: {len(gh_projects)} 个项目")

    # 3. 生成今日报告
    sh_md = render_office_skills_md(sh_skills, f"🛠️ 办公通用技能监控 · {TODAY}")
    gh_md = render_office_github_md(gh_projects, f"⭐ 办公工具 GitHub 监控 · {TODAY}")

    OFFICE_SKILLS_MD.write_text(sh_md, encoding="utf-8")
    OFFICE_GITHUB_MD.write_text(gh_md, encoding="utf-8")
    print("  → 今日报告已写入")

    # 4. 更新历史
    history = load_history()
    history[TODAY] = {
        "skillhub_skills": sh_skills,
        "github_projects": gh_projects,
    }
    save_history(history)
    OFFICE_HISTORY_MD.write_text(render_office_history_md(history), encoding="utf-8")
    print("  → 历史记录已更新")

    print("[DONE] 办公技能监控完成！")


if __name__ == "__main__":
    main()
