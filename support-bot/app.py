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


WELCOME_TEXT = """Welcome to use APTV Support Bot~

为防止广告轰炸，发送消息时必须使用 /send 指令，例如：
/send 你好

如需申请解禁或解除禁言，请直接发送 /unban 指令
"""

HELP_TEXT = """可用命令：
/send 你的问题
/unban
/help
"""


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

    # 管理员命令
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

    # 普通用户命令
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