#!/usr/bin/env python3
"""Replace diagrams in README.md with generated versions."""

import re

# Read generated diagrams
with open('diagram_out.txt', 'r', encoding='utf-8') as f:
    diagrams = f.read()

# Split by triple backtick fences
parts = diagrams.split('```')
flow_content = parts[1].strip('\n')
reg_content = parts[3].strip('\n')

print(f'Flow content: {len(flow_content)} chars')
print(f'Registry content: {len(reg_content)} chars')

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

# 1. Replace High-Level System Flow diagram
pattern = r'### High-Level System Flow\n\n```\n.*?\n```'
replacement = '### High-Level System Flow\n\n```\n' + flow_content + '\n```'
new_readme = re.sub(pattern, replacement, readme, count=1, flags=re.DOTALL)

if new_readme == readme:
    print("WARNING: High-Level System Flow pattern didn't match!")
else:
    print('Flow diagram replaced.')

# 2. Replace Model Registry diagram (after "### Key Design Principle")
parts_readme = new_readme.split('### Key Design Principle')
if len(parts_readme) == 2:
    before = parts_readme[0]
    after_kdp = parts_readme[1]

    idx_start = after_kdp.find('```')
    if idx_start >= 0:
        idx_end = after_kdp.find('```', idx_start + 3)
        if idx_end >= 0:
            new_block = '```\n' + reg_content + '\n```'
            after_kdp = after_kdp[:idx_start] + new_block + after_kdp[idx_end + 3:]
            new_readme = before + '### Key Design Principle' + after_kdp
            print('Registry diagram replaced.')
        else:
            print('WARNING: Could not find closing ```')
    else:
        print('WARNING: Could not find opening ```')
else:
    print('WARNING: Could not find "### Key Design Principle"')

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(new_readme)

print('README.md updated successfully.')
