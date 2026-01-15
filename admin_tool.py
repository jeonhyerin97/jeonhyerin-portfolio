#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JEONHYERIN Portfolio Admin Tool
프로젝트 및 드로잉 관리 도구

사용법:
    python admin_tool.py

기능:
    1. 프로젝트 추가
    2. 프로젝트 수정
    3. 프로젝트 삭제
    4. 프로젝트 목록 보기
    5. 드로잉 관리 (동일 기능)
"""

import json
import re
import os
from pathlib import Path

# 파일 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECTS_HTML = SCRIPT_DIR / "projects.html"
DRAWINGS_HTML = SCRIPT_DIR / "drawings.html"
IMAGES_DIR = SCRIPT_DIR / "images"


def extract_json_data(html_content):
    """HTML에서 JSON 데이터 추출"""
    pattern = r'<script type="application/json" id="projectsData">\s*(\[[\s\S]*?\])\s*</script>'
    match = re.search(pattern, html_content)
    if match:
        return json.loads(match.group(1))
    return []


def update_json_in_html(html_content, new_data):
    """HTML 내 JSON 데이터 업데이트"""
    json_str = json.dumps(new_data, indent=4, ensure_ascii=False)
    pattern = r'(<script type="application/json" id="projectsData">)\s*\[[\s\S]*?\]\s*(</script>)'
    replacement = f'\\1\n  {json_str}\n  \\2'
    return re.sub(pattern, replacement, html_content)


def generate_grid_items_html(projects):
    """그리드 아이템 HTML 생성"""
    items = []
    for i, project in enumerate(projects):
        slug = project.get('slug', project['title'].lower().replace(' ', '-'))
        year = project.get('duration', project.get('year', ''))[:4]
        
        item = f'''      <article class="grid-item" data-project="{i}">
        <button class="grid-item-btn" aria-haspopup="dialog">
          <div class="grid-item-image">
            <div class="grid-thumb" style="background-image: url('images/projects/{slug}/cover.jpg');" aria-label="{project['title']} thumbnail"></div>
          </div>
          <div class="grid-item-overlay">
            <span class="grid-item-title">{project['title']}</span>
            <span class="grid-item-year">{year}</span>
          </div>
        </button>
      </article>'''
        items.append(item)
    
    return '\n\n'.join(items)


def update_grid_items_in_html(html_content, projects):
    """HTML 내 그리드 아이템 업데이트"""
    new_grid_html = generate_grid_items_html(projects)
    pattern = r'(<div class="archive-grid" role="list">)\s*\n[\s\S]*?(</div>\s*</main>)'
    replacement = f'\\1\n      \n{new_grid_html}\n\n    \\2'
    return re.sub(pattern, replacement, html_content)


def create_project_folder(slug, project_type='projects'):
    """프로젝트 이미지 폴더 생성"""
    folder_path = IMAGES_DIR / project_type / slug
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # model_images 폴더도 생성
    model_folder = folder_path / "model_images"
    model_folder.mkdir(exist_ok=True)
    
    print(f"  📁 폴더 생성됨: {folder_path}")
    print(f"  📁 모형 이미지 폴더: {model_folder}")
    return folder_path


def list_projects(html_path):
    """프로젝트 목록 출력"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    projects = extract_json_data(content)
    
    print("\n" + "="*60)
    print("📋 프로젝트 목록")
    print("="*60)
    
    for p in projects:
        studio = f" | {p.get('studio', '')}" if p.get('studio') else ""
        duration = p.get('duration', p.get('year', ''))
        print(f"  [{p['index']}] {p['title']} ({duration}){studio}")
    
    print("="*60)
    return projects


def add_project(html_path, position=None):
    """새 프로젝트 추가"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    projects = extract_json_data(content)
    
    print("\n" + "="*60)
    print("➕ 새 프로젝트 추가")
    print("="*60)
    
    # 프로젝트 정보 입력
    title = input("  제목 (TITLE): ").strip().upper()
    if not title:
        print("  ❌ 제목은 필수입니다.")
        return
    
    slug = input(f"  슬러그 (기본값: {title.lower().replace(' ', '-')}): ").strip()
    if not slug:
        slug = title.lower().replace(' ', '-')
    
    location = input("  위치 (LOCATION, 선택): ").strip()
    duration = input("  기간 (DURATION, 예: 2025 또는 Sep 2025 – Dec 2025): ").strip()
    program = input("  프로그램 (PROGRAM, 선택): ").strip()
    studio = input("  스튜디오 (STUDIO, 선택): ").strip()
    description = input("  설명 (DESCRIPTION, 선택): ").strip()
    
    # 위치 결정
    if position is None:
        pos_input = input(f"  삽입 위치 (1-{len(projects)+1}, 기본값: 맨 끝): ").strip()
        if pos_input:
            position = int(pos_input) - 1
        else:
            position = len(projects)
    else:
        position = position - 1  # 1-indexed to 0-indexed
    
    # 새 프로젝트 객체 생성
    new_project = {
        "id": len(projects) + 1,
        "index": str(position + 1).zfill(2),
        "slug": slug,
        "title": title,
        "location": location,
        "duration": duration,
        "program": program,
        "studio": studio,
        "description": description
    }
    
    # 프로젝트 삽입
    projects.insert(position, new_project)
    
    # index와 id 재정렬
    for i, p in enumerate(projects):
        p['id'] = i + 1
        p['index'] = str(i + 1).zfill(2)
    
    # HTML 업데이트
    content = update_json_in_html(content, projects)
    content = update_grid_items_in_html(content, projects)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 이미지 폴더 생성
    create_project_folder(slug)
    
    print(f"\n  ✅ '{title}' 프로젝트가 {position + 1}번 위치에 추가되었습니다.")
    print(f"  📁 이미지 폴더: images/projects/{slug}/")
    print(f"     - cover.jpg (메인 이미지)")
    print(f"     - 01.jpg, 02.jpg... (서브 이미지)")
    print(f"     - model_images/1.jpg, 2.jpg... (모형 이미지)")
    print(f"     - 1.jpg, 2.jpg... (엑스트라 이미지)")


def edit_project(html_path):
    """프로젝트 수정"""
    projects = list_projects(html_path)
    
    print("\n" + "="*60)
    print("✏️ 프로젝트 수정")
    print("="*60)
    
    index_input = input("  수정할 프로젝트 번호 (01, 02, ...): ").strip()
    
    project = None
    project_idx = None
    for i, p in enumerate(projects):
        if p['index'] == index_input:
            project = p
            project_idx = i
            break
    
    if not project:
        print("  ❌ 해당 프로젝트를 찾을 수 없습니다.")
        return
    
    print(f"\n  현재 값 (Enter로 유지, '-'로 삭제)")
    print(f"  " + "-"*50)
    
    # 각 필드 수정
    fields = ['title', 'slug', 'location', 'duration', 'program', 'studio', 'description']
    labels = ['제목', '슬러그', '위치', '기간', '프로그램', '스튜디오', '설명']
    
    for field, label in zip(fields, labels):
        current = project.get(field, '')
        new_value = input(f"  {label} [{current}]: ").strip()
        
        if new_value == '-':
            project[field] = ''
        elif new_value:
            if field == 'title':
                project[field] = new_value.upper()
            else:
                project[field] = new_value
    
    # HTML 업데이트
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = update_json_in_html(content, projects)
    content = update_grid_items_in_html(content, projects)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n  ✅ '{project['title']}' 프로젝트가 수정되었습니다.")


def delete_project(html_path):
    """프로젝트 삭제"""
    projects = list_projects(html_path)
    
    print("\n" + "="*60)
    print("🗑️ 프로젝트 삭제")
    print("="*60)
    
    index_input = input("  삭제할 프로젝트 번호 (01, 02, ...): ").strip()
    
    project = None
    project_idx = None
    for i, p in enumerate(projects):
        if p['index'] == index_input:
            project = p
            project_idx = i
            break
    
    if not project:
        print("  ❌ 해당 프로젝트를 찾을 수 없습니다.")
        return
    
    confirm = input(f"  '{project['title']}' 프로젝트를 삭제하시겠습니까? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("  취소되었습니다.")
        return
    
    # 프로젝트 삭제
    projects.pop(project_idx)
    
    # index와 id 재정렬
    for i, p in enumerate(projects):
        p['id'] = i + 1
        p['index'] = str(i + 1).zfill(2)
    
    # HTML 업데이트
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = update_json_in_html(content, projects)
    content = update_grid_items_in_html(content, projects)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n  ✅ '{project['title']}' 프로젝트가 삭제되었습니다.")
    print(f"  ⚠️ 이미지 폴더는 수동으로 삭제해야 합니다: images/projects/{project['slug']}/")


def main_menu():
    """메인 메뉴"""
    while True:
        print("\n" + "="*60)
        print("🏛️ JEONHYERIN Portfolio Admin Tool")
        print("="*60)
        print("  [1] 프로젝트 목록 보기")
        print("  [2] 프로젝트 추가")
        print("  [3] 프로젝트 수정")
        print("  [4] 프로젝트 삭제")
        print("  [5] 드로잉 목록 보기")
        print("  [6] 드로잉 추가")
        print("  [7] 드로잉 수정")
        print("  [8] 드로잉 삭제")
        print("  [0] 종료")
        print("="*60)
        
        choice = input("  선택: ").strip()
        
        if choice == '1':
            list_projects(PROJECTS_HTML)
        elif choice == '2':
            add_project(PROJECTS_HTML)
        elif choice == '3':
            edit_project(PROJECTS_HTML)
        elif choice == '4':
            delete_project(PROJECTS_HTML)
        elif choice == '5':
            list_projects(DRAWINGS_HTML)
        elif choice == '6':
            add_project(DRAWINGS_HTML)
        elif choice == '7':
            edit_project(DRAWINGS_HTML)
        elif choice == '8':
            delete_project(DRAWINGS_HTML)
        elif choice == '0':
            print("\n  👋 종료합니다.")
            break
        else:
            print("  ❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    main_menu()
