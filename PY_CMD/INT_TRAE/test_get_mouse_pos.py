import os
import sys
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(SCRIPT_DIR, "mouse_pos.json")
GET_MOUSE_POS_SCRIPT = os.path.join(SCRIPT_DIR, "get_mouse_pos.py")

def test_import_module():
    print("[测试1] 检查模块导入...")
    try:
        import tkinter as tk
        from tkinter import messagebox
        import pyautogui
        print("  ✓ tkinter, pyautogui 模块导入成功")
        return True
    except ImportError as e:
        print(f"  ✗ 模块导入失败: {e}")
        return False

def test_json_file_exists():
    print("[测试2] 检查 mouse_pos.json 是否存在...")
    if os.path.exists(POS_FILE):
        print(f"  ✓ 文件存在: {POS_FILE}")
        return True
    else:
        print(f"  - 文件不存在（需要运行 get_mouse_pos.py 创建）: {POS_FILE}")
        return None

def test_json_content_valid():
    print("[测试3] 检查 mouse_pos.json 内容是否有效...")
    if not os.path.exists(POS_FILE):
        print("  - 跳过：文件不存在")
        return None
    try:
        with open(POS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "clicks" not in data or "count" not in data:
            print(f"  ✗ 内容格式错误: 缺少必要字段")
            return False

        clicks = data["clicks"]
        if not isinstance(clicks, list) or len(clicks) == 0:
            print(f"  ✗ clicks 字段无效: {clicks}")
            return False

        for i, click in enumerate(clicks):
            if "type" not in click or "abs_x" not in click or "abs_y" not in click:
                print(f"  ✗ 第{i+1}次点击数据格式错误: {click}")
                return False

        print(f"  ✓ 内容有效: 共 {data['count']} 次点击")
        for i, c in enumerate(clicks):
            print(f"      第{i+1}次: {c['type']}键 | 延迟{c.get('delay', 0)}s | 坐标({c['abs_x']}, {c['abs_y']})")
        return True
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON 解析失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 读取文件失败: {e}")
        return False

def test_script_exists():
    print("[测试4] 检查 get_mouse_pos.py 是否存在...")
    if os.path.exists(GET_MOUSE_POS_SCRIPT):
        print(f"  ✓ 脚本存在: {GET_MOUSE_POS_SCRIPT}")
        return True
    else:
        print(f"  ✗ 脚本不存在: {GET_MOUSE_POS_SCRIPT}")
        return False

def test_launch_script():
    print("[测试5] 启动 get_mouse_pos.py 进行交互测试...")
    print("  提示：请在弹出的窗口中操作")
    print("  1. 点击 [开始记录] 按钮")
    print("  2. 点击目标位置（可多次点击，支持左右键）")
    print("  3. 点击 [结束记录] 保存")
    print("  （由于是GUI程序，将保持运行直到用户完成操作或关闭窗口）")
    try:
        subprocess.run(["python", GET_MOUSE_POS_SCRIPT])
        return True
    except Exception as e:
        print(f"  ✗ 启动失败: {e}")
        return False

def main():
    print("=" * 50)
    print("get_mouse_pos.py 测试脚本")
    print("=" * 50)

    results = []
    results.append(("模块导入", test_import_module()))
    results.append(("脚本存在", test_script_exists()))
    results.append(("JSON文件存在", test_json_file_exists()))
    results.append(("JSON内容有效", test_json_content_valid()))

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    for name, result in results:
        if result is True:
            status = "✓ 通过"
        elif result is False:
            status = "✗ 失败"
        else:
            status = "- 跳过"
        print(f"  {name}: {status}")

    all_passed = all(r is True for _, r in results if r is not None)
    if all_passed:
        print("\n所有测试通过！")
    else:
        print("\n部分测试未通过或跳过。")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--launch":
        test_launch_script()
    else:
        main()
        print("\n如需进行GUI交互测试，请运行: python test_get_mouse_pos.py --launch")
