# 🚀 部署完整指引 - HR Agent Monitor

## 第一步：推送到 GitHub

### 1.1 在 GitHub 创建新仓库

1. 打开 https://github.com/new
2. 仓库名称填写：`hr-agent-monitor`
3. 可见性选择：**Public**（Cloudflare Pages 免费版需要公开仓库）
4. **不要**勾选 Initialize this repository（我们本地已有代码）
5. 点击「Create repository」

### 1.2 推送本地代码

在终端中执行（替换 `YOUR_USERNAME` 为你的 GitHub 用户名）：

```bash
cd C:\Users\ZHANGXIAOFAN\WorkBuddy\20260506141752\hr-agent-monitor

git remote add origin https://github.com/YOUR_USERNAME/hr-agent-monitor.git
git branch -M main
git push -u origin main
```

---

## 第二步：配置微信通知

### 方案：企业微信机器人

> 适合企业用户，推送效果最佳

**第一步：创建机器人**
1. 打开企业微信，进入一个群聊（或新建专属群）
2. 右键群聊 → 「添加机器人」→「新建机器人」
3. 取名「HR监控助手」，点击「添加机器人」
4. 复制 **Webhook URL**（格式：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`）

**第二步：添加到 GitHub Secrets**
1. 打开你的 GitHub 仓库 → Settings → Secrets and variables → Actions
2. 点击「New repository secret」
3. Name 填写：`WECHAT_WEBHOOK`
4. Value 粘贴刚才复制的 Webhook URL
5. 点击「Add secret」

---

## 第三步：连接 Cloudflare Pages

### 3.1 登录 Cloudflare

打开 https://dash.cloudflare.com/，登录或注册账号（免费账号即可）。

### 3.2 创建 Pages 项目

1. 左侧导航 → **Workers & Pages**
2. 点击「Create application」→「Pages」→「Connect to Git」
3. 授权 GitHub 访问
4. 选择 `hr-agent-monitor` 仓库
5. 点击「Begin setup」

### 3.3 配置构建设置

| 设置项 | 填写内容 |
|--------|---------|
| Production branch | `main` |
| Framework preset | `None` |
| Build command | （**留空**） |
| Build output directory | `/` |

6. 点击「Save and Deploy」

### 3.4 获取你的域名

部署完成后，Cloudflare 会分配一个类似：
```
https://hr-agent-monitor-xxx.pages.dev
```
记录下来，用于更新微信通知的链接。

### 3.5 更新脚本中的看板 URL

编辑 `scripts/fetch_hr_projects.py`，将最后的通知 URL 改为你的实际域名：

```python
f"[查看完整报告](https://hr-agent-monitor-xxx.pages.dev/)"
```

---

## 第四步：手动触发第一次更新

1. 打开 GitHub 仓库 → **Actions** 标签页
2. 左侧选择「HR Agent Monitor - 每日自动更新」
3. 点击「Run workflow」→「Run workflow」
4. 等待约 2-3 分钟执行完毕
5. 刷新你的 Pages 域名，即可看到真实数据

---

## 验证清单

- [ ] GitHub 仓库已创建并推送代码
- [ ] `WECHAT_WEBHOOK` Secret 已配置
- [ ] Cloudflare Pages 已连接仓库
- [ ] 手动触发一次 Actions 确认运行成功
- [ ] 微信收到推送通知
- [ ] 看板页面能正常显示数据

---

## 常见问题

**Q: GitHub Actions 报 403 错误？**
A: 进入仓库 Settings → Actions → General → Workflow permissions，选择「Read and write permissions」

**Q: Cloudflare Pages 报 404？**
A: 确认 Build output directory 设置为 `/`，且 index.html 在仓库根目录

**Q: 微信没收到通知？**
A: 检查 WECHAT_WEBHOOK 的值是否正确，机器人是否仍在群里

**Q: GitHub API 限速（rate limit）？**
A: 确认 GITHUB_TOKEN 已配置，未认证的 API 每小时限 60 次，认证后 5000 次

---

*📅 每天北京时间 09:00 自动更新 | 也可在 GitHub Actions 手动触发*
