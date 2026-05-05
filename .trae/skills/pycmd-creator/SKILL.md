---
name: "pycmd-creator"
description: "Creates PY_CMD subfolder, Python script, and updates CMD_list.json. Invoke when user wants to create a new PYCMD command."
---

# PYCMD Creator

This skill creates a new PY_CMD command module with the following steps:

## Steps

1. **Create subfolder**: Create `PY_CMD/XXX/` folder (XXX = command name)
2. **Create Python script**: Create `PY_CMD/XXX/xxx.py` with the required function
3. **Update CMD_list.json**: Add the new command configuration to `PY_CMD/CMD_list.json`

## Command Configuration Format

```json
{
  "name": "命令名称",
  "folder": "文件夹名",
  "file": "脚本文件名",
  "functions": ["函数名"],
  "description": "功能描述"
}
```

## Usage

When user asks to create a "PYCMD" command:
1. Determine the command name, functions, and description from user request
2. Create the folder structure under `PY_CMD/`
3. Write the Python script with required functions
4. Update `CMD_list.json` with the new command entry

## Example

User request: "创建一个截图命令"
1. Create folder: `PY_CMD/Screen_Shot/`
2. Create script: `PY_CMD/Screen_Shot/screen_shot.py` with `capture_and_send()` function
3. Update `CMD_list.json` with the new entry