#!/usr/bin/env python3
"""Check all tag nesting in office-section"""
from html.parser import HTMLParser

class TagTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.in_office = False
        self.errors = []
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        id_val = attrs_dict.get('id', '')
        cls_val = attrs_dict.get('class', '')
        
        if tag == 'div' and 'office-section' in id_val:
            self.in_office = True
            
        if self.in_office:
            self.stack.append((tag, id_val, cls_val))
            
    def handle_endtag(self, tag):
        if not self.in_office:
            return
            
        # Find matching start tag
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack.pop(i)
                break
        else:
            self.errors.append(f"Unmatched </{tag}>")
            
        # Check if we closed office-section
        if tag == 'div':
            for t, id_val, _ in self.stack:
                if id_val == 'office-section':
                    return
            self.in_office = False

with open('index.html', encoding='utf-8') as f:
    content = f.read()

# Extract office section
start = content.find('id="office-section"')
end = content.find('end office-section')

# Parse just that portion
tracker = TagTracker()
tracker.feed(content[start-100:end+60])

print("Errors:", tracker.errors if tracker.errors else "None")
print("Unclosed tags:", tracker.stack)
