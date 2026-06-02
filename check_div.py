import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 office-section 部分
start = content.find('<div class="section-panel" id="office-section">')
end = content.find('<!-- end office-section -->') + len('<!-- end office-section -->')
office_section = content[start:end]

# 统计 div 开启和关闭
div_opens = len(re.findall(r'<div[\s>]', office_section))
div_closes = len(re.findall(r'</div>', office_section))

print(f'Div opens: {div_opens}')
print(f'Div closes: {div_closes}')
print(f'Difference: {div_opens - div_closes}')

# 逐行跟踪
lines = office_section.split('\n')
stack = 0
for i, line in enumerate(lines, 1):
    opens = len(re.findall(r'<div[\s>]', line))
    closes = len(re.findall(r'</div>', line))
    if opens or closes:
        prev = stack
        stack += opens - closes
        safe_line = line[:80].encode('ascii', 'replace').decode('ascii')
        print(f'Line {i}: +{opens}/-{closes} -> stack={stack} | {safe_line}')
