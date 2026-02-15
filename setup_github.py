#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 원격 저장소 연결 스크립트
================================

사용법:
1. 이 파일을 실행합니다
2. GitHub 저장소 URL을 입력합니다
3. 자동으로 연결 및 첫 푸시가 진행됩니다

예시 URL: https://github.com/your-username/jeonhyerin-portfolio.git
"""

import subprocess
import os
from pathlib import Path

# Git 실행 파일 경로
GIT_PATH = r"C:\Program Files\Git\cmd\git.exe"

# 현재 스크립트 위치
SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

def run_git(*args, check=True):
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
    return result.returncode == 0, result.stdout, result.stderr

def main():
    print("="*60)
    print("  GitHub 원격 저장소 연결 스크립트")
    print("="*60)
    print()
    
    # Git 저장소 초기화 확인
    git_dir = SCRIPT_DIR / ".git"
    if not git_dir.exists():
        print("[0/5] Git 저장소 초기화 중...")
        success, _, _ = run_git("init")
        if success:
            print("✓ Git 저장소가 초기화되었습니다.")
        else:
            print("✗ Git 초기화 실패!")
            return
        
        # 첫 커밋 생성
        print("\n[0.5/5] 첫 커밋 생성 중...")
        run_git("add", "-A")
        run_git("commit", "-m", "Initial commit: JEONHYERIN Portfolio")
        print()
    
    # 현재 상태 확인
    print("[1/5] 현재 Git 상태 확인...")
    run_git("status", "--short")
    print()
    
    # 기존 원격 저장소 확인
    print("[2/5] 기존 원격 저장소 확인...")
    success, stdout, _ = run_git("remote", "-v")
    
    if stdout.strip():
        print("기존 원격 저장소가 있습니다.")
        confirm = input("기존 연결을 삭제하고 새로 연결하시겠습니까? (y/n): ")
        if confirm.lower() == 'y':
            run_git("remote", "remove", "origin")
            print("기존 연결 삭제됨")
        else:
            print("취소됨")
            return
    print()
    
    # GitHub URL 입력
    print("[3/5] GitHub 저장소 URL 입력")
    print("예시: https://github.com/your-username/jeonhyerin-portfolio.git")
    print()
    github_url = input("GitHub URL: ").strip()
    
    if not github_url:
        print("URL이 입력되지 않았습니다. 종료합니다.")
        return
    
    if not github_url.endswith('.git'):
        github_url += '.git'
    
    print()
    
    # 원격 저장소 연결
    print("[4/5] 원격 저장소 연결 중...")
    success, _, _ = run_git("remote", "add", "origin", github_url)
    if not success:
        print("원격 저장소 연결 실패!")
        return
    
    run_git("remote", "-v")
    print()
    
    # 첫 푸시
    print("[5/5] GitHub에 첫 푸시 중...")
    print("(GitHub 로그인 창이 뜨면 인증을 진행하세요)")
    print()
    
    # 브랜치 이름을 main으로 변경 (GitHub 기본값)
    run_git("branch", "-M", "main")
    
    # 푸시
    success, _, stderr = run_git("push", "-u", "origin", "main")
    
    print()
    print("="*60)
    if success or "Everything up-to-date" in stderr:
        print("  [SUCCESS] GitHub 연결 및 푸시 완료!")
        print("="*60)
        print()
        print("다음 단계:")
        print("1. https://app.netlify.com 접속")
        print("2. 'Add new site' > 'Import an existing project' 클릭")
        print("3. 'Deploy with GitHub' 선택")
        print("4. 방금 연결한 저장소 선택")
        print("5. 'Deploy site' 클릭")
        print()
        print("Netlify 설정 완료 후:")
        print("- 관리자 모드에서 [저장+배포] 버튼만 클릭하면")
        print("- 자동으로 jeonhyerin.com에 반영됩니다!")
    else:
        print("  [FAILED] 푸시 실패")
        print("="*60)
        print()
        print("문제 해결:")
        print("1. GitHub URL이 올바른지 확인하세요")
        print("2. GitHub 인증이 필요할 수 있습니다")
        print("3. 저장소가 비어있는지 확인하세요 (README 없이 생성)")

if __name__ == "__main__":
    main()
    input("\n아무 키나 누르면 종료됩니다...")
