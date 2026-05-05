import os
import sys
import io
import json
import logging
import threading
import time
import importlib.util
import pyperclip
import pyautogui
from dotenv import load_dotenv
from config import FEISHU_APP_ID, FEISHU_APP_SECRET

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

msg_logger = logging.getLogger("mobile_msg")
msg_logger.setLevel(logging.INFO)
msg_logger.propagate = False
msg_handler = logging.FileHandler("talk/mobile_rx.log", encoding="utf-8", mode="w")
msg_handler.setLevel(logging.INFO)
msg_handler.setFormatter(logging.Formatter('%(message)s'))
msg_logger.addHandler(msg_handler)

MOBILE_RX_FILE = "talk/mobile_rx.log"
MOBILE_TX_FILE = "talk/mobile_tx.log"
SENDREQUEST_FILE = "talk/sendrequest.log"
FEISHU_REPLY_OVER = "feishu_reply_over"

LOG_FILE = "talk/mobile_rx.log"
TX_LOG_FILE = "talk/mobile_tx.log"
DIAG_LOG_FILE = "diag/diagnosis.log"
CMD_LIST_FILE = "PY_CMD/CMD_list.json"

diag_logger = logging.getLogger("diagnosis")
diag_logger.setLevel(logging.DEBUG)
diag_handler = logging.FileHandler(DIAG_LOG_FILE, encoding="utf-8", mode="w")
diag_handler.setLevel(logging.DEBUG)
diag_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
diag_logger.addHandler(diag_handler)

env_x = os.getenv("TARGET_X")
env_y = os.getenv("TARGET_Y")
if env_x and env_y:
    TARGET_X = int(env_x)
    TARGET_Y = int(env_y)
else:
    print("请将鼠标移到目标位置，5秒后获取坐标...")
    time.sleep(5)
    mouse_pos = pyautogui.position()
    TARGET_X = mouse_pos.x
    TARGET_Y = mouse_pos.y
    print(f"获取到目标坐标: X={TARGET_X}, Y={TARGET_Y}")
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_file, "a", encoding="utf-8") as f:
        f.write(f"\nTARGET_X={TARGET_X}\nTARGET_Y={TARGET_Y}\n")

client = None
chat_id = None
wait_func_info = None


def do_p2_im_message_receive_v1(data):
    global chat_id

    diag_logger.info(f"[do_p2_im_message_receive_v1] START 收到消息事件")
    logger.info(f"收到消息事件")

    try:
        message = data.event.message
        diag_logger.info(f"[do_p2_im_message_receive_v1] message类型={type(message)}")
        logger.info(f"消息对象类型: {type(message)}")
        logger.info(f"消息内容: {message}")

        msg_type = message.message_type
        content = message.content
        chat_type = message.chat_type

        diag_logger.info(f"[do_p2_im_message_receive_v1] msg_type={msg_type}, chat_type={chat_type}")

        sender_id = None
        if hasattr(message, 'sender') and message.sender:
            sender = message.sender
            logger.info(f"sender属性: {sender}")
            if hasattr(sender, 'sender_id') and sender.sender_id:
                sender_id = sender.sender_id.open_id
        else:
            logger.info(f"message没有sender属性，检查其他属性")
            logger.info(f"message所有属性: {[attr for attr in dir(message) if not attr.startswith('_')]}")

        logger.info(f"消息类型: {msg_type}, 聊天类型: {chat_type}, 发送者: {sender_id}")

        msg_text = ""
        if msg_type == "text":
            try:
                logger.info(f"content类型: {type(content)}, content值: {content}")
                if isinstance(content, str):
                    content_dict = json.loads(content)
                    if isinstance(content_dict, dict):
                        if "text" in content_dict:
                            msg_text = content_dict.get("text", "")
                        elif " TEXT" in content_dict:
                            msg_text = content_dict.get("TEXT", "")
                        else:
                            msg_text = str(content_dict)
                    else:
                        msg_text = str(content_dict)
                elif isinstance(content, dict):
                    if "text" in content:
                        msg_text = content.get("text", "")
                    elif " TEXT" in content:
                        msg_text = content.get("TEXT", "")
                    else:
                        msg_text = str(content)
                else:
                    msg_text = str(content)
            except Exception as e:
                logger.error(f"解析消息内容失败: {e}, content={content}")
                msg_text = str(content) if content else ""

            diag_logger.info(f"[do_p2_im_message_receive_v1] 解析后msg_text={msg_text[:100]}...")
            logger.info(f"解析后msg_text: {msg_text}")

            chat_id = message.chat_id
            diag_logger.info(f"[do_p2_im_message_receive_v1] 设置chat_id={chat_id}")

            env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
            with open(env_file, "r", encoding="utf-8") as f:
                env_content = f.read()

            env_lines = []
            chat_id_updated = False
            for line in env_content.splitlines():
                if line.startswith("CHAT_ID="):
                    if line != f"CHAT_ID={chat_id}":
                        env_lines.append(f"CHAT_ID={chat_id}")
                        chat_id_updated = True
                    else:
                        env_lines.append(line)
                else:
                    env_lines.append(line)

            if chat_id_updated:
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(env_lines) + "\n")
                logger.info(f"已更新.env中的CHAT_ID为: {chat_id}")
            else:
                existing_chat_id = None
                for line in env_content.splitlines():
                    if line.startswith("CHAT_ID="):
                        existing_chat_id = line.split("=", 1)[1].strip()
                        break

                if existing_chat_id is None:
                    with open(env_file, "a", encoding="utf-8") as f:
                        f.write(f"\nCHAT_ID={chat_id}\n")
                    logger.info(f"已将CHAT_ID保存到.env: {chat_id}")

            msg_logger.info(msg_text)
            msg_handler.flush()
            with open(MOBILE_RX_FILE, "w", encoding="utf-8") as f:
                f.write(msg_text)
                f.flush()
            diag_logger.info(f"[do_p2_im_message_receive_v1] 已写入MOBILE_RX_FILE")

            response_text = f"收到你发送的消息：{msg_text}\n"
            content_json = json.dumps({"text": response_text})

            if chat_type == "p2p":
                from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

                request = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(message.chat_id)
                        .msg_type("text")
                        .content(content_json)
                        .build()
                    )
                    .build()
                )

                response = client.im.v1.message.create(request)
                if not response.success():
                    logger.error(f"发送消息失败: code={response.code}, msg={response.msg}")
                    diag_logger.error(f"[do_p2_im_message_receive_v1] 发送消息失败: code={response.code}, msg={response.msg}")
                else:
                    logger.info("消息回复成功")
                    diag_logger.info(f"[do_p2_im_message_receive_v1] 消息回复成功")

    except Exception as e:
        logger.error(f"处理消息失败: {e}", exc_info=True)
        diag_logger.error(f"[do_p2_im_message_receive_v1] 异常: {e}", exc_info=True)

    diag_logger.info(f"[do_p2_im_message_receive_v1] END")


def split_by_sentences(text, max_len=600):
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in '。！？.!?':
            sentences.append(current)
            current = ""

    if current.strip():
        sentences.append(current)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_len:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(sentence) <= max_len:
                current_chunk = sentence
            else:
                current_chunk = ""
                for char in sentence:
                    current_chunk += char
                    if char in '。！？.!?':
                        chunks.append(current_chunk)
                        current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def send_long_text(send_chat_id, text):
    diag_logger.info(f"[send_long_text] START chat_id={send_chat_id}, text长度={len(text)}")
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

    messages = split_by_sentences(text, max_len=600)

    logger.info(f"[send_long_text] 总长度={len(text)}字符，拆分={len(messages)}条")
    diag_logger.info(f"[send_long_text] 拆分消息数量={len(messages)}")

    for idx, msg in enumerate(messages):
        logger.info(f"[send_long_text] 第{idx+1}条: 长度={len(msg)}, 内容='{msg[:50]}...'")

    for idx, msg in enumerate(messages):
        diag_logger.info(f"[send_long_text] 发送第{idx+1}/{len(messages)}条消息")
        content_json = json.dumps({"text": msg})
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(send_chat_id)
                .msg_type("text")
                .content(content_json)
                .build()
            )
            .build()
        )
        response = client.im.v1.message.create(request)
        if not response.success():
            logger.error(f"发送第{idx+1}条消息失败: code={response.code}, msg={response.msg}")
            diag_logger.error(f"[send_long_text] 发送第{idx+1}条消息失败: code={response.code}, msg={response.msg}")
            return False
        else:
            logger.info(f"发送第{idx+1}/{len(messages)}条消息成功")
            diag_logger.info(f"[send_long_text] 发送第{idx+1}/{len(messages)}条消息成功")

    diag_logger.info(f"[send_long_text] END, 全部发送成功")
    return True


def monitor_mobile_tx():
    global chat_id

    last_mtime = 0
    diag_logger.info(f"[monitor_mobile_tx] START")
    logger.info(f"开始监控 {MOBILE_TX_FILE} 文件变化...")

    while True:
        try:
            if os.path.exists(MOBILE_TX_FILE):
                current_mtime = os.path.getmtime(MOBILE_TX_FILE)
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    diag_logger.info(f"[monitor_mobile_tx] 检测到文件变化")
                    time.sleep(0.5)

                    content = ""
                    stable_count = 0
                    for retry in range(5):
                        try:
                            with open(MOBILE_TX_FILE, "r", encoding="utf-8") as f:
                                new_content = f.read()
                            if new_content == content and len(content) > 0:
                                stable_count += 1
                                if stable_count >= 2:
                                    break
                            else:
                                content = new_content
                                stable_count = 0
                            time.sleep(0.3)
                        except Exception as e:
                            logger.warning(f"读取文件失败: {e}")
                            time.sleep(0.1)

                    logger.info(f"[monitor] 最终读取文件长度={len(content)}")
                    logger.info(f"[monitor] 文件内容前100字符: {content[:100]}")
                    diag_logger.info(f"[monitor_mobile_tx] 文件长度={len(content)}, 内容前100字符: {content[:100]}")

                    if FEISHU_REPLY_OVER in content:
                        logger.info(f"检测到 {FEISHU_REPLY_OVER}，准备发送飞书消息")
                        diag_logger.info(f"[monitor_mobile_tx] 检测到FEISHU_REPLY_OVER")

                        lines = content.split("\n")
                        reply_lines = []
                        for line in lines:
                            if line.strip() == FEISHU_REPLY_OVER:
                                break
                            reply_lines.append(line)

                        reply_text = "\n".join(reply_lines)
                        logger.info(f"[monitor] 待发送总长度={len(reply_text)}字符")
                        diag_logger.info(f"[monitor_mobile_tx] 待发送文本长度={len(reply_text)}")

                        if chat_id:
                            diag_logger.info(f"[monitor_mobile_tx] chat_id={chat_id}")
                            if len(reply_text) > 0:
                                diag_logger.info(f"[monitor_mobile_tx] 开始发送飞书消息...")
                                if send_long_text(chat_id, reply_text):
                                    logger.info("飞书消息发送成功")
                                    diag_logger.info(f"[monitor_mobile_tx] 飞书消息发送成功")
                                    with open(MOBILE_TX_FILE, "w", encoding="utf-8") as f:
                                        f.write("")
                                    logger.info(f"已清空 {MOBILE_TX_FILE}")
                                else:
                                    logger.error("飞书消息发送失败")
                                    diag_logger.error(f"[monitor_mobile_tx] 飞书消息发送失败")
                            else:
                                logger.warning("reply_text为空，跳过发送")
                                diag_logger.warning(f"[monitor_mobile_tx] reply_text为空，跳过发送")
                        else:
                            logger.warning("没有可用的 chat_id，无法发送飞书消息")
                            diag_logger.warning(f"[monitor_mobile_tx] 没有可用的 chat_id")

        except Exception as e:
            logger.error(f"监控文件出错: {e}", exc_info=True)
            diag_logger.error(f"[monitor_mobile_tx] 异常: {e}", exc_info=True)

        time.sleep(0.5)


def monitor_sendrequest():
    global chat_id

    last_mtime = 0
    diag_logger.info(f"[monitor_sendrequest] START")
    logger.info(f"开始监控 {SENDREQUEST_FILE} 文件变化...")

    while True:
        try:
            if os.path.exists(SENDREQUEST_FILE):
                current_mtime = os.path.getmtime(SENDREQUEST_FILE)
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    time.sleep(0.3)

                    try:
                        with open(SENDREQUEST_FILE, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                    except Exception as e:
                        logger.warning(f"读取文件失败: {e}")
                        time.sleep(0.1)
                        continue

                    remaining_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        if line.startswith("send:"):
                            file_path = line[5:].strip()
                            if file_path:
                                diag_logger.info(f"[monitor_sendrequest] 检测到发送请求: {file_path}")
                                logger.info(f"准备发送文件: {file_path}")

                                sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "PY_CMD", "Send_File"))
                                try:
                                    from send_file import send_file_to_feishu
                                    success = send_file_to_feishu(file_path)
                                    if success:
                                        logger.info(f"文件发送成功: {file_path}")
                                        diag_logger.info(f"[monitor_sendrequest] 文件发送成功")
                                    else:
                                        logger.error(f"文件发送失败: {file_path}")
                                        diag_logger.info(f"[monitor_sendrequest] 文件发送失败")
                                except Exception as e:
                                    logger.error(f"导入或执行send_file_to_feishu失败: {e}")
                                    diag_logger.error(f"[monitor_sendrequest] 异常: {e}")
                                finally:
                                    sys.path.pop(0)
                        else:
                            remaining_lines.append(line + "\n")

                    if remaining_lines:
                        with open(SENDREQUEST_FILE, "w", encoding="utf-8") as f:
                            f.writelines(remaining_lines)
                        diag_logger.info(f"[monitor_sendrequest] 剩余 {len(remaining_lines)} 行未处理")
                    else:
                        with open(SENDREQUEST_FILE, "w", encoding="utf-8") as f:
                            f.write("")
                        last_mtime = os.path.getmtime(SENDREQUEST_FILE)

        except Exception as e:
            logger.error(f"监控sendrequest文件出错: {e}", exc_info=True)
            diag_logger.error(f"[monitor_sendrequest] 异常: {e}", exc_info=True)

        time.sleep(0.5)


def read_log_content():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            content = content.replace("null", "").strip()
            return content
    return ""


def write_tx_log(content):
    with open(TX_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def load_cmd_list():
    diag_logger.info(f"[load_cmd_list] START")
    if os.path.exists(CMD_LIST_FILE):
        try:
            with open(CMD_LIST_FILE, "r", encoding="utf-8") as f:
                cmd_list = json.load(f)
            diag_logger.info(f"[load_cmd_list] 成功加载 {len(cmd_list)} 条命令")
            return cmd_list
        except Exception as e:
            diag_logger.error(f"[load_cmd_list] 加载失败: {e}")
            return []
    diag_logger.warning(f"[load_cmd_list] CMD_LIST_FILE不存在: {CMD_LIST_FILE}")
    return []


def find_command(command_name, cmd_list):
    diag_logger.info(f"[find_command] START command_name={command_name}, cmd_list长度={len(cmd_list)}")
    for cmd in cmd_list:
        if cmd.get("name") == command_name:
            diag_logger.info(f"[find_command] 找到命令: {cmd.get('name')}")
            return cmd
    diag_logger.warning(f"[find_command] 未找到命令: {command_name}")
    return None


def execute_py_command(cmd_info, cmd_list):
    import inspect
    import sys

    diag_logger.info(f"[execute_py_command] START cmd_info={cmd_info.get('name')}, folder={cmd_info.get('folder')}, file={cmd_info.get('file')}")

    folder = cmd_info.get("folder")
    file_name = cmd_info.get("file")
    functions = cmd_info.get("functions", [])

    diag_logger.info(f"[execute_py_command] functions列表={functions}")

    if not folder or not file_name:
        diag_logger.error(f"[execute_py_command] 命令配置缺少folder或file信息")
        return False, "命令配置缺少folder或file信息"

    script_path = os.path.join("PY_CMD", folder, file_name)
    diag_logger.info(f"[execute_py_command] script_path={script_path}")

    if not os.path.exists(script_path):
        diag_logger.error(f"[execute_py_command] 脚本文件不存在: {script_path}")
        return False, f"脚本文件不存在: {script_path}"

    script_dir = os.path.dirname(os.path.abspath(script_path))
    project_root = os.path.dirname(os.path.abspath(__file__))

    diag_logger.info(f"[execute_py_command] script_dir={script_dir}, project_root={project_root}")

    original_path = sys.path.copy()
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        diag_logger.info(f"[execute_py_command] 加载模块: {script_path}")
        spec = importlib.util.spec_from_file_location("cmd_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        diag_logger.info(f"[execute_py_command] 模块加载成功")

        if not functions or len(functions) == 0:
            diag_logger.error(f"[execute_py_command] 命令配置缺少functions信息")
            return False, "命令配置缺少functions信息"

        last_error = ""
        for func_name in functions:
            diag_logger.info(f"[execute_py_command] 检查函数: {func_name}")
            if hasattr(module, func_name):
                func = getattr(module, func_name)
                diag_logger.info(f"[execute_py_command] 找到函数 {func_name}，检查参数...")
                try:
                    sig = inspect.signature(func)
                    params = sig.parameters
                    diag_logger.info(f"[execute_py_command] 函数 {func_name} 参数数量: {len(params)}")

                    if len(params) == 0:
                        diag_logger.info(f"[execute_py_command] 调用无参函数 {func_name}")
                        result = func()
                    else:
                        default_args = {}
                        for param_name, param in params.items():
                            if param.default is not inspect.Parameter.empty:
                                default_args[param_name] = param.default
                                diag_logger.info(f"[execute_py_command] 参数 {param_name} 有默认值: {param.default}")
                            elif param_name == 'save_path':
                                default_args[param_name] = "screenshot.png"
                                diag_logger.info(f"[execute_py_command] 参数 {param_name} 使用默认值: screenshot.png")
                            elif param_name == 'image_path':
                                default_args[param_name] = "screenshot.png"
                                diag_logger.info(f"[execute_py_command] 参数 {param_name} 使用默认值: screenshot.png")

                        diag_logger.info(f"[execute_py_command] 调用函数 {func_name}，参数: {default_args}")
                        if len(default_args) >= len(params):
                            result = func(**default_args)
                        else:
                            last_error = f"函数 {func_name} 需要参数且无默认值"
                            diag_logger.warning(f"[execute_py_command] {last_error}")
                            continue

                    diag_logger.info(f"[execute_py_command] 函数 {func_name} 返回值: {result}")
                    if result == "wait":
                        diag_logger.info(f"[execute_py_command] 检测到wait返回值，设置wait_func_info")
                        return True, "wait", (module, func_name)

                    diag_logger.info(f"[execute_py_command] 函数执行成功")
                    return True, f"执行命令成功: {cmd_info.get('name')}"
                except Exception as func_error:
                    last_error = f"执行函数 {func_name} 失败: {str(func_error)}"
                    diag_logger.error(f"[execute_py_command] {last_error}", exc_info=True)
                    continue
            else:
                last_error = f"脚本中未找到函数: {func_name}"
                diag_logger.warning(f"[execute_py_command] {last_error}")
                continue

        diag_logger.error(f"[execute_py_command] 所有函数执行失败: {last_error}")
        return False, f"执行命令失败: {last_error}"

    except Exception as e:
        diag_logger.error(f"[execute_py_command] 异常: {str(e)}", exc_info=True)
        return False, f"执行命令失败: {str(e)}"
    finally:
        sys.path[:] = original_path
        diag_logger.info(f"[execute_py_command] END")


def parse_command(content):
    diag_logger.info(f"[parse_command] START content={content[:100]}...")
    if not content.startswith("&"):
        diag_logger.info(f"[parse_command] 不以&开头，返回None, 非命令")
        return None, None, "非&命令，直接粘贴"

    rest = content[1:].strip()
    diag_logger.info(f"[parse_command] 去除&后: {rest}")

    if "：" in rest:
        parts = rest.split("：", 1)
        if len(parts) == 2:
            agent_name = parts[0].strip()
            task_content = parts[1].strip()
            diag_logger.info(f"[parse_command] agent命令: agent_name={agent_name}, task_content={task_content[:50]}...")
            return "agent", agent_name, task_content

    diag_logger.info(f"[parse_command] direct命令: rest={rest}")
    return "direct", rest, ""


def execute_command(cmd_type, param1, param2):
    global wait_func_info

    diag_logger.info(f"[execute_command] START cmd_type={cmd_type}, param1={param1}, param2={param2}, wait_func_info={wait_func_info}")

    if wait_func_info is not None:
        module, func_name = wait_func_info
        func = getattr(module, func_name)
        diag_logger.info(f"[execute_command] wait_func_info调用函数: {func_name}")
        print(f"[execute_command] 当前强制获取输入的函数: {func_name}", flush=True)
        if cmd_type == "direct":
            result = func(param1)
        else:
            result = func(param2 if param2 else param1)
        diag_logger.info(f"[execute_command] wait_func_info调用函数返回值: {result}")
        print(f"[execute_command] 函数 {func_name} 返回值: {result}", flush=True)
        if result == "q":
            wait_func_info = None
            diag_logger.info(f"[execute_command] 函数返回q，wait_func_info已清除")
            print(f"[execute_command] 函数返回q，wait_func_info已清除", flush=True)
        else:
            diag_logger.info(f"[execute_command] wait_func_info保持不变，等待下次输入")
            print(f"[execute_command] 函数返回{result}，wait_func_info保持不变", flush=True)
        return True

    if cmd_type == "agent":
        agent_name = param1
        task_content = param2
        response = f"[智能体任务] 向 {agent_name} 发送任务: {task_content}"
        write_tx_log(response)
        logger.info(response)
        return True
    elif cmd_type == "direct":
        command = param1
        cmd_list = load_cmd_list()
        cmd_info = find_command(command, cmd_list)
        diag_logger.info(f"[execute_command] 查找到cmd_info={cmd_info}")

        if cmd_info:
            result = execute_py_command(cmd_info, cmd_list)
            diag_logger.info(f"[execute_command] execute_py_command返回result={result}")
            diag_logger.info(f"[execute_command] 返回值={result}")
            if len(result) == 3 and result[1] == "wait":
                wait_func_info = result[2]
                func_name = result[2][1]
                diag_logger.info(f"[execute_command] 设置wait_func_info={wait_func_info}")
                print(f"[execute_command] 函数 {func_name} 返回wait，进入强制输入状态", flush=True)
                return True
            elif result[0]:
                diag_logger.info(f"[execute_command] 命令执行成功，返回True")
                return True
        else:
            response = f"[错误] 命令 '{command}' 无法执行，命令不存在或命令本身有问题\n{FEISHU_REPLY_OVER}"
            write_tx_log(response)
            logger.error(response)
    diag_logger.info(f"[execute_command] END，返回False")
    return False


def paste_content(content):
    diag_logger.info(f"[paste_content] START content={content[:50]}...")
    pyperclip.copy(content)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
    diag_logger.info(f"[paste_content] 已清空LOG_FILE")

    pyautogui.moveTo(TARGET_X, TARGET_Y)
    time.sleep(0.1)
    pyautogui.click(TARGET_X, TARGET_Y)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)
    pyautogui.press('enter')

    diag_logger.info(f"[paste_content] 已粘贴到位置 ({TARGET_X}, {TARGET_Y})")


def mouse_paste_monitor():
    global wait_func_info

    diag_logger.info(f"[mouse_paste_monitor] START")
    logger.info(f"开始监控 {LOG_FILE} 文件变化（鼠标粘贴监控）...")

    while True:
        if os.path.exists(LOG_FILE):
            content = read_log_content()
            if content:
                logger.info(f"检测到内容: {content}")
                diag_logger.info(f"[mouse_paste_monitor] 读取到内容: {content}, wait_func_info={wait_func_info}")

                if content == "clear" or content == "Clear" or content == "Clr" or content == "clr":
                    wait_func_info = None
                    diag_logger.info(f"[mouse_paste_monitor] 检测到clear命令，已重置wait_func_info")
                    with open(LOG_FILE, "w", encoding="utf-8") as f:
                        f.write("")
                    with open(MOBILE_TX_FILE, "w", encoding="utf-8") as f:
                        f.write("[消息内容:已退出所有等待中的函数]\nfeishu_reply_over")
                    continue

                if wait_func_info is not None:
                    content = "&" + content
                    diag_logger.info(f"[mouse_paste_monitor] wait_func_info不为空，添加&前缀")

                cmd_type, param1, param2 = parse_command(content)
                diag_logger.info(f"[mouse_paste_monitor] parse_command返回: cmd_type={cmd_type}, param1={param1}, param2={param2}")

                if cmd_type == "direct" or cmd_type == "agent":
                    result = execute_command(cmd_type, param1, param2)
                    diag_logger.info(f"[mouse_paste_monitor] execute_command返回: {result}")
                    with open(LOG_FILE, "w", encoding="utf-8") as f:
                        f.write("")
                    diag_logger.info(f"[mouse_paste_monitor] 已清空LOG_FILE")
                    continue

                paste_content(content)

        time.sleep(0.5)

    diag_logger.info(f"[mouse_paste_monitor] END")


def main():
    global client

    import lark_oapi as lark

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
        .build()
    )

    client = (
        lark.Client.builder()
        .app_id(FEISHU_APP_ID)
        .app_secret(FEISHU_APP_SECRET)
        .build()
    )

    monitor_thread = threading.Thread(target=monitor_mobile_tx, daemon=True)
    monitor_thread.start()
    logger.info("飞书消息监控线程已启动")

    mouse_thread = threading.Thread(target=mouse_paste_monitor, daemon=True)
    mouse_thread.start()
    logger.info("鼠标粘贴监控线程已启动")

    sendrequest_thread = threading.Thread(target=monitor_sendrequest, daemon=True)
    sendrequest_thread.start()
    logger.info("发送请求监控线程已启动")

    wsClient = (
        lark.ws.Client(
            FEISHU_APP_ID,
            FEISHU_APP_SECRET,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )
    )

    logger.info("正在启动飞书机器人 WebSocket 连接...")
    logger.info("按 Ctrl+C 停止")

    wsClient.start()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=" * 50)
    print("Feishu Bot + Mouse Paste Monitor 整合版")
    print("=" * 50)

    try:
        main()
    except KeyboardInterrupt:
        logger.info("正在停止机器人...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
