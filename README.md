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
