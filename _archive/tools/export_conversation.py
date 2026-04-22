import json
import re
from datetime import datetime

fp = r'C:\Users\Jieic\.claude\projects\D--AI-AI------\faa98b3b-0200-4ac6-8cae-9dda242060ec.jsonl'

with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()

conversations = []

for line in lines:
    try:
        data = json.loads(line)
        msg_type = data.get('type', '')

        if msg_type == 'assistant':
            msg = data.get('message', {})
            content_list = msg.get('content', [])
            if isinstance(content_list, list):
                for c in content_list:
                    if c.get('type') == 'text':
                        text = c.get('text', '')
                        ts = data.get('timestamp', '')
                        if ts:
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            dt_str = ''
                        conversations.append(f"**[{dt_str}] AI 回复：**\n\n{text}\n")

        elif msg_type == 'human' or msg_type == 'user':
            content = data.get('message', {}).get('content', '')
            if not content:
                content = data.get('display', '')
            ts = data.get('timestamp', '')
            if ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                dt_str = ''
            if content:
                conversations.append(f"**[{dt_str}] 用户：**\n\n{content}\n")

        elif msg_type == 'last-prompt':
            content = data.get('lastPrompt', '')
            ts = data.get('timestamp', '')
            if ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                dt_str = ''
            if content:
                conversations.append(f"**[{dt_str}] 用户：**\n\n{content}\n")

    except Exception as e:
        pass

output = """# Claude Code 会话导出

**会话ID：** faa98b3b-0200-4ac6-8cae-9dda242060ec
**项目：** D:\\AI\\AI小说创作系统
**导出时间：** {export_time}

---

""".format(export_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

output += "\n\n---\n\n".join(conversations)

out_fp = r'd:\AI\AI小说创作系统\claude_conversation_export.md'
with open(out_fp, 'w', encoding='utf-8') as f:
    f.write(output)

print(f'已导出到: {out_fp}')
print(f'共 {len(conversations)} 条消息')
