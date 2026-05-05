import json
import os
import sys
import importlib.util
import inspect


STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "list_cmd_state.json")


def save_state(wait_func_info):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(wait_func_info, f)


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            try:
                os.remove(STATE_FILE)
            except:
                pass
            return None
    return None


def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def reload_module(script_path, module_name):
    keys_to_remove = []
    for mod_name in list(sys.modules.keys()):
        if mod_name == module_name or mod_name.startswith("cmd_module_"):
            keys_to_remove.append(mod_name)
    for key in keys_to_remove:
        del sys.modules[key]

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def LIST_CMD(input_val=None) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd_list_path = os.path.join(base_dir, "CMD_list.json")
    log_path = os.path.join(base_dir, "..", "talk", "mobile_tx.log")
    log_path = os.path.normpath(log_path)

    with open(cmd_list_path, "r", encoding="utf-8") as f:
        cmd_list = json.load(f)

    state = load_state()

    if state is not None and input_val is not None:
        func_name = state.get("func_name")
        module_name = state.get("module_name")
        script_path = state.get("script_path")

        module = reload_module(script_path, module_name)
        func = getattr(module, func_name)
        result = func(input_val)

        if result == "wait":
            return "wait"
        else:
            clear_state()
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"函数 {func_name} 执行完成,继续执行其他命令：\n")
                for i, cmd in enumerate(cmd_list, 1):
                    line = f"{i}. {cmd['name']} - {cmd['description']}"
                    f.write(line + "\n")
                f.write("注：如要退出命令列表，请输入（q）\n")
                f.write("feishu_reply_over\n")
            return result

    if input_val is None:
        clear_state()
        with open(log_path, "w", encoding="utf-8") as f:
            for i, cmd in enumerate(cmd_list, 1):
                line = f"{i}. {cmd['name']} - {cmd['description']}"
                f.write(line + "\n")
            f.write("feishu_reply_over\n")
        return "wait"

    input_str = str(input_val).strip()

    if input_str.lower() == "q":
        clear_state()
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("已退出命令列表\n")
            f.write("feishu_reply_over\n")
        return "q"

    if input_str.isdigit():
        idx = int(input_str)
        if 1 <= idx <= len(cmd_list):
            cmd_info = cmd_list[idx - 1]
            func_name = cmd_info.get("functions", [None])[0]
            folder = cmd_info.get("folder")
            file_name = cmd_info.get("file")
            script_path = os.path.join(base_dir, folder, file_name)

            if os.path.exists(script_path):
                script_dir = os.path.dirname(os.path.abspath(script_path))
                original_path = sys.path.copy()
                if script_dir not in sys.path:
                    sys.path.insert(0, script_dir)
                if base_dir not in sys.path:
                    sys.path.insert(0, base_dir)

                try:
                    module_name = f"cmd_module_{folder}_{file_name}"
                    module = reload_module(script_path, module_name)

                    functions = cmd_info.get("functions", [])
                    if functions and hasattr(module, functions[0]):
                        func = getattr(module, functions[0])
                        sig = inspect.signature(func)
                        params = sig.parameters

                        if len(params) == 0:
                            func()
                            result = "0"
                        else:
                            default_args = {}
                            for param_name, param in params.items():
                                if param.default is not inspect.Parameter.empty:
                                    default_args[param_name] = param.default
                                elif param_name == 'save_path':
                                    default_args[param_name] = "screenshot.png"
                                elif param_name == 'image_path':
                                    default_args[param_name] = "screenshot.png"

                            if len(default_args) >= len(params):
                                result = func(**default_args)
                            else:
                                result = "0"

                        if result == "wait":
                            save_state({
                                "func_name": func_name,
                                "module_name": module_name,
                                "script_path": script_path
                            })
                            return "wait"
                        else:
                            clear_state()
                            return result
                finally:
                    sys.path[:] = original_path

            clear_state()
            return "0"

    clear_state()
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("输入信息不合法，请输入有效编号(1-{})或q退出\n".format(len(cmd_list)))
        f.write("feishu_reply_over\n")

    return "wait"