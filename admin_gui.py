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
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk
import threading

# 파일 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECTS_HTML = SCRIPT_DIR / "projects.html"
DRAWINGS_HTML = SCRIPT_DIR / "drawings.html"
ABOUT_HTML = SCRIPT_DIR / "about.html"
IMAGES_DIR = SCRIPT_DIR / "images"
BACKUP_DIR = SCRIPT_DIR / "backups"

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
    
    def push(self):
        """원격 저장소에 푸시"""
        success, stdout, stderr = self._run_git('push')
        return success, stdout or stderr
    
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


class DropZone(tk.Frame):
    """드래그앤드롭 가능한 이미지 등록 영역"""
    
    def __init__(self, parent, image_type, title, project_folder, on_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.image_type = image_type
        self.title = title
        self.project_folder = project_folder
        self.on_change = on_change
        self.images = []
        self.thumbnails = {}
        self.selected_images = set()  # 선택된 이미지들
        self.check_vars = {}  # 체크박스 변수들
        
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
        # 기존 위젯 제거
        for widget in self.image_container.winfo_children():
            widget.destroy()
        
        self.check_vars.clear()
        
        if not self.images:
            self.empty_label = tk.Label(self.image_container,
                                       text="📷 클릭하여 이미지 추가",
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
                                    relief='solid', borderwidth=1, cursor='hand2')
                img_label.pack()
                # 클릭 시 체크박스 토글
                img_label.bind('<Button-1>', lambda e, v=var: v.set(not v.get()))
            else:
                img_label = tk.Label(frame, text="📷", font=ModernStyle.get_font(20),
                                    bg=ModernStyle.BG_LIGHT, width=8, height=4)
                img_label.pack()
            
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
        
        self.load_images()
        self._renumber_images()
        if self.on_change:
            self.on_change()
    
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
        if avg_reduction > 0:
            messagebox.showinfo("최적화 완료", 
                              f"{processed}개 이미지 추가됨\n평균 {avg_reduction:.1f}% 용량 감소")
        
        self.load_images()
        if self.on_change:
            self.on_change()
    
    def delete_image(self, img_path):
        """이미지 삭제 (단일)"""
        if messagebox.askyesno("확인", f"'{img_path.name}'을(를) 삭제하시겠습니까?"):
            if img_path.exists():
                os.remove(str(img_path))
            self.load_images()
            self._renumber_images()
            if self.on_change:
                self.on_change()
    
    def move_image(self, idx, direction):
        """이미지 순서 변경"""
        new_idx = idx + direction
        if 0 <= new_idx < len(self.images):
            self.images[idx], self.images[new_idx] = self.images[new_idx], self.images[idx]
            self._renumber_images()
            self.load_images()
            if self.on_change:
                self.on_change()
    
    def _renumber_images(self):
        """이미지 파일명 재정렬"""
        if self.image_type == 'cover':
            return
        
        if not self.images:
            return
        
        if self.image_type == 'sub':
            temp_files = []
            for i, img in enumerate(self.images):
                if img.exists():
                    temp_path = self.project_folder / f"_temp_sub_{i}{img.suffix}"
                    shutil.move(str(img), str(temp_path))
                    temp_files.append(temp_path)
            
            for i, temp_path in enumerate(temp_files):
                new_path = self.project_folder / f"{str(i+1).zfill(2)}.jpg"
                if temp_path.exists():
                    # 최적화된 jpg로 변환
                    ImageOptimizer.optimize_for_web(temp_path, SUB_MAX_SIZE)
                    temp_jpg = temp_path.with_suffix('.jpg')
                    if temp_jpg.exists() and temp_jpg != new_path:
                        shutil.move(str(temp_jpg), str(new_path))
                    elif temp_path.exists():
                        shutil.move(str(temp_path), str(new_path))
        
        elif self.image_type == 'model':
            model_folder = self.project_folder / "model_images"
            temp_files = []
            for i, img in enumerate(self.images):
                if img.exists():
                    temp_path = model_folder / f"_temp_model_{i}{img.suffix}"
                    shutil.move(str(img), str(temp_path))
                    temp_files.append(temp_path)
            
            for i, temp_path in enumerate(temp_files):
                new_path = model_folder / f"{i+1}.jpg"
                if temp_path.exists():
                    ImageOptimizer.optimize_for_web(temp_path, MODEL_MAX_SIZE)
                    temp_jpg = temp_path.with_suffix('.jpg')
                    if temp_jpg.exists() and temp_jpg != new_path:
                        shutil.move(str(temp_jpg), str(new_path))
                    elif temp_path.exists():
                        shutil.move(str(temp_path), str(new_path))
        
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
                new_path = slide_folder / f"{i+1}.jpg"
                if temp_path.exists():
                    ImageOptimizer.optimize_for_web(temp_path, SLIDE_MAX_SIZE)
                    temp_jpg = temp_path.with_suffix('.jpg')
                    if temp_jpg.exists() and temp_jpg != new_path:
                        shutil.move(str(temp_jpg), str(new_path))
                    elif temp_path.exists():
                        shutil.move(str(temp_path), str(new_path))


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
        self.transient(parent)
        self.grab_set()
        
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
        
        # === 탭 3: 레이아웃 설정 ===
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
        
        canvas_frame = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 캔버스 크기에 맞게 프레임 크기 조정
        def configure_scroll_region(event):
            canvas.itemconfig(canvas_frame, width=event.width - 20)
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
            ('title', '제목 (TITLE) *', '대문자로 입력'),
            ('slug', '슬러그 (폴더명)', '예: montana-hannam'),
            ('display_title', '표시 제목', '그리드 호버 시 표시'),
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
            if field == 'display_title' and not value:
                value = self.project.get('title', '')
            entry.insert(0, value)
            entry.pack(fill=tk.X, pady=(3, 0), ipady=8)
            self.entries[field] = entry
        
        # 설명
        desc_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        desc_frame.pack(fill=tk.X, padx=20, pady=8)
        tk.Label(desc_frame, text="설명 (DESCRIPTION)", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W)
        
        desc_text = scrolledtext.ScrolledText(desc_frame, height=4,
                                             font=ModernStyle.get_font(10),
                                             bg=ModernStyle.BG_WHITE,
                                             relief='solid', borderwidth=1)
        desc_text.insert(tk.END, self.project.get('description', ''))
        desc_text.pack(fill=tk.X, pady=(3, 0))
        self.entries['description'] = desc_text
        
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
    
    def create_image_tab(self, parent):
        """이미지 관리 탭"""
        # 스크롤 캔버스
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_frame = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_region(event):
            canvas.itemconfig(canvas_frame, width=event.width - 20)
        canvas.bind('<Configure>', configure_scroll_region)
        
        # 마우스 휠
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable.bind("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 프로젝트 폴더
        project_type = 'drawings' if self.mode == 'drawings' else 'projects'
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
        
        # 이미지 드롭존들
        self.drop_zones = []
        
        # 썸네일 이미지 (그리드용 정사각형)
        thumb_zone = DropZone(scrollable, 'thumb', 
                             '🖼️ 썸네일 이미지 (thumb.jpg) - 프로젝트 목록 그리드에 표시되는 정사각형 이미지',
                             project_folder, on_change=self._on_image_change)
        thumb_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(thumb_zone)
        
        # 메인 이미지 (상세페이지 첫 이미지)
        main_zone = DropZone(scrollable, 'main',
                            '📷 메인 이미지 (main.jpg) - 프로젝트 상세페이지 맨 위에 표시되는 대표 이미지',
                            project_folder, on_change=self._on_image_change)
        main_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(main_zone)
        
        # 서브 이미지
        sub_zone = DropZone(scrollable, 'sub', '📄 서브 이미지 (01.jpg, 02.jpg, ...) - 상세페이지 본문 이미지들',
                           project_folder, on_change=self._on_image_change)
        sub_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(sub_zone)
        
        # 모델 이미지
        model_zone = DropZone(scrollable, 'model', '🏗 모델 이미지 (model_images/) - 3열 그리드로 표시',
                             project_folder, on_change=self._on_image_change)
        model_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(model_zone)
        
        # 슬라이드 이미지
        slide_zone = DropZone(scrollable, 'slide', '📑 슬라이드 이미지 (slide_images/) - 하단 추가 이미지',
                             project_folder, on_change=self._on_image_change)
        slide_zone.pack(fill=tk.X, padx=20, pady=5)
        self.drop_zones.append(slide_zone)
        
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
    
    def _on_image_change(self):
        """이미지 변경 시"""
        pass
    
    def create_layout_tab(self, parent):
        """레이아웃 설정 탭"""
        # 스크롤 캔버스
        canvas = tk.Canvas(parent, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_frame = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_region(event):
            canvas.itemconfig(canvas_frame, width=event.width - 20)
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
        
        # 커버 비율
        row3 = tk.Frame(settings, bg=ModernStyle.BG_WHITE)
        row3.pack(fill=tk.X, pady=10)
        tk.Label(row3, text="커버 이미지 비율:", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        self.cover_ratio = tk.StringVar(value=self.project.get('cover_ratio', '16:10'))
        ttk.Combobox(row3, textvariable=self.cover_ratio,
                    values=['16:9', '16:10', '4:3', '3:2', '1:1'],
                    width=10, state='readonly').pack(side=tk.LEFT, padx=10)
    
    def save(self):
        """저장"""
        title = self.entries['title'].get().strip().upper()
        if not title:
            messagebox.showwarning("경고", "제목은 필수입니다.")
            return
        
        # display_title 처리: 비어있거나 이전 title과 같으면 새 title로 설정
        display_title = self.entries['display_title'].get().strip()
        old_title = self.project.get('title', '')
        if not display_title or display_title == old_title:
            display_title = title
        
        self.result = {
            'title': title,
            'slug': self.entries['slug'].get().strip() or title.lower().replace(' ', '-').replace('_', '-'),
            'display_title': display_title,
            'display_year': self.entries['display_year'].get().strip(),
            'location': self.entries['location'].get().strip(),
            'duration': self.entries['duration'].get().strip(),
            'program': self.entries['program'].get().strip(),
            'studio': self.entries['studio'].get().strip(),
            'description': self.entries['description'].get('1.0', tk.END).strip(),
            'visible': self.visible_var.get(),
            'model_cols': self.model_cols.get(),
            'show_slides': self.show_slides.get(),
            'cover_ratio': self.cover_ratio.get(),
        }
        
        if self.on_save:
            self.on_save(self.result)
        
        self.destroy()
    
    def preview(self):
        """미리보기"""
        project_type = 'drawings' if self.mode == 'drawings' else 'projects'
        html_path = DRAWINGS_HTML if self.mode == 'drawings' else PROJECTS_HTML
        webbrowser.open(f'file:///{html_path}')


class AboutEditorDialog(tk.Toplevel):
    """About 페이지 편집"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("About 페이지 편집")
        self.geometry("650x700")
        self.configure(bg=ModernStyle.BG_WHITE)
        self.transient(parent)
        self.grab_set()
        
        self.load_about_data()
        self.create_ui()
    
    def load_about_data(self):
        self.data = {'name': 'JEON HYERIN', 'tagline': '', 'bio': '', 'email': '', 'instagram': ''}
        try:
            with open(ABOUT_HTML, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 이름
            match = re.search(r'<h1 class="about-name">([^<]+)</h1>', content)
            if match: self.data['name'] = match.group(1)
            
            # 태그라인
            match = re.search(r'<p class="about-tagline">([^<]+)</p>', content)
            if match: self.data['tagline'] = match.group(1)
            
            # 소개글
            match = re.search(r'<div class="about-text">([\s\S]*?)</div>', content)
            if match:
                paragraphs = re.findall(r'<p>([^<]+)</p>', match.group(1))
                self.data['bio'] = '\n\n'.join(paragraphs)
            
            # 이메일 (mailto: 링크에서 추출)
            match = re.search(r'href="mailto:([^"]+)"', content)
            if match: self.data['email'] = match.group(1)
            
            # 인스타그램 (INSTAGRAM 라벨 뒤의 링크 텍스트)
            match = re.search(r'<span class="contact-label">INSTAGRAM</span>\s*<a[^>]*class="contact-value"[^>]*>([^<]+)</a>', content)
            if match: self.data['instagram'] = match.group(1).strip()
        except Exception as e:
            print(f"About 데이터 로드 오류: {e}")
    
    def create_ui(self):
        # 스크롤 캔버스
        canvas = tk.Canvas(self, bg=ModernStyle.BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=ModernStyle.BG_WHITE)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw", width=610)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.entries = {}
        
        # 헤더
        tk.Label(scrollable, text="About 페이지 편집", font=ModernStyle.get_font(16, 'bold'),
                bg=ModernStyle.BG_WHITE).pack(anchor=tk.W, padx=20, pady=20)
        
        # 필드들
        for key, label in [('name', '이름'), ('tagline', '태그라인'), ('email', '이메일'), ('instagram', '인스타그램')]:
            frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
            frame.pack(fill=tk.X, padx=20, pady=8)
            tk.Label(frame, text=label, font=ModernStyle.get_font(9),
                    bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W)
            entry = tk.Entry(frame, font=ModernStyle.get_font(10), relief='solid', borderwidth=1)
            entry.insert(0, self.data.get(key, ''))
            entry.pack(fill=tk.X, pady=(3, 0), ipady=8)
            self.entries[key] = entry
        
        # 소개글
        frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        frame.pack(fill=tk.X, padx=20, pady=8)
        tk.Label(frame, text="소개글 (BIO)", font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_SUBTLE).pack(anchor=tk.W)
        bio = scrolledtext.ScrolledText(frame, height=6, font=ModernStyle.get_font(10),
                                       relief='solid', borderwidth=1)
        bio.insert(tk.END, self.data.get('bio', ''))
        bio.pack(fill=tk.X, pady=(3, 0))
        self.entries['bio'] = bio
        
        # 버튼
        btn_frame = tk.Frame(scrollable, bg=ModernStyle.BG_WHITE)
        btn_frame.pack(fill=tk.X, padx=20, pady=30)
        
        tk.Button(btn_frame, text="💾 저장", font=ModernStyle.get_font(11, 'bold'),
                 bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE,
                 relief='flat', padx=25, pady=8, command=self.save).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="취소", font=ModernStyle.get_font(10),
                 bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                 padx=20, pady=8, command=self.destroy).pack(side=tk.LEFT)
    
    def save(self):
        try:
            with open(ABOUT_HTML, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 이름 업데이트
            content = re.sub(r'<h1 class="about-name">[^<]+</h1>',
                           f'<h1 class="about-name">{self.entries["name"].get()}</h1>', content)
            
            # 태그라인 업데이트
            content = re.sub(r'<p class="about-tagline">[^<]+</p>',
                           f'<p class="about-tagline">{self.entries["tagline"].get()}</p>', content)
            
            # 소개글 업데이트
            bio = self.entries['bio'].get('1.0', tk.END).strip()
            bio_html = '\n        '.join([f'<p>{p}</p>' for p in bio.split('\n\n') if p.strip()])
            content = re.sub(r'<div class="about-text">[\s\S]*?</div>',
                           f'<div class="about-text">\n        {bio_html}\n      </div>', content)
            
            # 이메일 업데이트 (class 속성 등을 고려한 패턴)
            email = self.entries['email'].get().strip()
            content = re.sub(
                r'(<a\s+href="mailto:)[^"]+("[^>]*class="contact-value"[^>]*>)[^<]+(</a>)',
                f'\\g<1>{email}\\g<2>{email}\\g<3>', 
                content
            )
            
            # 인스타그램 업데이트 (INSTAGRAM 라벨 뒤의 contact-value 링크)
            instagram = self.entries['instagram'].get().strip()
            content = re.sub(
                r'(<span class="contact-label">INSTAGRAM</span>\s*<a[^>]*class="contact-value"[^>]*>)[^<]+(</a>)',
                f'\\g<1>{instagram}\\g<2>',
                content
            )
            
            with open(ABOUT_HTML, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("저장 완료", "About 페이지가 저장되었습니다.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {str(e)}")


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
        
        # 우측 메뉴
        menu = tk.Frame(header, bg=ModernStyle.BG_WHITE)
        menu.pack(side=tk.RIGHT)
        
        for text, cmd in [("📝 About", self.edit_about), ("💾 백업", self.backup), ("🌐 사이트", self.open_site)]:
            tk.Button(menu, text=text, font=ModernStyle.get_font(9),
                     bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                     padx=12, pady=5, command=cmd).pack(side=tk.LEFT, padx=3)
        
        # 네비게이션
        nav = tk.Frame(main, bg=ModernStyle.BG_WHITE)
        nav.pack(fill=tk.X, padx=40, pady=(20, 0))
        
        self.nav_buttons = {}
        for mode in ['projects', 'drawings']:
            btn = tk.Button(nav, text=mode.upper(), font=ModernStyle.get_font(10),
                           bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY,
                           relief='flat', padx=15, pady=8,
                           command=lambda m=mode: self.switch_mode(m))
            btn.pack(side=tk.LEFT, padx=(0, 5))
            self.nav_buttons[mode] = btn
        
        self._update_nav_style()
        
        # 검색
        search_frame = tk.Frame(nav, bg=ModernStyle.BG_WHITE)
        search_frame.pack(side=tk.RIGHT)
        tk.Label(search_frame, text="🔍", font=ModernStyle.get_font(10),
                bg=ModernStyle.BG_WHITE).pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.search_var, width=20,
                font=ModernStyle.get_font(10), relief='solid', borderwidth=1).pack(side=tk.LEFT, padx=5, ipady=5)
        
        self.count_label = tk.Label(nav, text="", font=ModernStyle.get_font(9),
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
        
        for text, cmd in [("📁 폴더", self.open_folder), ("👁 미리보기", self.preview), ("🔄", self.load_data)]:
            tk.Button(right, text=text, font=ModernStyle.get_font(10),
                     bg=ModernStyle.BG_WHITE, relief='solid', borderwidth=1,
                     padx=12, pady=8, command=cmd).pack(side=tk.LEFT, padx=3)
        
        # 상태바
        status = tk.Frame(main, bg=ModernStyle.BG_LIGHT)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="준비됨")
        tk.Label(status, textvariable=self.status_var, font=ModernStyle.get_font(9),
                bg=ModernStyle.BG_LIGHT, fg=ModernStyle.TEXT_MUTED).pack(padx=20, pady=10, anchor=tk.W)
    
    def _update_nav_style(self):
        for mode, btn in self.nav_buttons.items():
            if mode == self.current_mode:
                btn.configure(bg=ModernStyle.ACCENT, fg=ModernStyle.BG_WHITE)
            else:
                btn.configure(bg=ModernStyle.BG_WHITE, fg=ModernStyle.TEXT_PRIMARY)
    
    def switch_mode(self, mode):
        self.current_mode = mode
        self.current_html = DRAWINGS_HTML if mode == 'drawings' else PROJECTS_HTML
        self._update_nav_style()
        self.search_var.set("")
        self.load_data()
    
    def extract_json(self, content):
        match = re.search(r'<script type="application/json" id="projectsData">\s*(\[[\s\S]*?\])\s*</script>', content)
        return json.loads(match.group(1)) if match else []
    
    def update_json(self, content, data):
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        return re.sub(r'(<script type="application/json" id="projectsData">)\s*\[[\s\S]*?\]\s*(</script>)',
                     f'\\1\n  {json_str}\n  \\2', content)
    
    def generate_grid(self, projects):
        items = []
        project_type = 'drawings' if self.current_mode == 'drawings' else 'projects'
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
        return re.sub(r'(<div class="archive-grid" role="list">)\s*\n[\s\S]*?(</div>\s*</main>)',
                     f'\\1\n\n{grid}\n\n    \\2', content)
    
    def load_data(self):
        try:
            with open(self.current_html, 'r', encoding='utf-8') as f:
                self.projects = self.extract_json(f.read())
            self.update_tree()
            self.count_label.config(text=f"{len(self.projects)} items")
            self.status_var.set(f"{len(self.projects)}개 {self.current_mode} 로드됨")
        except Exception as e:
            messagebox.showerror("오류", f"로드 실패: {e}")
    
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
        new = {'id': len(self.projects)+1, 'index': str(len(self.projects)+1).zfill(2),
               'title': 'NEW PROJECT', 'slug': 'new-project', 'visible': True}
        
        def on_save(result):
            result['id'] = len(self.projects) + 1
            result['index'] = str(len(self.projects) + 1).zfill(2)
            self.projects.append(result)
            
            project_type = 'drawings' if self.current_mode == 'drawings' else 'projects'
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
        self.save_data()
        self.load_data()
    
    def move_down(self):
        project, idx = self.get_selected()
        if not project or idx >= len(self.projects) - 1:
            return
        self.projects[idx], self.projects[idx+1] = self.projects[idx+1], self.projects[idx]
        self._reindex()
        self.save_data()
        self.load_data()
    
    def duplicate(self):
        project, idx = self.get_selected()
        if not project:
            return
        new = project.copy()
        new['title'] = project['title'] + " (복사)"
        new['slug'] = project['slug'] + "-copy"
        self.projects.insert(idx + 1, new)
        self._reindex()
        
        project_type = 'drawings' if self.current_mode == 'drawings' else 'projects'
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
        project_type = 'drawings' if self.current_mode == 'drawings' else 'projects'
        folder = IMAGES_DIR / project_type / project.get('slug', '')
        if folder.exists():
            os.startfile(str(folder))
        elif messagebox.askyesno("폴더 없음", "생성하시겠습니까?"):
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "model_images").mkdir(exist_ok=True)
            os.startfile(str(folder))
    
    def preview(self):
        webbrowser.open(f'file:///{self.current_html}')
    
    def edit_about(self):
        AboutEditorDialog(self.root)
    
    def open_site(self):
        webbrowser.open(f'file:///{SCRIPT_DIR / "index.html"}')
    
    def backup(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        BACKUP_DIR.mkdir(exist_ok=True)
        for html in [PROJECTS_HTML, DRAWINGS_HTML, ABOUT_HTML]:
            if html.exists():
                shutil.copy(html, BACKUP_DIR / f"{html.stem}_{ts}.html")
        messagebox.showinfo("백업 완료", f"백업됨: backups/{ts}")
    
    def apply_changes(self):
        """변경사항을 로컬 HTML 파일에 적용 (Git 푸시 없음)"""
        try:
            # 백업 먼저 생성
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            BACKUP_DIR.mkdir(exist_ok=True)
            
            if self.current_html.exists():
                shutil.copy(self.current_html, BACKUP_DIR / f"{self.current_html.stem}_{ts}_backup.html")
            
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
            
            # 원격 저장소 확인
            if not git.has_remote():
                result = messagebox.askyesno("GitHub 연결 필요", 
                    "⚠️ GitHub 원격 저장소가 연결되지 않았습니다.\n\n"
                    "로컬 저장은 완료되었습니다.\n\n"
                    "GitHub 연결 스크립트(setup_github.py)를\n"
                    "실행하시겠습니까?\n\n"
                    "💡 GitHub 저장소 URL이 필요합니다.\n"
                    "   예: https://github.com/username/repo.git")
                
                if result:
                    # setup_github.py 실행
                    import subprocess
                    subprocess.Popen(['python', str(SCRIPT_DIR / 'setup_github.py')], 
                                   creationflags=subprocess.CREATE_NEW_CONSOLE)
                
                self.status_var.set("✅ 로컬 저장 완료 (GitHub 연결 필요)")
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
            with open(self.current_html, 'r', encoding='utf-8') as f:
                content = f.read()
            content = self.update_json(content, self.projects)
            content = self.update_grid(content, self.projects)
            with open(self.current_html, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {e}")


def main():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        import subprocess
        subprocess.check_call(['pip', 'install', 'Pillow'])
    
    root = tk.Tk()
    PortfolioAdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
