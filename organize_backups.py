"""백업 파일을 날짜별 폴더로 정리"""
import os
import shutil
from pathlib import Path

# 스크립트 위치 기준으로 백업 폴더 찾기
script_dir = Path(__file__).parent
backup_dir = script_dir / 'backups'

if backup_dir.exists():
    organized = 0
    for file in backup_dir.glob('*.html'):
        name = file.stem
        parts = name.split('_')
        date_str = None
        for i, part in enumerate(parts):
            if part.isdigit() and len(part) == 8:
                date_str = part
                break
        
        if date_str:
            date_folder = backup_dir / date_str
            date_folder.mkdir(exist_ok=True)
            new_path = date_folder / file.name
            if not new_path.exists():
                shutil.move(str(file), str(new_path))
                organized += 1
                print(f'Moved: {file.name} -> {date_str}/')
    print(f'Total organized: {organized} files')
else:
    print('Backup folder not found')
