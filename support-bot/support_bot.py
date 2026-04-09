import time
import requests

BOT_TOKEN = "替换成你的BOT_TOKEN"
ADMIN_CHAT_ID = 123456789  # 替换成你的 Telegram 私聊 chat_id

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0


def api_get(method, params=None, timeout=30):
    r = requests.get(f"{BASE_URL}/{method}", params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def api_post(method, data=None, timeout=30):
    r = requests.post(f"{BASE_URL}/{method}", json=data or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text, reply_to_message_id=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    return api_post("sendMessage", payload)


def get_updates(offset=None, timeout=20):
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    return api_get("getUpdates", params=params, timeout=timeout + 10)


def get_bot_username():
    return api_get("getMe")["result"]["username"]


def set_commands():
    commands = [
        {"command": "start", "description": "开始使用"},
        {"command": "send", "description": "发送消息给技术支持"},
        {"command": "unban", "description": "申请解禁"},
        {"command": "help", "description": "查看帮助"},
    ]
    return api_post("setMyCommands", {"commands": commands})


WELCOME_TEXT = """Welcome to use Support Bot~

为防止广告轰炸，发送消息时必须使用 /send 指令，例如：
/send 你好

如需申请解禁或解除禁言，请直接回复 /unban 指令
"""

HELP_TEXT = """可用命令：
/send 你的问题
/unban
/help
"""


def notify_admin(user, text, kind="消息"):
    user_id = user.get("id")
    first_name = user.get("first_name", "")
    username = user.get("username", "")
    username_text = f"@{username}" if username else "无"

    admin_text = (
        f"新的{kind}\n"
        f"用户ID：{user_id}\n"
        f"昵称：{first_name or '无'}\n"
        f"用户名：{username_text}\n\n"
        f"内容：\n{text}\n\n"
        f"回复格式：\n/reply {user_id} 你的回复内容"
    )
    send_message(ADMIN_CHAT_ID, admin_text)


def handle_user_private(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user = message.get("from", {})

    # 管理员命令
    if chat_id == ADMIN_CHAT_ID and text.startswith("/reply "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            send_message(chat_id, "用法：/reply 用户ID 回复内容")
            return

        target_id = parts[1].strip()
        reply_text = parts[2].strip()

        try:
            target_id = int(target_id)
            send_message(target_id, f"技术支持回复：\n{reply_text}")
            send_message(chat_id, "已发送。")
        except Exception as e:
            send_message(chat_id, f"发送失败：{e}")
        return

    if chat_id == ADMIN_CHAT_ID and text.startswith("/say "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            send_message(chat_id, "用法：/say 用户ID 消息内容")
            return

        try:
            target_id = int(parts[1].strip())
            msg = parts[2].strip()
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

    # 非命令消息，提示按规则发
    send_message(chat_id, WELCOME_TEXT)


def main():
    global last_update_id

    bot_username = get_bot_username()
    print("Bot started:", bot_username)

    try:
        set_commands()
        print("Bot commands set.")
    except Exception as e:
        print("setMyCommands failed:", e)

    while True:
        try:
            data = get_updates(offset=last_update_id + 1)
            updates = data.get("result", [])

            for update in updates:
                last_update_id = update["update_id"]

                message = update.get("message")
                if not message:
                    continue

                chat = message.get("chat", {})
                if chat.get("type") != "private":
                    continue

                handle_user_private(message)

        except Exception as e:
            print("error:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()