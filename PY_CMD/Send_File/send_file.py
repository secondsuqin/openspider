import json
import requests
import logging
import os
import sys
import re
from requests_toolbelt import MultipartEncoder

def natural_sort_key(string):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', string)]

def sort_entries(entries):
    return sorted(entries, key=lambda e: (0 if e["type"] == "dir" else 1, natural_sort_key(e["name"])))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("diag/send_file.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def get_tenant_access_token():
    from config import FEISHU_APP_ID, FEISHU_APP_SECRET
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    if result.get("code") == 0:
        return result.get("tenant_access_token")
    return None


def get_chat_id():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_file = os.path.join(project_root, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("CHAT_ID="):
                    return line.split("=", 1)[1].strip()
    return None


def send_file_to_feishu(file_path: str) -> bool:
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False

    token = get_tenant_access_token()
    if not token:
        logger.error("获取access_token失败")
        return False

    file_name = os.path.basename(file_path)
    logger.info(f"准备发送文件: {file_name}")

    form = {
        "file_type": "stream",
        "file_name": file_name,
        "file": (file_name, open(file_path, "rb"), "application/octet-stream")
    }

    multi_form = MultipartEncoder(form)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": multi_form.content_type
    }

    url = "https://open.feishu.cn/open-apis/im/v1/files"
    response = requests.post(url, headers=headers, data=multi_form)
    result = response.json()

    if result.get("code") != 0:
        logger.error(f"上传文件失败: code={result.get('code')}, msg={result.get('msg')}")
        return False

    file_key = result.get("data", {}).get("file_key")
    logger.info(f"文件上传成功, file_key={file_key}")

    CHAT_ID = get_chat_id()
    content_json = json.dumps({"file_key": file_key})
    message_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    message_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    message_data = {
        "receive_id": CHAT_ID,
        "msg_type": "file",
        "content": content_json
    }

    message_response = requests.post(message_url, headers=message_headers, json=message_data)
    message_result = message_response.json()

    if message_result.get("code") == 0:
        logger.info("文件消息发送成功")
        return True
    else:
        logger.error(f"发送文件消息失败: code={message_result.get('code')}, msg={message_result.get('msg')}")
        return False


STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_file_state.json")
SAVE_PATH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_path.log")


def save_current_path(path):
    with open(SAVE_PATH_LOG, "w", encoding="utf-8") as f:
        f.write(path)


def load_last_path():
    if os.path.exists(SAVE_PATH_LOG):
        with open(SAVE_PATH_LOG, "r", encoding="utf-8") as f:
            path = f.read().strip()
            if path and os.path.exists(path):
                return path
    return None


def save_state(current_dir, items):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"current_dir": current_dir, "items": items}, f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def SEND_FILE(input_val=None) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(base_dir, "..", "talk", "mobile_tx.log")
    log_path = os.path.normpath(log_path)

    state = load_state()

    if input_val is None:
        start_dir = load_last_path()
        if start_dir is None:
            start_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        entries = []
        for name in os.listdir(start_dir):
            if os.path.isdir(os.path.join(start_dir, name)):
                entries.append({"name": name, "type": "dir", "path": os.path.join(start_dir, name)})
            else:
                entries.append({"name": name, "type": "file", "path": os.path.join(start_dir, name)})
        entries = sort_entries(entries)

        save_state(start_dir, entries)
        save_current_path(start_dir)

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("当前目录: {}\n".format(start_dir))
            f.write("请输入编号选择文件/文件夹(q退出,b返回上级):\n")
            for i, entry in enumerate(entries, 1):
                suffix = "/" if entry["type"] == "dir" else ""
                f.write("{}. {}{}\n".format(i, entry["name"], suffix))
            f.write("feishu_reply_over\n")

        return "wait"

    input_str = str(input_val).strip()

    if input_str.lower() == "q":
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("已退出文件浏览\n")
            f.write("feishu_reply_over\n")
        return "0"

    if input_str.lower() == "b":
        if state is not None:
            parent_dir = os.path.dirname(state.get("current_dir", ""))
            if parent_dir and os.path.exists(parent_dir):
                entries = []
                for name in os.listdir(parent_dir):
                    if os.path.isdir(os.path.join(parent_dir, name)):
                        entries.append({"name": name, "type": "dir", "path": os.path.join(parent_dir, name)})
                    else:
                        entries.append({"name": name, "type": "file", "path": os.path.join(parent_dir, name)})
                entries = sort_entries(entries)
                save_state(parent_dir, entries)
                save_current_path(parent_dir)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("当前目录: {}\n".format(parent_dir))
                    f.write("请输入编号选择文件/文件夹(q退出,b返回上级):\n")
                    for i, entry in enumerate(entries, 1):
                        suffix = "/" if entry["type"] == "dir" else ""
                        f.write("{}. {}{}\n".format(i, entry["name"], suffix))
                    f.write("feishu_reply_over\n")
                return "wait"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("无法返回上级目录\n")
            f.write("feishu_reply_over\n")
        return "wait"

    if state is None:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("状态已过期，请重新输入\n")
            f.write("feishu_reply_over\n")
        return "0"

    if input_str.isdigit():
        idx = int(input_str)
        items = state.get("items", [])
        if 1 <= idx <= len(items):
            selected = items[idx - 1]
            item_path = selected["path"]

            if selected["type"] == "dir":
                try:
                    sub_entries = []
                    for name in os.listdir(item_path):
                        sub_path = os.path.join(item_path, name)
                        if os.path.isdir(sub_path):
                            sub_entries.append({"name": name, "type": "dir", "path": sub_path})
                        else:
                            sub_entries.append({"name": name, "type": "file", "path": sub_path})
                    sub_entries = sort_entries(sub_entries)

                    save_state(item_path, sub_entries)
                    save_current_path(item_path)

                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write("当前目录: {}\n".format(item_path))
                        f.write("请输入编号选择文件/文件夹(q返回上级):\n")
                        for i, entry in enumerate(sub_entries, 1):
                            suffix = "/" if entry["type"] == "dir" else ""
                            f.write("{}. {}{}\n".format(i, entry["name"], suffix))
                        f.write("feishu_reply_over\n")
                except Exception as e:
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write("无法访问文件夹: {}\n".format(str(e)))
                        f.write("feishu_reply_over\n")

                return "wait"

            else:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("正在发送文件: {}...\n".format(selected["name"]))
                    f.write("feishu_reply_over\n")

                success = send_file_to_feishu(item_path)

                if success:
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write("文件发送成功: {}\n".format(selected["name"]))
                        f.write("请继续选择文件，或输入q退出\n")
                        f.write("当前目录: {}\n".format(state.get("current_dir", "")))
                        for i, entry in enumerate(items, 1):
                            suffix = "/" if entry["type"] == "dir" else ""
                            f.write("{}. {}{}\n".format(i, entry["name"], suffix))
                        f.write("feishu_reply_over\n")
                else:
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write("文件发送失败: {}\n".format(selected["name"]))
                        f.write("请继续选择文件，或输入q退出\n")
                        f.write("当前目录: {}\n".format(state.get("current_dir", "")))
                        for i, entry in enumerate(items, 1):
                            suffix = "/" if entry["type"] == "dir" else ""
                            f.write("{}. {}{}\n".format(i, entry["name"], suffix))
                        f.write("feishu_reply_over\n")

                return "wait"

    current_dir = state.get("current_dir", "")
    items = state.get("items", [])
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("输入无效，请输入1-{}之间的编号\n".format(len(items)))
        f.write("当前目录: {}\n".format(current_dir))
        for i, entry in enumerate(items, 1):
            suffix = "/" if entry["type"] == "dir" else ""
            f.write("{}. {}{}\n".format(i, entry["name"], suffix))
        f.write("feishu_reply_over\n")

    return "wait"