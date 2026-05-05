---
name: "send-file-request"
description: "Writes file send request to sendrequest.log. Invoke when user asks to send/upload a file."
---

# Send File Request

This skill handles file sending requests by writing to `talk/sendrequest.log`.

## When to Invoke

- User asks to send a file
- User asks to upload a file to Feishu
- User requests sending a specific file

## How It Works

When you need to send a file to Feishu:

1. Write the file path in format `send:<absolute_file_path>` to `talk/sendrequest.log`
2. The `monitor_sendrequest` function will detect this and call `send_file_to_feishu()`
3. The file will be sent to the configured Feishu chat

## Usage

```python
# Format to write to talk/sendrequest.log
"send:d:\\work\\zymxs\\openspider3\\config.py"

# Example content in sendrequest.log:
# send:d:\work\zymxs\openspider3\config.py
# send:d:\work\zymxs\openspider3\combined_bot.py
```

## Implementation

Use the `Write` tool to write to `talk/sendrequest.log` with the format:
```
send:<file_path>
```

The path should be an absolute path or relative to the project root `d:\work\zymxs\openspider3`.
