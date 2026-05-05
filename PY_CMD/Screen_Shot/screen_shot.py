import pyautogui
import json
import requests
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("diag/screen_shot.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def capture_screen(save_path: str) -> None:
    screenshot = pyautogui.screenshot()
    screenshot.save(save_path)


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


def send_image(image_path: str):
    token = get_tenant_access_token()
    if not token:
        logger.error("获取access_token失败")
        return False

    with open(image_path, "rb") as f:
        image_data = f.read()

    url = "https://open.feishu.cn/open-apis/im/v1/images"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    files = {
        "image_type": (None, "message", None),
        "image": ("image.png", image_data, "image/png")
    }

    response = requests.post(url, headers=headers, files=files)
    result = response.json()

    if result.get("code") != 0:
        logger.error(f"上传图片失败: code={result.get('code')}, msg={result.get('msg')}")
        return False

    image_key = result.get("data", {}).get("image_key")
    logger.info(f"图片上传成功, image_key={image_key}")

    CHAT_ID = get_chat_id()
    content_json = json.dumps({"image_key": image_key})
    message_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    message_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    message_data = {
        "receive_id": CHAT_ID,
        "msg_type": "image",
        "content": content_json
    }

    message_response = requests.post(message_url, headers=message_headers, json=message_data)
    message_result = message_response.json()

    if message_result.get("code") == 0:
        logger.info("图片消息发送成功")
        return True
    else:
        logger.error(f"发送图片消息失败: code={message_result.get('code')}, msg={message_result.get('msg')}")
        return False


def capture_and_send(save_path: str) -> bool:
    capture_screen(save_path)
    logger.info(f"截图已保存到: {save_path}")

    result = send_image(save_path)
    if result:
        logger.info("图片发送成功，删除本地截图...")
        try:
            os.remove(save_path)
            logger.info("本地截图已删除")
        except Exception as e:
            logger.error(f"删除本地截图失败: {e}")
        return True
    else:
        logger.error("图片发送失败")
        return False