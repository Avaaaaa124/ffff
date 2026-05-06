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
def render_github_md(projects: list[dict], title: str) -> str:
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
        f"| 最高 Star | {max((p['stars'] for p in projects), default=0)} |",
        f"| 涉及编程语言 | {len(set(p['language'] for p in projects))} 种 |",
        f"",
        f"---",
        f"",
        f"## 项目列表",
        f"",
        f"| # | 项目 | 描述 | ⭐ Stars | 🍴 Forks | 语言 | 最近更新 |",
        f"|---|------|------|---------|---------|------|---------|",
    ]
    for i, p in enumerate(projects[:80], 1):
        desc = p["description"][:50].replace("|", "｜") if p["description"] else "—"
        topics_str = " ".join(f"`{t}`" for t in p.get("topics", [])[:3])
        lines.append(
            f"| {i} | [{p['name']}]({p['url']}) | {desc} | {p['stars']:,} | {p['forks']:,} | {p['language']} | {p['updated_at']} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## 深度分析",
        f"",
        f"### 📊 语言分布",
        f"",
    ]
    lang_count: dict = {}
    for p in projects:
        lang_count[p["language"]] = lang_count.get(p["language"], 0) + 1
    for lang, cnt in sorted(lang_count.items(), key=lambda x: -x[1])[:10]:
        bar = "█" * min(cnt * 2, 30)
        lines.append(f"- **{lang}**：{cnt} 个项目  `{bar}`")

    lines += [
        f"",
        f"### 🏷️ 热门话题标签",
        f"",
    ]
    topic_count: dict = {}
    for p in projects:
        for t in p.get("topics", []):
            topic_count[t] = topic_count.get(t, 0) + 1
    for topic, cnt in sorted(topic_count.items(), key=lambda x: -x[1])[:15]:
        lines.append(f"- `{topic}` × {cnt}")

    lines += [
        f"",
        f"### 🔍 关键词命中分布",
        f"",
    ]
    kw_count: dict = {}
    for p in projects:
        k = p.get("keyword", "other")
        kw_count[k] = kw_count.get(k, 0) + 1
    for kw, cnt in sorted(kw_count.items(), key=lambda x: -x[1]):
        lines.append(f"- **{kw}**：{cnt} 个")

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
        f"[查看完整报告](https://your-pages-domain.pages.dev/)"
    )

    print("[DONE] 所有任务完成！")


if __name__ == "__main__":
    main()
