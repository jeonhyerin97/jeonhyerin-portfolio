#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 초기화 및 GitHub 푸시 스크립트
"""

import subprocess
import os
import sys
from pathlib import Path

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 설정
GITHUB_URL = "https://github.com/jeonhyerin97/jeonhyerin-portfolio"
GIT_PATH = r"C:\Program Files\Git\cmd\git.exe"
SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

def run_git(*args):
    """Git 명령 실행"""
    result = subprocess.run(
        [GIT_PATH] + list(args),
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print(f"$ git {' '.join(args)}")
    if result.stdout.strip():
        print(result.stdout)
    if result.stderr.strip():
        print(result.stderr)
    return result.returncode == 0

def main():
    print("=" * 60)
    print("  Git Init and GitHub Push")
    print("=" * 60)
    print(f"\nGitHub URL: {GITHUB_URL}")
    print(f"Working Dir: {SCRIPT_DIR}\n")
    
    # 1. Git 저장소 확인/초기화
    git_dir = SCRIPT_DIR / ".git"
    if not git_dir.exists():
        print("[1/5] Initializing Git repository...")
        if not run_git("init"):
            print("[FAIL] Git init failed!")
            return False
        print("[OK] Git repository initialized\n")
    else:
        print("[1/5] Git repository already exists [OK]\n")
    
    # 2. 모든 파일 스테이징
    print("[2/5] Staging files...")
    run_git("add", "-A")
    print()
    
    # 3. 커밋
    print("[3/5] Creating commit...")
    run_git("commit", "-m", "Initial commit: JEONHYERIN Portfolio")
    print()
    
    # 4. 원격 저장소 연결
    print("[4/5] Connecting to GitHub...")
    run_git("remote", "remove", "origin")
    run_git("remote", "add", "origin", GITHUB_URL)
    run_git("branch", "-M", "main")
    print()
    
    # 5. 푸시
    print("[5/5] Pushing to GitHub...")
    print("(If login window appears, please authenticate)\n")
    
    if run_git("push", "-u", "origin", "main"):
        print("\n" + "=" * 60)
        print("  [SUCCESS] Pushed to GitHub!")
        print("=" * 60)
        print(f"\nRepository: {GITHUB_URL}")
        print("\nNext steps:")
        print("1. Connect this repository in Netlify")
        print("2. After that, just click 'Save+Deploy' in admin_gui.py")
        print("   to automatically update JEONHYERIN.com!")
        return True
    else:
        print("\n" + "=" * 60)
        print("  [FAIL] Push failed")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Check if you are logged in to GitHub")
        print("2. Check repository permissions")
        print("3. Check internet connection")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
