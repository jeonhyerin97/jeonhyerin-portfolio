"""기존 백업 파일을 시간별 폴더로 정리"""
import os
import shutil
from pathlib import Path
import re

script_dir = Path(__file__).parent
backup_dir = script_dir / 'backups'

if backup_dir.exists():
    organized = 0
    
    # 날짜별 폴더 순회
    for date_dir in backup_dir.iterdir():
        if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
            # 해당 날짜 폴더의 HTML 파일들 처리
            for file in list(date_dir.glob("*.html")):
                name = file.stem
                
                # 파일명에서 시간 추출 (예: projects_20260114_180815.html 또는 projects_20260114_180815_backup.html)
                # 패턴: 타입_YYYYMMDD_HHMMSS 또는 타입_YYYYMMDD_HHMMSS_backup
                match = re.search(r'_(\d{8})_(\d{6})', name)
                
                if match:
                    time_str = match.group(2)  # HHMMSS
                    
                    # 시간별 폴더 생성
                    time_folder = date_dir / time_str
                    time_folder.mkdir(exist_ok=True)
                    
                    # 원본 파일명 추출 (projects, drawings, about)
                    original_type = name.split('_')[0]
                    new_filename = f"{original_type}.html"
                    
                    new_path = time_folder / new_filename
                    
                    # 파일 이동 (이미 존재하면 스킵)
                    if not new_path.exists():
                        shutil.move(str(file), str(new_path))
                        organized += 1
                        print(f"Moved: {file.name} -> {date_dir.name}/{time_str}/{new_filename}")
                    else:
                        # 이미 존재하면 원본 파일 삭제
                        file.unlink()
                        print(f"Deleted duplicate: {file.name}")
    
    print(f"\nTotal organized: {organized} files")
else:
    print("Backup folder not found")
