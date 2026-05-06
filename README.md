# HR Agent Monitor

🧑‍💼 **自动监控 GitHub、Skillhub、Clawhub 三大渠道的人力资源 AI 相关项目**

[![Daily Update](https://github.com/YOUR_USERNAME/hr-agent-monitor/actions/workflows/daily_update.yml/badge.svg)](https://github.com/YOUR_USERNAME/hr-agent-monitor/actions/workflows/daily_update.yml)

🌐 **在线看板**：https://your-project.pages.dev

---

## 功能特性

- ✅ 每日自动抓取 GitHub HR 相关项目（筛选 star > 200）
- ✅ 监控 Skillhub / Clawhub HR 相关 Skill 和 MCP
- ✅ 生成深度分析报告（语言分布、热门标签、关键词命中）
- ✅ 历史数据归档，可查看每日快照
- ✅ 企业微信机器人每日推送通知
- ✅ Cloudflare Pages 自动部署，每次 push 自动更新

---

## 监控关键词

**GitHub 搜索关键词：**
- human resources AI / HR recruitment AI agent
- talent acquisition AI / resume screening AI
- employee onboarding AI / workforce management AI
- HR chatbot / ATS AI agent / people analytics AI
- performance review AI

**Skillhub / Clawhub 关键词：**
- hr / recruitment / resume / talent
- 人力资源 / 招聘 / 简历

---

## 项目结构

```
hr-agent-monitor/
├── index.html              # 看板主页面
├── data/                   # 自动生成的数据文件
│   ├── github_today.md     # GitHub 今日监控报告
│   ├── skills_today.md     # Skills/MCP 今日监控报告
│   ├── github_history.md   # GitHub 历史归档
│   ├── skills_history.md   # Skills 历史归档
│   └── history.json        # 原始历史数据
├── scripts/
│   └── fetch_hr_projects.py  # 监控抓取脚本
├── .github/
│   └── workflows/
│       └── daily_update.yml  # GitHub Actions 自动化
└── requirements.txt
```

---

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork**，将仓库复制到你的账号下。

### 2. 配置 Secrets

在仓库设置 → **Secrets and variables → Actions** 中添加：

| Secret 名称 | 说明 |
|------------|------|
| `WECHAT_WEBHOOK` | 企业微信机器人 Webhook URL |

> `GITHUB_TOKEN` 是 GitHub Actions 内置的，无需手动配置。

**获取企业微信机器人 Webhook：**
1. 打开企业微信群聊 → 右键 → 「添加机器人」
2. 复制 Webhook URL，粘贴到 Secrets

### 3. 连接 Cloudflare Pages

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages → Create application → Pages**
3. 连接你的 GitHub 仓库
4. 构建设置：
   - **Framework preset**：None
   - **Build command**：（留空）
   - **Build output directory**：`/`
5. 保存，Cloudflare 会自动分配一个 `*.pages.dev` 域名

之后每次 GitHub Actions 推送数据更新，Cloudflare Pages 都会自动重新部署。

### 4. 手动触发第一次更新

在 GitHub 仓库页面 → **Actions** → 「HR Agent Monitor - 每日自动更新」→ **Run workflow**

### 5. 更新看板域名

将 `scripts/fetch_hr_projects.py` 底部的微信通知里的 URL 替换为你的实际 Pages 域名：

```python
f"[查看完整报告](https://your-project.pages.dev/)"
```

---

## 自动化时间表

| 任务 | 时间 |
|------|------|
| 每日自动抓取 | 北京时间 09:00 |
| 微信推送通知 | 抓取完成后立即发送 |
| Cloudflare 部署 | push 后约 1 分钟 |

---

## License

MIT
