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
from pathlib import Path

# ────────────────────────────────────────────
# 配置区
# ────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
WECHAT_WEBHOOK = os.environ.get("WECHAT_WEBHOOK", "")   # 企业微信机器人 Webhook
STAR_THRESHOLD = 200

# HR 相关关键词（GitHub 搜索用）
HR_KEYWORDS = [
    "human resources AI",
    "HR recruitment AI agent",
    "talent acquisition AI",
    "resume screening AI",
    "employee onboarding AI",
    "workforce management AI",
    "HR chatbot",
    "ATS AI agent",
    "people analytics AI",
    "performance review AI",
]

# Skillhub / Clawhub 搜索关键词
SKILL_KEYWORDS = ["hr", "recruitment", "resume", "talent", "人力资源", "招聘", "简历"]

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
# 工具函数
# ────────────────────────────────────────────
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

    for kw in HR_KEYWORDS:
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"{kw} stars:>{STAR_THRESHOLD}",
            "sort": "stars",
            "order": "desc",
            "per_page": 20,
        }
        try:
            resp = requests.get(url, headers=gh_headers(), params=params, timeout=15)
            if resp.status_code == 403:
                print(f"[WARN] GitHub API 限速，关键词: {kw}")
                time.sleep(10)
                continue
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
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
                        "keyword": kw,
                    })
        except Exception as e:
            print(f"[ERROR] GitHub 搜索异常 ({kw}): {e}")
        time.sleep(1.2)  # 避免触发速率限制

    # 按 star 降序
    results.sort(key=lambda x: x["stars"], reverse=True)
    return results


# ────────────────────────────────────────────
# Skillhub 抓取
# ────────────────────────────────────────────
def fetch_skillhub_projects() -> list[dict]:
    """从 Skillhub 搜索 HR 相关 skill"""
    results = []
    seen = set()
    base_url = "https://skillhub.dev/api/skills/search"

    for kw in SKILL_KEYWORDS:
        try:
            resp = requests.get(base_url, params={"q": kw, "limit": 30}, timeout=15)
            if resp.status_code != 200:
                # 尝试备用接口路径
                resp = requests.get(
                    f"https://skillhub.dev/api/search",
                    params={"keyword": kw},
                    timeout=15,
                )
            if resp.status_code == 200:
                items = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])
                for item in items:
                    name = item.get("name") or item.get("title") or ""
                    if name and name not in seen:
                        seen.add(name)
                        results.append({
                            "name": name,
                            "url": item.get("url") or item.get("link") or f"https://skillhub.dev/skills/{name}",
                            "description": item.get("description") or "",
                            "stars": item.get("stars") or item.get("downloads") or 0,
                            "category": item.get("category") or "HR",
                            "keyword": kw,
                        })
        except Exception as e:
            print(f"[WARN] Skillhub 搜索异常 ({kw}): {e}")
        time.sleep(0.8)

    # Skillhub 无 star 数据时按名称展示
    results.sort(key=lambda x: x.get("stars", 0), reverse=True)
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
    """根据描述关键词给项目分类标签"""
    desc_lower = (p.get("description") or "").lower()
    name_lower = (p.get("name") or "").lower()
    text = desc_lower + " " + name_lower
    mapping = [
        (["resume", "cv", "resume screening"],          "📄 简历/简历筛选"),
        (["recruit", "talent acquisition", "sourc"],    "🎯 招聘/人才获取"),
        (["chatbot", "conversational", "assistant"],     "🤖 HR 聊天机器人"),
        (["onboard", "employee experience", "hcm"],      "👥 入职/员工管理"),
        (["analytics", "insight", "people analyt"],       "📊 人力数据分析"),
        (["performance", "review", "evaluation"],         "📝 绩效管理"),
        (["payroll", "compensation", "salary", "benefit"],"💰 薪酬/福利"),
        (["ats", "applicant track"],                      "📋 ATS 招聘管理"),
        (["interview", "schedule", "assessment"],         "🎙️ 面试/评估"),
        (["llm", "gpt", "transformer", "nlp"],            "🧠 AI/NLP 基础"),
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

    # ── 项目列表（卡片式） ──
    lines += [f"## 项目监控", f""]
    for i, p in enumerate(projects[:80], 1):
        desc = p["description"] or "暂无简介"
        level = _star_level(p["stars"])
        category = _classify_project(p)
        lines += [
            f"### {i}. {p['name']}",
            f"",
            f"| 属性 | 详情 |",
            f"|------|------|",
            f"| ⭐ Stars | **{p['stars']:,}** |",
            f"| 🍴 Forks | {p['forks']:,} |",
            f"| 💻 语言 | {p['language']} |",
            f"| 📅 最近更新 | {p['updated_at']} |",
            f"| 🏷️ 分类 | {category} |",
            f"| 📊 等级 | {level} |",
            f"| 🔗 链接 | [{p['url']}]({p['url']}) |",
            f"",
            f"> {desc}",
            f"",
        ]

    # ── 深度分析 ──
    lines += [f"---", f"", f"## 深度分析", f""]

    # ── 1. 重点项目分析 ──
    lines += [f"### 🔍 重点项目分析", f""]
    if projects:
        top10 = projects[:10]
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
        lines.append(f"- [{p['name']}]({p['url']}) — ⭐{p['stars']:,}　|　更新于 {p['updated_at']}")
    lines.append("")

    # 高 Fork 项目（社区参与度高）
    high_fork = sorted(projects, key=lambda x: x["forks"], reverse=True)[:5]
    lines += [f"#### 社区参与度 Top 5（按 Fork）", f""]
    for p in high_fork:
        lines.append(f"- [{p['name']}]({p['url']}) — 🍴{p['forks']:,}　|　⭐{p['stars']:,}")
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
    lines = [
        f"# {title}",
        f"",
        f"> 更新时间：{TODAY}　｜　来源：Skillhub + Clawhub",
        f"",
    ]

    # Skillhub
    lines += [
        f"## 🛠️ Skillhub HR Skill",
        f"",
        f"共 **{len(skillhub)}** 个匹配项",
        f"",
        f"| # | Skill 名称 | 描述 | 分类 | 关键词 |",
        f"|---|-----------|------|------|-------|",
    ]
    for i, p in enumerate(skillhub[:50], 1):
        desc = p["description"][:50].replace("|", "｜") if p["description"] else "—"
        lines.append(f"| {i} | [{p['name']}]({p['url']}) | {desc} | {p.get('category','—')} | {p.get('keyword','—')} |")

    # Clawhub
    lines += [
        f"",
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
