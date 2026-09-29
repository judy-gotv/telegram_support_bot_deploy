# APTV Support Bot 说明文档

> **版本切换**：[JS 版（Cloudflare Worker）](#js-版部署cloudflare-worker) ｜ [PY 版（VPS + FastAPI）](#py-版部署vps--fastapi)

Telegram 工单机器人：用户私聊 bot 提交问题 / 申请解封，管理员在私聊中统一处理。

## 版本对比

| 功能 | JS 版 | PY 版 |
|---|---|---|
| 用户命令 `/start` `/send` `/unban` `/help` | ✅ | ✅ |
| 管理员引用工单消息直接回复 | ✅ | ❌ |
| `/reply` `/say` 命令回复 | ✅ | ✅（仅 `/reply`） |
| `/unban` 绑定群自动解封（QUNID） | ✅ | ❌ |
| 部署方式 | Cloudflare Worker（免服务器） | VPS + FastAPI + Nginx + systemd |

---

## 功能说明（通用）

### 用户侧

用户私聊 Bot 后可使用：

```text
/start
/send 你好，我的线路有问题
/unban
/help
```

为防止广告轰炸，直接发文字（不带 `/send`）会被提示使用 `/send` 指令发送。

### 管理员侧

管理员会收到类似通知：

```text
新的工单消息
用户ID：123456789
昵称：Judy
用户名：@abc

内容：
你好，我的线路有问题

回复方式（二选一）：
1. 直接引用这条消息，输入回复内容发送（推荐）
2. /reply 123456789 你的回复内容
```

**方式一：引用回复（仅 JS 版）** — 直接引用（Reply）这条通知消息，输入回复内容发送，bot 自动解析用户 ID。发送成功后管理员收到「已发送（用户ID：xxx）」确认。

**方式二：命令回复** — `/reply 123456789 已收到，我帮你检查一下`，用户收到：

```text
技术支持回复：
已收到，我帮你检查一下
```

`/say 用户ID 消息内容`（仅 JS 版）— 原样发送消息给用户，无「技术支持回复：」前缀。

### `/unban` 自动解封（仅 JS 版，需配置 QUNID）

用户发送 `/unban` 后：

1. 未设置 `QUNID` → 通知管理员手动处理
2. 已设置 `QUNID` → bot 查询该用户在绑定群中的状态：
   - 被封禁（kicked）→ **自动解封**，用户收到"已自动为你解除封禁"，管理员收到一条"已自动解封"记录，全程无需手动操作
   - 禁言中（restricted）→ 转管理员手动解除禁言
   - 未被封禁 → 告知用户当前没有被封禁，并转管理员确认
   - 查询/解封接口失败 → 转管理员手动处理，并附带失败原因

前提：bot 必须是绑定群的**管理员**且拥有「封禁用户」权限；解封后用户需自己重新加入群组。

---

## JS 版部署（Cloudflare Worker）

### 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `BOT_TOKEN` | 是 | Bot Token |
| `ADMIN_CHAT_ID` | 是 | 管理员的 Telegram 用户 ID（数字） |
| `TELEGRAM_SECRET_TOKEN` | 否 | Webhook 校验密钥 |
| `SETUP_SECRET` | 否 | `/telegram/setup` 与 `/telegram/status` 接口的访问密钥 |
| `QUNID` | 否 | 绑定的群组 ID（例如 `-1002176362246`），用于 `/unban` 自动解封 |

### 接口

- `GET /` — 健康检查
- `/telegram/setup?secret=xxx` — 设置 Webhook + 注册命令菜单
- `/telegram/status?secret=xxx` — 查看 bot 信息与 Webhook 状态
- `POST /telegram/webhook` — Telegram 消息回调（仅处理私聊）

### 部署步骤

```bash
# 1. 安装 wrangler 并登录
npm install -g wrangler
wrangler login

# 2. 进入项目目录，配置 wrangler.toml 后部署
wrangler deploy

# 3. 设置环境变量（敏感值用 secret）
wrangler secret put BOT_TOKEN
wrangler secret put ADMIN_CHAT_ID
wrangler secret put SETUP_SECRET
# 可选：自动解封
wrangler secret put QUNID

# 4. 设置 Webhook（把 <你的域名> 换成 Worker 域名）
curl "https://<你的域名>/telegram/setup?secret=你的SETUP_SECRET"

# 5. 检查状态
curl "https://<你的域名>/telegram/status?secret=你的SETUP_SECRET"
```

### 异常处理

- 处理消息时抛出异常 → 自动通知管理员「机器人处理异常：xxx」
- 发消息失败 → 返回失败原因，不静默丢弃

---

## PY 版部署（VPS + FastAPI）

### 目录结构

在服务器创建目录：

```bash
mkdir -p /root/support-bot
cd /root/support-bot
```

建议目录结构如下：

```text
/root/support-bot/
├─ app.py
├─ requirements.txt
├─ .env
└─ support-bot.service
```

### requirements.txt

```text
fastapi
uvicorn
requests
python-dotenv
```

### .env

把下面内容改成你自己的：

```env
BOT_TOKEN=你的BOT_TOKEN
ADMIN_CHAT_ID=你的私聊chat_id
```

### 本地测试

安装依赖：

```bash
cd /root/support-bot
pip install -r requirements.txt
```

启动：

```bash
export $(cat .env | xargs)
uvicorn app:app --host 127.0.0.1 --port 8000
```

访问健康检查：

```text
http://127.0.0.1:8000/
```

如果正常，会返回：

```json
{"ok":true,"service":"support-bot"}
```

### 配置 Nginx

假设你的域名是：

```text
bot.example.com
```

新建配置：

```bash
nano /etc/nginx/conf.d/support-bot.conf
```

内容如下：

```nginx
server {
    listen 80;
    server_name bot.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

测试并重载：

```bash
nginx -t
systemctl reload nginx
```

### 配置 HTTPS

如果已安装 certbot：

```bash
certbot --nginx -d bot.example.com
```

### 设置 Telegram Webhook

执行：

```bash
curl "https://api.telegram.org/bot你的BOT_TOKEN/setWebhook?url=https://bot.example.com/telegram/webhook"
```

查看状态：

```bash
curl "https://api.telegram.org/bot你的BOT_TOKEN/getWebhookInfo"
```

### 配置 systemd 开机自启

创建服务文件：

```bash
nano /etc/systemd/system/support-bot.service
```

内容如下：

```ini
[Unit]
Description=Telegram Support Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/support-bot
EnvironmentFile=/root/support-bot/.env
ExecStart=/usr/local/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
systemctl daemon-reload
systemctl enable support-bot
systemctl start support-bot
systemctl status support-bot
```

查看日志：

```bash
journalctl -u support-bot -f
```

### 获取 ADMIN_CHAT_ID

你必须先用自己的 Telegram 账号私聊 Bot 一次，发送：

```text
/start
```

然后执行：

```bash
curl "https://api.telegram.org/bot你的BOT_TOKEN/getUpdates"
```

返回里找到类似：

```json
"chat":{"id":123456789,"first_name":"xxx","type":"private"}
```

这里的 `id` 就是你的 `ADMIN_CHAT_ID`。

### BotFather 建议设置

你可以通过 `@BotFather` 进一步设置机器人信息：

```text
/setname
/setdescription
/setabouttext
/setuserpic
```

建议：

**名称**
```text
APTV - 技术支持
```

**简介**
```text
这是APTV官方的技术支持机器人，您可以通过该Bot联系到APTV的开发者。
```

### 最短部署流程

```bash
mkdir -p /root/support-bot && cd /root/support-bot
pip install -r requirements.txt
export $(cat .env | xargs)
uvicorn app:app --host 127.0.0.1 --port 8000
```

然后：

1. 配置 Nginx
2. 配置 HTTPS
3. 设置 Webhook
4. 配置 systemd

---

## 常见问题

### 1）用户收不到回复

先确认：

- 用户是否先私聊过 Bot
- `BOT_TOKEN` 是否正确
- `ADMIN_CHAT_ID` 是否正确
- Webhook 是否设置成功

### 2）Webhook 没反应

检查：

```bash
curl "https://api.telegram.org/bot你的BOT_TOKEN/getWebhookInfo"
```

看是否有报错信息。

### 3）Nginx 重载失败

检查配置：

```bash
nginx -t
```

### 4）（JS 版）自动解封失败

- 确认 `QUNID` 已设置且为正确的群组 ID（含 `-100` 前缀）
- 确认 bot 是该群管理员且拥有「封禁用户」权限
- 查看管理员收到的失败原因（查询失败 / 接口失败 / 用户为禁言状态）
