#!/usr/bin/env python3
"""푸터 데이터 동기화 스크립트"""
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# HTML 파일들
files = {
    'projects': SCRIPT_DIR / 'projects.html',
    'drawings': SCRIPT_DIR / 'drawings.html',
    'graphics': SCRIPT_DIR / 'graphics.html',
    'about': SCRIPT_DIR / 'about.html'
}

# 각 섹션의 데이터 추출
def get_data(html_file):
    if not html_file.exists():
        return []
    content = html_file.read_text(encoding='utf-8')
    match = re.search(r'<script type="application/json" id="projectsData">\s*(\[[\s\S]*?\])\s*</script>', content)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return []

projects_data = get_data(files['projects'])
drawings_data = get_data(files['drawings'])
graphics_data = get_data(files['graphics'])

print(f'Projects: {len(projects_data)} items')
print(f'Drawings: {len(drawings_data)} items')
print(f'Graphics: {len(graphics_data)} items')

# footerData 생성
footer_data = {
    'projects': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in projects_data],
    'drawings': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in drawings_data],
    'graphics': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in graphics_data]
}

footer_json = json.dumps(footer_data, ensure_ascii=False)
print(f'\nfooterData preview:')
print(f'  Projects: {[p["title"] for p in footer_data["projects"]]}')
print(f'  Drawings: {[p["title"] for p in footer_data["drawings"]]}')
print(f'  Graphics: {[p["title"] for p in footer_data["graphics"]]}')

# 각 HTML 파일에 footerData 추가
for name, html_file in files.items():
    if not html_file.exists():
        print(f'Skipped: {name}.html (not found)')
        continue
    
    content = html_file.read_text(encoding='utf-8')
    
    # 기존 footerData 제거
    content = re.sub(r'\s*<script type="application/json" id="footerData">[\s\S]*?</script>', '', content)
    
    # script.js 바로 전에 추가
    footer_script = f'\n  <script type="application/json" id="footerData">{footer_json}</script>'
    content = re.sub(r'(\s*<script src="script\.js">)', footer_script + r'\1', content)
    
    html_file.write_text(content, encoding='utf-8')
    print(f'Updated: {name}.html')

print('\n✅ 푸터 데이터 동기화 완료!')
