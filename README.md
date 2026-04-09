# Telegram 技术支持 Bot 部署说明

这是一套仿截图风格的 **Telegram 技术支持 / 联系管理员 Bot** 部署方案，支持：

- 用户私聊 Bot
- 用户使用 `/send 内容` 提交问题
- 用户使用 `/unban` 提交解禁申请
- 管理员私聊收到通知
- 管理员使用 `/reply 用户ID 回复内容` 回用户
- 使用 Webhook 长期在线运行

---

## 1. 功能效果

### 用户侧
用户私聊 Bot 后可使用：

```text
/start
/send 你好，我的线路有问题
/unban
/help
```

### 管理员侧
管理员会收到类似通知：

```text
新的工单消息
用户ID：123456789
昵称：Judy
用户名：@abc

内容：
你好，我的线路有问题

回复格式：
/reply 123456789 你的回复内容
```

然后管理员回复：

```text
/reply 123456789 已收到，我帮你检查一下
```

用户就会收到：

```text
技术支持回复：
已收到，我帮你检查一下
```

---

## 2. 目录结构

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

---

## 3. app.py

```python
from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0").strip())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN 未设置")
if not ADMIN_CHAT_ID:
    raise RuntimeError("ADMIN_CHAT_ID 未设置")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_post(method, data=None):
    r = requests.post(f"{BASE_URL}/{method}", json=data or {}, timeout=30)
    r.raise_for_status()
    return r.json()

def tg_get(method, params=None):
    r = requests.get(f"{BASE_URL}/{method}", params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()

def send_message(chat_id, text, reply_to_message_id=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    return tg_post("sendMessage", payload)

def set_commands():
    commands = [
        {"command": "start", "description": "开始使用"},
        {"command": "send", "description": "发送消息给技术支持"},
        {"command": "unban", "description": "申请解禁"},
        {"command": "help", "description": "查看帮助"},
    ]
    return tg_post("setMyCommands", {"commands": commands})

WELCOME_TEXT = '''Welcome to use APTV Support Bot~

为防止广告轰炸，发送消息时必须使用 /send 指令，例如：
/send 你好

如需申请解禁或解除禁言，请直接发送 /unban 指令
'''

HELP_TEXT = '''可用命令：
/send 你的问题
/unban
/help
'''

def notify_admin(user, text, kind="工单消息"):
    user_id = user.get("id")
    first_name = user.get("first_name", "") or "无"
    username = user.get("username", "")
    username_text = f"@{username}" if username else "无"

    admin_text = (
        f"新的{kind}\n"
        f"用户ID：{user_id}\n"
        f"昵称：{first_name}\n"
        f"用户名：{username_text}\n\n"
        f"内容：\n{text}\n\n"
        f"回复格式：\n/reply {user_id} 你的回复内容"
    )
    send_message(ADMIN_CHAT_ID, admin_text)

def handle_private_message(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    user = message.get("from", {})

    if not text:
        send_message(chat_id, WELCOME_TEXT)
        return

    if chat_id == ADMIN_CHAT_ID:
        if text.startswith("/reply "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                send_message(chat_id, "用法：/reply 用户ID 回复内容")
                return

            try:
                target_id = int(parts[1].strip())
                reply_text = parts[2].strip()
                if not reply_text:
                    send_message(chat_id, "回复内容不能为空")
                    return

                send_message(target_id, f"技术支持回复：\n{reply_text}")
                send_message(chat_id, "已发送。")
            except Exception as e:
                send_message(chat_id, f"发送失败：{e}")
            return

        if text.startswith("/say "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                send_message(chat_id, "用法：/say 用户ID 消息内容")
                return

            try:
                target_id = int(parts[1].strip())
                msg = parts[2].strip()
                if not msg:
                    send_message(chat_id, "消息内容不能为空")
                    return

                send_message(target_id, msg)
                send_message(chat_id, "已发送。")
            except Exception as e:
                send_message(chat_id, f"发送失败：{e}")
            return

    if text == "/start":
        send_message(chat_id, WELCOME_TEXT)
        return

    if text == "/help":
        send_message(chat_id, HELP_TEXT)
        return

    if text == "/unban":
        notify_admin(user, "/unban", kind="解禁申请")
        send_message(chat_id, "已收到你的解禁申请，请等待管理员处理。")
        return

    if text.startswith("/send "):
        content = text[6:].strip()
        if not content:
            send_message(chat_id, "格式错误，请这样发送：\n/send 你的问题")
            return

        notify_admin(user, content, kind="工单消息")
        send_message(chat_id, "已收到，开发者看到后会尽快回复，请耐心等待。")
        return

    send_message(chat_id, WELCOME_TEXT)

@app.on_event("startup")
def startup_event():
    try:
        set_commands()
        print("Bot commands set OK")
    except Exception as e:
        print("setMyCommands failed:", e)

@app.get("/")
def health():
    return {"ok": True, "service": "support-bot"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()

    message = update.get("message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return {"ok": True}

    try:
        handle_private_message(message)
    except Exception as e:
        try:
            send_message(ADMIN_CHAT_ID, f"机器人处理异常：{e}")
        except Exception:
            pass

    return {"ok": True}
```

---

## 4. requirements.txt

```text
fastapi
uvicorn
requests
python-dotenv
```

---

## 5. .env

把下面内容改成你自己的：

```env
BOT_TOKEN=你的BOT_TOKEN
ADMIN_CHAT_ID=你的私聊chat_id
```

---

## 6. 本地测试

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

---

## 7. 配置 Nginx

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

---

## 8. 配置 HTTPS

如果已安装 certbot：

```bash
certbot --nginx -d bot.example.com
```

---

## 9. 设置 Telegram Webhook

执行：

```bash
curl "https://api.telegram.org/bot你的BOT_TOKEN/setWebhook?url=https://bot.example.com/telegram/webhook"
```

查看状态：

```bash
curl "https://api.telegram.org/bot你的BOT_TOKEN/getWebhookInfo"
```

---

## 10. 配置 systemd 开机自启

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

---

## 11. 获取 ADMIN_CHAT_ID

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

---

## 12. BotFather 建议设置

你可以通过 `@BotFather` 进一步设置机器人信息：

```text
/setname
/setdescription
/setabouttext
/setuserpic
```

建议：

### 名称
```text
APTV - 技术支持
```

### 简介
```text
这是APTV官方的技术支持机器人，您可以通过该Bot联系到APTV的开发者。
```

---

## 13. 最短部署流程

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

## 14. 常见问题

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

---

## 15. 扩展建议

你还可以继续加：

- 频率限制，防止刷屏
- 黑名单词过滤
- 用户消息存库
- 管理员多账号支持
- 图片 / 文件转发支持
- 群组支持版本

---
