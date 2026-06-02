import re, json

with open('data/office_github_today.md', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<!-- OFFICE_GITHUB_DATA:(.+?):OFFICE_GITHUB_DATA -->', content, re.DOTALL)
if match:
    try:
        data = json.loads(match.group(1))
        print('JSON parsed successfully!')
        print('github count:', len(data))
        print('First project:', data[0]['name'])
    except Exception as e:
        print('JSON parse error:', e)
else:
    print('No OFFICE_GITHUB_DATA found')
