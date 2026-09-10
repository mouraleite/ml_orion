import json
import re

log_file = r'C:\Users\Usuario\.gemini\antigravity-ide\brain\27fcb9c8-c1e4-43b2-9279-6203bfa57d8c\.system_generated\logs\transcript_full.jsonl'
lines_dict = {}
with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            step_idx = data.get('step_index', 0)
            if step_idx > 130:
                continue
            if data.get('type') == 'VIEW_FILE' and 'tracking.py' in data.get('content', ''):
                content = data['content']
                if 'Showing lines ' in content:
                    parts = content.split('remove the line number, colon, and leading space.\n')
                    if len(parts) > 1:
                        code_lines = parts[1].split('\nThe above content')[0].split('\n')
                        for cl in code_lines:
                            if cl.strip() == '': continue
                            match = re.match(r'^(\d+):\s(.*)', cl)
                            if match:
                                num = int(match.group(1))
                                text = match.group(2)
                                lines_dict[num] = text
        except:
            pass

if not lines_dict:
    print('No lines found in VIEW_FILE events.')
else:
    max_line = max(lines_dict.keys())
    with open('tracking_restored.py', 'w', encoding='utf-8') as out:
        for i in range(1, max_line + 1):
            out.write(lines_dict.get(i, '') + '\n')
    print(f'Restored {max_line} lines to tracking_restored.py')
