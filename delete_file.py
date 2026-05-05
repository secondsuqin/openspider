import sys
import os

def delete_file(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"已删除: {filepath}")
        return True
    else:
        print(f"文件不存在: {filepath}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        delete_file(sys.argv[1])
    else:
        print("请提供要删除的文件路径")