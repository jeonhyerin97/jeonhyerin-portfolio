#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JEONHYERIN Portfolio Admin Tool - Pro Version v2
전문 포트폴리오 관리 도구

기능:
    - 프로젝트/드로잉 관리 (CRUD)
    - 이미지 관리 (드래그앤드롭 영역, 자동분류, 자동파일명)
    - 이미지 자동 최적화 (용량 압축)
    - 레이아웃 편집
    - About 페이지 편집
    - 백업/복원

사용법:
    python admin_gui.py
"""

import json
import re
import os
import webbrowser
import shutil
import subprocess
from urllib.parse import quote
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from PIL import Image, ImageTk
import threading

# 파일 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECTS_HTML = SCRIPT_DIR / "projects.html"
DRAWINGS_HTML = SCRIPT_DIR / "drawings.html"
GRAPHICS_HTML = SCRIPT_DIR / "graphics.html"
ABOUT_HTML = SCRIPT_DIR / "about.html"
INDEX_HTML = SCRIPT_DIR / "index.html"
STUDY_HTML = SCRIPT_DIR / "study.html"
STYLES_CSS = SCRIPT_DIR / "styles.css"
SCRIPT_JS = SCRIPT_DIR / "script.js"
TABS_CONFIG_JSON = SCRIPT_DIR / "tabs_config.json"
HOME_DATA_JSON = SCRIPT_DIR / "home_data.json"
IMAGES_DIR = SCRIPT_DIR / "images"
HOME_IMAGES_DIR = IMAGES_DIR / "home"
BACKUP_DIR = SCRIPT_DIR / "backups"
BACKUP_METADATA_FILES = {"VERSION.txt", "CHANGELOG.md", "SELECTED.txt"}
DEFAULT_GITHUB_REPO_URL = "https://github.com/jeonhyerin97/jeonhyerin-portfolio"


def get_backup_target_map():
    """백업 대상 파일 매핑 (filename -> Path)."""
    return {
        "projects.html": PROJECTS_HTML,
        "drawings.html": DRAWINGS_HTML,
        "graphics.html": GRAPHICS_HTML,
        "about.html": ABOUT_HTML,
        "index.html": INDEX_HTML,
        "study.html": STUDY_HTML,
        "styles.css": STYLES_CSS,
        "script.js": SCRIPT_JS,
        "home_data.json": HOME_DATA_JSON,
        "tabs_config.json": TABS_CONFIG_JSON,
    }


def list_backup_payload_files(folder: Path):
    """백업 폴더에서 메타데이터 파일을 제외한 실제 백업 파일 목록."""
    if not folder.exists():
        return []
    return sorted(
        [
            f
            for f in folder.iterdir()
            if f.is_file() and f.name not in BACKUP_METADATA_FILES
        ],
        key=lambda p: p.name.lower(),
    )

# 이미지 최적화 설정
THUMBNAIL_SIZE = (100, 100)
THUMB_MAX_SIZE = 1000      # 썸네일 이미지 (그리드용)
MAIN_MAX_SIZE = 2000       # 메인 이미지 (상세페이지 첫 이미지)
SUB_MAX_SIZE = 2000        # 서브 이미지 최대 크기
MODEL_MAX_SIZE = 1200      # 모델 이미지 최대 크기
SLIDE_MAX_SIZE = 1600      # 슬라이드 이미지 최대 크기
WEBP_QUALITY = 80          # WebP 품질 (75-85 권장)
JPEG_QUALITY = 80          # JPEG 품질 (fallback)
USE_WEBP = True            # WebP 포맷 사용 여부


class ModernStyle:
    """모던 스타일 정의"""
    BG_WHITE = "#ffffff"
    BG_LIGHT = "#f5f5f5"
    BG_HOVER = "#eeeeee"
    BG_SELECTED = "#e0e0e0"
    BG_DROP = "#e8f4fd"
    TEXT_PRIMARY = "#000000"
    TEXT_MUTED = "#555555"
    TEXT_SUBTLE = "#888888"
    BORDER = "#e0e0e0"
    BORDER_DROP = "#2196F3"
    ACCENT = "#000000"
    DANGER = "#cc3333"
    SUCCESS = "#28a745"
    
    @classmethod
    def get_font(cls, size=11, weight="normal"):
        return ("Segoe UI", size, weight)


class ImageOptimizer:
    """
    이미지 최적화 클래스
    
    기능:
    - 자동 리사이즈 (비율 유지)
    - WebP 포맷 자동 변환
    - EXIF 회전 자동 처리
    - 품질 최적화 (75-85)
    """
    
    @staticmethod
    def optimize_for_web(image_path, max_size, quality=None, use_webp=None):
        """
        웹용 이미지 최적화
        
        Args:
            image_path: 원본 이미지 경로
            max_size: 최대 크기 (px)
            quality: 품질 (75-85 권장)
            use_webp: WebP 포맷 사용 여부
        
        Returns:
            (output_path, reduction_percent)
        """
        if quality is None:
            quality = WEBP_QUALITY
        if use_webp is None:
            use_webp = USE_WEBP
            
        try:
            img = Image.open(image_path)
            original_size = os.path.getsize(image_path)
            
            # 1. EXIF 회전 처리
            img = ImageOptimizer._fix_orientation(img)
            
            # 2. 리사이즈 (비율 유지)
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 3. 색상 모드 변환
            if img.mode == 'RGBA':
                # 투명 배경을 흰색으로 변환
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 4. WebP 또는 JPEG로 저장
            if use_webp:
                output_path = image_path.with_suffix('.webp')
                img.save(output_path, 'WEBP', quality=quality, method=6)
            else:
                output_path = image_path.with_suffix('.jpg')
                img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
            
            # 5. 원본이 다른 확장자였으면 삭제
            if image_path != output_path and image_path.exists():
                os.remove(str(image_path))
            
            # 6. 용량 감소율 계산
            new_file_size = os.path.getsize(output_path)
            reduction = ((original_size - new_file_size) / original_size) * 100 if original_size > 0 else 0
            
            return output_path, reduction
            
        except Exception as e:
            print(f"Optimize error: {e}")
            return image_path, 0
    
    @staticmethod
    def _fix_orientation(img):
        """EXIF 회전 정보에 따라 이미지 회전"""
        try:
            from PIL import ExifTags
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except:
            pass
        return img
    
    @staticmethod
    def create_thumbnail(image_path, size=THUMBNAIL_SIZE):
        """썸네일 생성 (UI 표시용)"""
        try:
            img = Image.open(image_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except:
            return None
    
    @staticmethod
    def process_batch(file_paths, target_folder, image_type='sub'):
        """
        배치 이미지 처리 파이프라인
        
        1. 파일 순서대로 처리
        2. 첫 이미지는 cover, 이후는 01, 02, 03... 순번
        3. 자동 리사이즈 + WebP 변환
        4. 타겟 폴더에 저장
        
        Args:
            file_paths: 이미지 파일 경로 리스트
            target_folder: 저장할 폴더
            image_type: 'thumb', 'main', 'sub', 'model', 'slide'
        
        Returns:
            (processed_files, total_reduction)
        """
        target_folder = Path(target_folder)
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # 이미지 타입별 최대 크기 설정
        max_sizes = {
            'thumb': THUMB_MAX_SIZE,
            'main': MAIN_MAX_SIZE,
            'sub': SUB_MAX_SIZE,
            'model': MODEL_MAX_SIZE,
            'slide': SLIDE_MAX_SIZE
        }
        max_size = max_sizes.get(image_type, SUB_MAX_SIZE)
        
        # 서브폴더 처리
        if image_type == 'model':
            target_folder = target_folder / "model_images"
            target_folder.mkdir(exist_ok=True)
        elif image_type == 'slide':
            target_folder = target_folder / "slide_images"
            target_folder.mkdir(exist_ok=True)
        
        processed_files = []
        total_reduction = 0
        ext = '.webp' if USE_WEBP else '.jpg'
        
        for i, file_path in enumerate(file_paths):
            src = Path(file_path)
            
            # 파일명 결정
            if image_type == 'thumb':
                new_name = f"thumb{ext}"
            elif image_type == 'main':
                new_name = f"main{ext}"
            elif image_type == 'sub':
                # 01, 02, 03... 형식
                new_name = f"{str(i + 1).zfill(2)}{ext}"
            else:
                # 1, 2, 3... 형식
                new_name = f"{i + 1}{ext}"
            
            # 파일 복사
            dst = target_folder / new_name
            shutil.copy(str(src), str(dst))
            
            # 최적화
            optimized_path, reduction = ImageOptimizer.optimize_for_web(dst, max_size)
            processed_files.append(optimized_path)
            total_reduction += reduction
        
        avg_reduction = total_reduction / len(file_paths) if file_paths else 0
        return processed_files, avg_reduction


class GitAutomation:
    """
    Git 자동화 모듈
    
    기능:
    - 변경사항 확인 (git status)
    - 자동 스테이징 (git add)
    - 자동 커밋 (git commit)
    - 자동 푸시 (git push)
    
    Netlify와 연동되어 push 후 자동 배포됨
    """
    
    # Windows에서 Git 기본 설치 경로
    GIT_PATHS = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        "git"  # PATH에 등록된 경우
    ]
    
    def __init__(self, repo_path):
        """
        Args:
            repo_path: Git 저장소 루트 경로
        """
        self.repo_path = Path(repo_path)
        self.git_exe = self._find_git()
    
    def _find_git(self):
        """Git 실행 파일 경로 찾기"""
        for git_path in self.GIT_PATHS:
            if Path(git_path).exists() or git_path == "git":
                try:
                    result = subprocess.run(
                        [git_path, '--version'],
                        capture_output=True,
                        text=True,
                        encoding='utf-8'
                    )
                    if result.returncode == 0:
                        return git_path
                except:
                    continue
        return None
    
    def _run_git(self, *args):
        """Git 명령 실행"""
        if not self.git_exe:
            return False, "", "Git을 찾을 수 없습니다. Git을 설치해주세요."
        try:
            result = subprocess.run(
                [self.git_exe] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return False, "", str(e)
    
    def is_git_repo(self):
        """Git 저장소인지 확인"""
        git_dir = self.repo_path / ".git"
        return git_dir.exists()
    
    def init_repo(self):
        """Git 저장소 초기화"""
        success, stdout, stderr = self._run_git('init')
        return success, stdout or stderr
    
    def has_remote(self):
        """원격 저장소가 설정되어 있는지 확인"""
        success, stdout, _ = self._run_git('remote', '-v')
        return success and len(stdout.strip()) > 0

    @staticmethod
    def _normalize_remote_url(url):
        """URL 비교를 위한 정규화 (.git, 슬래시 차이 무시)"""
        normalized = url.strip().rstrip('/')
        if normalized.endswith('.git'):
            normalized = normalized[:-4]
        return normalized

    def get_remote_url(self, remote_name='origin'):
        """원격 저장소 URL 조회"""
        success, stdout, _ = self._run_git('remote', 'get-url', remote_name)
        if success:
            return stdout.strip()
        return None

    def ensure_remote(self, expected_url, remote_name='origin'):
        """원격 저장소를 expected_url로 보정 (없으면 추가, 있으면 set-url)"""
        current_url = self.get_remote_url(remote_name)
        if current_url:
            if self._normalize_remote_url(current_url) == self._normalize_remote_url(expected_url):
                return True, f"{remote_name} 연결 확인됨: {current_url}"
            success, stdout, stderr = self._run_git('remote', 'set-url', remote_name, expected_url)
            return success, stdout or stderr or f"{remote_name} URL 업데이트 완료"
        success, stdout, stderr = self._run_git('remote', 'add', remote_name, expected_url)
        return success, stdout or stderr or f"{remote_name} 연결 완료"
    
    def has_changes(self):
        """변경사항이 있는지 확인"""
        success, stdout, _ = self._run_git('status', '--porcelain')
        if success:
            return len(stdout.strip()) > 0
        return False
    
    def get_status(self):
        """현재 상태 반환"""
        success, stdout, stderr = self._run_git('status', '--short')
        if success:
            return stdout
        return stderr
    
    def add_all(self):
        """모든 변경사항 스테이징"""
        success, stdout, stderr = self._run_git('add', '-A')
        return success, stdout or stderr
    
    def commit(self, message):
        """커밋 생성"""
        success, stdout, stderr = self._run_git('commit', '-m', message)
        return success, stdout or stderr

    @staticmethod
    def _join_git_output(*parts):
        return "\n".join([p for p in parts if p])

    @staticmethod
    def _is_upstream_error(message):
        text = (message or "").lower()
        return (
            "no upstream branch" in text
            or "has no upstream branch" in text
            or "--set-upstream" in text
        )

    @staticmethod
    def _is_non_fast_forward_error(message):
        text = (message or "").lower()
        return (
            "fetch first" in text
            or "non-fast-forward" in text
            or "failed to push some refs" in text
            or "updates were rejected" in text
            or "rejected" in text
        )
    
    def push(self):
        """원격 저장소에 푸시"""
        success, stdout, stderr = self._run_git('push')
        if success:
            return True, stdout or stderr

        branch = self.get_current_branch()
        if not branch or branch == "unknown":
            return False, stdout or stderr

        detail = self._join_git_output(stderr, stdout)

        # 1) 업스트림 미설정이면 먼저 -u 푸시 시도
        if self._is_upstream_error(detail):
            up_success, up_stdout, up_stderr = self._run_git('push', '-u', 'origin', branch)
            if up_success:
                return True, up_stdout or up_stderr
            detail = self._join_git_output(detail, up_stderr, up_stdout)

        # 2) fetch first / non-fast-forward면 pull --rebase 후 재시도
        if self._is_non_fast_forward_error(detail):
            pull_success, pull_stdout, pull_stderr = self._run_git('pull', '--rebase', 'origin', branch)
            pull_detail = self._join_git_output(pull_stderr, pull_stdout)

            if (
                not pull_success
                and "refusing to merge unrelated histories" in (pull_detail or "").lower()
            ):
                pull_success, pull_stdout, pull_stderr = self._run_git(
                    'pull', '--rebase', '--allow-unrelated-histories', 'origin', branch
                )
                pull_detail = self._join_git_output(pull_stderr, pull_stdout)

            if pull_success:
                retry_success, retry_stdout, retry_stderr = self._run_git('push', '-u', 'origin', branch)
                if retry_success:
                    return True, retry_stdout or retry_stderr
                detail = self._join_git_output(detail, pull_detail, retry_stderr, retry_stdout)
            else:
                # rebase 충돌 상태가 남으면 정리 후 마지막 대안 진행
                self._run_git('rebase', '--abort')
                detail = self._join_git_output(detail, pull_detail)

            # 3) 마지막 대안: 원격 이력을 덮어쓰되 lease 보호 사용
            self._run_git('fetch', 'origin', branch)
            force_success, force_stdout, force_stderr = self._run_git(
                'push', '-u', 'origin', branch, '--force-with-lease'
            )
            if force_success:
                force_msg = force_stdout or force_stderr or ""
                notice = "원격 이력 충돌로 force-with-lease 푸시를 수행했습니다."
                return True, self._join_git_output(force_msg, notice)
            detail = self._join_git_output(detail, force_stderr, force_stdout)

        return False, detail
    
    def get_current_branch(self):
        """현재 브랜치 이름 반환"""
        success, stdout, _ = self._run_git('branch', '--show-current')
        return stdout if success else "unknown"
    
    def auto_deploy(self, project_slug=None, custom_message=None):
        """
        전체 자동 배포 파이프라인
        
        1. 변경사항 확인
        2. git add -A
        3. git commit (자동 메시지 생성)
        4. git push
        
        Args:
            project_slug: 프로젝트 슬러그 (커밋 메시지용)
            custom_message: 커스텀 커밋 메시지
        
        Returns:
            (success, message)
        """
        # Git 저장소 확인
        if not self.is_git_repo():
            return False, "❌ Git 저장소가 아닙니다."
        
        # 변경사항 확인
        if not self.has_changes():
            return True, "ℹ️ 변경사항이 없습니다."
        
        # 커밋 메시지 생성
        if custom_message:
            commit_msg = custom_message
        elif project_slug:
            commit_msg = f"Update images for project: {project_slug}"
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_msg = f"Update portfolio content: {timestamp}"
        
        # git add
        success, msg = self.add_all()
        if not success:
            return False, f"❌ git add 실패: {msg}"
        
        # git commit
        success, msg = self.commit(commit_msg)
        if not success:
            return False, f"❌ git commit 실패: {msg}"
        
        # git push
        success, msg = self.push()
        if not success:
            return False, f"❌ git push 실패: {msg}"
        
        branch = self.get_current_branch()
        return True, f"✅ 배포 완료!\n\n브랜치: {branch}\n커밋: {commit_msg}\n\nNetlify 자동 배포가 시작됩니다."


class DragDropManager:
    """
    드래그 앤 드롭 매니저
    여러 DropZone 간의 이미지 이동을 관리
    """
    
    def __init__(self, root):
        self.root = root
        self.drop_zones = []
        self.dragging = False
        self.drag_data = None  # {'source_zone': zone, 'image_path': path, 'thumbnail': tk_image}
        self.drag_label = None  # 드래그 중 표시되는 플로팅 이미지
        self.highlight_zone = None  # 현재 하이라이트된 드롭 존
    
    def register_zone(self, zone):
        """DropZone 등록"""
        self.drop_zones.append(zone)
        zone.drag_manager = self
    
    def start_drag(self, source_zone, image_path, thumbnail, event):
        """드래그 시작"""
        self.dragging = True
        self.drag_data = {
            'source_zone': source_zone,
            'image_path': image_path,
            'thumbnail': thumbnail
        }
        
        # 플로팅 드래그 이미지 생성
        self.drag_label = tk.Label(self.root, image=thumbnail, 
                                   bg='white', relief='raised', borderwidth=2,
                                   cursor='fleur')
        self.drag_label.image = thumbnail
        self.drag_label.place(x=event.x_root - self.root.winfo_rootx() + 10, 
                             y=event.y_root - self.root.winfo_rooty() + 10)
        self.drag_label.lift()
        
        # 드래그 중 커서 변경
        self.root.config(cursor='fleur')
    
    def on_drag(self, event):
        """드래그 중"""
        if not self.dragging or not self.drag_label:
            return
        
        # 플로팅 이미지 위치 업데이트
        self.drag_label.place(x=event.x_root - self.root.winfo_rootx() + 10, 
                             y=event.y_root - self.root.winfo_rooty() + 10)
        
        # 현재 마우스 위치의 DropZone 확인 및 하이라이트
        target_zone = self._get_zone_at(event.x_root, event.y_root)
        
        if target_zone != self.highlight_zone:
            # 이전 하이라이트 해제
            if self.highlight_zone:
                self.highlight_zone.configure(relief='solid', borderwidth=1)
                self.highlight_zone._set_drop_highlight(False)
            
            # 새 하이라이트
            if target_zone and target_zone != self.drag_data['source_zone']:
                target_zone.configure(relief='solid', borderwidth=3)
                target_zone._set_drop_highlight(True)
            
            self.highlight_zone = target_zone
    
    def end_drag(self, event):
        """드래그 종료"""
        if not self.dragging:
            return
        
        # 드롭 대상 확인
        target_zone = self._get_zone_at(event.x_root, event.y_root)
        
        # 플로팅 이미지 제거
        if self.drag_label:
            self.drag_label.destroy()
            self.drag_label = None
        
        # 하이라이트 해제
        if self.highlight_zone:
            self.highlight_zone.configure(relief='solid', borderwidth=1)
            self.highlight_zone._set_drop_highlight(False)
            self.highlight_zone = None
        
        # 커서 복원
        self.root.config(cursor='')
        
        # 이미지 이동 처리
        if target_zone and target_zone != self.drag_data['source_zone']:
            self._move_image(self.drag_data['source_zone'], target_zone, 
                           self.drag_data['image_path'])
        
        self.dragging = False
        self.drag_data = None
    
    def _get_zone_at(self, x_root, y_root):
        """주어진 화면 좌표에 있는 DropZone 반환"""
        for zone in self.drop_zones:
            try:
                if not zone.winfo_exists():
                    continue
                zx = zone.winfo_rootx()
                zy = zone.winfo_rooty()
                zw = zone.winfo_width()
                zh = zone.winfo_height()
                
                if zx <= x_root <= zx + zw and zy <= y_root <= zy + zh:
                    return zone
            except:
                continue
        return None
    
    def _move_image(self, source_zone, target_zone, image_path):
        """이미지를 소스 카테고리에서 타겟 카테고리로 이동"""
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {image_path.name}")
                return
            
            target_type = target_zone.image_type
            project_folder = target_zone.project_folder
            
            # 타겟 폴더 결정
            if target_type == 'thumb':
                target_folder = project_folder
                new_name = f"thumb{image_path.suffix}"
            elif target_type == 'main':
                target_folder = project_folder
                new_name = f"main{image_path.suffix}"
            elif target_type == 'sub':
                target_folder = project_folder
                # 다음 번호 찾기
                existing = list(project_folder.glob("[0-9][0-9].*"))
                next_num = len(existing) + 1
                new_name = f"{str(next_num).zfill(2)}{image_path.suffix}"
            elif target_type == 'model':
                target_folder = project_folder / "model_images"
                target_folder.mkdir(exist_ok=True)
                existing = list(target_folder.glob("*.*"))
                valid_existing = [f for f in existing if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
                next_num = len(valid_existing) + 1
                new_name = f"{next_num}{image_path.suffix}"
            elif target_type == 'slide':
                target_folder = project_folder / "slide_images"
                target_folder.mkdir(exist_ok=True)
                existing = list(target_folder.glob("*.*"))
                valid_existing = [f for f in existing if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
                next_num = len(valid_existing) + 1
                new_name = f"{next_num}{image_path.suffix}"
            else:
                return
            
            # 파일 이동
            target_path = target_folder / new_name
            shutil.move(str(image_path), str(target_path))
            
            # 양쪽 카테고리 새로고침
            source_zone.load_images()
            source_zone._renumber_images()
            source_zone.load_images()
            
            target_zone.load_images()
            
            # 변경 콜백 호출
            if source_zone.on_change:
                source_zone.on_change()
            if target_zone.on_change:
                target_zone.on_change()
            
            messagebox.showinfo("이동 완료", 
                              f"✅ 이미지가 이동되었습니다.\n\n"
                              f"📁 {source_zone.image_type} → {target_zone.image_type}\n"
                              f"📄 {image_path.name} → {new_name}")
        
        except Exception as e:
            messagebox.showerror("이동 오류", f"이미지 이동 실패: {str(e)}")


class CaptionManager:
    """이미지 캡션 관리"""
    
    CAPTION_FILE = "captions.json"
    
    @staticmethod
    def load_captions(project_folder):
        """캡션 데이터 로드"""
        caption_file = Path(project_folder) / CaptionManager.CAPTION_FILE
        if caption_file.exists():
            try:
                with open(caption_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save_captions(project_folder, captions):
        """캡션 데이터 저장"""
        caption_file = Path(project_folder) / CaptionManager.CAPTION_FILE
        Path(project_folder).mkdir(parents=True, exist_ok=True)
        with open(caption_file, 'w', encoding='utf-8') as f:
            json.dump(captions, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def get_caption_key(image_path, image_type):
        """이미지의 캡션 키 생성"""
        path = Path(image_path)
        if image_type == 'model':
            return f"model_{path.stem}"
        elif image_type == 'slide':
            return f"slide_{path.stem}"
        elif image_type == 'sub':
            return f"sub_{path.stem}"
        else:
            return path.stem


class CaptionDialog(tk.Toplevel):
    """이미지 캡션 편집 다이얼로그"""
    
    def __init__(self, parent, image_path, image_type, project_folder, on_save=None):
        super().__init__(parent)
        
        self.image_path = Path(image_path)
        self.image_type = image_type
        self.project_folder = Path(project_folder)
        self.on_save = on_save
        self.result = None
        
        self.title(f"📝 이미지 주석 - {self.image_path.name}")
        self.geometry("500x400")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.resizable(True, True)
        
        # 모달 - 다른 창 클릭 시에도 유지되도록 수정
        # self.transient(parent)
        # self.grab_set()
        self.lift()
        
        self.create_ui()
        self.load_caption()
        
        # 중앙 배치
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def create_ui(self):
        # 이미지 미리보기
        preview_frame = tk.Frame(self, bg=ModernStyle.BG_LIGHT)
        preview_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        thumb = ImageOptimizer.create_thumbnail(self.image_path, size=(150, 150))
        if thumb:
            self._thumb = thumb  # 참조 유지
            tk.Label(preview_frame, image=thumb, bg=ModernStyle.BG_LIGHT).pack(pady=10)
        
        tk.Label(preview_frame, text=self.image_path.name, 
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_LIGHT,
                fg=ModernStyle.TEXT_MUTED).pack(pady=(0, 10))
        
        # 캡션 입력
        input_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(input_frame, text="이미지 주석 (캡션)", 
                font=ModernStyle.get_font(11, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        tk.Label(input_frame, text="이미지 오른쪽에 표시될 설명 텍스트를 입력하세요.",
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=(2, 8))
        
        self.caption_text = scrolledtext.ScrolledText(
            input_frame, font=ModernStyle.get_font(10),
            wrap=tk.WORD, height=6, relief='solid', borderwidth=1
        )
        self.caption_text.pack(fill=tk.BOTH, expand=True)
        
        # 버튼
        btn_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                 relief='solid', borderwidth=1, width=10,
                 command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        
        tk.Button(btn_frame, text="저장", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', width=10,
                 command=self.save).pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="삭제", font=ModernStyle.get_font(10),
                 bg=ModernStyle.DANGER, fg=ModernStyle.BG_WHITE,
                 relief='flat', width=8,
                 command=self.delete_caption).pack(side=tk.LEFT)
    
    def load_caption(self):
        """기존 캡션 로드"""
        captions = CaptionManager.load_captions(self.project_folder)
        key = CaptionManager.get_caption_key(self.image_path, self.image_type)
        if key in captions:
            self.caption_text.insert('1.0', captions[key])
    
    def save(self):
        """캡션 저장"""
        caption = self.caption_text.get('1.0', tk.END).strip()
        captions = CaptionManager.load_captions(self.project_folder)
        key = CaptionManager.get_caption_key(self.image_path, self.image_type)
        
        if caption:
            captions[key] = caption
        elif key in captions:
            del captions[key]
        
        CaptionManager.save_captions(self.project_folder, captions)
        self.result = caption
        
        if self.on_save:
            self.on_save()
        
        self.destroy()
    
    def delete_caption(self):
        """캡션 삭제"""
        if messagebox.askyesno("확인", "이 이미지의 주석을 삭제하시겠습니까?"):
            captions = CaptionManager.load_captions(self.project_folder)
            key = CaptionManager.get_caption_key(self.image_path, self.image_type)
            if key in captions:
                del captions[key]
                CaptionManager.save_captions(self.project_folder, captions)
            
            if self.on_save:
                self.on_save()
            
            self.destroy()
    
    def cancel(self):
        """취소"""
        self.destroy()


class DropZone(tk.Frame):
    """드래그앤드롭 가능한 이미지 등록 영역"""
    
    def __init__(self, parent, image_type, title, project_folder, on_change=None, drag_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.image_type = image_type
        self.title = title
        self.project_folder = project_folder
        self.on_change = on_change
        self.drag_manager = drag_manager
        self.images = []
        self.thumbnails = {}
        self.selected_images = set()  # 선택된 이미지들
        self.check_vars = {}  # 체크박스 변수들
        self.image_labels = {}  # 이미지 라벨 참조 저장
        
        self.configure(bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1)
        self.create_ui()
        self.load_images()
    
    def create_ui(self):
        # 헤더
        header = tk.Frame(self, bg=ModernStyle.BG_LIGHT)
        header.pack(fill=tk.X)
        
        tk.Label(header, text=self.title, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT, padx=10, pady=8)
        
        # 버튼
        btn_frame = tk.Frame(header, bg=ModernStyle.BG_LIGHT)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Button(btn_frame, text="+ 추가", font=ModernStyle.get_font(9),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                 relief='solid', borderwidth=1, cursor='hand2',
                 command=self.add_images).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(btn_frame, text="🗑 선택삭제", font=ModernStyle.get_font(9),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.DANGER,
                 relief='solid', borderwidth=1, cursor='hand2',
                 command=self.delete_selected).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(btn_frame, text="전체선택", font=ModernStyle.get_font(8),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED,
                 relief='flat', cursor='hand2',
                 command=self.select_all).pack(side=tk.LEFT, padx=2, pady=5)
        
        # 드롭 영역
        self.drop_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        self.drop_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 이미지 리스트 (스크롤 가능)
        self.canvas = tk.Canvas(self.drop_frame, bg=ModernStyle.BG_WHITE, 
                               highlightthickness=0, height=140)
        self.scrollbar = ttk.Scrollbar(self.drop_frame, orient=tk.HORIZONTAL, 
                                       command=self.canvas.xview)
        self.image_container = tk.Frame(self.canvas, bg=ModernStyle.BG_WHITE)
        
        self.canvas.configure(xscrollcommand=self.scrollbar.set)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.image_container, anchor='nw')
        
        self.image_container.bind('<Configure>', self._on_container_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 마우스 휠 바인딩
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.image_container.bind('<MouseWheel>', self._on_mousewheel)
        
        # 빈 상태 표시
        self.empty_label = tk.Label(self.image_container, 
                                   text="📷 클릭하여 이미지 추가\n또는 파일을 여기에 드래그",
                                   font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                                   fg=ModernStyle.TEXT_SUBTLE, justify='center')
        self.empty_label.pack(expand=True, pady=30)
        self.empty_label.bind('<Button-1>', lambda e: self.add_images())
    
    def _on_container_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        pass
    
    def _on_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")
    
    def _get_slide_folder(self):
        """슬라이드 이미지 폴더 반환 (별도 폴더 사용)"""
        slide_folder = self.project_folder / "slide_images"
        return slide_folder
    
    def load_images(self):
        """이미지 로드"""
        # 위젯이 유효한지 확인
        try:
            if not self.winfo_exists():
                return
        except:
            return
        
        self.images = []
        self.selected_images.clear()
        self.check_vars.clear()
        
        if not self.project_folder.exists():
            self._update_display()
            return
        
        if self.image_type == 'thumb':
            # 썸네일 이미지 (그리드용 정사각형): thumb.jpg
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                thumb = self.project_folder / f"thumb{ext}"
                if thumb.exists():
                    self.images = [thumb]
                    break
            # fallback: cover.jpg (하위 호환성)
            if not self.images:
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    cover = self.project_folder / f"cover{ext}"
                    if cover.exists():
                        self.images = [cover]
                        break
        
        elif self.image_type == 'main':
            # 메인 이미지 (상세페이지용): main.jpg
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                main = self.project_folder / f"main{ext}"
                if main.exists():
                    self.images = [main]
                    break
        
        elif self.image_type == 'sub':
            # 서브 이미지: 01.jpg, 02.jpg, ... (두 자리 숫자)
            for f in sorted(self.project_folder.glob("[0-9][0-9].*")):
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    self.images.append(f)
        
        elif self.image_type == 'model':
            model_folder = self.project_folder / "model_images"
            if model_folder.exists():
                for f in sorted(model_folder.glob("*.*"), key=lambda x: self._sort_key(x)):
                    if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        self.images.append(f)
        
        elif self.image_type == 'slide':
            # 슬라이드 이미지: slide_images 폴더에서 로드
            slide_folder = self._get_slide_folder()
            if slide_folder.exists():
                for f in sorted(slide_folder.glob("*.*"), key=lambda x: self._sort_key(x)):
                    if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        self.images.append(f)
        
        self._update_display()
    
    def _sort_key(self, path):
        """숫자 기반 정렬 키"""
        try:
            return int(''.join(filter(str.isdigit, path.stem)) or 0)
        except:
            return 0
    
    def _update_display(self):
        """화면 업데이트"""
        # 위젯이 유효한지 확인
        try:
            if not self.winfo_exists() or not self.image_container.winfo_exists():
                return
        except:
            return
        
        # 기존 위젯 제거
        try:
            for widget in self.image_container.winfo_children():
                widget.destroy()
        except Exception:
            return
        
        self.check_vars.clear()
        self.image_labels.clear()
        
        if not self.images:
            self.empty_label = tk.Label(self.image_container,
                                       text="📷 클릭하여 이미지 추가\n🔀 다른 카테고리에서 드래그하여 이동",
                                       font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                                       fg=ModernStyle.TEXT_SUBTLE, justify='center')
            self.empty_label.pack(expand=True, pady=30)
            self.empty_label.bind('<Button-1>', lambda e: self.add_images())
            return
        
        # 이미지 썸네일 표시
        for i, img_path in enumerate(self.images):
            frame = tk.Frame(self.image_container, bg=ModernStyle.BG_WHITE)
            frame.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 체크박스 (다중 선택용)
            var = tk.BooleanVar(value=False)
            self.check_vars[str(img_path)] = var
            cb = tk.Checkbutton(frame, variable=var, bg=ModernStyle.BG_WHITE,
                               activebackground=ModernStyle.BG_WHITE)
            cb.pack()
            
            # 썸네일
            thumb = ImageOptimizer.create_thumbnail(img_path)
            if thumb:
                self.thumbnails[str(img_path)] = thumb
                img_label = tk.Label(frame, image=thumb, bg=ModernStyle.BG_WHITE,
                                    relief='solid', borderwidth=1, cursor='fleur')
                img_label.pack()
                self.image_labels[str(img_path)] = img_label
                
                # 드래그 앤 드롭 이벤트 바인딩
                self._bind_drag_events(img_label, img_path, thumb)
                # 더블클릭으로 캡션 편집
                img_label.bind('<Double-Button-1>', lambda e, p=img_path: self._open_caption_dialog(p))
            else:
                img_label = tk.Label(frame, text="📷", font=ModernStyle.get_font(20),
                                    bg=ModernStyle.BG_LIGHT, width=8, height=4, cursor='fleur')
                img_label.pack()
                self.image_labels[str(img_path)] = img_label
                # 플레이스홀더도 드래그 가능
                self._bind_drag_events(img_label, img_path, None)
                # 더블클릭으로 캡션 편집
                img_label.bind('<Double-Button-1>', lambda e, p=img_path: self._open_caption_dialog(p))
            
            # 파일명
            name_label = tk.Label(frame, text=img_path.name, font=ModernStyle.get_font(8),
                                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED)
            name_label.pack()
            
            # 순서 변경 버튼
            if len(self.images) > 1:
                order_frame = tk.Frame(frame, bg=ModernStyle.BG_WHITE)
                order_frame.pack()
                if i > 0:
                    tk.Button(order_frame, text="◀", font=ModernStyle.get_font(7),
                             bg=ModernStyle.BG_WHITE, relief='flat',
                             command=lambda idx=i: self.move_image(idx, -1)).pack(side=tk.LEFT)
                if i < len(self.images) - 1:
                    tk.Button(order_frame, text="▶", font=ModernStyle.get_font(7),
                             bg=ModernStyle.BG_WHITE, relief='flat',
                             command=lambda idx=i: self.move_image(idx, 1)).pack(side=tk.LEFT)
    
    def _bind_drag_events(self, widget, img_path, thumbnail):
        """드래그 앤 드롭 이벤트 바인딩"""
        def on_press(event):
            # 드래그 시작
            if self.drag_manager:
                # 썸네일이 없으면 새로 생성
                thumb = thumbnail
                if not thumb:
                    thumb = ImageOptimizer.create_thumbnail(img_path)
                if thumb:
                    self.drag_manager.start_drag(self, img_path, thumb, event)
        
        def on_motion(event):
            if self.drag_manager:
                self.drag_manager.on_drag(event)
        
        def on_release(event):
            if self.drag_manager:
                self.drag_manager.end_drag(event)
        
        widget.bind('<Button-1>', on_press)
        widget.bind('<B1-Motion>', on_motion)
        widget.bind('<ButtonRelease-1>', on_release)
    
    def _open_caption_dialog(self, img_path):
        """캡션 편집 다이얼로그 열기"""
        # 서브, 모델, 슬라이드 이미지만 캡션 지원
        if self.image_type not in ['sub', 'model', 'slide']:
            messagebox.showinfo("알림", "캡션은 서브/모델/슬라이드 이미지에만 추가할 수 있습니다.")
            return
        
        CaptionDialog(
            self.winfo_toplevel(),
            img_path,
            self.image_type,
            self.project_folder,
            on_save=self._on_caption_saved
        )
    
    def _on_caption_saved(self):
        """캡션 저장 완료 콜백"""
        # 필요시 UI 업데이트
        pass
    
    def _set_drop_highlight(self, highlight):
        """드롭 대상 하이라이트 설정"""
        if highlight:
            self.configure(bg=ModernStyle.BG_DROP)
            self.drop_frame.configure(bg=ModernStyle.BG_DROP)
            self.canvas.configure(bg=ModernStyle.BG_DROP)
        else:
            self.configure(bg=ModernStyle.BG_WHITE)
            self.drop_frame.configure(bg=ModernStyle.BG_WHITE)
            self.canvas.configure(bg=ModernStyle.BG_WHITE)
    
    def select_all(self):
        """전체 선택/해제"""
        # 현재 모두 선택되어 있으면 해제, 아니면 전체 선택
        all_selected = all(var.get() for var in self.check_vars.values()) if self.check_vars else False
        for var in self.check_vars.values():
            var.set(not all_selected)
    
    def delete_selected(self):
        """선택된 이미지들 삭제"""
        selected = [path for path, var in self.check_vars.items() if var.get()]
        
        if not selected:
            messagebox.showinfo("알림", "삭제할 이미지를 선택하세요.\n(체크박스를 클릭하여 선택)")
            return
        
        if not messagebox.askyesno("확인", f"{len(selected)}개 이미지를 삭제하시겠습니까?"):
            return
        
        for path_str in selected:
            path = Path(path_str)
            if path.exists():
                os.remove(str(path))
        
        try:
            if self.winfo_exists():
                self.load_images()
                self._renumber_images()
                if self.on_change:
                    self.on_change()
        except Exception:
            pass
    
    def add_images(self):
        """이미지 추가"""
        files = filedialog.askopenfilenames(
            title=f"{self.title} 이미지 선택",
            filetypes=[("이미지 파일", "*.jpg *.jpeg *.png *.webp *.bmp *.gif")]
        )
        
        if not files:
            return
        
        # 폴더 생성
        self.project_folder.mkdir(parents=True, exist_ok=True)
        if self.image_type == 'model':
            (self.project_folder / "model_images").mkdir(exist_ok=True)
        if self.image_type == 'slide':
            self._get_slide_folder().mkdir(exist_ok=True)
        
        # 최적화 설정
        max_sizes = {
            'thumb': THUMB_MAX_SIZE,
            'main': MAIN_MAX_SIZE,
            'sub': SUB_MAX_SIZE,
            'model': MODEL_MAX_SIZE,
            'slide': SLIDE_MAX_SIZE
        }
        max_size = max_sizes.get(self.image_type, 1400)
        
        total_reduction = 0
        processed = 0
        
        for file_path in files:
            src = Path(file_path)
            
            # 대상 폴더 및 파일명 결정
            if self.image_type == 'thumb':
                target_folder = self.project_folder
                new_name = f"thumb{src.suffix}"
            elif self.image_type == 'main':
                target_folder = self.project_folder
                new_name = f"main{src.suffix}"
            elif self.image_type == 'sub':
                target_folder = self.project_folder
                idx = len(self.images) + processed + 1
                new_name = f"{str(idx).zfill(2)}{src.suffix}"
            elif self.image_type == 'model':
                target_folder = self.project_folder / "model_images"
                idx = len(self.images) + processed + 1
                new_name = f"{idx}{src.suffix}"
            elif self.image_type == 'slide':
                # 슬라이드는 별도 폴더에 저장
                target_folder = self._get_slide_folder()
                idx = len(self.images) + processed + 1
                new_name = f"{idx}{src.suffix}"
            else:
                continue
            
            # 파일 복사
            dst = target_folder / new_name
            shutil.copy(str(src), str(dst))
            
            # 최적화
            optimized_path, reduction = ImageOptimizer.optimize_for_web(dst, max_size)
            total_reduction += reduction
            processed += 1
        
        # 결과 표시
        avg_reduction = total_reduction / processed if processed > 0 else 0
        if processed > 0:
            msg = f"{processed}개 이미지 추가됨"
            if avg_reduction > 0:
                msg += f"\n평균 {avg_reduction:.1f}% 용량 감소"
            messagebox.showinfo("완료", msg)
        
        # 위젯이 유효한 경우에만 업데이트
        try:
            if self.winfo_exists():
                self.load_images()
                if self.on_change:
                    self.on_change()
                # 파일 다이얼로그 후 팝업이 뒤로 가는 문제 해결 - Toplevel 창을 앞으로
                toplevel = self.winfo_toplevel()
                if toplevel and toplevel.winfo_exists():
                    toplevel.lift()
                    toplevel.focus_force()
        except Exception:
            pass
    
    def delete_image(self, img_path):
        """이미지 삭제 (단일)"""
        if messagebox.askyesno("확인", f"'{img_path.name}'을(를) 삭제하시겠습니까?"):
            if img_path.exists():
                os.remove(str(img_path))
            try:
                if self.winfo_exists():
                    self.load_images()
                    self._renumber_images()
                    if self.on_change:
                        self.on_change()
            except Exception:
                pass
    
    def move_image(self, idx, direction):
        """이미지 순서 변경"""
        new_idx = idx + direction
        if 0 <= new_idx < len(self.images):
            self.images[idx], self.images[new_idx] = self.images[new_idx], self.images[idx]
            self._renumber_images()
            try:
                if self.winfo_exists():
                    self.load_images()
                    if self.on_change:
                        self.on_change()
            except Exception:
                pass
    
    def _renumber_images(self):
        """이미지 파일명 재정렬"""
        if self.image_type == 'cover' or self.image_type == 'thumb' or self.image_type == 'main':
            return
        
        if not self.images:
            return
        
        # 확장자 결정 (WebP 또는 JPG)
        ext = '.webp' if USE_WEBP else '.jpg'
        
        if self.image_type == 'sub':
            temp_files = []
            for i, img in enumerate(self.images):
                if img.exists():
                    temp_path = self.project_folder / f"_temp_sub_{i}{img.suffix}"
                    shutil.move(str(img), str(temp_path))
                    temp_files.append(temp_path)
            
            for i, temp_path in enumerate(temp_files):
                new_path = self.project_folder / f"{str(i+1).zfill(2)}{ext}"
                if temp_path.exists():
                    # 최적화 후 반환된 경로 사용
                    optimized_path, _ = ImageOptimizer.optimize_for_web(temp_path, SUB_MAX_SIZE)
                    if optimized_path.exists() and optimized_path != new_path:
                        shutil.move(str(optimized_path), str(new_path))
        
        elif self.image_type == 'model':
            model_folder = self.project_folder / "model_images"
            temp_files = []
            for i, img in enumerate(self.images):
                if img.exists():
                    temp_path = model_folder / f"_temp_model_{i}{img.suffix}"
                    shutil.move(str(img), str(temp_path))
                    temp_files.append(temp_path)
            
            for i, temp_path in enumerate(temp_files):
                new_path = model_folder / f"{i+1}{ext}"
                if temp_path.exists():
                    optimized_path, _ = ImageOptimizer.optimize_for_web(temp_path, MODEL_MAX_SIZE)
                    if optimized_path.exists() and optimized_path != new_path:
                        shutil.move(str(optimized_path), str(new_path))
        
        elif self.image_type == 'slide':
            slide_folder = self._get_slide_folder()
            if not slide_folder.exists():
                return
            temp_files = []
            for i, img in enumerate(self.images):
                if img.exists():
                    temp_path = slide_folder / f"_temp_slide_{i}{img.suffix}"
                    shutil.move(str(img), str(temp_path))
                    temp_files.append(temp_path)
            
            for i, temp_path in enumerate(temp_files):
                new_path = slide_folder / f"{i+1}{ext}"
                if temp_path.exists():
                    optimized_path, _ = ImageOptimizer.optimize_for_web(temp_path, SLIDE_MAX_SIZE)
                    if optimized_path.exists() and optimized_path != new_path:
                        shutil.move(str(optimized_path), str(new_path))


class ProjectEditorDialog(tk.Toplevel):
    """프로젝트 편집 다이얼로그"""
    
    def __init__(self, parent, project, mode='projects', on_save=None):
        super().__init__(parent)
        
        self.project = project
        self.mode = mode
        self.on_save = on_save
        self.result = None
        
        self.title(f"프로젝트 편집 - {project.get('title', 'New')}")
        self.geometry("950x800")
        self.configure(bg=ModernStyle.BG_WHITE)
        # transient와 grab_set 제거 - 다른 창 클릭 시에도 팝업 유지
        # self.transient(parent)
        # self.grab_set()
        
        # 대신 항상 위에 표시
        self.attributes('-topmost', False)
        self.lift()
        
        # 중앙 배치
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 950) // 2
        y = (self.winfo_screenheight() - 800) // 2
        self.geometry(f"+{x}+{y}")
        
        self.setup_styles()
        self.create_ui()
    
    def setup_styles(self):
        style = ttk.Style()
        style.configure('Modern.TFrame', background=ModernStyle.BG_WHITE)
        style.configure('Header.TLabel', background=ModernStyle.BG_WHITE,
                       foreground=ModernStyle.TEXT_SUBTLE, font=ModernStyle.get_font(9))
        style.configure('Modern.TLabel', background=ModernStyle.BG_WHITE,
                       foreground=ModernStyle.TEXT_PRIMARY, font=ModernStyle.get_font(10))
        style.configure('Title.TLabel', background=ModernStyle.BG_WHITE,
                       foreground=ModernStyle.TEXT_PRIMARY, font=ModernStyle.get_font(16, 'bold'))
        style.configure('Subtitle.TLabel', background=ModernStyle.BG_WHITE,
                       foreground=ModernStyle.TEXT_MUTED, font=ModernStyle.get_font(10))
    
    def create_ui(self):
        # 메인 컨테이너 (스크롤 가능)
        main_container = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 노트북 (탭)
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))
        
        # === 탭 1: 기본 정보 ===
        info_frame = ttk.Frame(notebook, style='Modern.TFrame')
        notebook.add(info_frame, text="  기본 정보  ")
        self.create_info_tab(info_frame)
        
        # === 탭 2: 이미지 관리 ===
        image_frame = ttk.Frame(notebook, style='Modern.TFrame')
        notebook.add(image_frame, text="  이미지 관리  ")
        self.create_image_tab(image_frame)
        
        # === 탭 3: 캡션 관리 ===
        caption_frame = ttk.Frame(notebook, style='Modern.TFrame')
        notebook.add(caption_frame, text="  📝 캡션 관리  ")
        self.create_caption_tab(caption_frame)
        
        # === 탭 4: 레이아웃 설정 ===
        layout_frame = ttk.Frame(notebook, style='Modern.TFrame')
        notebook.add(layout_frame, text="  레이아웃  ")
        self.create_layout_tab(layout_frame)
        
        # 하단 버튼 프레임 (항상 보임)
        btn_frame = tk.Frame(main_container, bg=ModernStyle.BG_LIGHT, height=60)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        btn_frame.pack_propagate(False)
        
        inner_btn = tk.Frame(btn_frame, bg=ModernStyle.BG_LIGHT)
        inner_btn.pack(expand=True)
        
        tk.Button(inner_btn, text="💾 저장", font=ModernStyle.get_font(11, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=30, pady=8, cursor='hand2',
                 command=self.save).pack(side=tk.LEFT, padx=10, pady=15)
        
        tk.Button(inner_btn, text="👁 미리보기", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                 relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2',
                 command=self.preview).pack(side=tk.LEFT, padx=5, pady=15)
        
        tk.Button(inner_btn, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED,
                 relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2',
                 command=self.destroy).pack(side=tk.LEFT, padx=5, pady=15)
    
    def create_info_tab(self, parent):
        """기본 정보 탭 (스크롤 가능)"""
        # 스크롤 캔버스
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>", 
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 캔버스 크기에 맞게 프레임 크기 조정
        def configure_scroll_region(event, cid=canvas_window_id):
            try:
                canvas.itemconfig(cid, width=event.width - 20)
            except:
                pass
        canvas.bind('<Configure>', configure_scroll_region)
        
        # 마우스 휠 스크롤
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        scrollable.bind("<MouseWheel>", _on_mousewheel)
        
        # 탭 전환 시 바인딩 해제
        def on_destroy(event):
            try:
                canvas.unbind_all("<MouseWheel>")
            except:
                pass
        parent.bind("<Destroy>", on_destroy)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.entries = {}
        
        # 헤더
        header = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(header, text="프로젝트 정보", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        
        fields = [
            ('title', '📌 팝업 제목 (TITLE) *', '상세 팝업 상단에 표시되는 제목'),
            ('display_title', '📷 그리드 제목', '정사각형 썸네일 위에 표시되는 제목'),
            ('slug', '슬러그 (폴더명)', '예: montana-hannam'),
            ('display_year', '표시 연도', '예: 2025'),
            ('location', '위치 (LOCATION)', '예: Seoul, Korea'),
            ('duration', '기간 (DURATION)', '예: Sep 2025 – Dec 2025'),
            ('program', '프로그램 (PROGRAM)', '예: Residential'),
            ('studio', '스튜디오 (STUDIO)', '예: INTERIOR ARCHITECTURE STUDIO(2)'),
        ]
        
        for field, label, placeholder in fields:
            frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
            frame.pack(fill=tk.X, padx=20, pady=8)
            
            tk.Label(frame, text=label, font=ModernStyle.get_font(9),
                    bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W)
            
            entry = tk.Entry(frame, font=ModernStyle.get_font(10),
                           bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                           relief='solid', borderwidth=1)
            value = self.project.get(field, '')
            # display_title이 비어있으면 title 사용
            if field == 'display_title' and not value:
                value = self.project.get('title', '')
            # title이 비어있으면 display_title 사용
            if field == 'title' and not value:
                value = self.project.get('display_title', '')
            entry.insert(0, value)
            entry.pack(fill=tk.X, pady=(3, 0), ipady=8)
            self.entries[field] = entry
        
        # 설명 (텍스트 드래그 선택 기반 링크 지원)
        desc_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        desc_frame.pack(fill=tk.X, padx=20, pady=8)
        
        desc_label_frame = tk.Frame(desc_frame, bg=ModernStyle.BG_WHITE)
        desc_label_frame.pack(fill=tk.X)
        tk.Label(desc_label_frame, text="설명 (DESCRIPTION)", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT)
        tk.Label(desc_label_frame, text="  (텍스트 드래그 후 우클릭 → 링크 추가)", font=ModernStyle.get_font(7),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(side=tk.LEFT)
        
        desc_text = scrolledtext.ScrolledText(desc_frame, height=4,
                                             font=ModernStyle.get_font(10),
                                             bg=ModernStyle.BG_WHITE,
                                             relief='solid', borderwidth=1)
        desc_text.insert(tk.END, self.project.get('description', ''))
        desc_text.pack(fill=tk.X, pady=(3, 0))
        desc_text.bind('<Button-3>', lambda e, txt=desc_text: self._show_text_selection_menu(e, txt))
        self.entries['description'] = desc_text
        
        # 한국어 설명
        desc_ko_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        desc_ko_frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        
        tk.Label(desc_ko_frame, text="설명 (한국어)", font=ModernStyle.get_font(11, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(desc_ko_frame, text="  영문 설명 아래에 표시됩니다", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(side=tk.LEFT)
        
        desc_ko_text = scrolledtext.ScrolledText(desc_ko_frame, height=4,
                                             font=ModernStyle.get_font(10),
                                             bg=ModernStyle.BG_WHITE,
                                             relief='solid', borderwidth=1)
        desc_ko_text.insert(tk.END, self.project.get('description_ko', ''))
        desc_ko_text.pack(fill=tk.X, pady=(3, 0))
        desc_ko_text.bind('<Button-3>', lambda e, txt=desc_ko_text: self._show_text_selection_menu(e, txt))
        self.entries['description_ko'] = desc_ko_text
        
        # === 커스텀 메타 필드 섹션 ===
        # 먼저 위젯 리스트 초기화
        self.custom_field_widgets = []
        
        custom_section = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        custom_section.pack(fill=tk.X, padx=20, pady=(20, 8))
        
        custom_header = tk.Frame(custom_section, bg=ModernStyle.BG_WHITE)
        custom_header.pack(fill=tk.X)
        
        tk.Label(custom_header, text="추가 정보 필드", font=ModernStyle.get_font(12, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        
        tk.Label(custom_section, text="프로젝트 상세페이지에 표시될 추가 정보 (예: COLLABORATOR, CLIENT, AREA 등)",
                font=ModernStyle.get_font(8), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, pady=(5, 0))
        
        # 커스텀 필드 컨테이너 (먼저 생성)
        custom_fields_container = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        custom_fields_container.pack(fill=tk.X, padx=20, pady=5)
        
        # 컨테이너 참조 저장
        self.custom_fields_container = custom_fields_container
        
        # + 버튼 추가 (컨테이너 생성 후)
        tk.Button(custom_header, text="+ 필드 추가", font=ModernStyle.get_font(9),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT,
                 relief='solid', borderwidth=1, cursor='hand2',
                 command=self._add_custom_field_click).pack(side=tk.RIGHT)
        
        # 기존 커스텀 필드 로드
        existing_custom = self.project.get('custom_fields', [])
        if existing_custom:
            for cf in existing_custom:
                self.add_custom_field(custom_fields_container, cf.get('label', ''), cf.get('value', ''))
        
        # 공개/비공개
        vis_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        vis_frame.pack(fill=tk.X, padx=20, pady=15)
        
        self.visible_var = tk.BooleanVar(value=self.project.get('visible', True))
        cb = tk.Checkbutton(vis_frame, text=" 사이트에 공개", variable=self.visible_var,
                           font=ModernStyle.get_font(10), bg=ModernStyle.BG_WHITE,
                           activebackground=ModernStyle.BG_WHITE)
        cb.pack(anchor=tk.W)
        
        # 여백
        tk.Frame(scrollable, bg=ModernStyle.BG_WHITE, height=50).pack(fill=tk.X)
    
    def _show_entry_selection_menu(self, event, entry_widget):
        """Entry 위젯에서 텍스트 선택 시 컨텍스트 메뉴 표시"""
        try:
            selected = entry_widget.selection_get()
            if selected:
                menu = tk.Menu(self, tearoff=0)
                display_text = f"'{selected[:20]}...'" if len(selected) > 20 else f"'{selected}'"
                menu.add_command(label=f"🔗 {display_text} 에 링크 추가",
                               command=lambda: self._add_link_to_entry(entry_widget, selected))
                menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            pass
    
    def _add_link_to_entry(self, entry_widget, selected_text):
        """Entry 위젯의 선택된 텍스트에 링크 추가"""
        popup = tk.Toplevel(self)
        popup.title("🔗 선택 텍스트에 링크 추가")
        popup.geometry("450x280")
        popup.configure(bg=ModernStyle.BG_WHITE)
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 450) // 2
        y = (popup.winfo_screenheight() - 280) // 2
        popup.geometry(f"+{x}+{y}")
        
        current_text = entry_widget.get()
        
        # 헤더
        tk.Label(popup, text="선택한 텍스트에 링크 추가", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(15, 10))
        
        # 선택된 텍스트 표시
        tk.Label(popup, text="선택된 텍스트:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        selected_frame = tk.Frame(popup, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
        selected_frame.pack(fill=tk.X, padx=20, pady=(3, 10))
        tk.Label(selected_frame, text=selected_text, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.ACCENT, wraplength=380).pack(padx=10, pady=8)
        
        # URL 입력
        tk.Label(popup, text="URL 주소", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        url_entry = tk.Entry(popup, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        url_entry.insert(0, "https://")
        url_entry.pack(fill=tk.X, padx=20, pady=(3, 10), ipady=6)
        
        # 스타일 선택
        tk.Label(popup, text="링크 스타일", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        style_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        style_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        style_var = tk.StringVar(value="highlight")
        
        highlight_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        highlight_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(highlight_frame, text="", variable=style_var, value="highlight",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(highlight_frame, text=" 하이라이트 ", font=ModernStyle.get_font(10),
                bg=ModernStyle.ACCENT, fg="white").pack(side=tk.LEFT)
        
        underline_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        underline_frame.pack(side=tk.LEFT)
        tk.Radiobutton(underline_frame, text="", variable=style_var, value="underline",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(underline_frame, text="밑줄", font=('Segoe UI', 10, 'underline'),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        def apply_link():
            url = url_entry.get().strip()
            style = style_var.get()
            
            if url and url != "https://":
                markdown_link = f"[{selected_text}]({url}|{style})"
                new_text = current_text.replace(selected_text, markdown_link, 1)
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, new_text)
                popup.destroy()
            else:
                messagebox.showwarning("URL 필요", "URL을 입력해주세요.", parent=popup)
        
        # 버튼
        btn_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Button(btn_frame, text="✓ 링크 적용", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=6, command=apply_link).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=6, command=popup.destroy).pack(side=tk.LEFT)
        
        popup.bind('<Return>', lambda e: apply_link())
        url_entry.focus_set()
    
    def _show_text_selection_menu(self, event, text_widget):
        """Text 위젯에서 텍스트 선택 시 컨텍스트 메뉴 표시"""
        try:
            selected = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                menu = tk.Menu(self, tearoff=0)
                display_text = f"'{selected[:20]}...'" if len(selected) > 20 else f"'{selected}'"
                menu.add_command(label=f"🔗 {display_text} 에 링크 추가",
                               command=lambda: self._add_link_to_text(text_widget, selected))
                menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            pass  # 선택된 텍스트 없음
    
    def _add_link_to_text(self, text_widget, selected_text):
        """Text 위젯의 선택된 텍스트에 링크 추가"""
        popup = tk.Toplevel(self)
        popup.title("🔗 선택 텍스트에 링크 추가")
        popup.geometry("450x280")
        popup.configure(bg=ModernStyle.BG_WHITE)
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 450) // 2
        y = (popup.winfo_screenheight() - 280) // 2
        popup.geometry(f"+{x}+{y}")
        
        # 헤더
        tk.Label(popup, text="선택한 텍스트에 링크 추가", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(15, 10))
        
        # 선택된 텍스트 표시
        tk.Label(popup, text="선택된 텍스트:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        selected_frame = tk.Frame(popup, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
        selected_frame.pack(fill=tk.X, padx=20, pady=(3, 10))
        tk.Label(selected_frame, text=selected_text, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.ACCENT, wraplength=380).pack(padx=10, pady=8)
        
        # URL 입력
        tk.Label(popup, text="URL 주소", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        url_entry = tk.Entry(popup, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        url_entry.insert(0, "https://")
        url_entry.pack(fill=tk.X, padx=20, pady=(3, 10), ipady=6)
        
        # 스타일 선택
        tk.Label(popup, text="링크 스타일", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        style_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        style_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        style_var = tk.StringVar(value="highlight")
        
        highlight_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        highlight_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(highlight_frame, text="", variable=style_var, value="highlight",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(highlight_frame, text=" 하이라이트 ", font=ModernStyle.get_font(10),
                bg=ModernStyle.ACCENT, fg="white").pack(side=tk.LEFT)
        
        underline_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        underline_frame.pack(side=tk.LEFT)
        tk.Radiobutton(underline_frame, text="", variable=style_var, value="underline",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(underline_frame, text="밑줄", font=('Segoe UI', 10, 'underline'),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        def apply_link():
            url = url_entry.get().strip()
            style = style_var.get()
            
            if url and url != "https://":
                # Text 위젯의 현재 내용에서 선택된 텍스트를 링크로 대체
                try:
                    sel_start = text_widget.index(tk.SEL_FIRST)
                    sel_end = text_widget.index(tk.SEL_LAST)
                    markdown_link = f"[{selected_text}]({url}|{style})"
                    text_widget.delete(sel_start, sel_end)
                    text_widget.insert(sel_start, markdown_link)
                    popup.destroy()
                except tk.TclError:
                    # 선택이 해제된 경우 전체 텍스트에서 대체
                    current = text_widget.get("1.0", tk.END)
                    markdown_link = f"[{selected_text}]({url}|{style})"
                    new_text = current.replace(selected_text, markdown_link, 1)
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", new_text.strip())
                    popup.destroy()
            else:
                messagebox.showwarning("URL 필요", "URL을 입력해주세요.", parent=popup)
        
        # 버튼
        btn_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Button(btn_frame, text="✓ 링크 적용", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=6, command=apply_link).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=6, command=popup.destroy).pack(side=tk.LEFT)
        
        popup.bind('<Return>', lambda e: apply_link())
        url_entry.focus_set()
    
    def _add_custom_field_click(self):
        """+ 버튼 클릭 시 커스텀 필드 추가"""
        if hasattr(self, 'custom_fields_container'):
            self.add_custom_field(self.custom_fields_container)
    
    def add_custom_field(self, container, label='', value=''):
        """커스텀 메타 필드 추가"""
        frame = tk.Frame(container, bg=ModernStyle.BG_WHITE)
        frame.pack(fill=tk.X, pady=5)
        
        # 라벨 입력 (필드명)
        label_frame = tk.Frame(frame, bg=ModernStyle.BG_WHITE)
        label_frame.pack(fill=tk.X)
        
        tk.Label(label_frame, text="필드명 (대문자로 표시됨)", font=ModernStyle.get_font(8),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT)
        
        # 삭제 버튼
        def remove_field():
            self.custom_field_widgets.remove(field_data)
            frame.destroy()
        
        tk.Button(label_frame, text="✕", font=ModernStyle.get_font(8),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.DANGER,
                 relief='flat', cursor='hand2', width=2,
                 command=remove_field).pack(side=tk.RIGHT)
        
        label_entry = tk.Entry(frame, font=ModernStyle.get_font(9),
                              bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                              relief='solid', borderwidth=1)
        label_entry.insert(0, label)
        label_entry.pack(fill=tk.X, pady=(2, 5), ipady=5)
        
        # 값 입력 (텍스트 드래그 선택 기반 링크 지원)
        value_label_frame = tk.Frame(frame, bg=ModernStyle.BG_WHITE)
        value_label_frame.pack(fill=tk.X)
        tk.Label(value_label_frame, text="내용", font=ModernStyle.get_font(8),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT)
        tk.Label(value_label_frame, text="  (텍스트 드래그 후 우클릭 → 링크)", font=ModernStyle.get_font(7),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(side=tk.LEFT)
        
        value_entry = tk.Entry(frame, font=ModernStyle.get_font(10),
                              bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                              relief='solid', borderwidth=1)
        value_entry.insert(0, value)
        value_entry.pack(fill=tk.X, pady=(2, 0), ipady=8)
        value_entry.bind('<Button-3>', lambda e, ent=value_entry: self._show_entry_selection_menu(e, ent))
        
        # 구분선
        tk.Frame(frame, bg=ModernStyle.BORDER, height=1).pack(fill=tk.X, pady=(10, 0))
        
        field_data = {'label_entry': label_entry, 'value_entry': value_entry, 'frame': frame}
        self.custom_field_widgets.append(field_data)
        
        return field_data
    
    def create_image_tab(self, parent):
        """이미지 관리 탭"""
        # 스크롤 캔버스
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_region(event, cid=canvas_window_id):
            try:
                canvas.itemconfig(cid, width=event.width - 20)
            except:
                pass
        canvas.bind('<Configure>', configure_scroll_region)
        
        # 마우스 휠
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable.bind("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 프로젝트 폴더
        project_type = self.mode if self.mode in ['drawings', 'graphics'] else 'projects'
        slug = self.project.get('slug', 'new-project')
        project_folder = IMAGES_DIR / project_type / slug
        
        # 헤더
        header = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=20, pady=(20, 5))
        
        tk.Label(header, text="이미지 관리", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        
        tk.Button(header, text="📂 폴더 열기", font=ModernStyle.get_font(9),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 command=lambda: self._open_folder(project_folder)).pack(side=tk.RIGHT, padx=5)
        
        # 안내
        info = tk.Label(scrollable, 
                       text="💡 각 영역의 '+ 추가' 버튼을 클릭하여 이미지를 등록하세요. 이미지는 자동으로 최적화되어 저장됩니다.",
                       font=ModernStyle.get_font(9), bg=ModernStyle.BG_LIGHT,
                       fg=ModernStyle.TEXT_MUTED, pady=10, padx=15, anchor='w', justify='left')
        info.pack(fill=tk.X, padx=20, pady=10)
        
        # 최적화 설정 안내
        opt_info = tk.Label(scrollable,
                           text=f"📊 최적화: 썸네일 {THUMB_MAX_SIZE}px / 메인 {MAIN_MAX_SIZE}px / 서브 {SUB_MAX_SIZE}px / 모델 {MODEL_MAX_SIZE}px / 슬라이드 {SLIDE_MAX_SIZE}px | JPEG {JPEG_QUALITY}%",
                           font=ModernStyle.get_font(8), bg=ModernStyle.BG_WHITE,
                           fg=ModernStyle.TEXT_SUBTLE)
        opt_info.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # 드래그 앤 드롭 매니저 생성
        self.drag_manager = DragDropManager(self)
        
        # 이미지 드롭존들
        self.drop_zones = []
        
        # 드래그 앤 드롭 안내
        drag_hint = tk.Label(scrollable, 
                            text="💡 이미지를 드래그하여 다른 카테고리로 이동할 수 있습니다",
                            font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                            fg=ModernStyle.ACCENT)
        drag_hint.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        # 썸네일 이미지 (그리드용 정사각형)
        thumb_zone = DropZone(scrollable, 'thumb', 
                             '🖼️ 썸네일 이미지 (thumb.jpg) - 프로젝트 목록 그리드에 표시되는 정사각형 이미지',
                             project_folder, on_change=self._on_image_change)
        thumb_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(thumb_zone)
        self.drag_manager.register_zone(thumb_zone)
        
        # 메인 이미지 (상세페이지 첫 이미지)
        main_zone = DropZone(scrollable, 'main',
                            '📷 메인 이미지 (main.jpg) - 프로젝트 상세페이지 맨 위에 표시되는 대표 이미지',
                            project_folder, on_change=self._on_image_change)
        main_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(main_zone)
        self.drag_manager.register_zone(main_zone)
        
        # === 메인 이미지 자르기 & 위치 조절 ===
        pos_frame = tk.Frame(scrollable, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
        pos_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.pos_frame = pos_frame  # 참조 저장
        self.project_folder = project_folder  # 참조 저장
        
        pos_header = tk.Frame(pos_frame, bg=ModernStyle.BG_LIGHT)
        pos_header.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(pos_header, text="✂️ 메인 이미지 자르기", font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT).pack(side=tk.LEFT)
        tk.Label(pos_header, text="비율 선택 후 드래그하여 표시 영역 조절", 
                font=ModernStyle.get_font(8), bg=ModernStyle.BG_LIGHT,
                fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT, padx=10)
        
        # === 비율 선택 영역 ===
        ratio_frame = tk.Frame(pos_frame, bg=ModernStyle.BG_WHITE)
        ratio_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(ratio_frame, text="비율:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT, padx=5)
        
        # 비율 옵션
        current_ratio = self.project.get('cover_ratio', '16:9')
        self.cover_ratio_var = tk.StringVar(value=current_ratio)
        
        ratio_options = [
            ('16:9', '16:9'),
            ('4:3', '4:3'),
            ('3:2', '3:2'),
            ('21:9', '21:9'),
            ('1:1', '1:1'),
            ('2:1', '2:1'),
        ]
        
        self.ratio_buttons = []
        for ratio_val, ratio_text in ratio_options:
            is_selected = (ratio_val == current_ratio) and not self._is_custom_ratio(current_ratio)
            btn = tk.Button(ratio_frame, text=ratio_text, 
                           font=ModernStyle.get_font(8),
                           bg=ModernStyle.ACCENT if is_selected else ModernStyle.BG_WHITE,
                           fg='white' if is_selected else ModernStyle.TEXT_PRIMARY,
                           relief='solid', borderwidth=1, padx=6, pady=2,
                           command=lambda r=ratio_val: self._set_cover_ratio(r))
            btn.pack(side=tk.LEFT, padx=1)
            self.ratio_buttons.append((btn, ratio_val))
        
        # 원본 비율 버튼
        self.original_ratio_btn = tk.Button(ratio_frame, text="📐 원본", 
                            font=ModernStyle.get_font(8),
                            bg=ModernStyle.BG_WHITE,
                            fg=ModernStyle.TEXT_PRIMARY,
                            relief='solid', borderwidth=1, padx=6, pady=2,
                            command=self._set_original_ratio)
        self.original_ratio_btn.pack(side=tk.LEFT, padx=(5, 1))
        
        # 자유 비율 버튼
        self.free_ratio_mode = tk.BooleanVar(value=self._is_custom_ratio(current_ratio))
        free_btn = tk.Button(ratio_frame, text="✋ 자유", 
                            font=ModernStyle.get_font(8),
                            bg=ModernStyle.ACCENT if self.free_ratio_mode.get() else ModernStyle.BG_WHITE,
                            fg='white' if self.free_ratio_mode.get() else ModernStyle.TEXT_PRIMARY,
                            relief='solid', borderwidth=1, padx=6, pady=2,
                            command=self._toggle_free_ratio)
        free_btn.pack(side=tk.LEFT, padx=(5, 1))
        self.free_ratio_btn = free_btn
        
        tk.Label(ratio_frame, text="(프레임 모서리 드래그)", font=ModernStyle.get_font(7),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT, padx=5)
        
        # 현재 값 로드 (키워드 또는 백분율 지원)
        current_pos = self.project.get('cover_position', 'center center')
        pos_map = {
            'left': 0, 'center': 50, 'right': 100,
            'top': 0, 'bottom': 100
        }
        parts = current_pos.split()
        
        # 백분율 또는 키워드 파싱
        if len(parts) >= 1:
            if '%' in parts[0]:
                x_pos = float(parts[0].replace('%', ''))
            else:
                x_pos = pos_map.get(parts[0], 50)
        else:
            x_pos = 50
        
        if len(parts) >= 2:
            if '%' in parts[1]:
                y_pos = float(parts[1].replace('%', ''))
            else:
                y_pos = pos_map.get(parts[1], 50)
        else:
            y_pos = 50
        
        self.cover_pos_var = tk.StringVar(value=current_pos)
        self.cover_pos_x = x_pos
        self.cover_pos_y = y_pos
        
        # === 이미지 미리보기 캔버스 ===
        canvas_frame = tk.Frame(pos_frame, bg=ModernStyle.BG_WHITE)
        canvas_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.canvas_frame = canvas_frame
        
        self.pos_canvas_width = 450
        self.pos_canvas_height = 250
        
        self.pos_canvas = tk.Canvas(canvas_frame, width=self.pos_canvas_width, 
                                   height=self.pos_canvas_height, bg='#333',
                                   highlightthickness=1, highlightbackground='#999')
        self.pos_canvas.pack(pady=5)
        
        # 이미지 로드
        self._load_main_image_preview()
        
        # 드래그 이벤트 (위치 이동 + 프레임 리사이즈)
        self.pos_canvas.bind('<Button-1>', self._on_canvas_click)
        self.pos_canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.pos_canvas.bind('<ButtonRelease-1>', self._on_canvas_release)
        self.pos_canvas.bind('<Motion>', self._on_canvas_motion)  # 커서 변경용
        
        # 마우스 휠 이벤트 (확대/축소)
        self.pos_canvas.bind('<MouseWheel>', self._on_mouse_wheel)
        self.pos_canvas.bind('<Button-4>', lambda e: self._zoom_in())  # Linux
        self.pos_canvas.bind('<Button-5>', lambda e: self._zoom_out())  # Linux
        
        self.resizing_frame = False
        
        # === 확대/축소 컨트롤 ===
        zoom_frame = tk.Frame(canvas_frame, bg=ModernStyle.BG_WHITE)
        zoom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 저장된 확대율 로드
        saved_zoom = self.project.get('cover_zoom', 1.5)
        try:
            initial_zoom = float(saved_zoom)
        except:
            initial_zoom = 1.5
        
        tk.Label(zoom_frame, text="🔍 확대/축소:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(zoom_frame, text="➖", width=3, command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = tk.Label(zoom_frame, text=f"{int(initial_zoom * 100)}%", font=ModernStyle.get_font(9, 'bold'),
                                  bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT, width=5)
        self.zoom_label.pack(side=tk.LEFT)
        
        ttk.Button(zoom_frame, text="➕", width=3, command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        
        tk.Label(zoom_frame, text="(마우스 휠로도 조절 가능)", font=ModernStyle.get_font(8),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT, padx=10)
        
        # === 정보 및 버튼 영역 ===
        pos_info = tk.Frame(canvas_frame, bg=ModernStyle.BG_WHITE)
        pos_info.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(pos_info, text="위치:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT, padx=5)
        self.pos_label = tk.Label(pos_info, textvariable=self.cover_pos_var, 
                                 font=ModernStyle.get_font(9, 'bold'),
                                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT)
        self.pos_label.pack(side=tk.LEFT)
        
        tk.Label(pos_info, text="  |  비율:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT)
        self.ratio_label = tk.Label(pos_info, textvariable=self.cover_ratio_var, 
                                   font=ModernStyle.get_font(9, 'bold'),
                                   bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT)
        self.ratio_label.pack(side=tk.LEFT)
        
        ttk.Button(pos_info, text="🔄 새로고침", 
                  command=self._refresh_main_image).pack(side=tk.RIGHT, padx=2)
        ttk.Button(pos_info, text="↺ 중앙으로", 
                  command=self._reset_cover_position).pack(side=tk.RIGHT, padx=2)
        
        # 서브 이미지
        sub_zone = DropZone(scrollable, 'sub', '📄 서브 이미지 (01.jpg, 02.jpg, ...) - 상세페이지 본문 이미지들',
                           project_folder, on_change=self._on_image_change)
        sub_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(sub_zone)
        self.drag_manager.register_zone(sub_zone)
        
        # 모델 이미지
        model_zone = DropZone(scrollable, 'model', '🏗 모델 이미지 (model_images/) - 3열 그리드로 표시',
                             project_folder, on_change=self._on_image_change)
        model_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(model_zone)
        self.drag_manager.register_zone(model_zone)
        
        # 슬라이드 이미지
        slide_zone = DropZone(scrollable, 'slide', '📑 슬라이드 이미지 (slide_images/) - 하단 추가 이미지',
                             project_folder, on_change=self._on_image_change)
        slide_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(slide_zone)
        self.drag_manager.register_zone(slide_zone)
        
        # 여백
        tk.Frame(scrollable, bg=ModernStyle.BG_WHITE, height=30).pack(fill=tk.X)
    
    def _open_folder(self, folder):
        if folder.exists():
            os.startfile(str(folder))
        else:
            if messagebox.askyesno("폴더 없음", "폴더를 생성하시겠습니까?"):
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "model_images").mkdir(exist_ok=True)
                os.startfile(str(folder))
    
    def _update_pos_canvas(self):
        """위치 조절 캔버스 업데이트"""
        if not hasattr(self, 'pos_photo') or self.pos_photo is None:
            return
        
        # 캔버스 초기화
        self.pos_canvas.delete('all')
        
        # 이미 계산된 뷰포트 크기 사용
        viewport_w = getattr(self, 'viewport_w', int(self.pos_canvas_width * 0.7))
        viewport_h = getattr(self, 'viewport_h', int(self.pos_canvas_height * 0.7))
        display_w, display_h = self.pos_display_size
        
        # 이동 가능 범위
        max_offset_x = getattr(self, 'max_offset_x', max(0, display_w - viewport_w))
        max_offset_y = getattr(self, 'max_offset_y', max(0, display_h - viewport_h))
        
        # 현재 위치에 따른 오프셋
        offset_x = int(self.cover_pos_x / 100 * max_offset_x) if max_offset_x > 0 else 0
        offset_y = int(self.cover_pos_y / 100 * max_offset_y) if max_offset_y > 0 else 0
        
        # 캔버스 중앙
        canvas_center_x = self.pos_canvas_width // 2
        canvas_center_y = self.pos_canvas_height // 2
        
        # 뷰포트 위치 (캔버스 중앙에 고정)
        vp_left = canvas_center_x - viewport_w // 2
        vp_top = canvas_center_y - viewport_h // 2
        vp_right = canvas_center_x + viewport_w // 2
        vp_bottom = canvas_center_y + viewport_h // 2
        
        # 이미지 위치 (뷰포트를 기준으로 오프셋 적용)
        img_x = vp_left - offset_x
        img_y = vp_top - offset_y
        
        # 이미지 표시
        self.pos_img_id = self.pos_canvas.create_image(img_x, img_y, 
                                                       image=self.pos_photo, anchor='nw')
        
        # 어두운 오버레이 (뷰포트 밖 영역) - 반투명 검정
        # 상단
        self.pos_canvas.create_rectangle(0, 0, self.pos_canvas_width, vp_top,
                                        fill='#000000', stipple='gray50', outline='')
        # 하단
        self.pos_canvas.create_rectangle(0, vp_bottom, self.pos_canvas_width, self.pos_canvas_height,
                                        fill='#000000', stipple='gray50', outline='')
        # 좌측
        self.pos_canvas.create_rectangle(0, vp_top, vp_left, vp_bottom,
                                        fill='#000000', stipple='gray50', outline='')
        # 우측
        self.pos_canvas.create_rectangle(vp_right, vp_top, self.pos_canvas_width, vp_bottom,
                                        fill='#000000', stipple='gray50', outline='')
        
        # 뷰포트 테두리 (녹색)
        self.pos_canvas.create_rectangle(vp_left, vp_top, vp_right, vp_bottom,
                                        outline='#00ff00', width=2)
        
        # 비율 텍스트 표시
        ratio_text = self.cover_ratio_var.get() if hasattr(self, 'cover_ratio_var') else '16:9'
        self.pos_canvas.create_text(vp_right - 5, vp_top + 5, text=ratio_text,
                                   fill='#00ff00', anchor='ne', font=('Arial', 10, 'bold'))
        
        # 자유 비율 모드일 때 리사이즈 핸들 표시
        if hasattr(self, 'free_ratio_mode') and self.free_ratio_mode.get():
            handle_size = 10
            # 우하단 핸들
            self.pos_canvas.create_rectangle(
                vp_right - handle_size, vp_bottom - handle_size,
                vp_right, vp_bottom,
                fill='#00ff00', outline='white', width=1
            )
            # 좌하단 핸들
            self.pos_canvas.create_rectangle(
                vp_left, vp_bottom - handle_size,
                vp_left + handle_size, vp_bottom,
                fill='#00ff00', outline='white', width=1
            )
            # 우상단 핸들
            self.pos_canvas.create_rectangle(
                vp_right - handle_size, vp_top,
                vp_right, vp_top + handle_size,
                fill='#00ff00', outline='white', width=1
            )
            # 좌상단 핸들
            self.pos_canvas.create_rectangle(
                vp_left, vp_top,
                vp_left + handle_size, vp_top + handle_size,
                fill='#00ff00', outline='white', width=1
            )
        
        # 뷰포트 좌표 저장
        self.vp_left = vp_left
        self.vp_top = vp_top
        self.vp_right = vp_right
        self.vp_bottom = vp_bottom
    
    def _on_canvas_click(self, event):
        """캔버스 클릭 - 리사이즈 또는 드래그 시작"""
        # 자유 비율 모드이고 모서리 근처인지 확인
        if hasattr(self, 'free_ratio_mode') and self.free_ratio_mode.get():
            vp_right = getattr(self, 'vp_right', self.pos_canvas_width // 2 + 100)
            vp_bottom = getattr(self, 'vp_bottom', self.pos_canvas_height // 2 + 75)
            vp_left = getattr(self, 'vp_left', self.pos_canvas_width // 2 - 100)
            vp_top = getattr(self, 'vp_top', self.pos_canvas_height // 2 - 75)
            
            handle_size = 15
            
            # 어느 모서리인지 확인
            if abs(event.x - vp_right) < handle_size and abs(event.y - vp_bottom) < handle_size:
                self.resize_corner = 'br'
            elif abs(event.x - vp_left) < handle_size and abs(event.y - vp_bottom) < handle_size:
                self.resize_corner = 'bl'
            elif abs(event.x - vp_right) < handle_size and abs(event.y - vp_top) < handle_size:
                self.resize_corner = 'tr'
            elif abs(event.x - vp_left) < handle_size and abs(event.y - vp_top) < handle_size:
                self.resize_corner = 'tl'
            else:
                self.resize_corner = None
            
            if self.resize_corner:
                self.resizing_frame = True
                self.resize_start_x = event.x
                self.resize_start_y = event.y
                self.resize_start_w = getattr(self, 'viewport_w', 200)
                self.resize_start_h = getattr(self, 'viewport_h', 150)
                return
        
        # 일반 드래그 시작
        self.resizing_frame = False
        self._pos_drag_start(event)
    
    def _on_canvas_drag(self, event):
        """캔버스 드래그 - 리사이즈 또는 위치 이동"""
        if getattr(self, 'resizing_frame', False):
            self._do_frame_resize(event)
        else:
            self._pos_drag_move(event)
    
    def _on_canvas_release(self, event):
        """캔버스 릴리즈"""
        if getattr(self, 'resizing_frame', False):
            self.resizing_frame = False
        else:
            self._pos_drag_end(event)
    
    def _on_canvas_motion(self, event):
        """마우스 이동 - 커서 변경"""
        if hasattr(self, 'free_ratio_mode') and self.free_ratio_mode.get():
            vp_right = getattr(self, 'vp_right', 0)
            vp_bottom = getattr(self, 'vp_bottom', 0)
            vp_left = getattr(self, 'vp_left', 0)
            vp_top = getattr(self, 'vp_top', 0)
            
            handle_size = 15
            
            # 모서리 근처면 커서 변경
            on_corner = (
                (abs(event.x - vp_right) < handle_size and abs(event.y - vp_bottom) < handle_size) or
                (abs(event.x - vp_left) < handle_size and abs(event.y - vp_bottom) < handle_size) or
                (abs(event.x - vp_right) < handle_size and abs(event.y - vp_top) < handle_size) or
                (abs(event.x - vp_left) < handle_size and abs(event.y - vp_top) < handle_size)
            )
            
            if on_corner:
                self.pos_canvas.config(cursor='sizing')
            else:
                self.pos_canvas.config(cursor='fleur')
        else:
            self.pos_canvas.config(cursor='fleur')
    
    def _do_frame_resize(self, event):
        """프레임 리사이즈 처리"""
        dx = event.x - self.resize_start_x
        dy = event.y - self.resize_start_y
        
        corner = getattr(self, 'resize_corner', 'br')
        
        # 모서리에 따라 크기 조정
        if corner == 'br':
            new_w = max(80, self.resize_start_w + dx * 2)
            new_h = max(60, self.resize_start_h + dy * 2)
        elif corner == 'bl':
            new_w = max(80, self.resize_start_w - dx * 2)
            new_h = max(60, self.resize_start_h + dy * 2)
        elif corner == 'tr':
            new_w = max(80, self.resize_start_w + dx * 2)
            new_h = max(60, self.resize_start_h - dy * 2)
        elif corner == 'tl':
            new_w = max(80, self.resize_start_w - dx * 2)
            new_h = max(60, self.resize_start_h - dy * 2)
        else:
            return
        
        # 캔버스 범위 내로 제한
        new_w = min(new_w, self.pos_canvas_width * 0.95)
        new_h = min(new_h, self.pos_canvas_height * 0.95)
        
        # 비율 계산 (간단한 정수 비율)
        ratio = new_w / new_h
        
        # 근사 비율 찾기
        if abs(ratio - 16/9) < 0.1:
            custom_ratio = "16:9"
        elif abs(ratio - 4/3) < 0.1:
            custom_ratio = "4:3"
        elif abs(ratio - 1) < 0.1:
            custom_ratio = "1:1"
        elif abs(ratio - 21/9) < 0.1:
            custom_ratio = "21:9"
        else:
            # 소수점 한자리까지 표시
            custom_ratio = f"{ratio:.1f}:1"
        
        self.viewport_w = int(new_w)
        self.viewport_h = int(new_h)
        self.max_offset_x = max(0, getattr(self, 'pos_display_size', (400, 250))[0] - new_w)
        self.max_offset_y = max(0, getattr(self, 'pos_display_size', (400, 250))[1] - new_h)
        
        self.cover_ratio_var.set(custom_ratio)
        self.project['cover_ratio'] = custom_ratio
        
        # 캔버스 업데이트
        self._update_pos_canvas()
    
    def _pos_drag_start(self, event):
        """드래그 시작"""
        self.pos_drag_start_x = event.x
        self.pos_drag_start_y = event.y
        self.pos_drag_start_pos_x = self.cover_pos_x
        self.pos_drag_start_pos_y = self.cover_pos_y
    
    def _pos_drag_move(self, event):
        """드래그 중"""
        if not hasattr(self, 'pos_photo') or self.pos_photo is None:
            return
        
        dx = event.x - self.pos_drag_start_x
        dy = event.y - self.pos_drag_start_y
        
        # 이동량을 백분율로 변환
        if hasattr(self, 'max_offset_x') and self.max_offset_x > 0:
            delta_percent_x = -dx / self.max_offset_x * 100
        else:
            delta_percent_x = 0
        
        if hasattr(self, 'max_offset_y') and self.max_offset_y > 0:
            delta_percent_y = -dy / self.max_offset_y * 100
        else:
            delta_percent_y = 0
        
        # 새 위치 계산
        new_x = self.pos_drag_start_pos_x + delta_percent_x
        new_y = self.pos_drag_start_pos_y + delta_percent_y
        
        # 범위 제한
        self.cover_pos_x = max(0, min(100, new_x))
        self.cover_pos_y = max(0, min(100, new_y))
        
        # 캔버스 업데이트
        self._update_pos_canvas()
        
        # 위치 문자열 업데이트
        self._update_position_string()
    
    def _pos_drag_end(self, event):
        """드래그 종료"""
        self._update_position_string()
        self.project['cover_position'] = self.cover_pos_var.get()
    
    def _update_position_string(self):
        """위치 백분율을 문자열로 변환"""
        # 백분율을 CSS object-position 값으로 변환
        x_percent = round(self.cover_pos_x)
        y_percent = round(self.cover_pos_y)
        
        # 가까운 명명된 위치로 변환 (5% 이내)
        x_names = [(0, 'left'), (50, 'center'), (100, 'right')]
        y_names = [(0, 'top'), (50, 'center'), (100, 'bottom')]
        
        x_name = None
        y_name = None
        
        for val, name in x_names:
            if abs(x_percent - val) <= 5:
                x_name = name
                break
        
        for val, name in y_names:
            if abs(y_percent - val) <= 5:
                y_name = name
                break
        
        if x_name and y_name:
            position = f"{x_name} {y_name}"
        else:
            position = f"{x_percent}% {y_percent}%"
        
        self.cover_pos_var.set(position)
    
    def _load_main_image_preview(self):
        """메인 이미지 미리보기 로드"""
        self.pos_image = None
        self.pos_photo = None
        self.pos_img_id = None
        self.pos_pil_image = None
        self.pos_display_size = (self.pos_canvas_width, self.pos_canvas_height)
        
        # 확대/축소 초기화 (저장된 값 또는 기본값)
        if not hasattr(self, 'pos_zoom'):
            saved_zoom = self.project.get('cover_zoom', 1.5)
            try:
                self.pos_zoom = float(saved_zoom)
            except:
                self.pos_zoom = 1.5  # 기본 1.5배 확대
        
        # 메인 이미지 찾기
        main_img_path = self.project_folder / "main.jpg"
        if not main_img_path.exists():
            main_img_path = self.project_folder / "main.webp"
        
        if main_img_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(main_img_path)
                self.pos_original_size = img.size
                self.pos_pil_image = img.copy()  # PIL 이미지 저장
                
                self._update_zoomed_image()
                
            except Exception as e:
                self.pos_canvas.delete('all')
                self.pos_canvas.create_text(self.pos_canvas_width // 2, self.pos_canvas_height // 2,
                                           text=f"이미지 로드 실패: {e}", fill='white')
        else:
            self.pos_canvas.delete('all')
            self.pos_canvas.create_text(self.pos_canvas_width // 2, self.pos_canvas_height // 2,
                                       text="메인 이미지 없음\n(이미지를 먼저 추가하세요)", 
                                       fill='white', justify='center')
    
    def _update_zoomed_image(self):
        """확대/축소된 이미지 업데이트"""
        if not hasattr(self, 'pos_pil_image') or self.pos_pil_image is None:
            return
        
        from PIL import Image, ImageTk
        
        img = self.pos_pil_image
        img_ratio = img.width / img.height
        
        # 뷰포트 비율 계산 (소수점 비율도 지원)
        cover_ratio = self.cover_ratio_var.get() if hasattr(self, 'cover_ratio_var') else '16:9'
        try:
            if ':' in cover_ratio:
                ratio_parts = cover_ratio.split(':')
                viewport_ratio = float(ratio_parts[0]) / float(ratio_parts[1])
            else:
                viewport_ratio = 16 / 9
        except:
            viewport_ratio = 16 / 9
        
        # 뷰포트 크기 (캔버스의 80%)
        viewport_w = int(self.pos_canvas_width * 0.8)
        viewport_h = int(viewport_w / viewport_ratio)
        
        if viewport_h > self.pos_canvas_height * 0.8:
            viewport_h = int(self.pos_canvas_height * 0.8)
            viewport_w = int(viewport_h * viewport_ratio)
        
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h
        
        # 이미지 크기 계산 (뷰포트 * 확대율)
        # 이미지가 뷰포트를 항상 덮도록 함
        if img_ratio > viewport_ratio:
            # 이미지가 더 넓음 - 높이 기준
            base_height = viewport_h
            base_width = int(base_height * img_ratio)
        else:
            # 이미지가 더 높음 - 너비 기준
            base_width = viewport_w
            base_height = int(base_width / img_ratio)
        
        # 확대율 적용
        display_width = int(base_width * self.pos_zoom)
        display_height = int(base_height * self.pos_zoom)
        
        self.pos_display_size = (display_width, display_height)
        
        # 이미지 리사이즈
        img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.pos_photo = ImageTk.PhotoImage(img_resized)
        
        # 이동 가능 범위 계산
        self.max_offset_x = max(0, display_width - viewport_w)
        self.max_offset_y = max(0, display_height - viewport_h)
        
        self._update_pos_canvas()
    
    def _on_mouse_wheel(self, event):
        """마우스 휠로 확대/축소"""
        if not hasattr(self, 'pos_pil_image') or self.pos_pil_image is None:
            return
        
        # 휠 방향에 따라 확대/축소
        if event.delta > 0:
            self.pos_zoom = min(3.0, self.pos_zoom + 0.1)  # 최대 3배
        else:
            self.pos_zoom = max(1.0, self.pos_zoom - 0.1)  # 최소 1배
        
        # 줌 라벨 업데이트
        if hasattr(self, 'zoom_label'):
            self.zoom_label.config(text=f"{int(self.pos_zoom * 100)}%")
        
        self._update_zoomed_image()
    
    def _zoom_in(self):
        """확대"""
        if not hasattr(self, 'pos_zoom'):
            self.pos_zoom = 1.5
        self.pos_zoom = min(3.0, self.pos_zoom + 0.2)
        if hasattr(self, 'zoom_label'):
            self.zoom_label.config(text=f"{int(self.pos_zoom * 100)}%")
        self._update_zoomed_image()
    
    def _zoom_out(self):
        """축소"""
        if not hasattr(self, 'pos_zoom'):
            self.pos_zoom = 1.5
        self.pos_zoom = max(1.0, self.pos_zoom - 0.2)
        if hasattr(self, 'zoom_label'):
            self.zoom_label.config(text=f"{int(self.pos_zoom * 100)}%")
        self._update_zoomed_image()
    
    def _is_custom_ratio(self, ratio):
        """커스텀 비율인지 확인"""
        standard_ratios = ['16:9', '4:3', '3:2', '21:9', '1:1', '2:1', '16:10']
        return ratio not in standard_ratios
    
    def _toggle_free_ratio(self):
        """자유 비율 모드 토글"""
        self.free_ratio_mode.set(not self.free_ratio_mode.get())
        
        if self.free_ratio_mode.get():
            # 자유 비율 버튼 활성화
            self.free_ratio_btn.configure(bg=ModernStyle.ACCENT, fg='white')
            # 다른 버튼 비활성화 스타일
            for btn, _ in self.ratio_buttons:
                btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
            # 원본 비율 버튼도 비활성화 스타일
            if hasattr(self, 'original_ratio_btn'):
                self.original_ratio_btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        else:
            # 16:9로 복귀
            self.free_ratio_btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
            self._set_cover_ratio('16:9')
    
    def _on_frame_resize_start(self, event):
        """프레임 리사이즈 시작"""
        if not self.free_ratio_mode.get():
            return
        
        # 마우스 위치가 프레임 모서리 근처인지 확인
        canvas_center_x = self.pos_canvas_width // 2
        canvas_center_y = self.pos_canvas_height // 2
        viewport_w = getattr(self, 'viewport_w', 200)
        viewport_h = getattr(self, 'viewport_h', 150)
        
        # 모서리 영역 (우하단)
        corner_x = canvas_center_x + viewport_w // 2
        corner_y = canvas_center_y + viewport_h // 2
        
        if abs(event.x - corner_x) < 15 and abs(event.y - corner_y) < 15:
            self.resizing_frame = True
            self.resize_start_x = event.x
            self.resize_start_y = event.y
            self.resize_start_w = viewport_w
            self.resize_start_h = viewport_h
        else:
            self.resizing_frame = False
    
    def _on_frame_resize_move(self, event):
        """프레임 리사이즈 중"""
        if not getattr(self, 'resizing_frame', False):
            return
        
        dx = event.x - self.resize_start_x
        dy = event.y - self.resize_start_y
        
        # 새 크기 계산
        new_w = max(50, self.resize_start_w + dx * 2)
        new_h = max(50, self.resize_start_h + dy * 2)
        
        # 캔버스 범위 내로 제한
        new_w = min(new_w, self.pos_canvas_width * 0.9)
        new_h = min(new_h, self.pos_canvas_height * 0.9)
        
        # 비율 계산
        ratio_w = int(new_w)
        ratio_h = int(new_h)
        
        # 간단한 비율로 변환 (최대공약수)
        from math import gcd
        g = gcd(ratio_w, ratio_h)
        ratio_w //= g
        ratio_h //= g
        
        # 너무 큰 숫자면 근사값 사용
        if ratio_w > 100 or ratio_h > 100:
            ratio_w = round(new_w / new_h * 10)
            ratio_h = 10
        
        custom_ratio = f"{ratio_w}:{ratio_h}"
        
        self.viewport_w = int(new_w)
        self.viewport_h = int(new_h)
        self.cover_ratio_var.set(custom_ratio)
        self.project['cover_ratio'] = custom_ratio
        
        # 캔버스 업데이트
        self._update_pos_canvas()
    
    def _on_frame_resize_end(self, event):
        """프레임 리사이즈 종료"""
        self.resizing_frame = False
    
    def _set_cover_ratio(self, ratio):
        """커버 비율 설정"""
        self.cover_ratio_var.set(ratio)
        self.project['cover_ratio'] = ratio
        
        # 자유 비율 모드 비활성화
        if hasattr(self, 'free_ratio_mode'):
            self.free_ratio_mode.set(False)
        if hasattr(self, 'free_ratio_btn'):
            self.free_ratio_btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        # 원본 비율 버튼 비활성화 스타일
        if hasattr(self, 'original_ratio_btn'):
            self.original_ratio_btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        
        # 버튼 스타일 업데이트
        if hasattr(self, 'ratio_buttons'):
            for btn, ratio_val in self.ratio_buttons:
                if ratio_val == ratio:
                    btn.configure(bg=ModernStyle.ACCENT, fg='white')
                else:
                    btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        
        # 이미지 크기 재계산
        if hasattr(self, 'pos_pil_image') and self.pos_pil_image:
            self._update_zoomed_image()
        elif hasattr(self, 'pos_photo') and self.pos_photo:
            self._update_pos_canvas()
    
    def _set_original_ratio(self):
        """원본 이미지의 비율 그대로 사용"""
        if not hasattr(self, 'pos_pil_image') or not self.pos_pil_image:
            messagebox.showwarning("알림", "먼저 메인 이미지를 첨부해주세요.")
            return
        
        # 원본 이미지 크기에서 비율 계산
        img_width, img_height = self.pos_pil_image.size
        
        # 최대공약수로 간단한 비율 만들기
        from math import gcd
        divisor = gcd(img_width, img_height)
        ratio_w = img_width // divisor
        ratio_h = img_height // divisor
        
        # 너무 큰 숫자면 근사값 사용
        if ratio_w > 100 or ratio_h > 100:
            # 소수점 비율로 표현
            ratio = f"{img_width}:{img_height}"
        else:
            ratio = f"{ratio_w}:{ratio_h}"
        
        self.cover_ratio_var.set(ratio)
        self.project['cover_ratio'] = ratio
        
        # 모든 비율 버튼 비활성화 스타일로
        if hasattr(self, 'ratio_buttons'):
            for btn, ratio_val in self.ratio_buttons:
                btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        if hasattr(self, 'free_ratio_btn'):
            self.free_ratio_btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        if hasattr(self, 'free_ratio_mode'):
            self.free_ratio_mode.set(False)
        
        # 원본 비율 버튼 활성화 스타일
        if hasattr(self, 'original_ratio_btn'):
            self.original_ratio_btn.configure(bg=ModernStyle.ACCENT, fg='white')
        
        # 캔버스 업데이트
        if hasattr(self, 'pos_pil_image') and self.pos_pil_image:
            self._update_zoomed_image()
        elif hasattr(self, 'pos_photo') and self.pos_photo:
            self._update_pos_canvas()
    
    def _on_ratio_combo_change(self):
        """설정 탭의 비율 콤보박스 변경 시"""
        ratio = self.cover_ratio_var.get()
        self.project['cover_ratio'] = ratio
        
        # 이미지 관리 탭의 비율 버튼 업데이트
        if hasattr(self, 'ratio_buttons'):
            for btn, ratio_val in self.ratio_buttons:
                if ratio_val == ratio:
                    btn.configure(bg=ModernStyle.ACCENT, fg='white')
                else:
                    btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
        
        # 캔버스 업데이트
        if hasattr(self, 'pos_photo') and self.pos_photo:
            self._update_pos_canvas()
    
    def _refresh_main_image(self):
        """메인 이미지 새로고침"""
        self._load_main_image_preview()
    
    def _reset_cover_position(self):
        """위치를 중앙으로 초기화"""
        self.cover_pos_x = 50
        self.cover_pos_y = 50
        self._update_pos_canvas()
        self._update_position_string()
        self.project['cover_position'] = 'center center'
    
    def _set_cover_position(self, position):
        """메인 이미지 위치 설정 (백분율 또는 이름)"""
        self.cover_pos_var.set(position)
        self.project['cover_position'] = position
        
        # 위치 문자열을 백분율로 변환
        pos_map = {
            'left': 0, 'center': 50, 'right': 100,
            'top': 0, 'bottom': 100
        }
        parts = position.split()
        if len(parts) >= 2:
            if '%' in parts[0]:
                self.cover_pos_x = float(parts[0].replace('%', ''))
            else:
                self.cover_pos_x = pos_map.get(parts[0], 50)
            
            if '%' in parts[1]:
                self.cover_pos_y = float(parts[1].replace('%', ''))
            else:
                self.cover_pos_y = pos_map.get(parts[1], 50)
        
        if hasattr(self, 'pos_canvas'):
            self._update_pos_canvas()
    
    def _on_image_change(self):
        """이미지 변경 시 - 메인 이미지 미리보기 업데이트"""
        # 잠시 후 이미지 새로고침 (파일 저장 완료 대기)
        if hasattr(self, 'pos_canvas'):
            self.after(500, self._refresh_main_image)
    
    def create_caption_tab(self, parent):
        """캡션 관리 탭 - 홈페이지 미리보기 스타일"""
        # 스크롤 캔버스
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_region(event, cid=canvas_window_id):
            try:
                canvas.itemconfig(cid, width=event.width - 20)
            except:
                pass
        canvas.bind('<Configure>', configure_scroll_region)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable.bind("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 프로젝트 폴더
        project_type = self.mode if self.mode in ['drawings', 'graphics'] else 'projects'
        slug = self.project.get('slug', 'new-project')
        project_folder = IMAGES_DIR / project_type / slug
        
        # 헤더 - 깔끔한 디자인
        header = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        tk.Label(header, text="이미지 캡션 편집", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        tk.Label(header, text="각 이미지에 설명을 추가합니다. 저장 후 브라우저 새로고침(Ctrl+Shift+R) 필요", 
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=(3, 0))
        
        # 캡션 저장소 참조
        self.caption_project_folder = project_folder
        self.caption_labels = {}
        
        # === 서브 이미지 섹션 ===
        self._create_caption_section(scrollable, project_folder, 'sub', "서브 이미지")
        
        # === 슬라이드 이미지 섹션 ===
        slide_folder = project_folder / "slide_images"
        self._create_caption_section(scrollable, slide_folder, 'slide', "슬라이드 이미지", is_slide=True)
    
    def _create_caption_section(self, parent, folder, image_type, title, is_slide=False):
        """캡션 섹션 생성 - 깔끔한 UI"""
        section = tk.Frame(parent, bg=ModernStyle.BG_WHITE)
        section.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        # 섹션 헤더 - 간단하게
        header = tk.Frame(section, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header, text=title, font=ModernStyle.get_font(11, 'bold'),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # 이미지 목록
        images = []
        if folder.exists():
            if is_slide:
                for f in sorted(folder.glob("*.*"), key=lambda x: self._sort_key_num(x)):
                    if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        images.append(f)
            else:
                for f in sorted(folder.glob("[0-9][0-9].*")):
                    if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        images.append(f)
        
        # 이미지 수 표시
        caption_count = 0
        captions = CaptionManager.load_captions(self.caption_project_folder)
        for img in images:
            key = f"{image_type}_{img.stem}"
            if key in captions:
                caption_count += 1
        
        count_text = f"{len(images)}개 중 {caption_count}개 캡션"
        tk.Label(header, text=count_text, font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.RIGHT)
        
        if not images:
            tk.Label(section, text="이미지가 없습니다", 
                    font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE, 
                    fg=ModernStyle.TEXT_SUBTLE).pack(anchor='w', pady=10)
            return
        
        # 이미지 + 캡션 미리보기
        for img_path in images:
            self._create_caption_item(section, img_path, image_type, captions)
    
    def _sort_key_num(self, path):
        """숫자 기반 정렬 키"""
        try:
            return int(''.join(filter(str.isdigit, path.stem)) or 0)
        except:
            return 0
    
    def _create_caption_item(self, parent, img_path, image_type, captions):
        """캡션 아이템 생성 - 깔끔한 UI"""
        # 캡션 키 생성
        if image_type == 'sub':
            caption_key = f"sub_{img_path.stem}"
        else:
            caption_key = f"slide_{img_path.stem}"
        
        caption_text = captions.get(caption_key, "")
        has_caption = bool(caption_text)
        
        # 컨테이너 - 깔끔한 흰색 배경
        container = tk.Frame(parent, bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1)
        container.pack(fill=tk.X, pady=5)
        
        # 내부 레이아웃
        inner = tk.Frame(container, bg=ModernStyle.BG_WHITE)
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        
        # 상단: 이미지 + 캡션 입력
        top_row = tk.Frame(inner, bg=ModernStyle.BG_WHITE)
        top_row.pack(fill=tk.X)
        
        # 왼쪽: 이미지 썸네일
        try:
            thumb = ImageOptimizer.create_thumbnail(img_path, size=(120, 80))
            if thumb:
                img_frame = tk.Frame(top_row, bg=ModernStyle.BG_WHITE)
                img_frame.pack(side=tk.LEFT)
                
                img_label = tk.Label(img_frame, image=thumb, bg=ModernStyle.BG_WHITE,
                                    relief='solid', borderwidth=1)
                img_label.image = thumb
                img_label.pack()
                
                # 파일명
                tk.Label(img_frame, text=img_path.name, font=ModernStyle.get_font(8),
                        bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack()
        except:
            tk.Label(top_row, text="📷", font=ModernStyle.get_font(16),
                    bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT)
        
        # 오른쪽: 캡션 입력 영역
        right = tk.Frame(top_row, bg=ModernStyle.BG_WHITE)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0))
        
        # 캡션 텍스트 영역
        self.caption_texts = getattr(self, 'caption_texts', {})
        
        caption_entry = tk.Text(right, font=ModernStyle.get_font(10),
                               height=3, wrap=tk.WORD, relief='solid', borderwidth=1,
                               bg=ModernStyle.BG_WHITE)
        caption_entry.pack(fill=tk.BOTH, expand=True)
        
        if caption_text:
            caption_entry.insert('1.0', caption_text)
        
        # 우클릭으로 링크 추가 기능
        caption_entry.bind('<Button-3>', lambda e, txt=caption_entry: self._show_caption_link_menu(e, txt))
        
        self.caption_texts[caption_key] = caption_entry
        
        # 버튼 영역
        btn_frame = tk.Frame(right, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(anchor='e', pady=(5, 0))
        
        # 저장 버튼
        tk.Button(btn_frame, text="저장", font=ModernStyle.get_font(9),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                 relief='solid', borderwidth=1, padx=12, cursor='hand2',
                 command=lambda k=caption_key, e=caption_entry: self._save_inline_caption(k, e)).pack(side=tk.LEFT, padx=(0, 5))
        
        # 삭제 버튼
        if has_caption:
            tk.Button(btn_frame, text="삭제", font=ModernStyle.get_font(9),
                     bg=ModernStyle.BG_WHITE, fg=ModernStyle.DANGER,
                     relief='solid', borderwidth=1, padx=8, cursor='hand2',
                     command=lambda k=caption_key: self._delete_caption(k)).pack(side=tk.LEFT)
        
        # 레이블 참조 저장
        self.caption_labels[caption_key] = (caption_entry, container)
    
    def _save_inline_caption(self, caption_key, text_widget):
        """인라인 캡션 저장"""
        caption = text_widget.get('1.0', tk.END).strip()
        captions = CaptionManager.load_captions(self.caption_project_folder)
        
        if caption:
            captions[caption_key] = caption
        elif caption_key in captions:
            del captions[caption_key]
        
        CaptionManager.save_captions(self.caption_project_folder, captions)
        messagebox.showinfo("저장", "캡션이 저장되었습니다.\n브라우저에서 Ctrl+Shift+R로 새로고침하세요.")
        self._refresh_caption_tab()
    
    def _edit_caption(self, img_path, image_type):
        """캡션 편집 다이얼로그 열기"""
        CaptionDialog(
            self,
            img_path,
            image_type,
            self.caption_project_folder,
            on_save=self._refresh_caption_tab
        )
    
    def _delete_caption(self, caption_key):
        """캡션 삭제"""
        if messagebox.askyesno("확인", "이 캡션을 삭제하시겠습니까?"):
            captions = CaptionManager.load_captions(self.caption_project_folder)
            if caption_key in captions:
                del captions[caption_key]
                CaptionManager.save_captions(self.caption_project_folder, captions)
            self._refresh_caption_tab()
    
    def _show_caption_link_menu(self, event, text_widget):
        """캡션 텍스트 우클릭 시 링크 추가 메뉴 표시"""
        try:
            # 선택된 텍스트 확인
            selected = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(
                    label=f"🔗 '{selected[:20]}...' 에 링크 추가" if len(selected) > 20 else f"🔗 '{selected}' 에 링크 추가",
                    command=lambda: self._add_caption_link(text_widget, selected)
                )
                menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            # 선택된 텍스트 없음
            pass
    
    def _add_caption_link(self, text_widget, selected_text):
        """캡션의 선택된 텍스트에 링크 추가"""
        popup = tk.Toplevel(self)
        popup.title("🔗 캡션에 링크 추가")
        popup.geometry("450x300")
        popup.configure(bg=ModernStyle.BG_WHITE)
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 450) // 2
        y = (popup.winfo_screenheight() - 300) // 2
        popup.geometry(f"+{x}+{y}")
        
        current_text = text_widget.get('1.0', tk.END).strip()
        
        # 헤더
        tk.Label(popup, text="선택한 텍스트에 링크 추가", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(15, 10))
        
        # 선택된 텍스트 표시
        tk.Label(popup, text="선택된 텍스트:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        selected_frame = tk.Frame(popup, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
        selected_frame.pack(fill=tk.X, padx=20, pady=(3, 10))
        tk.Label(selected_frame, text=selected_text, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.ACCENT, wraplength=380).pack(padx=10, pady=8)
        
        # URL 입력
        tk.Label(popup, text="URL 주소", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        url_entry = tk.Entry(popup, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        url_entry.insert(0, "https://")
        url_entry.pack(fill=tk.X, padx=20, pady=(3, 10), ipady=6)
        
        # 스타일 선택
        tk.Label(popup, text="링크 스타일", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        style_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        style_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        style_var = tk.StringVar(value="highlight")
        
        highlight_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        highlight_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(highlight_frame, text="", variable=style_var, value="highlight",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(highlight_frame, text=" 하이라이트 ", font=ModernStyle.get_font(10),
                bg=ModernStyle.ACCENT, fg="white").pack(side=tk.LEFT)
        
        underline_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        underline_frame.pack(side=tk.LEFT)
        tk.Radiobutton(underline_frame, text="", variable=style_var, value="underline",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(underline_frame, text="밑줄", font=('Segoe UI', 10, 'underline'),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        def apply_link():
            url = url_entry.get().strip()
            style = style_var.get()
            
            if url and url != "https://":
                # 마크다운 형식으로 변환: [텍스트](URL|스타일)
                markdown_link = f"[{selected_text}]({url}|{style})"
                new_text = current_text.replace(selected_text, markdown_link, 1)
                text_widget.delete('1.0', tk.END)
                text_widget.insert('1.0', new_text)
                popup.destroy()
            else:
                messagebox.showwarning("URL 필요", "URL을 입력해주세요.", parent=popup)
        
        # 버튼
        btn_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Button(btn_frame, text="✓ 저장", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=6, command=apply_link).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=6, command=popup.destroy).pack(side=tk.LEFT)
        
        # 엔터 키로 저장
        popup.bind('<Return>', lambda e: apply_link())
        url_entry.focus_set()
    
    def _refresh_caption_tab(self):
        """캡션 탭 새로고침"""
        # 노트북의 캡션 탭 찾기
        for widget in self.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Notebook):
                        # 캡션 탭 (인덱스 2) 새로고침
                        for tab in child.winfo_children():
                            if child.index(tab) == 2:  # 캡션 탭
                                for w in tab.winfo_children():
                                    w.destroy()
                                self.create_caption_tab(tab)
                                return
    
    def create_layout_tab(self, parent):
        """레이아웃 설정 탭"""
        # 스크롤 캔버스
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_region(event, cid=canvas_window_id):
            try:
                canvas.itemconfig(cid, width=event.width - 20)
            except:
                pass
        canvas.bind('<Configure>', configure_scroll_region)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 헤더
        header = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(header, text="레이아웃 설정", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        tk.Label(header, text="프로젝트 상세 페이지에서 이미지가 표시되는 방식을 설정합니다.",
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_MUTED).pack(anchor=tk.W, pady=(5, 0))
        
        settings = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        settings.pack(fill=tk.X, padx=20, pady=20)
        
        # 모델 이미지 열 수
        row1 = tk.Frame(settings, bg=ModernStyle.BG_WHITE)
        row1.pack(fill=tk.X, pady=10)
        tk.Label(row1, text="모델 이미지 열 수:", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        self.model_cols = tk.StringVar(value=self.project.get('model_cols', '3'))
        tk.Spinbox(row1, from_=2, to=4, textvariable=self.model_cols,
                  width=5, font=ModernStyle.get_font(10)).pack(side=tk.LEFT, padx=10)
        
        # 슬라이드 표시
        row2 = tk.Frame(settings, bg=ModernStyle.BG_WHITE)
        row2.pack(fill=tk.X, pady=10)
        self.show_slides = tk.BooleanVar(value=self.project.get('show_slides', True))
        tk.Checkbutton(row2, text=" 슬라이드 이미지 표시", variable=self.show_slides,
                      font=ModernStyle.get_font(10), bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        
        # 커버 비율 (이미지 관리 탭의 비율 선택과 연동)
        row3 = tk.Frame(settings, bg=ModernStyle.BG_WHITE)
        row3.pack(fill=tk.X, pady=10)
        tk.Label(row3, text="커버 이미지 비율:", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        # cover_ratio_var가 이미 생성되어 있으면 사용, 아니면 생성
        if not hasattr(self, 'cover_ratio_var'):
            self.cover_ratio_var = tk.StringVar(value=self.project.get('cover_ratio', '16:9'))
        combo = ttk.Combobox(row3, textvariable=self.cover_ratio_var,
                    values=['16:9', '4:3', '3:2', '21:9', '1:1', '2:1'],
                    width=10, state='readonly')
        combo.pack(side=tk.LEFT, padx=10)
        combo.bind('<<ComboboxSelected>>', lambda e: self._on_ratio_combo_change())
        tk.Label(row3, text="(이미지 관리 탭에서 시각적으로 조절 가능)", 
                font=ModernStyle.get_font(8), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT, padx=5)
    
    def save(self):
        """저장"""
        title = self.entries['title'].get().strip()
        if not title:
            messagebox.showwarning("경고", "제목은 필수입니다.")
            return
        
        # display_title 처리: 비어있으면 title 사용
        display_title = self.entries['display_title'].get().strip()
        if not display_title:
            display_title = title
        
        # 커스텀 필드 수집 (줄바꿈 제거 - JSON 호환성)
        custom_fields = []
        if hasattr(self, 'custom_field_widgets'):
            for field_data in self.custom_field_widgets:
                label = field_data['label_entry'].get().strip().upper()
                # 줄바꿈을 쉼표+공백으로 대체
                value = field_data['value_entry'].get().strip().replace('\n', ', ').replace('\r', '')
                if label and value:
                    custom_fields.append({'label': label, 'value': value})
        
        # 새 slug 결정
        new_slug = self.entries['slug'].get().strip() or title.lower().replace(' ', '-').replace('_', '-')
        old_slug = self.project.get('slug', '')
        
        # slug이 변경되었거나 새 프로젝트인 경우 폴더 이동/생성
        project_type = self.mode if self.mode in ['drawings', 'graphics'] else 'projects'
        if old_slug and old_slug != new_slug:
            old_folder = IMAGES_DIR / project_type / old_slug
            new_folder = IMAGES_DIR / project_type / new_slug
            
            if old_folder.exists() and not new_folder.exists():
                try:
                    shutil.move(str(old_folder), str(new_folder))
                except Exception as e:
                    print(f"폴더 이동 오류: {e}")
        
        self.result = {
            'id': self.project.get('id'),
            'index': self.project.get('index'),
            'title': title,
            'slug': new_slug,
            'display_title': display_title,
            'display_year': self.entries['display_year'].get().strip(),
            'location': self.entries['location'].get().strip(),
            'duration': self.entries['duration'].get().strip(),
            'program': self.entries['program'].get().strip(),
            'studio': self.entries['studio'].get().strip(),
            # 줄바꿈 보존 (JSON은 \n을 자동 이스케이프)
            'description': self.entries['description'].get('1.0', tk.END).strip().replace('\r\n', '\n').replace('\r', '\n'),
            'description_ko': self.entries['description_ko'].get('1.0', tk.END).strip().replace('\r\n', '\n').replace('\r', '\n'),
            'visible': self.visible_var.get(),
            'model_cols': self.model_cols.get(),
            'show_slides': self.show_slides.get(),
            'cover_ratio': self.cover_ratio_var.get() if hasattr(self, 'cover_ratio_var') else '16:9',
            'cover_position': self.cover_pos_var.get() if hasattr(self, 'cover_pos_var') else 'center center',
            'cover_zoom': self.pos_zoom if hasattr(self, 'pos_zoom') else 1.5,
            'custom_fields': custom_fields,
        }
        
        if self.on_save:
            self.on_save(self.result)
        
        self.destroy()
    
    def preview(self):
        """미리보기 - 저장 후 브라우저에서 열기"""
        # 먼저 저장
        self.save()
        # 브라우저에서 열기
        if self.mode == 'drawings':
            html_path = DRAWINGS_HTML
        elif self.mode == 'graphics':
            html_path = GRAPHICS_HTML
        else:
            html_path = PROJECTS_HTML
        webbrowser.open(f'file:///{html_path}')


class TabManagerDialog(tk.Toplevel):
    """탭(카테고리) 관리 다이얼로그"""
    
    # 탭 설정 파일
    TABS_CONFIG_FILE = SCRIPT_DIR / "tabs_config.json"
    
    # 기본 탭 구성
    DEFAULT_TABS = [
        {"id": "projects", "name": "PROJECTS", "file": "projects.html", "visible": True, "order": 0},
        {"id": "drawings", "name": "DRAWINGS", "file": "drawings.html", "visible": True, "order": 1},
        {"id": "graphics", "name": "GRAPHICS", "file": "graphics.html", "visible": True, "order": 2}
    ]
    
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.title("📑 탭(카테고리) 관리")
        self.geometry("700x550")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.on_save = on_save
        
        self.transient(parent)
        self.grab_set()
        
        # 중앙 배치
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 700) // 2
        y = (self.winfo_screenheight() - 550) // 2
        self.geometry(f"+{x}+{y}")
        
        self.tabs = self.load_tabs()
        self.create_ui()
    
    @classmethod
    def load_tabs(cls):
        """탭 설정 로드"""
        if cls.TABS_CONFIG_FILE.exists():
            try:
                with open(cls.TABS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    tabs = json.load(f)
                return sorted(tabs, key=lambda x: x.get('order', 0))
            except:
                pass
        return cls.DEFAULT_TABS.copy()
    
    @classmethod
    def save_tabs(cls, tabs):
        """탭 설정 저장"""
        for i, tab in enumerate(tabs):
            tab['order'] = i
        with open(cls.TABS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(tabs, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def get_visible_tabs(cls):
        """보이는 탭만 반환"""
        tabs = cls.load_tabs()
        return [t for t in tabs if t.get('visible', True)]
    
    def create_ui(self):
        # 헤더
        header = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=25, pady=(20, 15))
        
        tk.Label(header, text="📑 탭(카테고리) 관리", 
                font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        
        tk.Label(header, text="네비게이션에 표시될 탭을 관리합니다", 
                font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(side=tk.LEFT, padx=(15, 0))
        
        # 설명
        info_frame = tk.Frame(self, bg=ModernStyle.BG_LIGHT)
        info_frame.pack(fill=tk.X, padx=25, pady=(0, 15))
        tk.Label(info_frame, text="💡 탭을 추가/수정하면 자동으로 HTML 파일이 생성됩니다. 드래그하여 순서를 변경할 수 있습니다.",
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_LIGHT, 
                fg=ModernStyle.TEXT_MUTED).pack(padx=15, pady=10)
        
        # 리스트 프레임
        list_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 15))
        
        # 리스트 헤더
        header_row = tk.Frame(list_frame, bg=ModernStyle.BG_LIGHT)
        header_row.pack(fill=tk.X)
        
        tk.Label(header_row, text="순서", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=6).pack(side=tk.LEFT, padx=5)
        tk.Label(header_row, text="탭 이름", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=20, anchor='w').pack(side=tk.LEFT, padx=10)
        tk.Label(header_row, text="ID (영문)", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=15, anchor='w').pack(side=tk.LEFT, padx=10)
        tk.Label(header_row, text="파일명", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=18, anchor='w').pack(side=tk.LEFT, padx=10)
        tk.Label(header_row, text="공개", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=6).pack(side=tk.LEFT, padx=5)
        
        # 스크롤 가능한 리스트
        canvas = tk.Canvas(list_frame, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.tabs_container = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.create_window((0, 0), window=self.tabs_container, anchor='nw')
        self.tabs_container.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self.tab_widgets = []
        self.refresh_tabs_list()
        
        # 버튼
        btn_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=25, pady=(0, 20))
        
        tk.Button(btn_frame, text="+ 새 탭 추가", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=15, pady=8, command=self.add_tab).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="✓ 저장", font=ModernStyle.get_font(10),
                 bg=ModernStyle.SUCCESS, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=8, command=self.save).pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=8, command=self.destroy).pack(side=tk.RIGHT, padx=(0, 10))
    
    def refresh_tabs_list(self):
        """탭 리스트 새로고침"""
        for widget in self.tabs_container.winfo_children():
            widget.destroy()
        self.tab_widgets = []
        
        for i, tab in enumerate(self.tabs):
            row = tk.Frame(self.tabs_container, bg=ModernStyle.BG_WHITE)
            row.pack(fill=tk.X, pady=3)
            
            # 순서
            tk.Label(row, text=f"{i + 1}", font=ModernStyle.get_font(10),
                    bg=ModernStyle.BG_WHITE, width=6).pack(side=tk.LEFT, padx=5)
            
            # 탭 이름
            name_var = tk.StringVar(value=tab.get('name', ''))
            name_entry = tk.Entry(row, textvariable=name_var, width=20,
                                 font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            name_entry.pack(side=tk.LEFT, padx=10, ipady=3)
            
            # ID
            id_var = tk.StringVar(value=tab.get('id', ''))
            id_entry = tk.Entry(row, textvariable=id_var, width=15,
                               font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            id_entry.pack(side=tk.LEFT, padx=10, ipady=3)
            
            # 파일명
            file_var = tk.StringVar(value=tab.get('file', ''))
            file_entry = tk.Entry(row, textvariable=file_var, width=18,
                                 font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            file_entry.pack(side=tk.LEFT, padx=10, ipady=3)
            
            # 공개 체크박스
            visible_var = tk.BooleanVar(value=tab.get('visible', True))
            cb = tk.Checkbutton(row, variable=visible_var, bg=ModernStyle.BG_WHITE)
            cb.pack(side=tk.LEFT, padx=5)
            
            # 순서 변경 버튼
            order_frame = tk.Frame(row, bg=ModernStyle.BG_WHITE)
            order_frame.pack(side=tk.LEFT, padx=10)
            
            if i > 0:
                tk.Button(order_frame, text="▲", font=ModernStyle.get_font(8),
                         bg=ModernStyle.BG_WHITE, relief='flat',
                         command=lambda idx=i: self.move_tab(idx, -1)).pack(side=tk.LEFT)
            if i < len(self.tabs) - 1:
                tk.Button(order_frame, text="▼", font=ModernStyle.get_font(8),
                         bg=ModernStyle.BG_WHITE, relief='flat',
                         command=lambda idx=i: self.move_tab(idx, 1)).pack(side=tk.LEFT)
            
            # 삭제 버튼
            tk.Button(row, text="✕", font=ModernStyle.get_font(9),
                     bg=ModernStyle.DANGER, fg=ModernStyle.BG_WHITE, relief='flat',
                     padx=8, command=lambda idx=i: self.delete_tab(idx)).pack(side=tk.RIGHT, padx=5)
            
            self.tab_widgets.append({
                'name_var': name_var,
                'id_var': id_var,
                'file_var': file_var,
                'visible_var': visible_var
            })
    
    def move_tab(self, idx, direction):
        """탭 순서 변경"""
        self.collect_tab_data()
        new_idx = idx + direction
        if 0 <= new_idx < len(self.tabs):
            self.tabs[idx], self.tabs[new_idx] = self.tabs[new_idx], self.tabs[idx]
            self.refresh_tabs_list()
    
    def add_tab(self):
        """새 탭 추가 - 모드 선택 포함"""
        self.collect_tab_data()
        
        # 모드 선택 다이얼로그
        mode_dialog = tk.Toplevel(self)
        mode_dialog.title("새 탭 추가")
        mode_dialog.geometry("400x300")
        mode_dialog.configure(bg=ModernStyle.BG_WHITE)
        mode_dialog.transient(self)
        mode_dialog.grab_set()
        
        # 중앙 배치
        mode_dialog.update_idletasks()
        x = (mode_dialog.winfo_screenwidth() - 400) // 2
        y = (mode_dialog.winfo_screenheight() - 300) // 2
        mode_dialog.geometry(f"+{x}+{y}")
        
        tk.Label(mode_dialog, text="탭 모드 선택", font=ModernStyle.get_font(12, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(pady=(20, 15))
        
        selected_mode = tk.StringVar(value="project")
        
        modes = [
            ("project", "📁 프로젝트 그리드", "이미지 썸네일 그리드 형식 (기존 방식)"),
            ("magazine", "📰 매거진", "기사 목록 형식 (제목, 카테고리, 날짜)"),
            ("gallery", "🖼️ 갤러리", "전체 화면 이미지 슬라이드쇼"),
        ]
        
        for mode_id, mode_name, mode_desc in modes:
            frame = tk.Frame(mode_dialog, bg=ModernStyle.BG_WHITE)
            frame.pack(fill=tk.X, padx=30, pady=5)
            
            rb = tk.Radiobutton(frame, text=mode_name, variable=selected_mode, value=mode_id,
                               font=ModernStyle.get_font(11), bg=ModernStyle.BG_WHITE,
                               anchor='w')
            rb.pack(side=tk.TOP, anchor='w')
            tk.Label(frame, text=mode_desc, font=ModernStyle.get_font(9),
                    fg=ModernStyle.TEXT_MUTED, bg=ModernStyle.BG_WHITE).pack(anchor='w', padx=25)
        
        def on_continue():
            mode = selected_mode.get()
            mode_dialog.destroy()
            self.create_new_tab_with_mode(mode)
        
        btn_frame = tk.Frame(mode_dialog, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, pady=20, padx=30)
        
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=6, command=mode_dialog.destroy).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="다음 →", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE, relief='flat',
                 padx=20, pady=6, command=on_continue).pack(side=tk.RIGHT)
    
    def create_new_tab_with_mode(self, mode):
        """선택한 모드로 새 탭 생성"""
        new_id = simpledialog.askstring("새 탭", "탭 ID를 입력하세요 (영문, 예: photography):", parent=self)
        if not new_id:
            return
        new_id = new_id.lower().replace(' ', '-')
        
        # 중복 확인
        if any(t['id'] == new_id for t in self.tabs):
            messagebox.showerror("오류", f"'{new_id}' ID가 이미 존재합니다.")
            return
        
        new_tab = {
            "id": new_id,
            "name": new_id.upper(),
            "file": f"{new_id}.html",
            "visible": True,
            "order": len(self.tabs),
            "mode": mode  # 탭 모드 저장
        }
        self.tabs.append(new_tab)
        self.refresh_tabs_list()
    
    def delete_tab(self, idx):
        """탭 삭제"""
        tab = self.tabs[idx]
        if messagebox.askyesno("확인", f"'{tab['name']}' 탭을 삭제하시겠습니까?\n\n※ HTML 파일은 삭제되지 않습니다."):
            self.tabs.pop(idx)
            self.refresh_tabs_list()
    
    def collect_tab_data(self):
        """위젯에서 데이터 수집"""
        for i, widgets in enumerate(self.tab_widgets):
            if i < len(self.tabs):
                self.tabs[i]['name'] = widgets['name_var'].get()
                self.tabs[i]['id'] = widgets['id_var'].get()
                self.tabs[i]['file'] = widgets['file_var'].get()
                self.tabs[i]['visible'] = widgets['visible_var'].get()
    
    def save(self):
        """저장"""
        self.collect_tab_data()
        
        # 유효성 검사
        for tab in self.tabs:
            if not tab['id'] or not tab['name'] or not tab['file']:
                messagebox.showerror("오류", "모든 필드를 입력해주세요.")
                return
        
        # 탭 설정 저장
        self.save_tabs(self.tabs)
        
        # 없는 HTML 파일 생성
        self.create_missing_html_files()
        
        # 모든 HTML 파일의 네비게이션 업데이트
        self.update_all_navigation()
        
        messagebox.showinfo("완료", "탭 설정이 저장되었습니다.")
        
        if self.on_save:
            self.on_save()
        
        self.destroy()
    
    def create_missing_html_files(self):
        """없는 HTML 파일 생성 - 모드별 템플릿 사용"""
        
        # 프로젝트 그리드 템플릿
        project_template = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — JEONHYERIN</title>
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
  <link rel="stylesheet" href="styles.css">
</head>
<body class="page-archive">
  
  <nav class="nav nav--archive" aria-label="Main navigation">
    <div class="nav-inner">
      <a href="index.html" class="nav-logo">JEONHYERIN</a>
      <div class="nav-links">
{nav_links}
        <a href="about.html" class="nav-link">ABOUT</a>
      </div>
    </div>
  </nav>

  <main class="archive">
    <header class="archive-header">
      <h1 class="archive-title">{title}</h1>
      <span class="archive-count">00</span>
    </header>

    <div class="archive-grid" role="list">
    </div>
  </main>

  <div class="overlay" id="projectOverlay" role="dialog" aria-modal="true" aria-hidden="true">
    <div class="overlay-backdrop"></div>
    <div class="overlay-content">
      <button class="overlay-close" aria-label="Close detail view">
        <span class="close-icon"></span>
      </button>
      <div class="overlay-scroll">
        <article class="project-detail"></article>
      </div>
      <nav class="overlay-nav" aria-label="Navigation">
        <button class="overlay-nav-btn overlay-nav-prev" aria-label="Previous"><span>PREV</span></button>
        <button class="overlay-nav-btn overlay-nav-top" aria-label="Scroll to top"><span class="arrow-up-icon"></span></button>
        <button class="overlay-nav-btn overlay-nav-next" aria-label="Next"><span>NEXT</span></button>
      </nav>
    </div>
  </div>

  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="footer-header">
        <div class="footer-logo">JEONHYERIN</div>
        <p class="footer-description">Portfolio</p>
      </div>
      <hr class="footer-divider">
      <div class="footer-bottom">
        <p class="footer-copyright">© 2026 JEONHYERIN. All rights reserved.</p>
      </div>
    </div>
  </footer>

  <script type="application/json" id="projectsData">[]</script>
  <script type="application/json" id="footerData">{{}}</script>
  <script src="script.js"></script>
</body>
</html>'''

        # 매거진 템플릿
        magazine_template = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — JEONHYERIN</title>
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
  <link rel="stylesheet" href="styles.css">
</head>
<body class="page-study-magazine">
  
  <header class="magazine-banner"></header>
  
  <nav class="nav nav--archive magazine-nav" aria-label="Main navigation">
    <div class="nav-inner">
      <a href="index.html" class="nav-logo">JEONHYERIN</a>
      <div class="nav-links">
{nav_links}
        <a href="about.html" class="nav-link">ABOUT</a>
      </div>
    </div>
  </nav>

  <main class="magazine-content">
    <div class="magazine-list" id="magazineList"></div>
  </main>

  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="footer-header">
        <div class="footer-logo">JEONHYERIN</div>
        <p class="footer-description">Portfolio</p>
      </div>
      <hr class="footer-divider">
      <div class="footer-bottom">
        <p class="footer-copyright">© 2026 JEONHYERIN. All rights reserved.</p>
      </div>
    </div>
  </footer>

  <script type="application/json" id="magazineData">[]</script>

  <script>
    function formatDate(dateStr) {{
      const date = new Date(dateStr);
      const options = {{ year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }};
      return date.toLocaleDateString('en-US', options).toUpperCase().replace(',', '');
    }}

    function renderMagazine() {{
      const container = document.getElementById('magazineList');
      const dataEl = document.getElementById('magazineData');
      if (!dataEl) return;
      
      let articles = [];
      try {{ articles = JSON.parse(dataEl.textContent); }} catch (e) {{ return; }}

      container.innerHTML = articles
        .filter(a => a.visible !== false)
        .map(article => `
          <article class="magazine-article" ${{article.link ? `onclick="window.open('${{article.link}}', '_blank')"` : ''}}>
            <span class="magazine-category">${{article.category || 'STUDY'}}</span>
            <h2 class="magazine-title">${{article.title}}</h2>
            <time class="magazine-date">${{formatDate(article.date)}}</time>
          </article>
        `).join('');
    }}

    document.addEventListener('DOMContentLoaded', renderMagazine);
  </script>

  <script src="script.js"></script>
</body>
</html>'''

        # 갤러리 템플릿
        gallery_template = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — JEONHYERIN</title>
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
</head>
<body class="page-gallery">
  
  <nav class="nav nav--archive" aria-label="Main navigation">
    <div class="nav-inner">
      <a href="index.html" class="nav-logo">JEONHYERIN</a>
      <div class="nav-links">
{nav_links}
        <a href="about.html" class="nav-link">ABOUT</a>
      </div>
    </div>
  </nav>

  <main class="gallery-content">
    <div class="gallery-slider" id="gallerySlider"></div>
  </main>

  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="footer-header">
        <div class="footer-logo">JEONHYERIN</div>
        <p class="footer-description">Portfolio</p>
      </div>
      <hr class="footer-divider">
      <div class="footer-bottom">
        <p class="footer-copyright">© 2026 JEONHYERIN. All rights reserved.</p>
      </div>
    </div>
  </footer>

  <script type="application/json" id="galleryData">[]</script>
  <script src="script.js"></script>
</body>
</html>'''
        
        for tab in self.tabs:
            html_path = SCRIPT_DIR / tab['file']
            if not html_path.exists():
                # 네비게이션 링크 생성
                nav_links = []
                for t in self.tabs:
                    active = ' nav-link--active' if t['id'] == tab['id'] else ''
                    nav_links.append(f'        <a href="{t["file"]}" class="nav-link{active}">{t["name"]}</a>')
                
                # 모드에 따라 템플릿 선택
                mode = tab.get('mode', 'project')
                if mode == 'magazine':
                    template = magazine_template
                elif mode == 'gallery':
                    template = gallery_template
                else:
                    template = project_template
                
                content = template.format(
                    title=tab['name'],
                    nav_links='\n'.join(nav_links)
                )
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 이미지 폴더 생성
                img_folder = IMAGES_DIR / tab['id']
                img_folder.mkdir(parents=True, exist_ok=True)
    
    def update_all_navigation(self):
        """모든 HTML 파일의 네비게이션 업데이트"""
        # 네비게이션 링크 생성
        visible_tabs = [t for t in self.tabs if t.get('visible', True)]
        
        for tab in self.tabs:
            html_path = SCRIPT_DIR / tab['file']
            if html_path.exists():
                try:
                    with open(html_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 네비게이션 링크 생성
                    nav_links = []
                    for t in visible_tabs:
                        active = ' nav-link--active' if t['id'] == tab['id'] else ''
                        nav_links.append(f'        <a href="{t["file"]}" class="nav-link{active}">{t["name"]}</a>')
                    nav_html = '\n'.join(nav_links)
                    
                    # nav-links 내용 교체 (about.html 링크 전까지)
                    pattern = r'(<div class="nav-links">)\s*([\s\S]*?)(\s*<a href="about\.html")'
                    replacement = f'\\1\n{nav_html}\n\\3'
                    content = re.sub(pattern, replacement, content)
                    
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    print(f"Error updating {html_path}: {e}")
        
        # about.html과 index.html도 업데이트
        for html_file in [ABOUT_HTML, INDEX_HTML]:
            if html_file.exists():
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    nav_links = []
                    for t in visible_tabs:
                        nav_links.append(f'        <a href="{t["file"]}" class="nav-link">{t["name"]}</a>')
                    nav_html = '\n'.join(nav_links)
                    
                    pattern = r'(<div class="nav-links">)\s*([\s\S]*?)(\s*<a href="about\.html")'
                    replacement = f'\\1\n{nav_html}\n\\3'
                    content = re.sub(pattern, replacement, content)
                    
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    print(f"Error updating {html_file}: {e}")


class BackupOptionsDialog(tk.Toplevel):
    """백업 옵션 선택 대화상자"""
    
    def __init__(self, parent, on_backup):
        super().__init__(parent)
        self.title("💾 백업 생성")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.on_backup = on_backup
        self.result = None
        self.backup_type_var = tk.StringVar(value="full")
        self.auto_version_var = tk.BooleanVar(value=True)
        self.version_name_var = tk.StringVar(value="")
        self.file_vars = {
            name: tk.BooleanVar(value=True)
            for name in get_backup_target_map().keys()
        }
        self.file_checks = []
        
        self._create_ui()
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
    
    def _center_window(self):
        # size to requested widget size (ensure buttons are visible)
        self.update_idletasks()
        req_w = max(450, self.winfo_reqwidth())
        req_h = max(380, self.winfo_reqheight())
        x = (self.winfo_screenwidth() // 2) - (req_w // 2)
        y = (self.winfo_screenheight() // 2) - (req_h // 2)
        self.geometry(f"{req_w}x{req_h}+{x}+{y}")
    
    def _create_ui(self):
        root = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        root.pack(fill=tk.BOTH, expand=True, padx=18, pady=16)
        
        tk.Label(root, text="백업 상세 설정", font=ModernStyle.get_font(14, "bold"),
                 bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(anchor="w")
        tk.Label(
            root,
            text="백업 유형을 선택하고 '생성(저장)' 버튼을 누르세요.",
            font=ModernStyle.get_font(10),
            bg=ModernStyle.BG_WHITE,
            fg=ModernStyle.TEXT_MUTED,
        ).pack(anchor="w", pady=(4, 14))
        
        type_frame = tk.LabelFrame(
            root,
            text="백업 방식",
            font=ModernStyle.get_font(10, "bold"),
            bg=ModernStyle.BG_WHITE,
            fg=ModernStyle.TEXT_PRIMARY,
            padx=12,
            pady=8,
        )
        type_frame.pack(fill=tk.X)
        
        options = [
            ("📦 전체 파일 백업", "핵심 사이트 파일 전체를 백업합니다.", "full"),
            ("📝 업데이트된 부분만 백업", "직전 백업 대비 변경된 파일만 저장합니다.", "changed"),
            ("🎯 선택하여 백업", "원하는 파일만 골라 백업합니다.", "selected"),
        ]
        
        for title, desc, value in options:
            row = tk.Frame(type_frame, bg=ModernStyle.BG_WHITE)
            row.pack(fill=tk.X, pady=3)
            tk.Radiobutton(
                row,
                text=title,
                value=value,
                variable=self.backup_type_var,
                command=self._update_file_selection_state,
                bg=ModernStyle.BG_WHITE,
                anchor="w",
                font=ModernStyle.get_font(10),
                relief="flat",
                highlightthickness=0,
            ).pack(anchor="w")
            tk.Label(
                row,
                text=desc,
                font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_SUBTLE,
            ).pack(anchor="w", padx=(24, 0))
        
        self.select_frame = tk.LabelFrame(
            root,
            text="선택 백업 파일",
            font=ModernStyle.get_font(10, "bold"),
            bg=ModernStyle.BG_WHITE,
            fg=ModernStyle.TEXT_PRIMARY,
            padx=12,
            pady=8,
        )
        self.select_frame.pack(fill=tk.X, pady=(10, 0))
        
        file_grid = tk.Frame(self.select_frame, bg=ModernStyle.BG_WHITE)
        file_grid.pack(fill=tk.X)
        
        for i, filename in enumerate(get_backup_target_map().keys()):
            var = self.file_vars[filename]
            chk = ttk.Checkbutton(file_grid, text=filename, variable=var)
            chk.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=2)
            self.file_checks.append(chk)
        
        version_frame = tk.LabelFrame(
            root,
            text="버전 설정",
            font=ModernStyle.get_font(10, "bold"),
            bg=ModernStyle.BG_WHITE,
            fg=ModernStyle.TEXT_PRIMARY,
            padx=12,
            pady=8,
        )
        version_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Checkbutton(
            version_frame,
            text="버전명 자동 생성 (v1, v2 ...)",
            variable=self.auto_version_var,
            command=self._toggle_version_input,
        ).pack(anchor="w")
        
        version_row = tk.Frame(version_frame, bg=ModernStyle.BG_WHITE)
        version_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(version_row, text="수동 버전명:", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        self.version_entry = tk.Entry(
            version_row,
            textvariable=self.version_name_var,
            font=ModernStyle.get_font(10),
            relief="solid",
            borderwidth=1,
            width=20,
        )
        self.version_entry.pack(side=tk.LEFT, padx=(8, 0))
        
        btn_row = tk.Frame(root, bg=ModernStyle.BG_WHITE)
        btn_row.pack(fill=tk.X, pady=(16, 0))
        
        ttk.Button(btn_row, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_row, text="생성(저장)", command=self._submit).pack(side=tk.RIGHT)
        
        self._toggle_version_input()
        self._update_file_selection_state()
    
    def _toggle_version_input(self):
        state = tk.DISABLED if self.auto_version_var.get() else tk.NORMAL
        self.version_entry.configure(state=state)
        if state == tk.NORMAL:
            self.version_entry.focus_set()
    
    def _update_file_selection_state(self):
        enabled = self.backup_type_var.get() == "selected"
        state = "normal" if enabled else "disabled"
        for chk in self.file_checks:
            chk.configure(state=state)
    
    def _submit(self):
        backup_type = self.backup_type_var.get()
        auto_version = self.auto_version_var.get()
        version_name = self.version_name_var.get().strip()
        
        if not auto_version and not version_name:
            messagebox.showwarning("입력 필요", "수동 버전명을 입력하세요.")
            return
        
        selected_files = []
        if backup_type == "selected":
            selected_files = [
                name for name, var in self.file_vars.items() if var.get()
            ]
            if not selected_files:
                messagebox.showwarning("선택 필요", "백업할 파일을 1개 이상 선택하세요.")
                return
        
        try:
            self.on_backup(backup_type, version_name, auto_version, selected_files)
            self.destroy()
        except TypeError:
            self.on_backup(backup_type, version_name, auto_version)
            self.destroy()
        except Exception as e:
            messagebox.showerror("백업 실패", str(e))


class BackupManagerDialog(tk.Toplevel):
    """백업 관리 대화상자"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📁 백업 관리")
        self.geometry("700x500")
        self.configure(bg=ModernStyle.BG_WHITE)
        # 다른 창 클릭 시에도 유지
        self.lift()
        
        self._create_ui()
        self._load_backups()
    
    def _create_ui(self):
        # 헤더
        header = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(header, text="백업 관리", font=ModernStyle.get_font(16, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        
        # 버튼
        btn_frame = tk.Frame(header, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="🔄 새로고침", command=self._load_backups).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📂 시간별 정리", command=self._organize_by_time).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ 오래된 백업 삭제", command=self._cleanup_old).pack(side=tk.LEFT, padx=2)
        
        # 트리뷰
        tree_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        columns = ('date', 'time', 'version', 'type', 'files', 'size')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        self.tree.heading('date', text='날짜')
        self.tree.heading('time', text='시간')
        self.tree.heading('version', text='버전')
        self.tree.heading('type', text='유형')
        self.tree.heading('files', text='파일')
        self.tree.heading('size', text='크기')
        
        self.tree.column('date', width=90)
        self.tree.column('time', width=70)
        self.tree.column('version', width=80)
        self.tree.column('type', width=70)
        self.tree.column('files', width=250)
        self.tree.column('size', width=70)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self._open_backup_folder)
        
        # 하단 버튼
        bottom = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        bottom.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(bottom, text="📂 폴더 열기", command=self._open_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="📋 변경사항 보기", command=self._view_changelog).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="🔙 복원", command=self._restore_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom, text="닫기", command=self.destroy).pack(side=tk.RIGHT)
        
        # 통계
        self.stats_label = tk.Label(bottom, text="", font=ModernStyle.get_font(9),
                                   bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE)
        self.stats_label.pack(side=tk.LEFT, padx=20)
    
    def _load_backups(self):
        """백업 목록 로드"""
        self.tree.delete(*self.tree.get_children())
        self.backups = {}
        
        if not BACKUP_DIR.exists():
            return
        
        total_size = 0
        count = 0
        
        import re
        for date_dir in sorted(BACKUP_DIR.iterdir(), reverse=True):
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                for time_dir in sorted(date_dir.iterdir(), reverse=True):
                    if time_dir.is_dir():
                        files = list_backup_payload_files(time_dir)
                        if files:
                            # 크기 계산
                            size = sum(f.stat().st_size for f in files)
                            total_size += size
                            
                            # 폴더명에서 버전 추출 (예: 143052_v5 -> v5)
                            folder_name = time_dir.name
                            version_match = re.search(r'_(.+)$', folder_name)
                            version_str = version_match.group(1) if version_match else "-"
                            
                            # 백업 유형 확인 (VERSION.txt = Full, CHANGELOG.md = Changed)
                            version_file = time_dir / "VERSION.txt"
                            changelog_file = time_dir / "CHANGELOG.md"
                            selected_file = time_dir / "SELECTED.txt"
                            if version_file.exists():
                                backup_type = "📦 전체"
                            elif selected_file.exists():
                                backup_type = "🎯 선택"
                            elif changelog_file.exists():
                                backup_type = "📝 변경"
                            else:
                                backup_type = "-"
                            
                            # 날짜/시간 포맷
                            date_str = f"{date_dir.name[:4]}-{date_dir.name[4:6]}-{date_dir.name[6:]}"
                            time_part = folder_name.split('_')[0] if '_' in folder_name else folder_name
                            if len(time_part) == 6:
                                time_str = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
                            else:
                                time_str = time_part
                            
                            iid = self.tree.insert('', 'end', values=(
                                date_str,
                                time_str,
                                version_str,
                                backup_type,
                                ', '.join(f.name for f in files[:6]) + (" ..." if len(files) > 6 else ""),
                                f"{size // 1024}KB"
                            ))
                            
                            self.backups[iid] = time_dir
                            count += 1
        
        self.stats_label.config(text=f"총 {count}개 백업 | {total_size // 1024 // 1024}MB")
    
    def _open_backup_folder(self, event):
        """백업 폴더 열기"""
        self._open_selected()
    
    def _open_selected(self):
        """선택된 백업 폴더 열기"""
        selected = self.tree.selection()
        if selected:
            path = self.backups.get(selected[0])
            if path and path.exists():
                os.startfile(str(path))
    
    def _view_changelog(self):
        """변경사항 보기"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("알림", "백업을 선택하세요.")
            return
        
        path = self.backups.get(selected[0])
        if path:
            changelog = path / "CHANGELOG.md"
            selected_note = path / "SELECTED.txt"
            if changelog.exists():
                content = changelog.read_text(encoding='utf-8')
                title = "변경사항"
            elif selected_note.exists():
                content = selected_note.read_text(encoding='utf-8')
                title = "선택 백업 정보"
            else:
                messagebox.showinfo("알림", "변경사항 파일이 없습니다.")
                return
            
            # 뷰어 창
            viewer = tk.Toplevel(self)
            viewer.title(title)
            viewer.geometry("600x400")
            
            text = scrolledtext.ScrolledText(viewer, font=ModernStyle.get_font(10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert('1.0', content)
            text.config(state='disabled')
    
    def _restore_selected(self):
        """선택된 백업 복원"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("알림", "복원할 백업을 선택하세요.")
            return
        
        path = self.backups.get(selected[0])
        if path:
            files = [f.name for f in list_backup_payload_files(path)]
            if files:
                if messagebox.askyesno("복원 확인", 
                                      f"다음 파일들을 복원하시겠습니까?\n\n" + 
                                      "\n".join(f"  • {f}" for f in files) +
                                      "\n\n⚠️ 현재 파일이 백업된 후 복원됩니다."):
                    # 복원 수행
                    for filename in files:
                        src = path / filename
                        dst = get_backup_target_map().get(filename)
                        if dst is None:
                            continue
                        shutil.copy(src, dst)
                    
                    messagebox.showinfo("복원 완료", "백업이 복원되었습니다.\n관리자 도구를 다시 시작해주세요.")
                    self.destroy()
    
    def _cleanup_old(self):
        """오래된 백업 삭제"""
        days = simpledialog.askinteger("백업 정리", 
                                      "며칠 이전의 백업을 삭제하시겠습니까?",
                                      initialvalue=30, minvalue=1, maxvalue=365)
        if not days:
            return
        
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        for date_dir in list(BACKUP_DIR.iterdir()):
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                    if dir_date < cutoff:
                        shutil.rmtree(date_dir)
                        deleted += 1
                except:
                    pass
        
        messagebox.showinfo("정리 완료", f"{deleted}일 분량의 백업이 삭제되었습니다.")
        self._load_backups()
    
    def _organize_by_time(self):
        """날짜 폴더 내 파일들을 시간별 폴더로 정리"""
        import re
        organized = 0
        
        for date_dir in BACKUP_DIR.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                # 날짜 폴더 내의 HTML 파일들
                for file in list(date_dir.glob("*.html")):
                    name = file.stem
                    match = re.search(r'_(\d{8})_(\d{6})', name)
                    
                    if match:
                        time_str = match.group(2)
                        
                        # 시간 폴더 생성
                        time_folder = date_dir / time_str
                        time_folder.mkdir(exist_ok=True)
                        
                        # 원본 파일명 (projects.html, drawings.html, about.html)
                        original_name = name.split('_')[0] + '.html'
                        new_path = time_folder / original_name
                        
                        if not new_path.exists():
                            shutil.move(str(file), str(new_path))
                            organized += 1
                        else:
                            # 중복 파일 삭제
                            file.unlink()
        
        messagebox.showinfo("정리 완료", f"{organized}개 파일이 시간별 폴더로 정리되었습니다.")
        self._load_backups()


class RestoreDialog(tk.Toplevel):
    """백업 복원 대화상자"""
    
    def __init__(self, parent, backups, on_restore):
        super().__init__(parent)
        self.title("🔙 백업 복원")
        self.geometry("500x400")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.lift()
        
        self.backups = backups
        self.on_restore = on_restore
        
        self._create_ui()
    
    def _create_ui(self):
        # 안내
        tk.Label(self, text="복원할 백업을 선택하세요", font=ModernStyle.get_font(12, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(pady=15)
        
        # 백업 목록
        list_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        self.listbox = tk.Listbox(list_frame, font=ModernStyle.get_font(10), height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for i, backup in enumerate(self.backups):
            date_str = f"{backup['date'][:4]}-{backup['date'][4:6]}-{backup['date'][6:]}"
            time_str = backup['time']
            if len(time_str) == 6:
                time_str = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            self.listbox.insert(tk.END, f"{date_str} {time_str} - {', '.join(backup['files'])}")
        
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        
        # 파일 선택
        file_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        file_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(file_frame, text="복원할 파일:", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        self.file_vars = {}
        self.file_checks = tk.Frame(file_frame, bg=ModernStyle.BG_WHITE)
        self.file_checks.pack(fill=tk.X)
        
        # 버튼
        btn_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        ttk.Button(btn_frame, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="✓ 복원", command=self._restore).pack(side=tk.RIGHT)
    
    def _on_select(self, event):
        """백업 선택 시"""
        selection = self.listbox.curselection()
        if not selection:
            return
        
        backup = self.backups[selection[0]]
        
        # 파일 체크박스 업데이트
        for widget in self.file_checks.winfo_children():
            widget.destroy()
        
        self.file_vars = {}
        for filename in backup['files']:
            var = tk.BooleanVar(value=True)
            self.file_vars[filename] = var
            ttk.Checkbutton(self.file_checks, text=filename, variable=var).pack(anchor='w')
    
    def _restore(self):
        """복원 수행"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("알림", "백업을 선택하세요.")
            return
        
        backup = self.backups[selection[0]]
        files_to_restore = [f for f, var in self.file_vars.items() if var.get()]
        
        if not files_to_restore:
            messagebox.showinfo("알림", "복원할 파일을 선택하세요.")
            return
        
        if messagebox.askyesno("복원 확인", 
                              f"다음 파일들을 복원하시겠습니까?\n\n" + 
                              "\n".join(f"  • {f}" for f in files_to_restore) +
                              "\n\n⚠️ 현재 파일이 먼저 백업됩니다."):
            self.on_restore(backup['path'], files_to_restore)
            self.destroy()


class AboutEditorDialog(tk.Toplevel):
    """About 페이지 편집 - 현재 Futura 스타일 about.html에 맞춤"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("About 페이지 편집")
        self.geometry("800x900")
        self.configure(bg=ModernStyle.BG_WHITE)
        # 다른 창 클릭 시에도 유지
        self.lift()
        
        # 중앙 배치
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 800) // 2
        y = (self.winfo_screenheight() - 900) // 2
        self.geometry(f"+{x}+{y}")
        
        self.load_about_data()
        self.create_ui()
    
    def load_about_data(self):
        self.data = {
            'name_main': 'Hyerin Jeon,',
            'name_title': 'Student',
            'affiliation': 'Student of Yonsei University, Dept. of Interior Architecture and Built Environment',
            'email': 'rnaakfn123@gmail.com',
            'instagram': '@herisharch',
            'education': [],
            'experience': [],
            'exhibitions': []
        }
        try:
            with open(ABOUT_HTML, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 이름 (name-main) - 링크 포함 가능
            match = re.search(r'<span class="name-main">([\s\S]*?)</span>', content)
            if match:
                self.data['name_main'] = self._html_to_markdown(match.group(1).strip())
            
            # 타이틀 (name-title) - 링크 포함 가능
            match = re.search(r'<span class="name-title">([\s\S]*?)</span>', content)
            if match:
                self.data['name_title'] = self._html_to_markdown(match.group(1).strip())
            
            # 소속 (affiliation) - 링크 포함 가능
            match = re.search(r'<p class="about-affiliation">([\s\S]*?)</p>', content)
            if match:
                affiliation_html = match.group(1).strip()
                # HTML 링크를 마크다운 형식으로 변환
                self.data['affiliation'] = self._html_to_markdown(affiliation_html)
            
            # CONTACT 섹션에서 이메일과 인스타그램 파싱 (순서 기반)
            contact_pattern = r'<h2 class="cv-heading">CONTACT</h2>\s*<ul class="cv-list-simple">([\s\S]*?)</ul>'
            contact_match = re.search(contact_pattern, content)
            if contact_match:
                contact_content = contact_match.group(1)
                # 모든 <li> 항목 추출
                li_items = re.findall(r'<li>([\s\S]*?)</li>', contact_content)
                
                # 첫 번째 항목: 이메일 (mailto: 포함)
                for item in li_items:
                    if 'mailto:' in item:
                        email_match = re.search(r'mailto:([^"]+)', item)
                        if email_match:
                            self.data['email'] = email_match.group(1)
                        break
                
                # 두 번째 항목: 인스타그램 (instagram.com 포함 또는 @ 포함)
                for item in li_items:
                    if 'instagram.com' in item:
                        # HTML 링크를 마크다운으로 변환
                        self.data['instagram'] = self._html_to_markdown(item)
                        break
                    elif '@' in item and 'mailto:' not in item:
                        # @ 기호가 있고 mailto가 아닌 경우
                        text = re.sub(r'<[^>]+>', '', item).strip()
                        self.data['instagram'] = text
                        break
            
            # EDUCATION 파싱
            self.data['education'] = self._parse_cv_section(content, 'EDUCATION')
            
            # EXPERIENCE 파싱
            self.data['experience'] = self._parse_cv_section(content, 'EXPERIENCE')
            
            # EXHIBITIONS 파싱
            self.data['exhibitions'] = self._parse_cv_section(content, 'EXHIBITIONS')
            
        except Exception as e:
            print(f"About 데이터 로드 오류: {e}")
    
    def _parse_cv_section(self, content, section_name):
        """CV 섹션의 항목들을 파싱"""
        items = []
        pattern = rf'<h2 class="cv-heading">{section_name}</h2>\s*<ul class="cv-list-simple">([\s\S]*?)</ul>'
        match = re.search(pattern, content)
        if match:
            list_content = match.group(1)
            # cv-date와 cv-content 파싱
            item_pattern = r'<li><span class="cv-date">([^<]*)</span><span class="cv-content">([\s\S]*?)</span></li>'
            for item_match in re.finditer(item_pattern, list_content):
                date = item_match.group(1).strip()
                content_html = item_match.group(2).strip()
                # HTML 링크를 마크다운 형식으로 변환
                content_md = self._html_to_markdown(content_html)
                items.append({'date': date, 'content': content_md})
        return items
    
    def _html_to_markdown(self, html_text):
        """HTML 링크를 마크다운 형식 [텍스트](URL|스타일)로 변환 (스타일 보존)"""
        def replace_link(match):
            full_tag = match.group(0)
            url = match.group(1)
            text = match.group(2)
            
            # 스타일 클래스 확인
            if 'link-underline' in full_tag:
                return f'[{text}]({url}|underline)'
            else:
                # 기본값: highlight (link-highlight 또는 클래스 없음)
                return f'[{text}]({url}|highlight)'
        
        pattern = r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>'
        return re.sub(pattern, replace_link, html_text)
    
    def create_ui(self):
        # 스크롤 캔버스
        canvas = tk.Canvas(self, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_width(event, cid=canvas_window_id):
            try:
                canvas.itemconfig(cid, width=event.width - 20)
            except:
                pass
        canvas.bind('<Configure>', configure_scroll_width)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.entries = {}
        self.section_widgets = {'education': [], 'experience': [], 'exhibitions': []}
        
        # 헤더
        tk.Label(scrollable, text="About 페이지 편집", font=ModernStyle.get_font(16, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(20, 10))
        
        # === 기본 정보 섹션 ===
        self._create_section_header(scrollable, "기본 정보 (Hero)")
        
        # 이름 (콤마 포함)
        self._create_linkable_field(scrollable, 'name_main', '이름 (예: Hyerin Jeon,)', 
                                   self.data.get('name_main', ''))
        
        # 타이틀
        self._create_linkable_field(scrollable, 'name_title', '타이틀 (예: Student)', 
                                   self.data.get('name_title', ''))
        
        # 소속
        self._create_linkable_field(scrollable, 'affiliation', '소속 (한 줄 설명)', 
                                   self.data.get('affiliation', ''))
        
        # === EDUCATION 섹션 ===
        self._create_editable_section(scrollable, 'education', 'EDUCATION (학력)', self.data['education'])
        
        # === EXPERIENCE 섹션 ===
        self._create_editable_section(scrollable, 'experience', 'EXPERIENCE (경력)', self.data['experience'])
        
        # === EXHIBITIONS 섹션 ===
        self._create_editable_section(scrollable, 'exhibitions', 'EXHIBITIONS (전시)', self.data['exhibitions'])
        
        # === 연락처 섹션 ===
        self._create_section_header(scrollable, "연락처 (CONTACT)")
        
        for key, label in [('email', '이메일'), ('instagram', '인스타그램 (@username)')]:
            self._create_linkable_field(scrollable, key, label, self.data.get(key, ''))
        
        # 버튼
        btn_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=30)
        
        tk.Button(btn_frame, text="💾 저장", font=ModernStyle.get_font(11, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=25, pady=8, command=self.save).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=20, pady=8, command=self.destroy).pack(side=tk.LEFT)
    
    def _create_section_header(self, parent, title):
        """섹션 헤더 생성"""
        frame = tk.Frame(parent, bg=ModernStyle.BG_LIGHT)
        frame.pack(fill=tk.X, padx=20, pady=(15, 5))
        tk.Label(frame, text=title, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY).pack(anchor=tk.W, padx=10, pady=8)
    
    def _create_linkable_field(self, parent, key, label, value):
        """링크 편집 가능한 텍스트 필드 생성 - 텍스트 드래그 선택 지원"""
        frame = tk.Frame(parent, bg=ModernStyle.BG_WHITE)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        # 라벨 + 안내
        label_frame = tk.Frame(frame, bg=ModernStyle.BG_WHITE)
        label_frame.pack(fill=tk.X)
        tk.Label(label_frame, text=label, font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(side=tk.LEFT)
        tk.Label(label_frame, text="  (텍스트 드래그 후 우클릭 → 링크 추가)", font=ModernStyle.get_font(7),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(side=tk.LEFT)
        
        # 입력 필드와 링크 버튼을 담을 프레임
        input_frame = tk.Frame(frame, bg=ModernStyle.BG_WHITE)
        input_frame.pack(fill=tk.X, pady=(3, 0))
        
        # 엔트리
        entry = tk.Entry(input_frame, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        entry.insert(0, value)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        
        # 우클릭 메뉴 바인딩 (텍스트 선택 시 링크 추가)
        entry.bind('<Button-3>', lambda e, ent=entry: self._show_selection_context_menu(e, ent))
        
        # 링크 수 확인
        link_count = value.count('](')
        has_links = link_count > 0
        
        # 링크 표시
        if link_count > 0:
            link_indicator = tk.Label(input_frame, text=f"🔗×{link_count}", font=ModernStyle.get_font(8),
                                     bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT)
            link_indicator.pack(side=tk.LEFT, padx=(5, 0))
        
        # 링크 편집 버튼
        link_text = "링크 편집" if has_links else "+ 링크"
        link_btn = tk.Button(input_frame, text=link_text, font=ModernStyle.get_font(8),
                            bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                            relief='solid', borderwidth=1, cursor='hand2', padx=8,
                            command=lambda e=entry: self._show_link_popup(e))
        link_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.entries[key] = entry
    
    def _create_editable_section(self, parent, section_key, title, items):
        """편집 가능한 섹션 생성"""
        self._create_section_header(parent, title)
        
        # 링크 안내
        hint_frame = tk.Frame(parent, bg=ModernStyle.BG_WHITE)
        hint_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        tk.Label(hint_frame, text="링크가 있는 항목은 🔗×N 으로 표시됩니다. '링크 편집' 버튼으로 수정하세요.", 
                font=ModernStyle.get_font(8), bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W)
        
        container = tk.Frame(parent, bg=ModernStyle.BG_WHITE)
        container.pack(fill=tk.X, padx=20, pady=5)
        
        # 기존 항목들
        for item in items:
            self._add_section_item(container, section_key, item.get('date', ''), item.get('content', ''))
        
        # 추가 버튼
        add_btn = tk.Button(container, text="+ 항목 추가", font=ModernStyle.get_font(9),
                           bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT,
                           relief='flat', cursor='hand2',
                           command=lambda c=container, k=section_key: self._add_section_item(c, k, '', ''))
        add_btn.pack(anchor=tk.W, pady=5)
        
        setattr(self, f'{section_key}_container', container)
        setattr(self, f'{section_key}_add_btn', add_btn)
    
    def _add_section_item(self, container, section_key, date='', content=''):
        """섹션에 항목 추가"""
        # 링크가 있는지 확인
        has_links = '[' in content and '](' in content
        
        frame = tk.Frame(container, bg=ModernStyle.BG_WHITE)
        frame.pack(fill=tk.X, pady=3)
        
        # 기간 입력
        date_entry = tk.Entry(frame, font=ModernStyle.get_font(9), width=18, relief='solid', borderwidth=1)
        date_entry.insert(0, date)
        date_entry.pack(side=tk.LEFT, padx=(0, 5), ipady=4)
        
        # 내용 입력 (텍스트 드래그 선택 지원)
        content_entry = tk.Entry(frame, font=ModernStyle.get_font(9), relief='solid', borderwidth=1)
        content_entry.insert(0, content)
        content_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=4)
        content_entry.bind('<Button-3>', lambda e, ent=content_entry: self._show_selection_context_menu(e, ent))
        
        # 링크 수 표시 (있는 경우)
        link_count = content.count('](')
        if link_count > 0:
            link_indicator = tk.Label(frame, text=f"🔗×{link_count}", font=ModernStyle.get_font(8),
                                     bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT)
            link_indicator.pack(side=tk.LEFT, padx=(0, 3))
        
        # 링크 추가/편집 버튼
        link_text = "링크 편집" if has_links else "+ 링크"
        link_btn = tk.Button(frame, text=link_text, font=ModernStyle.get_font(8),
                            bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                            relief='solid', borderwidth=1, cursor='hand2', padx=8,
                            command=lambda e=content_entry: self._show_link_popup(e))
        link_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # 삭제 버튼
        del_btn = tk.Button(frame, text="✕", font=ModernStyle.get_font(8),
                           bg=ModernStyle.BG_WHITE, fg=ModernStyle.DANGER,
                           relief='flat', cursor='hand2',
                           command=lambda f=frame, k=section_key: self._remove_section_item(f, k))
        del_btn.pack(side=tk.LEFT)
        
        widget_data = {'frame': frame, 'date': date_entry, 'content': content_entry}
        self.section_widgets[section_key].append(widget_data)
        
        # 추가 버튼을 맨 아래로 이동
        add_btn = getattr(self, f'{section_key}_add_btn', None)
        if add_btn:
            add_btn.pack_forget()
            add_btn.pack(anchor=tk.W, pady=5)
        
        return widget_data
    
    def _show_selection_context_menu(self, event, entry_widget):
        """텍스트 선택 시 컨텍스트 메뉴 표시"""
        try:
            selected = entry_widget.selection_get()
            if selected:
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label=f"🔗 '{selected[:20]}...' 에 링크 추가" if len(selected) > 20 else f"🔗 '{selected}' 에 링크 추가",
                               command=lambda: self._add_link_to_selection(entry_widget, selected))
                menu.add_separator()
                menu.add_command(label="📋 링크 관리", command=lambda: self._show_link_popup(entry_widget))
                menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            # 선택된 텍스트 없음 - 일반 링크 관리 메뉴
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="📋 링크 관리", command=lambda: self._show_link_popup(entry_widget))
            menu.tk_popup(event.x_root, event.y_root)
    
    def _add_link_to_selection(self, entry_widget, selected_text):
        """선택된 텍스트에 링크 추가하는 팝업"""
        popup = tk.Toplevel(self)
        popup.title("🔗 선택 텍스트에 링크 추가")
        popup.geometry("450x280")
        popup.configure(bg=ModernStyle.BG_WHITE)
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 450) // 2
        y = (popup.winfo_screenheight() - 280) // 2
        popup.geometry(f"+{x}+{y}")
        
        current_text = entry_widget.get()
        
        # 헤더
        tk.Label(popup, text="선택한 텍스트에 링크 추가", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(15, 10))
        
        # 선택된 텍스트 표시
        tk.Label(popup, text="선택된 텍스트:", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        selected_frame = tk.Frame(popup, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
        selected_frame.pack(fill=tk.X, padx=20, pady=(3, 10))
        tk.Label(selected_frame, text=selected_text, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.ACCENT, wraplength=380).pack(padx=10, pady=8)
        
        # URL 입력
        tk.Label(popup, text="URL 주소", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        url_entry = tk.Entry(popup, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        url_entry.insert(0, "https://")
        url_entry.pack(fill=tk.X, padx=20, pady=(3, 10), ipady=6)
        
        # 스타일 선택
        tk.Label(popup, text="링크 스타일", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        style_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        style_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        style_var = tk.StringVar(value="highlight")
        
        highlight_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        highlight_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(highlight_frame, text="", variable=style_var, value="highlight",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(highlight_frame, text=" 하이라이트 ", font=ModernStyle.get_font(10),
                bg=ModernStyle.ACCENT, fg="white").pack(side=tk.LEFT)
        
        underline_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        underline_frame.pack(side=tk.LEFT)
        tk.Radiobutton(underline_frame, text="", variable=style_var, value="underline",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(underline_frame, text="밑줄", font=('Segoe UI', 10, 'underline'),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        def apply_link():
            url = url_entry.get().strip()
            style = style_var.get()
            
            if url and url != "https://":
                markdown_link = f"[{selected_text}]({url}|{style})"
                new_text = current_text.replace(selected_text, markdown_link, 1)
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, new_text)
                popup.destroy()
            else:
                messagebox.showwarning("URL 필요", "URL을 입력해주세요.", parent=popup)
        
        # 버튼
        btn_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Button(btn_frame, text="✓ 링크 적용", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=6, command=apply_link).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=6, command=popup.destroy).pack(side=tk.LEFT)
        
        popup.bind('<Return>', lambda e: apply_link())
        url_entry.focus_set()
    
    def _show_link_popup(self, entry_widget):
        """링크 관리 팝업 - 기존 링크 목록 표시 및 편집/추가"""
        current_text = entry_widget.get()
        
        # 기존 링크 파싱
        link_pattern = r'\[([^\]]+)\]\(([^|)]+)\|?([^)]*)\)'
        existing_links = list(re.finditer(link_pattern, current_text))
        
        popup = tk.Toplevel(self)
        popup.title("🔗 링크 관리")
        popup.geometry("500x400")
        popup.configure(bg=ModernStyle.BG_WHITE)
        popup.transient(self)
        popup.grab_set()
        
        # 중앙 배치
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 500) // 2
        y = (popup.winfo_screenheight() - 400) // 2
        popup.geometry(f"+{x}+{y}")
        
        # 헤더
        tk.Label(popup, text="링크 관리", font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(15, 5))
        
        # 기존 링크 목록
        if existing_links:
            tk.Label(popup, text="현재 연결된 링크", font=ModernStyle.get_font(9),
                    bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20, pady=(5, 5))
            
            list_frame = tk.Frame(popup, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
            list_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
            
            for i, match in enumerate(existing_links):
                link_text = match.group(1)
                link_url = match.group(2)
                link_style = match.group(3) if match.group(3) else 'highlight'
                
                item_frame = tk.Frame(list_frame, bg=ModernStyle.BG_WHITE)
                item_frame.pack(fill=tk.X, padx=1, pady=1)
                
                # 링크 정보 표시
                info_frame = tk.Frame(item_frame, bg=ModernStyle.BG_WHITE)
                info_frame.pack(fill=tk.X, padx=10, pady=8)
                
                # 왼쪽: 정보
                left_frame = tk.Frame(info_frame, bg=ModernStyle.BG_WHITE)
                left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # 텍스트
                tk.Label(left_frame, text=f"📝 {link_text}", font=ModernStyle.get_font(10, 'bold'),
                        bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(anchor='w')
                
                # URL (축약)
                short_url = link_url[:35] + '...' if len(link_url) > 35 else link_url
                tk.Label(left_frame, text=f"🔗 {short_url}", font=ModernStyle.get_font(8),
                        bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(anchor='w')
                
                # 오른쪽: 편집/삭제 버튼
                btn_frame = tk.Frame(info_frame, bg=ModernStyle.BG_WHITE)
                btn_frame.pack(side=tk.RIGHT)
                
                def on_edit(text=link_text, url=link_url, style=link_style, match_obj=match):
                    popup.destroy()
                    self._show_edit_link_popup(entry_widget, text, url, style, match_obj.group(0))
                
                tk.Button(btn_frame, text="✏️ 편집", font=ModernStyle.get_font(8),
                         bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                         relief='solid', borderwidth=1, cursor='hand2', padx=6,
                         command=on_edit).pack(side=tk.LEFT, padx=(0, 5))
                
                def on_delete(match_obj=match, lt=link_text):
                    if messagebox.askyesno("확인", f"'{lt}' 링크를 삭제하시겠습니까?", parent=popup):
                        updated = current_text.replace(match_obj.group(0), lt, 1)
                        entry_widget.delete(0, tk.END)
                        entry_widget.insert(0, updated)
                        popup.destroy()
                
                tk.Button(btn_frame, text="🗑", font=ModernStyle.get_font(8),
                         bg=ModernStyle.BG_WHITE, fg=ModernStyle.DANGER,
                         relief='flat', cursor='hand2',
                         command=on_delete).pack(side=tk.LEFT)
        else:
            tk.Label(popup, text="연결된 링크가 없습니다", font=ModernStyle.get_font(10),
                    bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20, pady=10)
        
        # 구분선
        tk.Frame(popup, bg=ModernStyle.BORDER, height=1).pack(fill=tk.X, padx=20, pady=10)
        
        # 새 링크 추가 버튼
        tk.Label(popup, text="새 링크 추가", font=ModernStyle.get_font(11, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(5, 10))
        
        add_btn = tk.Button(popup, text="+ 새 링크 추가", font=ModernStyle.get_font(10),
                           bg=ModernStyle.BG_WHITE, fg=ModernStyle.ACCENT,
                           relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2',
                           command=lambda: [popup.destroy(), self._show_add_link_popup(entry_widget)])
        add_btn.pack(anchor=tk.W, padx=20)
        
        # 닫기 버튼
        tk.Button(popup, text="닫기", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=20, pady=6, command=popup.destroy).pack(side=tk.BOTTOM, pady=20)
    
    def _show_add_link_popup(self, entry_widget):
        """새 링크 추가 팝업"""
        self._show_edit_link_popup(entry_widget, "", "https://", "highlight", None)
    
    def _show_edit_link_popup(self, entry_widget, link_text="", link_url="https://", link_style_val="highlight", original_markdown=None):
        """링크 편집/추가 팝업"""
        popup = tk.Toplevel(self)
        popup.title("🔗 링크 편집" if original_markdown else "🔗 링크 추가")
        popup.geometry("450x320")
        popup.configure(bg=ModernStyle.BG_WHITE)
        popup.transient(self)
        popup.grab_set()
        
        # 중앙 배치
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 450) // 2
        y = (popup.winfo_screenheight() - 320) // 2
        popup.geometry(f"+{x}+{y}")
        
        current_text = entry_widget.get()
        
        # 헤더
        title = "링크 편집" if original_markdown else "새 링크 추가"
        tk.Label(popup, text=title, font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(15, 10))
        
        # 링크 텍스트 입력
        tk.Label(popup, text="링크할 텍스트", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        text_entry = tk.Entry(popup, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        text_entry.insert(0, link_text)
        text_entry.pack(fill=tk.X, padx=20, pady=(3, 10), ipady=6)
        
        # URL 입력
        tk.Label(popup, text="URL 주소", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        url_entry = tk.Entry(popup, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
        url_entry.insert(0, link_url)
        url_entry.pack(fill=tk.X, padx=20, pady=(3, 10), ipady=6)
        
        # 스타일 선택
        tk.Label(popup, text="링크 스타일", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W, padx=20)
        
        style_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        style_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        style_var = tk.StringVar(value=link_style_val)
        
        # 하이라이트 옵션
        highlight_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        highlight_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(highlight_frame, text="", variable=style_var, value="highlight",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(highlight_frame, text=" 하이라이트 ", font=ModernStyle.get_font(10),
                bg=ModernStyle.ACCENT, fg="white").pack(side=tk.LEFT)
        
        # 밑줄 옵션
        underline_frame = tk.Frame(style_frame, bg=ModernStyle.BG_WHITE)
        underline_frame.pack(side=tk.LEFT)
        tk.Radiobutton(underline_frame, text="", variable=style_var, value="underline",
                      bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(underline_frame, text="밑줄", font=('Segoe UI', 10, 'underline'),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        def save_link():
            new_text = text_entry.get().strip()
            new_url = url_entry.get().strip()
            new_style = style_var.get()
            
            if new_text and new_url:
                new_markdown = f"[{new_text}]({new_url}|{new_style})"
                
                if original_markdown:
                    # 기존 링크 교체
                    updated_text = current_text.replace(original_markdown, new_markdown, 1)
                else:
                    # 새 링크 추가 (끝에)
                    updated_text = current_text + (" " if current_text else "") + new_markdown
                
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, updated_text)
                popup.destroy()
            else:
                messagebox.showwarning("입력 필요", "텍스트와 URL을 모두 입력해주세요.", parent=popup)
        
        def delete_link():
            if original_markdown and messagebox.askyesno("확인", "이 링크를 삭제하시겠습니까?", parent=popup):
                # 링크를 텍스트로 변환 (마크다운에서 텍스트만 추출)
                updated_text = current_text.replace(original_markdown, link_text, 1)
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, updated_text)
                popup.destroy()
        
        # 버튼
        btn_frame = tk.Frame(popup, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Button(btn_frame, text="✓ 저장", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=6, command=save_link).pack(side=tk.LEFT, padx=(0, 10))
        
        if original_markdown:
            tk.Button(btn_frame, text="🗑 삭제", font=ModernStyle.get_font(10),
                     bg=ModernStyle.DANGER, fg="white",
                     relief='flat', padx=15, pady=6, command=delete_link).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=6, command=popup.destroy).pack(side=tk.LEFT)
        
        popup.bind('<Return>', lambda e: save_link())
        text_entry.focus_set()
    
    def _remove_section_item(self, frame, section_key):
        """섹션에서 항목 제거"""
        for i, widget_data in enumerate(self.section_widgets[section_key]):
            if widget_data['frame'] == frame:
                self.section_widgets[section_key].pop(i)
                frame.destroy()
                break
    
    def save(self):
        try:
            with open(ABOUT_HTML, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 이름 업데이트 (마크다운 링크 지원)
            name_main = self.entries['name_main'].get().strip()
            name_main_html = self._convert_markdown_links(name_main)
            content = re.sub(r'<span class="name-main">[\s\S]*?</span>',
                           f'<span class="name-main">{name_main_html}</span>', content)
            
            # 타이틀 업데이트 (마크다운 링크 지원)
            name_title = self.entries['name_title'].get().strip()
            name_title_html = self._convert_markdown_links(name_title)
            content = re.sub(r'<span class="name-title">[\s\S]*?</span>',
                           f'<span class="name-title">{name_title_html}</span>', content)
            
            # 소속 업데이트 (마크다운 링크 지원)
            affiliation = self.entries['affiliation'].get().strip()
            affiliation_html = self._convert_markdown_links(affiliation)
            content = re.sub(r'<p class="about-affiliation">[\s\S]*?</p>',
                           f'<p class="about-affiliation">{affiliation_html}</p>', content)
            
            # EDUCATION 업데이트
            content = self._update_cv_section(content, 'EDUCATION', 'education')
            
            # EXPERIENCE 업데이트
            content = self._update_cv_section(content, 'EXPERIENCE', 'experience')
            
            # EXHIBITIONS 업데이트
            content = self._update_cv_section(content, 'EXHIBITIONS', 'exhibitions')
            
            # CONTACT 섹션 전체 업데이트
            email = self.entries['email'].get().strip()
            instagram = self.entries['instagram'].get().strip()
            
            # 이메일 HTML 생성
            if '](' in email:
                email_html = self._convert_markdown_links(email)
            else:
                email_html = f'<a href="mailto:{email}">{email}</a>'
            
            # 인스타그램 HTML 생성
            if '](' in instagram:
                instagram_html = self._convert_markdown_links(instagram)
            else:
                # @username 형식에서 username 추출
                username = instagram.lstrip('@')
                instagram_html = f'<a href="https://www.instagram.com/{username}/" target="_blank" rel="noopener">{instagram}</a>'
            
            # CONTACT 섹션 업데이트
            contact_pattern = r'(<h2 class="cv-heading">CONTACT</h2>\s*<ul class="cv-list-simple">)[\s\S]*?(</ul>)'
            contact_items = f'''
          <li>{email_html}</li>
          <li>{instagram_html}</li>
        '''
            content = re.sub(contact_pattern, f'\\g<1>{contact_items}\\g<2>', content)
            
            with open(ABOUT_HTML, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("저장 완료", "About 페이지가 저장되었습니다.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {str(e)}")
    
    def _convert_markdown_links(self, text):
        """마크다운 링크 [텍스트](URL|스타일)를 HTML 링크로 변환"""
        def replace_link(match):
            link_text = match.group(1)
            url_part = match.group(2)
            
            # URL과 스타일 분리 (예: https://example.com|highlight)
            if '|' in url_part:
                url, style = url_part.rsplit('|', 1)
                if style == 'underline':
                    css_class = 'link-underline'
                else:
                    css_class = 'link-highlight'
            else:
                url = url_part
                css_class = 'link-highlight'  # 기본값: 하이라이트
            
            return f'<a href="{url}" class="{css_class}" target="_blank" rel="noopener">{link_text}</a>'
        
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        return re.sub(pattern, replace_link, text)
    
    def _update_cv_section(self, content, section_name, section_key):
        """CV 섹션 HTML 업데이트"""
        items = []
        for widget_data in self.section_widgets[section_key]:
            date = widget_data['date'].get().strip()
            item_content = widget_data['content'].get().strip()
            if date or item_content:
                # 마크다운 링크를 HTML로 변환
                item_content = self._convert_markdown_links(item_content)
                items.append(f'          <li><span class="cv-date">{date}</span><span class="cv-content">{item_content}</span></li>')
        
        items_html = '\n'.join(items) if items else ''
        
        # 더 유연한 정규식 패턴 (공백, 줄바꿈 등 처리)
        pattern = rf'(<h2\s+class="cv-heading">\s*{section_name}\s*</h2>\s*<ul\s+class="cv-list-simple">)[\s\S]*?(</ul>)'
        replacement = f'\\g<1>\n{items_html}\n        \\g<2>'
        
        result = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        return result


class FooterEditorDialog(tk.Toplevel):
    """푸터 편집 다이얼로그 - 모든 HTML 파일의 푸터를 동기화"""
    
    # 푸터가 있는 HTML 파일 목록
    FOOTER_FILES = ['projects.html', 'drawings.html', 'graphics.html', 'about.html']
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("📋 푸터 편집")
        self.geometry("700x600")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.lift()
        
        self.data = {}
        self.load_footer_data()
        self.create_ui()
        
        # 중앙 배치
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def load_footer_data(self):
        """첫 번째 푸터 파일에서 데이터 로드"""
        try:
            with open(SCRIPT_DIR / self.FOOTER_FILES[0], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 로고
            logo_match = re.search(r'<div class="footer-logo">([^<]+)</div>', content)
            self.data['logo'] = logo_match.group(1) if logo_match else 'JEONHYERIN'
            
            # 설명
            desc_match = re.search(r'<p class="footer-description">\s*([\s\S]*?)\s*</p>', content)
            self.data['description'] = desc_match.group(1).strip() if desc_match else ''
            
            # 저작권
            copy_match = re.search(r'<p class="footer-copyright">\s*([\s\S]*?)\s*</p>', content)
            self.data['copyright'] = copy_match.group(1).strip() if copy_match else ''
            
            # 이메일
            email_match = re.search(r'href="mailto:([^"]+)"', content)
            self.data['email'] = email_match.group(1) if email_match else ''
            
            # 인스타그램
            insta_match = re.search(r'href="(https://(?:www\.)?instagram\.com/[^"]+)"', content)
            self.data['instagram'] = insta_match.group(1) if insta_match else ''
            
        except Exception as e:
            print(f"푸터 데이터 로드 오류: {e}")
    
    def create_ui(self):
        # 스크롤 가능한 프레임
        canvas = tk.Canvas(self, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 마우스 휠 바인딩
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        self.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        self.entries = {}
        
        # 헤더
        tk.Label(scrollable, text="푸터 편집", font=ModernStyle.get_font(16, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=(20, 5))
        tk.Label(scrollable, text="모든 페이지(projects, drawings, graphics, about)의 푸터에 동일하게 적용됩니다.",
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(anchor=tk.W, padx=20, pady=(0, 15))
        
        # === 브랜드 섹션 ===
        brand_frame = tk.LabelFrame(scrollable, text="브랜드", font=ModernStyle.get_font(11, 'bold'),
                                    bg=ModernStyle.BG_WHITE, padx=15, pady=10)
        brand_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 로고
        tk.Label(brand_frame, text="로고 텍스트", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        logo_entry = tk.Entry(brand_frame, font=ModernStyle.get_font(10), width=40,
                             relief='solid', borderwidth=1)
        logo_entry.insert(0, self.data.get('logo', ''))
        logo_entry.pack(fill=tk.X, pady=(3, 10))
        self.entries['logo'] = logo_entry
        
        # 설명
        tk.Label(brand_frame, text="포트폴리오 설명", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        desc_text = scrolledtext.ScrolledText(brand_frame, font=ModernStyle.get_font(10),
                                              height=5, wrap=tk.WORD, relief='solid', borderwidth=1)
        desc_text.insert(tk.END, self.data.get('description', ''))
        desc_text.pack(fill=tk.X, pady=(3, 0))
        self.entries['description'] = desc_text
        
        # === 저작권 섹션 ===
        copy_frame = tk.LabelFrame(scrollable, text="저작권", font=ModernStyle.get_font(11, 'bold'),
                                   bg=ModernStyle.BG_WHITE, padx=15, pady=10)
        copy_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(copy_frame, text="저작권 문구", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        copy_text = scrolledtext.ScrolledText(copy_frame, font=ModernStyle.get_font(10),
                                              height=3, wrap=tk.WORD, relief='solid', borderwidth=1)
        copy_text.insert(tk.END, self.data.get('copyright', ''))
        copy_text.pack(fill=tk.X, pady=(3, 0))
        self.entries['copyright'] = copy_text
        
        # === 소셜 링크 섹션 ===
        social_frame = tk.LabelFrame(scrollable, text="소셜 링크", font=ModernStyle.get_font(11, 'bold'),
                                     bg=ModernStyle.BG_WHITE, padx=15, pady=10)
        social_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 이메일
        tk.Label(social_frame, text="이메일 주소", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        email_entry = tk.Entry(social_frame, font=ModernStyle.get_font(10), width=40,
                              relief='solid', borderwidth=1)
        email_entry.insert(0, self.data.get('email', ''))
        email_entry.pack(fill=tk.X, pady=(3, 10))
        self.entries['email'] = email_entry
        
        # 인스타그램
        tk.Label(social_frame, text="인스타그램 URL", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W)
        insta_entry = tk.Entry(social_frame, font=ModernStyle.get_font(10), width=40,
                              relief='solid', borderwidth=1)
        insta_entry.insert(0, self.data.get('instagram', ''))
        insta_entry.pack(fill=tk.X, pady=(3, 0))
        self.entries['instagram'] = insta_entry
        
        # === 버튼 ===
        btn_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                 relief='solid', borderwidth=1, width=10,
                 command=self.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        
        tk.Button(btn_frame, text="저장", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', width=10,
                 command=self.save).pack(side=tk.RIGHT)
    
    def save(self):
        """모든 푸터 파일에 변경사항 저장"""
        try:
            logo = self.entries['logo'].get().strip()
            description = self.entries['description'].get('1.0', tk.END).strip()
            copyright_text = self.entries['copyright'].get('1.0', tk.END).strip()
            email = self.entries['email'].get().strip()
            instagram = self.entries['instagram'].get().strip()
            
            updated_count = 0
            
            for filename in self.FOOTER_FILES:
                filepath = SCRIPT_DIR / filename
                if not filepath.exists():
                    continue
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 로고 업데이트
                content = re.sub(r'<div class="footer-logo">[^<]+</div>',
                               f'<div class="footer-logo">{logo}</div>', content)
                
                # 설명 업데이트
                content = re.sub(r'<p class="footer-description">\s*[\s\S]*?\s*</p>',
                               f'<p class="footer-description">\n          {description}\n        </p>', content)
                
                # 저작권 업데이트
                content = re.sub(r'<p class="footer-copyright">\s*[\s\S]*?\s*</p>',
                               f'<p class="footer-copyright">\n          {copyright_text}\n        </p>', content)
                
                # 이메일 업데이트
                content = re.sub(r'href="mailto:[^"]+"', f'href="mailto:{email}"', content)
                
                # 인스타그램 업데이트
                content = re.sub(r'href="https://(?:www\.)?instagram\.com/[^"]+"',
                               f'href="{instagram}"', content)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                updated_count += 1
            
            messagebox.showinfo("저장 완료", f"{updated_count}개의 페이지 푸터가 업데이트되었습니다.")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {str(e)}")


class HomeManagerDialog(tk.Toplevel):
    """홈 화면 관리 다이얼로그"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("홈 화면 관리")
        self.geometry("900x750")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.transient(parent)
        self.grab_set()
        
        # 홈 데이터
        self.home_data = self.load_home_data()
        self.image_path = None
        self.image_preview = None
        
        HOME_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        
        self.create_ui()
        self.load_current_values()
        
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def load_home_data(self):
        """홈 데이터 로드"""
        default_data = {
            "subtitle": "Architecture Portfolio",
            "name": "JEONHYERIN",
            "quote_text": "I'm not inventing anything new.\nI'm just using existing materials\nin a different way.",
            "quote_author": "Shigeru Ban",
            "focus": "Design, Architecture,\nAI, Computer",
            "education": "Yonsei Univ.",
            "contact_email": "contact@jeonhyerin.com",
            "hero_image": "",
            "hero_image_size": 100,
            "hero_image_opacity": 100,
            "hero_image_position": "center"
        }
        
        if HOME_DATA_JSON.exists():
            try:
                with open(HOME_DATA_JSON, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key in default_data:
                        if key not in data:
                            data[key] = default_data[key]
                    return data
            except:
                pass
        return default_data
    
    def create_ui(self):
        """UI 생성"""
        main = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        main.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # 제목
        tk.Label(main, text="홈 화면 관리", font=ModernStyle.get_font(16, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        tk.Label(main, text="홈 화면의 텍스트와 이미지를 편집합니다",
                font=ModernStyle.get_font(10), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=(0, 20))
        
        # 노트북 (탭)
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 텍스트 탭
        text_tab = tk.Frame(notebook, bg=ModernStyle.BG_WHITE)
        notebook.add(text_tab, text="📝 텍스트 편집")
        self.create_text_tab(text_tab)
        
        # 이미지 탭
        image_tab = tk.Frame(notebook, bg=ModernStyle.BG_WHITE)
        notebook.add(image_tab, text="🖼️ 이미지 관리")
        self.create_image_tab(image_tab)
        
        # 버튼
        btn_frame = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        tk.Button(btn_frame, text="저장", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=25, pady=8,
                 command=self.save).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=20, pady=8, command=self.destroy).pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="미리보기", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1,
                 padx=20, pady=8, command=self.preview).pack(side=tk.LEFT)
    
    def create_text_tab(self, parent):
        """텍스트 편집 탭"""
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 서브타이틀
        self._create_field(scroll_frame, "서브타이틀 (Subtitle)", "subtitle_entry", 
                          "예: Architecture Portfolio", single_line=True)
        
        # 이름
        self._create_field(scroll_frame, "이름 (Name)", "name_entry",
                          "예: JEONHYERIN", single_line=True)
        
        # 인용문
        self._create_field(scroll_frame, "인용문 (Quote)", "quote_entry",
                          "여러 줄 입력 가능", height=4)
        
        # 인용 저자
        self._create_field(scroll_frame, "인용 저자 (Author)", "author_entry",
                          "예: Shigeru Ban", single_line=True)
        
        # 구분선
        tk.Frame(scroll_frame, height=1, bg=ModernStyle.BORDER).pack(fill=tk.X, pady=20)
        tk.Label(scroll_frame, text="오른쪽 정보 영역", font=ModernStyle.get_font(11, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        # Focus
        self._create_field(scroll_frame, "Focus", "focus_entry",
                          "예: Design, Architecture,\nAI, Computer", height=3)
        
        # Education
        self._create_field(scroll_frame, "Education", "education_entry",
                          "예: Yonsei Univ.", single_line=True)
        
        # Contact Email
        self._create_field(scroll_frame, "Contact Email", "email_entry",
                          "예: contact@jeonhyerin.com", single_line=True)
    
    def _create_field(self, parent, label, attr_name, placeholder="", single_line=False, height=3):
        """필드 생성 헬퍼"""
        frame = tk.Frame(parent, bg=ModernStyle.BG_WHITE)
        frame.pack(fill=tk.X, pady=8)
        
        tk.Label(frame, text=label, font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        tk.Label(frame, text=placeholder, font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor='w')
        
        if single_line:
            entry = tk.Entry(frame, font=ModernStyle.get_font(10),
                           relief='solid', borderwidth=1)
            entry.pack(fill=tk.X, pady=(5, 0), ipady=6)
        else:
            entry = tk.Text(frame, font=ModernStyle.get_font(10),
                          relief='solid', borderwidth=1, height=height, wrap=tk.WORD)
            entry.pack(fill=tk.X, pady=(5, 0))
        
        setattr(self, attr_name, entry)
    
    def create_image_tab(self, parent):
        """이미지 관리 탭"""
        main = tk.Frame(parent, bg=ModernStyle.BG_WHITE)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 좌측: 컨트롤
        left = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        tk.Label(left, text="히어로 이미지", font=ModernStyle.get_font(11, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        tk.Label(left, text="홈 화면에 표시될 대표 이미지입니다",
                font=ModernStyle.get_font(9), bg=ModernStyle.BG_WHITE,
                fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=(0, 15))
        
        # 이미지 선택 버튼
        btn_frame = tk.Frame(left, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="📁 이미지 불러오기", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1,
                 padx=15, pady=8, command=self.load_image).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="🗑️ 이미지 삭제", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=8, command=self.remove_image).pack(side=tk.LEFT)
        
        # 현재 이미지 경로
        self.image_path_label = tk.Label(left, text="선택된 이미지 없음",
                                         font=ModernStyle.get_font(9),
                                         bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE)
        self.image_path_label.pack(anchor='w', pady=(10, 20))
        
        # 크기 조절
        size_frame = tk.Frame(left, bg=ModernStyle.BG_WHITE)
        size_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(size_frame, text="이미지 크기 (%)", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        self.size_var = tk.IntVar(value=100)
        self.size_scale = tk.Scale(size_frame, from_=20, to=200, orient=tk.HORIZONTAL,
                                   variable=self.size_var, length=250,
                                   bg=ModernStyle.BG_WHITE, highlightthickness=0,
                                   command=self.update_preview)
        self.size_scale.pack(fill=tk.X, pady=5)
        
        self.size_label = tk.Label(size_frame, text="100%", font=ModernStyle.get_font(9),
                                  bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED)
        self.size_label.pack(anchor='w')
        
        # 투명도 조절
        opacity_frame = tk.Frame(left, bg=ModernStyle.BG_WHITE)
        opacity_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(opacity_frame, text="투명도 (%)", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        self.opacity_var = tk.IntVar(value=100)
        self.opacity_scale = tk.Scale(opacity_frame, from_=10, to=100, orient=tk.HORIZONTAL,
                                      variable=self.opacity_var, length=250,
                                      bg=ModernStyle.BG_WHITE, highlightthickness=0,
                                      command=self.update_preview)
        self.opacity_scale.pack(fill=tk.X, pady=5)
        
        # 위치 선택
        pos_frame = tk.Frame(left, bg=ModernStyle.BG_WHITE)
        pos_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(pos_frame, text="이미지 위치", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(anchor='w')
        
        self.position_var = tk.StringVar(value="center")
        positions = [("왼쪽", "left"), ("중앙", "center"), ("오른쪽", "right")]
        pos_btn_frame = tk.Frame(pos_frame, bg=ModernStyle.BG_WHITE)
        pos_btn_frame.pack(fill=tk.X, pady=5)
        
        for text, value in positions:
            tk.Radiobutton(pos_btn_frame, text=text, variable=self.position_var,
                          value=value, font=ModernStyle.get_font(9),
                          bg=ModernStyle.BG_WHITE, command=self.update_preview).pack(side=tk.LEFT, padx=(0, 15))
        
        # 우측: 미리보기
        right = tk.Frame(main, bg=ModernStyle.BG_LIGHT, relief='solid', borderwidth=1)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right, text="미리보기", font=ModernStyle.get_font(10, 'bold'),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_MUTED).pack(pady=10)
        
        # 미리보기 캔버스
        self.preview_canvas = tk.Canvas(right, bg='#ffffff', width=400, height=300,
                                        highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        self.preview_canvas.pack(padx=20, pady=(0, 20))
        
        # 초기 미리보기 텍스트
        self.preview_canvas.create_text(200, 150, text="이미지를 불러와주세요",
                                        font=ModernStyle.get_font(10),
                                        fill=ModernStyle.TEXT_SUBTLE)
    
    def load_current_values(self):
        """현재 값 로드"""
        # 텍스트 필드
        self.subtitle_entry.insert(0, self.home_data.get('subtitle', ''))
        self.name_entry.insert(0, self.home_data.get('name', ''))
        self.quote_entry.insert('1.0', self.home_data.get('quote_text', ''))
        self.author_entry.insert(0, self.home_data.get('quote_author', ''))
        self.focus_entry.insert('1.0', self.home_data.get('focus', ''))
        self.education_entry.insert(0, self.home_data.get('education', ''))
        self.email_entry.insert(0, self.home_data.get('contact_email', ''))
        
        # 이미지
        hero_image = self.home_data.get('hero_image', '')
        if hero_image and Path(SCRIPT_DIR / hero_image).exists():
            self.image_path = str(SCRIPT_DIR / hero_image)
            self.image_path_label.config(text=f"현재: {hero_image}")
            self.load_preview_image()
        
        self.size_var.set(self.home_data.get('hero_image_size', 100))
        self.opacity_var.set(self.home_data.get('hero_image_opacity', 100))
        self.position_var.set(self.home_data.get('hero_image_position', 'center'))
    
    def load_image(self):
        """이미지 불러오기"""
        filetypes = [("이미지 파일", "*.jpg *.jpeg *.png *.webp *.gif"), ("모든 파일", "*.*")]
        path = filedialog.askopenfilename(title="홈 이미지 선택", filetypes=filetypes)
        
        if path:
            # 이미지를 home 폴더로 복사
            src = Path(path)
            dest = HOME_IMAGES_DIR / f"hero{src.suffix}"
            
            try:
                shutil.copy2(src, dest)
                self.image_path = str(dest)
                self.image_path_label.config(text=f"현재: images/home/hero{src.suffix}")
                self.load_preview_image()
            except Exception as e:
                messagebox.showerror("오류", f"이미지 복사 실패: {str(e)}")
    
    def remove_image(self):
        """이미지 삭제"""
        self.image_path = None
        self.image_preview = None
        self.image_path_label.config(text="선택된 이미지 없음")
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(200, 150, text="이미지를 불러와주세요",
                                        font=ModernStyle.get_font(10),
                                        fill=ModernStyle.TEXT_SUBTLE)
    
    def load_preview_image(self):
        """미리보기 이미지 로드"""
        if not self.image_path or not Path(self.image_path).exists():
            return
        
        try:
            img = Image.open(self.image_path)
            # 미리보기 크기에 맞게 리사이즈
            img.thumbnail((400, 300), Image.Resampling.LANCZOS)
            self.image_preview = ImageTk.PhotoImage(img)
            self.update_preview()
        except Exception as e:
            print(f"이미지 로드 오류: {e}")
    
    def update_preview(self, *args):
        """미리보기 업데이트"""
        self.size_label.config(text=f"{self.size_var.get()}%")
        
        if not self.image_preview:
            return
        
        self.preview_canvas.delete("all")
        
        # 위치 계산
        pos = self.position_var.get()
        canvas_w, canvas_h = 400, 300
        img_w = self.image_preview.width()
        img_h = self.image_preview.height()
        
        # 크기 적용
        scale = self.size_var.get() / 100
        
        if pos == 'left':
            x = int(img_w * scale / 2) + 10
        elif pos == 'right':
            x = canvas_w - int(img_w * scale / 2) - 10
        else:
            x = canvas_w // 2
        
        y = canvas_h // 2
        
        # 이미지 표시 (실제 앱에서는 크기/투명도 적용)
        self.preview_canvas.create_image(x, y, image=self.image_preview)
        
        # 크기 표시
        self.preview_canvas.create_text(canvas_w - 10, canvas_h - 10,
                                        text=f"크기: {self.size_var.get()}% | 투명도: {self.opacity_var.get()}%",
                                        anchor='se', font=ModernStyle.get_font(8),
                                        fill=ModernStyle.TEXT_SUBTLE)
    
    def preview(self):
        """브라우저에서 미리보기"""
        self.save(preview_only=True)
        webbrowser.open(f"file://{INDEX_HTML}")
    
    def save(self, preview_only=False):
        """저장"""
        try:
            # 데이터 수집
            data = {
                "subtitle": self.subtitle_entry.get().strip(),
                "name": self.name_entry.get().strip(),
                "quote_text": self.quote_entry.get('1.0', tk.END).strip(),
                "quote_author": self.author_entry.get().strip(),
                "focus": self.focus_entry.get('1.0', tk.END).strip(),
                "education": self.education_entry.get().strip(),
                "contact_email": self.email_entry.get().strip(),
                "hero_image": "",
                "hero_image_size": self.size_var.get(),
                "hero_image_opacity": self.opacity_var.get(),
                "hero_image_position": self.position_var.get()
            }
            
            # 이미지 경로 저장
            if self.image_path and Path(self.image_path).exists():
                rel_path = Path(self.image_path).relative_to(SCRIPT_DIR)
                data["hero_image"] = str(rel_path).replace("\\", "/")
            
            # JSON 저장
            with open(HOME_DATA_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # HTML 업데이트
            self.update_index_html(data)
            
            if not preview_only:
                messagebox.showinfo("저장 완료", "홈 화면이 업데이트되었습니다!")
                self.destroy()
                
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {str(e)}")
    
    def update_index_html(self, data):
        """index.html 업데이트"""
        if not INDEX_HTML.exists():
            return
        
        with open(INDEX_HTML, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # 서브타이틀 업데이트
        html = re.sub(
            r'(<p class="index-hero-subtitle[^"]*">)[^<]*(</p>)',
            rf'\1{data["subtitle"]}\2',
            html
        )
        
        # 이름 업데이트
        html = re.sub(
            r'(<span class="index-name-line[^"]*">)[^<]*(</span>)',
            rf'\1{data["name"]}\2',
            html
        )
        
        # 인용문 업데이트
        quote_html = data["quote_text"].replace("\n", "<br>\n          ")
        html = re.sub(
            r'(<blockquote class="index-quote-text">).*?(</blockquote>)',
            rf'\1\n          "{quote_html}"\n        \2',
            html,
            flags=re.DOTALL
        )
        
        # 저자 업데이트
        html = re.sub(
            r'(<cite class="index-quote-cite">)[^<]*(</cite>)',
            rf'\1— {data["quote_author"]}\2',
            html
        )
        
        # Focus 업데이트
        focus_html = data["focus"].replace("\n", "<br>")
        html = re.sub(
            r'(<span class="index-info-label">Focus</span>\s*<span class="index-info-value">)[^<]*(</span>)',
            rf'\1{focus_html}\2',
            html,
            flags=re.DOTALL
        )
        
        # Education 업데이트
        html = re.sub(
            r'(<span class="index-info-label">Education</span>\s*<span class="index-info-value">)[^<]*(</span>)',
            rf'\1{data["education"]}\2',
            html,
            flags=re.DOTALL
        )
        
        # Email 업데이트
        html = re.sub(
            r'(href="mailto:)[^"]*(")',
            rf'\1{data["contact_email"]}\2',
            html
        )
        
        with open(INDEX_HTML, 'w', encoding='utf-8') as f:
            f.write(html)


class PortfolioAdminApp:
    """메인 관리자 앱"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("JEONHYERIN Portfolio Admin Pro")
        self.root.geometry("1150x800")
        self.root.configure(bg=ModernStyle.BG_WHITE)
        self.root.minsize(1000, 650)
        
        self.setup_styles()
        
        self.current_mode = 'projects'
        self.current_html = PROJECTS_HTML
        self.projects = []
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_list)
        
        self.create_ui()
        self.load_data()
        
        BACKUP_DIR.mkdir(exist_ok=True)
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Modern.TFrame', background=ModernStyle.BG_WHITE)
        style.configure('Modern.Treeview', background=ModernStyle.BG_WHITE,
                       foreground=ModernStyle.TEXT_PRIMARY, font=ModernStyle.get_font(10),
                       rowheight=38, borderwidth=0)
        style.configure('Modern.Treeview.Heading', background=ModernStyle.BG_LIGHT,
                       foreground=ModernStyle.TEXT_SUBTLE, font=ModernStyle.get_font(9))
        style.map('Modern.Treeview', background=[('selected', ModernStyle.BG_HOVER)])
    
    def create_ui(self):
        main = tk.Frame(self.root, bg=ModernStyle.BG_WHITE)
        main.pack(fill=tk.BOTH, expand=True)
        
        # 헤더
        header = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=40, pady=(25, 0))
        
        tk.Label(header, text="JEONHYERIN", font=ModernStyle.get_font(20, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Label(header, text="Portfolio Admin Pro", font=ModernStyle.get_font(11),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_MUTED).pack(side=tk.LEFT, padx=(12, 0), pady=(5, 0))
        
        # 우측 메뉴 - 드롭다운 구조
        menu = tk.Frame(header, bg=ModernStyle.BG_WHITE)
        menu.pack(side=tk.RIGHT)
        
        # 드롭다운 메뉴 스타일 정의
        self.dropdown_menus = {}
        
        # 1. 콘텐츠 편집 드롭다운
        content_btn = tk.Menubutton(menu, text="📄 콘텐츠", font=ModernStyle.get_font(9),
                                   bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                                   padx=10, pady=5, indicatoron=False)
        content_menu = tk.Menu(content_btn, tearoff=0, font=ModernStyle.get_font(10))
        content_menu.add_command(label="🏠 홈페이지 편집", command=self.edit_home)
        content_menu.add_command(label="📱 모바일 미리보기 (현재 탭)", command=self.open_mobile_preview)
        content_menu.add_command(label="📱 모바일 미리보기 (홈)", command=self.open_mobile_preview_home)
        content_menu.add_separator()
        content_menu.add_command(label="📝 About 편집", command=self.edit_about)
        content_menu.add_command(label="📋 푸터 편집", command=self.edit_footer)
        content_btn.configure(menu=content_menu)
        content_btn.pack(side=tk.LEFT, padx=3)
        
        # 2. 설정 드롭다운
        settings_btn = tk.Menubutton(menu, text="⚙️ 설정", font=ModernStyle.get_font(9),
                                    bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                                    padx=10, pady=5, indicatoron=False)
        settings_menu = tk.Menu(settings_btn, tearoff=0, font=ModernStyle.get_font(10))
        settings_menu.add_command(label="📑 탭(카테고리) 관리", command=self.manage_tabs)
        settings_menu.add_separator()
        settings_menu.add_command(label="📰 매거진 기사 관리 (STUDY)", command=self.manage_magazine)
        settings_btn.configure(menu=settings_menu)
        settings_btn.pack(side=tk.LEFT, padx=3)
        
        # 3. 데이터 관리 드롭다운
        data_btn = tk.Menubutton(menu, text="💾 데이터", font=ModernStyle.get_font(9),
                                bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                                padx=10, pady=5, indicatoron=False)
        data_menu = tk.Menu(data_btn, tearoff=0, font=ModernStyle.get_font(10))
        data_menu.add_command(label="💾 백업 생성", command=self.backup)
        data_menu.add_command(label="📁 백업 관리", command=self.show_backup_manager)
        data_menu.add_separator()
        data_menu.add_command(label="🔄 백업에서 복원", command=self.restore_backup)
        data_btn.configure(menu=data_menu)
        data_btn.pack(side=tk.LEFT, padx=3)
        
        # 4. 사이트 열기 버튼 (단독)
        tk.Button(menu, text="🌐 사이트", font=ModernStyle.get_font(9),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=12, pady=5, command=self.open_site).pack(side=tk.LEFT, padx=3)
        
        # 네비게이션 (동적으로 탭 로드)
        self.nav_frame = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        self.nav_frame.pack(fill=tk.X, padx=40, pady=(20, 0))
        
        self.nav_btn_container = tk.Frame(self.nav_frame, bg=ModernStyle.BG_WHITE)
        self.nav_btn_container.pack(side=tk.LEFT)
        
        self.nav_buttons = {}
        self._create_nav_buttons()
        
        self._update_nav_style()
        
        # 검색
        search_frame = tk.Frame(self.nav_frame, bg=ModernStyle.BG_WHITE)
        search_frame.pack(side=tk.RIGHT)
        tk.Label(search_frame, text="🔍", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.search_var, width=20,
                font=ModernStyle.get_font(10), relief='solid', borderwidth=1).pack(side=tk.LEFT, padx=5, ipady=5)
        
        self.count_label = tk.Label(self.nav_frame, text="", font=ModernStyle.get_font(9),
                                   bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE)
        self.count_label.pack(side=tk.RIGHT, padx=20)
        
        # 리스트
        list_frame = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=(15, 0))
        
        columns = ('index', 'title', 'duration', 'studio', 'visible')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                 style='Modern.Treeview', height=12)
        
        self.tree.heading('index', text='#')
        self.tree.heading('title', text='TITLE')
        self.tree.heading('duration', text='DURATION')
        self.tree.heading('studio', text='STUDIO')
        self.tree.heading('visible', text='공개')
        
        self.tree.column('index', width=50, stretch=False)
        self.tree.column('title', width=220)
        self.tree.column('duration', width=180)
        self.tree.column('studio', width=250)
        self.tree.column('visible', width=60, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', lambda e: self.edit_project())
        
        # 드래그 앤 드롭 기능
        self._drag_data = {"item": None, "index": None}
        self.tree.bind('<ButtonPress-1>', self._on_drag_start)
        self.tree.bind('<B1-Motion>', self._on_drag_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_drag_end)
        
        # 버튼
        btn_frame = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=40, pady=20)
        
        left = tk.Frame(btn_frame, bg=ModernStyle.BG_WHITE)
        left.pack(side=tk.LEFT)
        
        tk.Button(left, text="+ 추가", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=8, command=self.add_project).pack(side=tk.LEFT, padx=(0, 8))
        
        for text, cmd in [("수정", self.edit_project), ("삭제", self.delete_project)]:
            bg = ModernStyle.DANGER if text == "삭제" else ModernStyle.BG_WHITE
            fg = ModernStyle.BG_WHITE if text == "삭제" else ModernStyle.TEXT_PRIMARY
            tk.Button(left, text=text, font=ModernStyle.get_font(10),
                     bg=bg, fg=fg, relief='solid', borderwidth=1,
                     padx=15, pady=8, command=cmd).pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Label(left, text="|", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.BORDER).pack(side=tk.LEFT, padx=10)
        
        for text, cmd in [("↑", self.move_up), ("↓", self.move_down), ("📋", self.duplicate)]:
            tk.Button(left, text=text, font=ModernStyle.get_font(10),
                     bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                     padx=12, pady=8, command=cmd).pack(side=tk.LEFT, padx=(0, 5))
        
        right = tk.Frame(btn_frame, bg=ModernStyle.BG_WHITE)
        right.pack(side=tk.RIGHT)
        
        # 🚀 저장+배포 버튼 (한 번에 저장 → Git Push → Netlify 배포)
        tk.Button(right, text="🚀 저장+배포", font=ModernStyle.get_font(10, 'bold'),
                 bg="#0066cc", fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=15, pady=8, cursor='hand2',
                 command=self.save_and_deploy).pack(side=tk.LEFT, padx=(0, 5))
        
        # ✅ 저장만 (Git 푸시 없이 로컬 저장)
        tk.Button(right, text="✅ 저장", font=ModernStyle.get_font(10),
                 bg=ModernStyle.SUCCESS, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=12, pady=8, cursor='hand2',
                 command=self.apply_changes).pack(side=tk.LEFT, padx=(0, 10))
        
        # ↩️ 되돌리기 버튼
        tk.Button(right, text="↩️ 되돌리기", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=10, pady=8, cursor='hand2',
                 command=self.undo).pack(side=tk.LEFT, padx=(0, 5))
        
        # 파일 정리 버튼
        tk.Button(right, text="🧹 정리", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=10, pady=8, cursor='hand2',
                 command=self.cleanup_files).pack(side=tk.LEFT, padx=(0, 5))
        
        for text, cmd in [("📁 폴더", self.open_folder), ("👁 미리보기", self.preview), ("🔄", self.load_data)]:
            tk.Button(right, text=text, font=ModernStyle.get_font(10),
                     bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                     padx=12, pady=8, command=cmd).pack(side=tk.LEFT, padx=3)
        
        tk.Button(right, text="모바일", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 width=8, padx=8, pady=8, command=self.open_mobile_preview).pack(side=tk.LEFT, padx=3)
        
        # 상태바
        status = tk.Frame(main, bg=ModernStyle.BG_LIGHT)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="준비됨")
        tk.Label(status, textvariable=self.status_var, font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_MUTED).pack(padx=20, pady=10, anchor=tk.W)
    
    def _create_nav_buttons(self):
        """탭 버튼들을 동적으로 생성"""
        # 기존 버튼 제거
        for widget in self.nav_btn_container.winfo_children():
            widget.destroy()
        self.nav_buttons.clear()
        
        # 탭 설정 로드
        tabs = TabManagerDialog.get_visible_tabs()
        
        # 기본 탭이 없으면 기본값 사용
        if not tabs:
            tabs = [
                {"id": "projects", "name": "PROJECTS", "file": "projects.html"},
                {"id": "drawings", "name": "DRAWINGS", "file": "drawings.html"},
                {"id": "graphics", "name": "GRAPHICS", "file": "graphics.html"}
            ]
        
        for tab in tabs:
            mode = tab['id']
            btn = tk.Button(self.nav_btn_container, text=tab['name'], 
                           font=ModernStyle.get_font(10),
                           bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                           relief='flat', padx=15, pady=8,
                           command=lambda m=mode, f=tab['file']: self.switch_mode(m, f))
            btn.pack(side=tk.LEFT, padx=(0, 5))
            self.nav_buttons[mode] = btn
        
        # 현재 모드가 탭 목록에 없으면 첫 번째 탭으로 변경
        if self.current_mode not in self.nav_buttons and tabs:
            first_tab = tabs[0]
            self.current_mode = first_tab['id']
            self.current_html = SCRIPT_DIR / first_tab['file']
    
    def _update_nav_style(self):
        for mode, btn in self.nav_buttons.items():
            if mode == self.current_mode:
                btn.configure(bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE)
            else:
                btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
    
    def manage_tabs(self):
        """탭 관리 다이얼로그 열기"""
        def on_save():
            # 탭 버튼 다시 생성
            self._create_nav_buttons()
            self._update_nav_style()
            self.load_data()
        
        TabManagerDialog(self.root, on_save=on_save)
    
    def manage_magazine(self):
        """매거진 기사 관리 다이얼로그 열기"""
        study_html = SCRIPT_DIR / "study.html"
        if not study_html.exists():
            messagebox.showerror("오류", "study.html 파일을 찾을 수 없습니다.")
            return
        
        MagazineEditorDialog(self.root, study_html)
    
    def switch_mode(self, mode, html_file=None):
        """모드 전환"""
        self.current_mode = mode
        
        # html_file이 제공되면 사용, 아니면 탭 설정에서 찾기
        if html_file:
            self.current_html = SCRIPT_DIR / html_file
        else:
            tabs = TabManagerDialog.load_tabs()
            for tab in tabs:
                if tab['id'] == mode:
                    self.current_html = SCRIPT_DIR / tab['file']
                    break
            else:
                # 폴백: 기존 방식
                if mode == 'drawings':
                    self.current_html = DRAWINGS_HTML
                elif mode == 'graphics':
                    self.current_html = GRAPHICS_HTML
                else:
                    self.current_html = PROJECTS_HTML
        
        self._update_nav_style()
        self.search_var.set("")
        self.load_data()
    
    def extract_json(self, content):
        # 비탐욕적 매칭으로 첫 번째 JSON 배열만 캡처
        match = re.search(r'<script type="application/json" id="projectsData">\s*(\[[\s\S]*?\])\s*</script>', content)
        if not match:
            return []
        
        json_str = match.group(1)
        
        # JSON 문자열 내의 실제 줄바꿈을 \n으로 변환 (문자열 값 내부만)
        # "..." 사이의 실제 줄바꿈을 \\n으로 이스케이프
        def fix_newlines_in_strings(m):
            return m.group(0).replace('\n', '\\n').replace('\r', '')
        
        # JSON 문자열 값 내의 줄바꿈 수정
        json_str = re.sub(r'"[^"]*"', fix_newlines_in_strings, json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {e}")
    
    def update_json(self, content, data):
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        # 비탐욕적 매칭으로 projectsData의 JSON만 대체
        return re.sub(r'(<script type="application/json" id="projectsData">)\s*\[[\s\S]*?\]\s*(</script>)',
                     f'\\1\n  {json_str}\n  \\2', content)
    
    def generate_grid(self, projects):
        items = []
        project_type = self.current_mode if self.current_mode in ['drawings', 'graphics'] else 'projects'
        for i, p in enumerate(projects):
            if not p.get('visible', True):
                continue
            slug = p.get('slug', p['title'].lower().replace(' ', '-'))
            display = p.get('display_title', p['title'])
            year = p.get('display_year', '')
            if not year:
                dur = p.get('duration', '')
                year = dur[:4] if dur else ''
            
            # thumb.jpg 우선, cover.jpg fallback (CSS에서 처리)
            items.append(f'''      <article class="grid-item" data-project="{i}">
        <button class="grid-item-btn" aria-haspopup="dialog">
          <div class="grid-item-image">
            <div class="grid-thumb" data-thumb="images/{project_type}/{slug}/thumb.jpg" data-cover="images/{project_type}/{slug}/cover.jpg" style="background-image: url('images/{project_type}/{slug}/thumb.jpg');"></div>
          </div>
          <div class="grid-item-overlay">
            <span class="grid-item-title">{display}</span>
            <span class="grid-item-year">{year}</span>
          </div>
        </button>
      </article>''')
        return '\n\n'.join(items)
    
    def update_grid(self, content, projects):
        grid = self.generate_grid(projects)
        # 탐욕적 매칭으로 전체 그리드 영역 대체
        return re.sub(r'(<div class="archive-grid" role="list">)[\s\S]*(</div>\s*</main>)',
                     f'\\1\n\n{grid}\n\n    \\2', content)
    
    def load_data(self):
        try:
            with open(self.current_html, 'r', encoding='utf-8') as f:
                content = f.read()
            self.projects = self.extract_json(content)
            self.update_tree()
            self.count_label.config(text=f"{len(self.projects)} items")
            self.status_var.set(f"{len(self.projects)}개 {self.current_mode} 로드됨")
        except FileNotFoundError:
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {self.current_html}")
        except json.JSONDecodeError as e:
            messagebox.showerror("오류", f"JSON 파싱 오류: {e}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"로드 오류: {error_detail}")
            messagebox.showerror("오류", f"로드 실패: {e}\n\n상세: {error_detail[:500]}")
    
    def update_tree(self, filtered=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in (filtered or self.projects):
            vis = "✓" if p.get('visible', True) else "✕"
            self.tree.insert('', tk.END, values=(p['index'], p['title'], p.get('duration', ''), p.get('studio', ''), vis))
    
    def filter_list(self, *args):
        term = self.search_var.get().lower()
        if not term:
            self.update_tree()
            return
        self.update_tree([p for p in self.projects if term in p.get('title', '').lower() or term in p.get('studio', '').lower()])
    
    def get_selected(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        idx = str(self.tree.item(sel[0])['values'][0]).zfill(2)
        for i, p in enumerate(self.projects):
            if str(p['index']) == idx:
                return p, i
        return None, None
    
    def add_project(self):
        # 고유한 임시 slug 생성 (timestamp 기반)
        import time
        temp_slug = f"new-project-{int(time.time())}"
        new = {'id': len(self.projects)+1, 'index': str(len(self.projects)+1).zfill(2),
               'title': 'NEW PROJECT', 'slug': temp_slug, 'visible': True, '_is_new': True}
        
        def on_save(result):
            result['id'] = len(self.projects) + 1
            result['index'] = str(len(self.projects) + 1).zfill(2)
            self.projects.append(result)
            
            project_type = self.current_mode if self.current_mode in ['drawings', 'graphics'] else 'projects'
            folder = IMAGES_DIR / project_type / result['slug']
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "model_images").mkdir(exist_ok=True)
            
            self.save_data()
            self.load_data()
            self.status_var.set(f"'{result['title']}' 추가됨")
        
        ProjectEditorDialog(self.root, new, self.current_mode, on_save=on_save)
    
    def edit_project(self):
        project, idx = self.get_selected()
        if not project:
            messagebox.showwarning("경고", "편집할 항목을 선택하세요.")
            return
        
        def on_save(result):
            self.projects[idx].update(result)
            self.save_data()
            self.load_data()
            self.status_var.set(f"'{result['title']}' 수정됨")
        
        ProjectEditorDialog(self.root, project, self.current_mode, on_save=on_save)
    
    def delete_project(self):
        project, idx = self.get_selected()
        if not project:
            messagebox.showwarning("경고", "삭제할 항목을 선택하세요.")
            return
        if messagebox.askyesno("확인", f"'{project['title']}'을(를) 삭제하시겠습니까?"):
            self.projects.pop(idx)
            for i, p in enumerate(self.projects):
                p['id'] = i + 1
                p['index'] = str(i + 1).zfill(2)
            self.save_data()
            self.load_data()
            self.status_var.set(f"'{project['title']}' 삭제됨")
    
    def move_up(self):
        project, idx = self.get_selected()
        if not project or idx == 0:
            return
        self.projects[idx], self.projects[idx-1] = self.projects[idx-1], self.projects[idx]
        self._reindex()
        self._refresh_list_keep_selection(idx - 1)  # 새 위치에서 선택 유지
    
    def move_down(self):
        project, idx = self.get_selected()
        if not project or idx >= len(self.projects) - 1:
            return
        self.projects[idx], self.projects[idx+1] = self.projects[idx+1], self.projects[idx]
        self._reindex()
        self._refresh_list_keep_selection(idx + 1)  # 새 위치에서 선택 유지
    
    def _refresh_list_keep_selection(self, new_idx):
        """리스트 갱신 후 선택 유지"""
        # Treeview 업데이트
        self.tree.delete(*self.tree.get_children())
        for p in self.projects:
            visible = "✓" if p.get('visible', True) else "✗"
            self.tree.insert('', 'end', values=(
                p.get('index', ''), p.get('title', ''), 
                p.get('duration', ''), p.get('studio', ''), visible
            ))
        
        # 새 위치에서 선택 유지
        children = self.tree.get_children()
        if 0 <= new_idx < len(children):
            self.tree.selection_set(children[new_idx])
            self.tree.focus(children[new_idx])
            self.tree.see(children[new_idx])
        
        self.count_label.config(text=f"총 {len(self.projects)}개")
    
    def _on_drag_start(self, event):
        """드래그 시작"""
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item
            children = self.tree.get_children()
            self._drag_data["index"] = children.index(item) if item in children else None
    
    def _on_drag_motion(self, event):
        """드래그 중 - 커서 변경"""
        if self._drag_data["item"]:
            target = self.tree.identify_row(event.y)
            if target and target != self._drag_data["item"]:
                self.tree.configure(cursor="sb_v_double_arrow")
            else:
                self.tree.configure(cursor="")
    
    def _on_drag_end(self, event):
        """드래그 종료 - 항목 이동"""
        if not self._drag_data["item"] or self._drag_data["index"] is None:
            self._drag_data = {"item": None, "index": None}
            return
        
        target = self.tree.identify_row(event.y)
        self.tree.configure(cursor="")
        
        if target and target != self._drag_data["item"]:
            children = self.tree.get_children()
            if target in children:
                target_idx = children.index(target)
                source_idx = self._drag_data["index"]
                
                if source_idx != target_idx:
                    # 프로젝트 이동
                    project = self.projects.pop(source_idx)
                    self.projects.insert(target_idx, project)
                    self._reindex()
                    self._refresh_list_keep_selection(target_idx)
                    self.status_var.set(f"'{project['title']}' 위치 변경됨")
        
        self._drag_data = {"item": None, "index": None}
    
    def cleanup_files(self):
        """이미지 파일 정리 - 중복 및 미사용 파일 제거"""
        if not messagebox.askyesno("파일 정리", 
            "프로젝트 폴더의 중복 파일 및 미사용 파일을 정리합니다.\n\n"
            "다음 작업을 수행합니다:\n"
            "• 중복 파일명 정리 (번호 재정렬)\n"
            "• 임시 파일 삭제\n"
            "• 빈 폴더 삭제\n\n"
            "계속하시겠습니까?"):
            return
        
        project_type = self.current_mode if self.current_mode in ['drawings', 'graphics'] else 'projects'
        base_folder = IMAGES_DIR / project_type
        
        cleaned = 0
        errors = 0
        
        for project in self.projects:
            slug = project.get('slug', '')
            if not slug:
                continue
            
            folder = base_folder / slug
            if not folder.exists():
                continue
            
            try:
                # 서브 이미지 재정렬 (01.jpg, 02.jpg, ...)
                sub_images = sorted([f for f in folder.glob("[0-9][0-9].*") 
                                    if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']])
                for i, img in enumerate(sub_images, 1):
                    new_name = f"{str(i).zfill(2)}{img.suffix}"
                    new_path = folder / new_name
                    if img.name != new_name:
                        if new_path.exists() and new_path != img:
                            # 임시 이름으로 먼저 이동
                            temp_path = folder / f"_temp_{img.name}"
                            shutil.move(str(img), str(temp_path))
                            img = temp_path
                        shutil.move(str(img), str(new_path))
                        cleaned += 1
                
                # 모델 이미지 재정렬
                model_folder = folder / "model_images"
                if model_folder.exists():
                    model_images = sorted([f for f in model_folder.glob("*.*") 
                                          if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']],
                                         key=lambda x: int(''.join(filter(str.isdigit, x.stem)) or 0))
                    for i, img in enumerate(model_images, 1):
                        new_name = f"{i}{img.suffix}"
                        new_path = model_folder / new_name
                        if img.name != new_name:
                            if new_path.exists() and new_path != img:
                                temp_path = model_folder / f"_temp_{img.name}"
                                shutil.move(str(img), str(temp_path))
                                img = temp_path
                            shutil.move(str(img), str(new_path))
                            cleaned += 1
                
                # 임시 파일 삭제
                for temp in folder.glob("_temp_*"):
                    os.remove(str(temp))
                    cleaned += 1
                
            except Exception as e:
                print(f"폴더 정리 오류 ({slug}): {e}")
                errors += 1
        
        # 빈 폴더 삭제
        for folder in base_folder.iterdir():
            if folder.is_dir() and not any(folder.iterdir()):
                try:
                    folder.rmdir()
                    cleaned += 1
                except:
                    pass
        
        msg = f"파일 정리 완료\n정리된 항목: {cleaned}개"
        if errors > 0:
            msg += f"\n오류: {errors}개"
        messagebox.showinfo("완료", msg)
        self.status_var.set(f"파일 정리 완료 ({cleaned}개 항목)")
    
    def duplicate(self):
        project, idx = self.get_selected()
        if not project:
            return
        new = project.copy()
        new['title'] = project['title'] + " (복사)"
        new['slug'] = project['slug'] + "-copy"
        self.projects.insert(idx + 1, new)
        self._reindex()
        
        project_type = self.current_mode if self.current_mode in ['drawings', 'graphics'] else 'projects'
        folder = IMAGES_DIR / project_type / new['slug']
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "model_images").mkdir(exist_ok=True)
        
        self.save_data()
        self.load_data()
    
    def _reindex(self):
        for i, p in enumerate(self.projects):
            p['id'] = i + 1
            p['index'] = str(i + 1).zfill(2)
    
    def open_folder(self):
        project, _ = self.get_selected()
        if not project:
            return
        project_type = self.current_mode if self.current_mode in ['drawings', 'graphics'] else 'projects'
        folder = IMAGES_DIR / project_type / project.get('slug', '')
        if folder.exists():
            os.startfile(str(folder))
        elif messagebox.askyesno("폴더 없음", "생성하시겠습니까?"):
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "model_images").mkdir(exist_ok=True)
            os.startfile(str(folder))
    
    def preview(self):
        webbrowser.open(f'file:///{self.current_html}')
    
    def _open_mobile_preview_for(self, html_file: Path):
        preview_file = SCRIPT_DIR / "mobile_preview.html"
        if not preview_file.exists():
            messagebox.showerror("오류", "mobile_preview.html 파일을 찾을 수 없습니다.")
            return
        target_name = html_file.name
        url = f"{preview_file.as_uri()}?page={quote(target_name)}"
        webbrowser.open(url)
    
    def open_mobile_preview(self):
        self._open_mobile_preview_for(self.current_html)
    
    def open_mobile_preview_home(self):
        self._open_mobile_preview_for(INDEX_HTML)
    
    def edit_home(self):
        """홈 화면 편집"""
        HomeManagerDialog(self.root)
    
    def edit_about(self):
        AboutEditorDialog(self.root)
    
    def edit_footer(self):
        FooterEditorDialog(self.root)
    
    def open_site(self):
        webbrowser.open(f'file:///{SCRIPT_DIR / "index.html"}')
    
    def backup(self):
        """백업 옵션 대화상자 표시"""
        BackupOptionsDialog(self.root, self._do_backup_with_options)
    
    def _cleanup_empty_backup_folder(self, backup_folder: Path):
        """빈 백업 폴더 및 상위 날짜 폴더 정리."""
        if backup_folder.exists() and not any(backup_folder.iterdir()):
            backup_folder.rmdir()
            parent = backup_folder.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
    
    def _do_backup_with_options(self, backup_type, version_name, auto_version, selected_files=None):
        """옵션에 따른 백업 수행"""
        now = datetime.now()
        date_folder = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        # 버전명 생성
        if auto_version:
            version_name = self._get_next_version()
        elif version_name:
            # 사용자 입력 버전명 정리 (특수문자 제거)
            version_name = "".join(c for c in version_name if c.isalnum() or c in '-_.')
        
        # 폴더명 생성: 날짜_시간_버전
        if version_name:
            folder_name = f"{time_str}_{version_name}"
        else:
            folder_name = time_str
        
        backup_folder = BACKUP_DIR / date_folder / folder_name
        backup_folder.mkdir(parents=True, exist_ok=True)
        
        target_map = get_backup_target_map()
        files_to_process = list(target_map.items())
        
        if backup_type == "selected":
            selected_names = selected_files or []
            files_to_process = [
                (name, target_map[name]) for name in selected_names if name in target_map
            ]
            if not files_to_process:
                self._cleanup_empty_backup_folder(backup_folder)
                messagebox.showwarning("백업", "선택된 백업 파일이 없습니다.")
                return
        
        if backup_type == "full":
            # 모든 파일 백업 (버전 스냅샷)
            backed_up = []
            for filename, file_path in files_to_process:
                if file_path.exists():
                    shutil.copy(file_path, backup_folder / filename)
                    backed_up.append(filename)
            
            if not backed_up:
                self._cleanup_empty_backup_folder(backup_folder)
                messagebox.showwarning("백업", "백업할 파일이 없습니다.")
                return
            
            # 버전 정보 파일 생성
            version_info = backup_folder / "VERSION.txt"
            version_info.write_text(
                f"Version: {version_name or 'N/A'}\n"
                f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Type: Full Backup (모든 파일)\n"
                f"Files: {', '.join(backed_up)}\n",
                encoding='utf-8'
            )
            
            messagebox.showinfo("백업 완료", 
                               f"📁 백업 위치: backups/{date_folder}/{folder_name}/\n\n"
                               f"📦 버전: {version_name or '자동'}\n"
                               f"📄 백업된 파일 ({len(backed_up)}개):\n" + 
                               "\n".join(f"  • {f}" for f in backed_up))
        elif backup_type == "changed":
            # 변경된 파일만 백업
            prev_backup = self._get_latest_backup()
            backed_up = []
            changes = []
            
            for filename, file_path in files_to_process:
                if file_path.exists():
                    current_content = file_path.read_text(encoding='utf-8', errors='replace')
                    
                    prev_content = ""
                    if prev_backup:
                        prev_file = prev_backup / filename
                        if prev_file.exists():
                            prev_content = prev_file.read_text(encoding='utf-8', errors='replace')
                    
                    if current_content != prev_content:
                        shutil.copy(file_path, backup_folder / filename)
                        backed_up.append(filename)
                        
                        change_summary = self._analyze_changes(filename, prev_content, current_content)
                        if change_summary:
                            changes.extend(change_summary)
            
            if not backed_up:
                messagebox.showinfo("백업", "변경된 파일이 없습니다.")
                self._cleanup_empty_backup_folder(backup_folder)
                return
            
            # 변경사항 요약 파일 생성
            summary_file = backup_folder / "CHANGELOG.md"
            self._write_changelog(summary_file, now, backed_up, changes)
            
            messagebox.showinfo("백업 완료", 
                               f"📁 백업 위치: backups/{date_folder}/{folder_name}/\n\n"
                               f"📝 버전: {version_name or '자동'}\n"
                               f"📄 변경된 파일:\n" + "\n".join(f"  • {f}" for f in backed_up) + "\n\n"
                               f"📝 변경사항 요약: CHANGELOG.md")
        elif backup_type == "selected":
            backed_up = []
            for filename, file_path in files_to_process:
                if file_path.exists():
                    shutil.copy(file_path, backup_folder / filename)
                    backed_up.append(filename)
            
            if not backed_up:
                self._cleanup_empty_backup_folder(backup_folder)
                messagebox.showwarning("백업", "선택한 파일 중 백업 가능한 파일이 없습니다.")
                return
            
            selected_note = backup_folder / "SELECTED.txt"
            selected_note.write_text(
                f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Version: {version_name or 'N/A'}\n"
                f"Type: Selected Backup (선택 백업)\n"
                f"Files:\n" + "\n".join(f"- {name}" for name in backed_up),
                encoding='utf-8'
            )
            
            messagebox.showinfo(
                "백업 완료",
                f"📁 백업 위치: backups/{date_folder}/{folder_name}/\n\n"
                f"🎯 버전: {version_name or '자동'}\n"
                f"📄 선택 백업 파일 ({len(backed_up)}개):\n" + "\n".join(f"  • {f}" for f in backed_up),
            )
        else:
            self._cleanup_empty_backup_folder(backup_folder)
            raise ValueError(f"지원하지 않는 백업 타입: {backup_type}")
    
    def _get_next_version(self):
        """다음 버전 번호 자동 생성"""
        if not BACKUP_DIR.exists():
            return "v1"
        
        max_version = 0
        import re
        
        for date_dir in BACKUP_DIR.iterdir():
            if date_dir.is_dir():
                for time_dir in date_dir.iterdir():
                    if time_dir.is_dir():
                        # 폴더명에서 버전 추출 (예: 143052_v5 -> v5)
                        match = re.search(r'_v(\d+)$', time_dir.name)
                        if match:
                            ver = int(match.group(1))
                            if ver > max_version:
                                max_version = ver
        
        return f"v{max_version + 1}"
    
    def _get_latest_backup(self):
        """가장 최근 백업 폴더 찾기"""
        if not BACKUP_DIR.exists():
            return None
        
        latest = None
        latest_time = None
        
        for date_dir in BACKUP_DIR.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                for time_dir in date_dir.iterdir():
                    if time_dir.is_dir():
                        time_part = time_dir.name.split('_')[0]
                        if not (time_part.isdigit() and len(time_part) == 6):
                            continue
                        if not list_backup_payload_files(time_dir):
                            continue
                        try:
                            dt = datetime.strptime(f"{date_dir.name}{time_part}", "%Y%m%d%H%M%S")
                            if latest_time is None or dt > latest_time:
                                latest_time = dt
                                latest = time_dir
                        except:
                            pass
        
        return latest
    
    def _analyze_changes(self, filename, prev_content, current_content):
        """파일 변경사항 분석"""
        changes = []
        
        if 'projects' in filename or 'drawings' in filename or 'graphics' in filename:
            # 프로젝트 개수 비교
            prev_count = prev_content.count('data-project=') if prev_content else 0
            curr_count = current_content.count('data-project=')
            
            if curr_count > prev_count:
                changes.append(f"[{filename}] 프로젝트 {curr_count - prev_count}개 추가 (총 {curr_count}개)")
            elif curr_count < prev_count:
                changes.append(f"[{filename}] 프로젝트 {prev_count - curr_count}개 삭제 (총 {curr_count}개)")
            else:
                changes.append(f"[{filename}] 프로젝트 내용 수정 (총 {curr_count}개)")
            
            # 제목 변경 감지
            import re
            prev_titles = set(re.findall(r'"title":\s*"([^"]+)"', prev_content)) if prev_content else set()
            curr_titles = set(re.findall(r'"title":\s*"([^"]+)"', current_content))
            
            new_titles = curr_titles - prev_titles
            removed_titles = prev_titles - curr_titles
            
            for title in new_titles:
                changes.append(f"  ✨ 새 프로젝트: {title}")
            for title in removed_titles:
                changes.append(f"  🗑️ 삭제됨: {title}")
                
        elif 'about' in filename:
            # About 페이지 변경
            if len(current_content) != len(prev_content) if prev_content else True:
                changes.append(f"[{filename}] About 페이지 내용 수정")
        else:
            if not prev_content and current_content:
                changes.append(f"[{filename}] 신규 백업")
            elif prev_content != current_content:
                changes.append(f"[{filename}] 파일 내용 수정")
        
        return changes
    
    def _write_changelog(self, filepath, timestamp, backed_up, changes):
        """변경사항 요약 파일 작성"""
        content = f"""# 백업 변경사항 요약

📅 **백업 일시**: {timestamp.strftime("%Y년 %m월 %d일 %H:%M:%S")}

---

## 📄 백업된 파일
"""
        for f in backed_up:
            content += f"- {f}\n"
        
        content += "\n---\n\n## 📝 변경사항\n"
        
        if changes:
            for change in changes:
                content += f"- {change}\n"
        else:
            content += "- 세부 변경사항 분석 불가\n"
        
        content += f"""
---

## 💡 복원 방법
이 백업을 복원하려면:
1. 관리자 도구에서 '🔄 복원' 버튼 클릭
2. 이 날짜/시간 선택
3. 복원할 파일 선택

또는 수동으로:
```
이 폴더의 백업 파일들을 프로젝트 루트 폴더에 복사
```

---
*자동 생성됨 by Portfolio Admin Tool*
"""
        filepath.write_text(content, encoding='utf-8')
    
    def organize_backups(self):
        """기존 백업 파일을 날짜/시간별 폴더로 정리"""
        if not BACKUP_DIR.exists():
            messagebox.showinfo("알림", "백업 폴더가 없습니다.")
            return
        
        import re
        organized = 0
        
        # 1. 루트 백업 폴더의 파일들 정리
        for file in BACKUP_DIR.glob("*.html"):
            name = file.stem
            match = re.search(r'_(\d{8})_(\d{6})', name)
            
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                
                target_folder = BACKUP_DIR / date_str / time_str
                target_folder.mkdir(parents=True, exist_ok=True)
                
                original_name = name.split('_')[0] + '.html'
                new_path = target_folder / original_name
                
                if not new_path.exists():
                    shutil.move(str(file), str(new_path))
                    organized += 1
        
        # 2. 날짜 폴더 내의 파일들도 시간별로 정리
        for date_dir in BACKUP_DIR.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                # 날짜 폴더 내의 HTML 파일들
                for file in list(date_dir.glob("*.html")):
                    name = file.stem
                    match = re.search(r'_(\d{8})_(\d{6})', name)
                    
                    if match:
                        time_str = match.group(2)
                        
                        # 시간 폴더 생성
                        time_folder = date_dir / time_str
                        time_folder.mkdir(exist_ok=True)
                        
                        # 원본 파일명 (projects.html, drawings.html, about.html)
                        original_name = name.split('_')[0] + '.html'
                        new_path = time_folder / original_name
                        
                        if not new_path.exists():
                            shutil.move(str(file), str(new_path))
                            organized += 1
                        else:
                            # 중복 파일 삭제
                            file.unlink()
        
        messagebox.showinfo("정리 완료", f"{organized}개 백업 파일이 시간별 폴더로 정리되었습니다.")
    
    def show_backup_manager(self):
        """백업 관리자 대화상자"""
        BackupManagerDialog(self.root)
    
    def restore_backup(self):
        """백업 복원"""
        if not BACKUP_DIR.exists():
            messagebox.showinfo("알림", "백업이 없습니다.")
            return
        
        # 백업 목록 수집
        backups = []
        for date_dir in sorted(BACKUP_DIR.iterdir(), reverse=True):
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                for time_dir in sorted(date_dir.iterdir(), reverse=True):
                    if time_dir.is_dir():
                        files = list_backup_payload_files(time_dir)
                        if files:
                            backups.append({
                                'path': time_dir,
                                'date': date_dir.name,
                                'time': time_dir.name,
                                'files': [f.name for f in files]
                            })
        
        if not backups:
            messagebox.showinfo("알림", "복원 가능한 백업이 없습니다.")
            return
        
        # 복원 대화상자
        RestoreDialog(self.root, backups, self._do_restore)
    
    def _do_restore(self, backup_path, files_to_restore):
        """실제 복원 수행"""
        try:
            # 현재 파일 백업 먼저
            self.backup()
            
            # 복원
            restored = []
            for filename in files_to_restore:
                src = backup_path / filename
                if src.exists():
                    dst = get_backup_target_map().get(filename)
                    if dst is None:
                        continue
                    
                    shutil.copy(src, dst)
                    restored.append(filename)
            
            if restored:
                # 데이터 다시 로드
                self.load_data()
                messagebox.showinfo("복원 완료", 
                                   f"✅ 복원 완료!\n\n"
                                   f"복원된 파일:\n" + "\n".join(f"  • {f}" for f in restored))
            
        except Exception as e:
            messagebox.showerror("복원 실패", str(e))
    
    def apply_changes(self):
        """변경사항을 로컬 HTML 파일에 적용 (Git 푸시 없음)"""
        try:
            # 백업 먼저 생성 (날짜별 폴더에)
            now = datetime.now()
            date_folder = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            
            backup_folder = BACKUP_DIR / date_folder / time_str
            backup_folder.mkdir(parents=True, exist_ok=True)
            
            if self.current_html.exists():
                shutil.copy(self.current_html, backup_folder / self.current_html.name)
            
            # 현재 데이터를 HTML에 저장
            self.save_data()
            
            # 성공 메시지
            messagebox.showinfo("저장 완료", 
                              f"✅ 로컬에 저장되었습니다.\n\n"
                              f"적용된 파일: {self.current_html.name}\n"
                              f"프로젝트 수: {len(self.projects)}개\n\n"
                              f"💡 실제 웹사이트에 배포하려면\n'🚀 저장+배포' 버튼을 클릭하세요.")
            
            self.status_var.set(f"✅ 로컬 저장 완료: {self.current_html.name}")
            
        except Exception as e:
            messagebox.showerror("저장 실패", f"오류 발생: {str(e)}")
    
    def save_and_deploy(self):
        """
        전체 저장+배포 파이프라인
        
        1. 로컬에 변경사항 저장
        2. Git add → commit → push
        3. Netlify 자동 배포 트리거
        """
        try:
            self.status_var.set("🔄 저장 및 배포 중...")
            self.root.update()
            
            # 1. 백업 생성
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            BACKUP_DIR.mkdir(exist_ok=True)
            if self.current_html.exists():
                shutil.copy(self.current_html, BACKUP_DIR / f"{self.current_html.stem}_{ts}_backup.html")
            
            # 2. 로컬에 데이터 저장
            self.save_data()
            self.status_var.set("✅ 로컬 저장 완료. Git 푸시 중...")
            self.root.update()
            
            # 3. Git 자동화
            git = GitAutomation(SCRIPT_DIR)
            
            # Git 저장소 확인 - 없으면 자동 초기화
            if not git.is_git_repo():
                self.status_var.set("🔧 Git 저장소 초기화 중...")
                self.root.update()
                
                success, msg = git.init_repo()
                if not success:
                    messagebox.showerror("Git 초기화 실패", f"Git 저장소 초기화 실패:\n{msg}")
                    return
                
                # 첫 커밋 생성
                git.add_all()
                git.commit("Initial commit: JEONHYERIN Portfolio")
                self.status_var.set("✅ Git 저장소 초기화 완료")
                self.root.update()
            
            # 원격 저장소 확인/보정
            self.status_var.set("🔗 GitHub 저장소 연결 확인 중...")
            self.root.update()
            remote_ok, remote_msg = git.ensure_remote(DEFAULT_GITHUB_REPO_URL)
            if not remote_ok:
                messagebox.showerror(
                    "GitHub 연결 실패",
                    f"원격 저장소 연결 확인에 실패했습니다.\n\n{remote_msg}\n\n"
                    f"대상 저장소: {DEFAULT_GITHUB_REPO_URL}"
                )
                self.status_var.set("❌ GitHub 연결 실패")
                return
            
            # 4. 변경사항 커밋 및 푸시
            project, _ = self.get_selected()
            project_slug = project.get('slug') if project else None
            
            success, message = git.auto_deploy(project_slug=project_slug)
            
            if success:
                messagebox.showinfo("🚀 배포 완료", message)
                self.status_var.set("🚀 배포 완료! Netlify 빌드 시작됨")
            else:
                messagebox.showerror("배포 실패", message)
                self.status_var.set("❌ 배포 실패")
            
        except Exception as e:
            messagebox.showerror("오류", f"저장+배포 실패: {str(e)}")
            self.status_var.set("❌ 오류 발생")
    
    def save_data(self):
        try:
            # 저장 전 현재 상태를 undo 스택에 저장
            with open(self.current_html, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            if not hasattr(self, 'undo_stack'):
                self.undo_stack = {}
            if self.current_mode not in self.undo_stack:
                self.undo_stack[self.current_mode] = []
            
            # 최대 10개까지만 저장
            if len(self.undo_stack[self.current_mode]) >= 10:
                self.undo_stack[self.current_mode].pop(0)
            self.undo_stack[self.current_mode].append(current_content)
            
            # 저장
            content = self.update_json(current_content, self.projects)
            content = self.update_grid(content, self.projects)
            
            # 푸터 데이터 동기화 (모든 섹션의 데이터를 각 HTML에 추가)
            content = self.sync_footer_data(content)
            
            with open(self.current_html, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 다른 HTML 파일들에도 푸터 데이터 동기화
            self.sync_all_footer_data()
            
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {e}")
    
    def get_section_data(self, html_file):
        """HTML 파일에서 프로젝트 데이터 추출"""
        try:
            if not html_file.exists():
                return []
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'<script type="application/json" id="projectsData">\s*(\[[\s\S]*?\])\s*</script>', content)
            if match:
                json_str = match.group(1)
                # JSON 문자열 내의 실제 줄바꿈을 \n으로 변환
                def fix_newlines(m):
                    return m.group(0).replace('\n', '\\n').replace('\r', '')
                json_str = re.sub(r'"[^"]*"', fix_newlines, json_str)
                return json.loads(json_str)
        except:
            pass
        return []
    
    def sync_footer_data(self, content):
        """현재 HTML에 세 섹션의 푸터 데이터 추가"""
        # 다른 섹션의 데이터 가져오기
        projects_data = self.get_section_data(PROJECTS_HTML) if self.current_mode != 'projects' else self.projects
        drawings_data = self.get_section_data(DRAWINGS_HTML) if self.current_mode != 'drawings' else (self.projects if self.current_mode == 'drawings' else self.get_section_data(DRAWINGS_HTML))
        graphics_data = self.get_section_data(GRAPHICS_HTML) if self.current_mode != 'graphics' else (self.projects if self.current_mode == 'graphics' else self.get_section_data(GRAPHICS_HTML))
        
        # 현재 모드에 따라 올바른 데이터 할당
        if self.current_mode == 'projects':
            projects_data = self.projects
        elif self.current_mode == 'drawings':
            drawings_data = self.projects
        elif self.current_mode == 'graphics':
            graphics_data = self.projects
        
        footer_data = {
            'projects': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in projects_data],
            'drawings': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in drawings_data],
            'graphics': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in graphics_data]
        }
        
        footer_json = json.dumps(footer_data, ensure_ascii=False)
        
        # 기존 footerData 태그가 있으면 교체, 없으면 추가
        if '<script type="application/json" id="footerData">' in content:
            content = re.sub(
                r'<script type="application/json" id="footerData">[\s\S]*?</script>',
                f'<script type="application/json" id="footerData">{footer_json}</script>',
                content
            )
        else:
            # projectsData 바로 다음에 추가
            content = re.sub(
                r'(</script>\s*\n\s*<script src="script\.js")',
                f'</script>\n  <script type="application/json" id="footerData">{footer_json}</script>\n  <script src="script.js"',
                content
            )
        
        return content
    
    def sync_all_footer_data(self):
        """모든 HTML 파일의 푸터 데이터 동기화"""
        # 모든 섹션의 최신 데이터 수집
        projects_data = self.get_section_data(PROJECTS_HTML)
        drawings_data = self.get_section_data(DRAWINGS_HTML)
        graphics_data = self.get_section_data(GRAPHICS_HTML)
        
        footer_data = {
            'projects': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in projects_data],
            'drawings': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in drawings_data],
            'graphics': [{'title': p.get('display_title', p.get('title', '')), 'visible': p.get('visible', True)} for p in graphics_data]
        }
        
        footer_json = json.dumps(footer_data, ensure_ascii=False)
        
        # 모든 관련 HTML 파일 업데이트
        for html_file in [PROJECTS_HTML, DRAWINGS_HTML, GRAPHICS_HTML, ABOUT_HTML]:
            if not html_file.exists() or html_file == self.current_html:
                continue
            
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '<script type="application/json" id="footerData">' in content:
                    content = re.sub(
                        r'<script type="application/json" id="footerData">[\s\S]*?</script>',
                        f'<script type="application/json" id="footerData">{footer_json}</script>',
                        content
                    )
                else:
                    # script.js 바로 전에 추가
                    content = re.sub(
                        r'(\s*<script src="script\.js")',
                        f'\n  <script type="application/json" id="footerData">{footer_json}</script>\\1',
                        content
                    )
                
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"푸터 데이터 동기화 실패 ({html_file}): {e}")
    
    def undo(self):
        """이전 상태로 되돌리기"""
        if not hasattr(self, 'undo_stack'):
            self.undo_stack = {}
        
        if self.current_mode not in self.undo_stack or not self.undo_stack[self.current_mode]:
            messagebox.showinfo("알림", "되돌릴 수 있는 변경사항이 없습니다.")
            return
        
        if messagebox.askyesno("확인", "마지막 저장 이전 상태로 되돌리시겠습니까?"):
            try:
                previous_content = self.undo_stack[self.current_mode].pop()
                with open(self.current_html, 'w', encoding='utf-8') as f:
                    f.write(previous_content)
                self.load_data()
                self.status_var.set("↩️ 이전 상태로 되돌림")
            except Exception as e:
                messagebox.showerror("오류", f"되돌리기 실패: {e}")


def main():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        import subprocess
        subprocess.check_call(['pip', 'install', 'Pillow'])
    
    root = tk.Tk()
    PortfolioAdminApp(root)
    root.mainloop()


class MagazineEditorDialog(tk.Toplevel):
    """매거진 기사 편집 다이얼로그"""
    
    def __init__(self, parent, html_file, on_save=None):
        super().__init__(parent)
        self.title("📰 매거진 기사 관리")
        self.geometry("800x600")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.html_file = html_file
        self.on_save = on_save
        
        self.transient(parent)
        self.grab_set()
        
        # 중앙 배치
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 800) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")
        
        self.articles = self.load_articles()
        self.create_ui()
    
    def load_articles(self):
        """HTML에서 매거진 데이터 로드"""
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            match = re.search(r'<script[^>]*id="magazineData"[^>]*>([\s\S]*?)</script>', content)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except Exception as e:
            print(f"Error loading magazine data: {e}")
        return []
    
    def create_ui(self):
        # 헤더
        header = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        header.pack(fill=tk.X, padx=25, pady=(20, 15))
        
        tk.Label(header, text="📰 매거진 기사 관리", 
                font=ModernStyle.get_font(14, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        
        # 리스트 프레임
        list_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 15))
        
        # 리스트 헤더
        header_row = tk.Frame(list_frame, bg=ModernStyle.BG_LIGHT)
        header_row.pack(fill=tk.X)
        
        tk.Label(header_row, text="카테고리", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=12).pack(side=tk.LEFT, padx=5)
        tk.Label(header_row, text="제목", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=30, anchor='w').pack(side=tk.LEFT, padx=10)
        tk.Label(header_row, text="날짜", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=12).pack(side=tk.LEFT, padx=10)
        tk.Label(header_row, text="공개", font=ModernStyle.get_font(9, 'bold'),
                bg=ModernStyle.BG_LIGHT, width=6).pack(side=tk.LEFT, padx=5)
        
        # 스크롤 가능한 리스트
        canvas = tk.Canvas(list_frame, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.articles_container = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.create_window((0, 0), window=self.articles_container, anchor='nw')
        self.articles_container.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self.article_widgets = []
        self.refresh_articles_list()
        
        # 버튼
        btn_frame = tk.Frame(self, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=25, pady=(0, 20))
        
        tk.Button(btn_frame, text="+ 새 기사 추가", font=ModernStyle.get_font(10, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=15, pady=8, command=self.add_article).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="✓ 저장", font=ModernStyle.get_font(10),
                 bg=ModernStyle.SUCCESS, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=20, pady=8, command=self.save).pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=15, pady=8, command=self.destroy).pack(side=tk.RIGHT, padx=(0, 10))
    
    def refresh_articles_list(self):
        """기사 리스트 새로고침"""
        for widget in self.articles_container.winfo_children():
            widget.destroy()
        self.article_widgets = []
        
        for i, article in enumerate(self.articles):
            row = tk.Frame(self.articles_container, bg=ModernStyle.BG_WHITE)
            row.pack(fill=tk.X, pady=3)
            
            # 카테고리
            cat_var = tk.StringVar(value=article.get('category', 'STUDY'))
            cat_entry = tk.Entry(row, textvariable=cat_var, width=12,
                                font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            cat_entry.pack(side=tk.LEFT, padx=5, ipady=3)
            
            # 제목
            title_var = tk.StringVar(value=article.get('title', ''))
            title_entry = tk.Entry(row, textvariable=title_var, width=30,
                                  font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            title_entry.pack(side=tk.LEFT, padx=10, ipady=3)
            
            # 날짜
            date_var = tk.StringVar(value=article.get('date', ''))
            date_entry = tk.Entry(row, textvariable=date_var, width=12,
                                 font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            date_entry.pack(side=tk.LEFT, padx=10, ipady=3)
            
            # 공개 체크박스
            visible_var = tk.BooleanVar(value=article.get('visible', True))
            cb = tk.Checkbutton(row, variable=visible_var, bg=ModernStyle.BG_WHITE)
            cb.pack(side=tk.LEFT, padx=5)
            
            # 삭제 버튼
            tk.Button(row, text="✕", font=ModernStyle.get_font(9),
                     bg=ModernStyle.DANGER, fg=ModernStyle.BG_WHITE, relief='flat',
                     padx=8, command=lambda idx=i: self.delete_article(idx)).pack(side=tk.RIGHT, padx=5)
            
            # 링크 편집 버튼
            tk.Button(row, text="🔗", font=ModernStyle.get_font(9),
                     bg=ModernStyle.BG_LIGHT, relief='flat',
                     padx=8, command=lambda idx=i: self.edit_link(idx)).pack(side=tk.RIGHT, padx=2)
            
            self.article_widgets.append({
                'category_var': cat_var,
                'title_var': title_var,
                'date_var': date_var,
                'visible_var': visible_var,
                'link': article.get('link', '')
            })
    
    def add_article(self):
        """새 기사 추가"""
        self.collect_article_data()
        from datetime import datetime
        new_article = {
            "id": len(self.articles) + 1,
            "category": "STUDY",
            "title": "New Article",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "content": "",
            "link": "",
            "visible": True
        }
        self.articles.append(new_article)
        self.refresh_articles_list()
    
    def delete_article(self, idx):
        """기사 삭제"""
        if messagebox.askyesno("확인", "이 기사를 삭제하시겠습니까?"):
            self.articles.pop(idx)
            self.refresh_articles_list()
    
    def edit_link(self, idx):
        """링크 편집"""
        current_link = self.article_widgets[idx].get('link', '')
        new_link = simpledialog.askstring("링크 편집", "외부 링크 URL을 입력하세요:", 
                                          initialvalue=current_link, parent=self)
        if new_link is not None:
            self.article_widgets[idx]['link'] = new_link
    
    def collect_article_data(self):
        """위젯에서 데이터 수집"""
        for i, widgets in enumerate(self.article_widgets):
            if i < len(self.articles):
                self.articles[i]['category'] = widgets['category_var'].get()
                self.articles[i]['title'] = widgets['title_var'].get()
                self.articles[i]['date'] = widgets['date_var'].get()
                self.articles[i]['visible'] = widgets['visible_var'].get()
                self.articles[i]['link'] = widgets.get('link', '')
    
    def save(self):
        """저장"""
        self.collect_article_data()
        
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # magazineData 업데이트
            json_str = json.dumps(self.articles, indent=2, ensure_ascii=False)
            pattern = r'(<script[^>]*id="magazineData"[^>]*>)[\s\S]*?(</script>)'
            replacement = f'\\1\n{json_str}\n\\2'
            content = re.sub(pattern, replacement, content)
            
            with open(self.html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("완료", "매거진 기사가 저장되었습니다.")
            
            if self.on_save:
                self.on_save()
            
            self.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{e}")


if __name__ == "__main__":
    main()
