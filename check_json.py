import re, json

with open('data/office_skills_today.md', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<!-- OFFICE_SKILL_DATA:(.+?):OFFICE_SKILL_DATA -->', content, re.DOTALL)
if match:
    try:
        data = json.loads(match.group(1))
        print('JSON parsed successfully!')
        print('office_skills count:', len(data.get('office_skills', [])))
        print('First skill:', data['office_skills'][0]['name'])
    except Exception as e:
        print('JSON parse error:', e)
else:
    print('No OFFICE_SKILL_DATA found')
