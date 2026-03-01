#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
홈 디자인 에디터 Pro v2.1
python home_editor_server.py
"""

import http.server
import ipaddress
import socket
import socketserver
import json
import shutil
import webbrowser
from urllib.parse import urlparse
import base64
import os
import sys
from pathlib import Path
from datetime import datetime
import threading
import time

PORT = 8765
DIR = Path(__file__).parent
INDEX = DIR / "index.html"
CSS = DIR / "styles.css"
IMAGES = DIR / "images" / "home"
BACKUP = DIR / "editor_backups"
BACKUP.mkdir(exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)


def _is_valid_lan_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.version == 4 and not (
        addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_unspecified
    )


def _get_lan_ip() -> str:
    candidates = []
    seen = set()

    def add(ip: str, priority: int):
        if not ip:
            return
        ip = str(ip).strip()
        if not _is_valid_lan_ip(ip) or ip in seen:
            return
        seen.add(ip)
        try:
            addr = ipaddress.ip_address(ip)
            weight = priority if addr.is_private else priority + 50
        except ValueError:
            weight = priority + 100
        candidates.append((weight, ip))

    for probe in ("8.8.8.8", "1.1.1.1", "192.168.0.1", "10.0.0.1"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((probe, 80))
                add(sock.getsockname()[0], 10)
        except Exception:
            pass

    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            add(ip, 30)
    except Exception:
        pass

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1] if candidates else "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(DIR), **k)
    
    def do_GET(self):
        req_path = urlparse(self.path).path
        if req_path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(EDITOR_HTML.encode())
        elif req_path == '/api/load':
            css = CSS.read_text('utf-8') if CSS.exists() else ''
            html = INDEX.read_text('utf-8') if INDEX.exists() else ''
            self.json({'css': css, 'html': html})
        elif req_path == '/api/images':
            imgs = []
            if IMAGES.exists():
                for f in IMAGES.iterdir():
                    if f.suffix.lower() in ['.png','.jpg','.jpeg','.webp','.gif']:
                        imgs.append(f.name)
            self.json({'images': imgs})
        else:
            super().do_GET()
    
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length)
        
        if self.path == '/api/save':
            d = json.loads(data.decode())
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            bk = BACKUP / ts
            bk.mkdir(exist_ok=True)
            if INDEX.exists(): shutil.copy(INDEX, bk/'index.html')
            if CSS.exists(): shutil.copy(CSS, bk/'styles.css')
            if 'css' in d: CSS.write_text(d['css'], 'utf-8')
            if 'html' in d: INDEX.write_text(d['html'], 'utf-8')
            self.json({'ok': True})
        
        elif self.path == '/api/upload':
            d = json.loads(data.decode())
            name = d.get('name', 'image.png')
            imgdata = d.get('data', '')
            if imgdata.startswith('data:'):
                imgdata = imgdata.split(',')[1]
            imgbytes = base64.b64decode(imgdata)
            filepath = IMAGES / name
            filepath.write_bytes(imgbytes)
            self.json({'ok': True, 'path': f'images/home/{name}'})
        
        elif self.path == '/api/reset':
            bks = sorted([x for x in BACKUP.iterdir() if x.is_dir()], reverse=True)
            if bks:
                b = bks[0]
                if (b/'index.html').exists(): shutil.copy(b/'index.html', INDEX)
                if (b/'styles.css').exists(): shutil.copy(b/'styles.css', CSS)
                self.json({'ok': True})
            else:
                self.json({'ok': False, 'error': '백업 없음'})
        else:
            self.json({'ok': False})
    
    def json(self, d):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(d).encode())
    
    def log_message(self, *a): pass


EDITOR_HTML = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>홈 디자인 에디터 Pro</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e0e0e0;overflow:hidden}

/* 상단바 */
.toolbar{
  position:fixed;top:0;left:0;right:0;height:56px;
  background:linear-gradient(180deg,#1a1a1a 0%,#141414 100%);
  border-bottom:1px solid #2a2a2a;
  display:flex;align-items:center;padding:0 20px;gap:8px;z-index:100;
}
.logo{font-size:16px;font-weight:700;margin-right:32px;display:flex;align-items:center;gap:10px}
.logo-icon{width:28px;height:28px;background:linear-gradient(135deg,#8b5cf6,#6366f1);border-radius:8px}
.toolbar-group{display:flex;gap:4px;padding:0 12px;border-right:1px solid #2a2a2a;flex-shrink:0}
.toolbar-group:last-child{border-right:none}
.btn{
  padding:8px 14px;background:#1f1f1f;border:1px solid #333;border-radius:8px;
  color:#999;font-size:12px;font-weight:500;cursor:pointer;transition:.15s;
  display:flex;align-items:center;gap:6px;white-space:nowrap;flex-shrink:0;
}
.btn:hover{background:#2a2a2a;color:#fff;border-color:#444}
.btn.primary{background:linear-gradient(135deg,#8b5cf6,#6366f1);border:none;color:#fff}
.btn.primary:hover{opacity:.9}
.btn-icon{font-size:14px}
.spacer{flex:1}

/* 메인 레이아웃 */
.main{display:flex;height:calc(100vh - 56px);margin-top:56px}

/* 좌측 도구 패널 */
.tools-panel{
  width:60px;background:#141414;border-right:1px solid #2a2a2a;
  display:flex;flex-direction:column;align-items:center;padding:12px 0;gap:8px;
  flex-shrink:0;
}
.tool-btn{
  width:44px;height:44px;background:transparent;border:none;border-radius:10px;
  color:#666;font-size:18px;cursor:pointer;transition:.15s;
  display:flex;align-items:center;justify-content:center;
}
.tool-btn:hover{background:#1f1f1f;color:#aaa}
.tool-btn.active{background:#2a2a2a;color:#8b5cf6}
.tool-divider{width:32px;height:1px;background:#2a2a2a;margin:8px 0}

/* 캔버스 영역 */
.canvas-area{
  flex:1;background:#1a1a1a;position:relative;
  overflow:auto;
}
.canvas-scroll{
  width:max-content;min-width:100%;
  padding:40px;
  display:flex;justify-content:center;align-items:flex-start;
}
.canvas-wrap{
  position:relative;transform-origin:top center;
  flex-shrink:0;
}
/* 캔버스 프레임 - 오른쪽 흰색 선 완전 제거 */
.canvas-frame{
  background:#000;
  box-shadow:0 20px 80px rgba(0,0,0,.6);
  position:relative;
  overflow:hidden;
}
.canvas-frame iframe{
  display:block;
  border:none;
  width:100%;
  height:100%;
  overflow:hidden;
}

/* 우측 속성 패널 */
.props-panel{
  width:300px;background:#141414;border-left:1px solid #2a2a2a;
  display:flex;flex-direction:column;overflow:hidden;flex-shrink:0;
}
.props-header{
  padding:16px 20px;background:#1a1a1a;border-bottom:1px solid #2a2a2a;
  font-size:13px;font-weight:600;
}
.props-content{flex:1;overflow-y:auto;padding:16px}
.props-section{margin-bottom:24px}
.props-title{
  font-size:11px;font-weight:600;color:#666;text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:12px;display:flex;align-items:center;gap:8px;
}
.props-title-icon{font-size:14px}

/* 섹션 크기 조절 */
.size-control{
  background:#1a1a1a;border-radius:12px;padding:16px;margin-bottom:12px;
}
.size-label{font-size:12px;color:#888;margin-bottom:8px;display:flex;justify-content:space-between}
.size-value{color:#8b5cf6;font-weight:600}
.size-slider{
  width:100%;-webkit-appearance:none;height:8px;
  background:#2a2a2a;border-radius:4px;outline:none;
}
.size-slider::-webkit-slider-thumb{
  -webkit-appearance:none;width:20px;height:20px;
  background:linear-gradient(135deg,#8b5cf6,#6366f1);
  border-radius:50%;cursor:pointer;box-shadow:0 2px 8px rgba(139,92,246,.4);
}
.size-btns{display:flex;gap:8px;margin-top:12px}
.size-btn{
  flex:1;padding:8px;background:#2a2a2a;border:none;border-radius:8px;
  color:#aaa;font-size:11px;cursor:pointer;transition:.15s;
}
.size-btn:hover{background:#333;color:#fff}

/* 이미지 관리 */
.image-upload{
  background:#1a1a1a;border:2px dashed #333;border-radius:12px;
  padding:24px;text-align:center;cursor:pointer;transition:.2s;
}
.image-upload:hover{border-color:#8b5cf6;background:#1f1a2e}
.image-upload-icon{font-size:32px;margin-bottom:8px}
.image-upload-text{font-size:12px;color:#888}
.image-list{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:12px}
.image-item{
  aspect-ratio:1;background:#1a1a1a;border-radius:8px;overflow:hidden;
  cursor:pointer;border:2px solid transparent;transition:.15s;position:relative;
}
.image-item:hover{border-color:#8b5cf6}
.image-item img{width:100%;height:100%;object-fit:cover}
.image-item-name{
  position:absolute;bottom:0;left:0;right:0;padding:4px;
  background:rgba(0,0,0,.8);font-size:9px;color:#aaa;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}

/* 색상 */
.color-row{display:flex;gap:12px;margin-bottom:12px}
.color-item{flex:1}
.color-label{font-size:11px;color:#666;margin-bottom:6px}
.color-picker{
  width:100%;height:40px;border:none;border-radius:8px;cursor:pointer;
  background:#1a1a1a;padding:4px;
}
.color-picker::-webkit-color-swatch-wrapper{padding:0}
.color-picker::-webkit-color-swatch{border:none;border-radius:6px}

/* 하단바 */
.bottom-bar{
  position:fixed;bottom:0;left:60px;right:300px;height:40px;
  background:#141414;border-top:1px solid #2a2a2a;
  display:flex;align-items:center;justify-content:center;gap:16px;
  z-index:50;
}
.zoom-btn{
  width:28px;height:28px;background:#1f1f1f;border:1px solid #333;
  border-radius:6px;color:#888;font-size:14px;cursor:pointer;
}
.zoom-btn:hover{background:#2a2a2a;color:#fff}
.zoom-val{font-size:12px;color:#666;min-width:50px;text-align:center}
.status{margin-left:24px;font-size:11px;color:#555}

/* 토스트 */
.toast{
  position:fixed;bottom:60px;left:50%;transform:translateX(-50%) translateY(20px);
  background:#1f1f1f;border:1px solid #333;padding:14px 28px;border-radius:12px;
  font-size:13px;opacity:0;transition:.2s;z-index:200;
  display:flex;align-items:center;gap:10px;
}
.toast.show{transform:translateX(-50%) translateY(0);opacity:1}
.toast.ok{border-color:#10b981;background:#064e3b}
.toast.err{border-color:#ef4444;background:#7f1d1d}
.toast-icon{font-size:16px}

/* 모달 */
.modal-bg{
  position:fixed;inset:0;background:rgba(0,0,0,.85);
  display:none;align-items:center;justify-content:center;z-index:300;
}
.modal-bg.show{display:flex}
.modal{
  background:#1a1a1a;border-radius:16px;width:90%;max-width:1200px;
  max-height:90vh;overflow:hidden;border:1px solid #2a2a2a;
}
.modal-header{
  padding:20px 24px;background:#1f1f1f;border-bottom:1px solid #2a2a2a;
  display:flex;justify-content:space-between;align-items:center;
}
.modal-title{font-size:16px;font-weight:600}
.modal-close{
  width:36px;height:36px;background:transparent;border:none;
  color:#666;font-size:24px;cursor:pointer;border-radius:8px;
}
.modal-close:hover{background:#2a2a2a;color:#fff}
.modal-body{
  padding:20px 24px 24px;
  max-height:calc(90vh - 140px);
  overflow:hidden;
  display:flex;
  flex-direction:column;
  gap:14px;
}
.preview-controls{
  display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
}
.preview-device-group{
  display:inline-flex;align-items:center;gap:6px;
  background:#131313;border:1px solid #2a2a2a;border-radius:10px;padding:4px;
}
.preview-device-btn{
  padding:7px 12px;background:transparent;border:none;border-radius:8px;
  color:#8f8f8f;font-size:12px;font-weight:600;cursor:pointer;transition:.15s;
}
.preview-device-btn:hover{background:#222;color:#f0f0f0}
.preview-device-btn.active{background:#2a2a2a;color:#fff}
.preview-device-btn:disabled{
  cursor:not-allowed;opacity:.4;background:transparent !important;color:#666 !important;
}
.preview-meta{
  font-size:11px;color:#777;min-width:150px;text-align:right;
}
.preview-stage{
  height:70vh;min-height:340px;
  border:1px solid #2a2a2a;border-radius:12px;background:#101010;
  display:flex;align-items:center;justify-content:center;
  overflow:auto;padding:16px;
}
.preview-scaler{position:relative;flex:0 0 auto}
.preview-viewport{
  width:100%;height:100%;overflow:hidden;
  border:1px solid #2a2a2a;border-radius:10px;background:#fff;
  box-shadow:0 16px 40px rgba(0,0,0,.45);
  transform-origin:top left;
}
.preview-viewport.mobile,
.preview-viewport.tablet{
  border-radius:30px;
  border-color:#444;
  background:#000;
}
.preview-viewport.mobile iframe,
.preview-viewport.tablet iframe{
  border-radius:24px;
}
.preview-viewport iframe{
  display:block;width:100%;height:100%;border:none;background:#fff;
}
.modal-footer{
  padding:16px 24px;background:#1f1f1f;border-top:1px solid #2a2a2a;
  display:flex;justify-content:flex-end;gap:12px;
}

/* 스크롤바 */
::-webkit-scrollbar{width:12px;height:12px}
::-webkit-scrollbar-track{background:#1a1a1a}
::-webkit-scrollbar-thumb{background:#333;border-radius:6px;border:3px solid #1a1a1a}
::-webkit-scrollbar-thumb:hover{background:#444}
::-webkit-scrollbar-corner{background:#1a1a1a}
</style>
</head>
<body>

<!-- 상단 툴바 -->
<div class="toolbar">
  <div class="logo">
    <div class="logo-icon"></div>
    홈 디자인 에디터
  </div>
  
  <div class="toolbar-group">
    <button class="btn" onclick="undo()"><span class="btn-icon">↶</span> 되돌리기</button>
    <button class="btn" onclick="redo()"><span class="btn-icon">↷</span> 다시</button>
  </div>
  
  <div class="toolbar-group">
    <button class="btn" onclick="resetPage()"><span class="btn-icon">🔄</span> 초기화</button>
  </div>
  
  <div class="spacer"></div>
  
  <div class="toolbar-group" style="border:none">
    <button class="btn" onclick="openPreview('desktop')"><span class="btn-icon">👁</span> 미리보기</button>
    <button class="btn" onclick="openPreview('mobile')"><span class="btn-icon">📱</span> 모바일 미리보기</button>
    <button class="btn primary" onclick="savePage()"><span class="btn-icon">💾</span> 저장하기</button>
  </div>
</div>

<!-- 메인 -->
<div class="main">
  <!-- 좌측 도구 -->
  <div class="tools-panel">
    <button class="tool-btn active" id="toolSelect" onclick="setTool('select')" title="선택 (V)">↖</button>
    <button class="tool-btn" id="toolHand" onclick="setTool('hand')" title="손 도구 (H)">✋</button>
    <div class="tool-divider"></div>
    <button class="tool-btn" id="toolImage" onclick="triggerImageUpload()" title="이미지 추가">🖼</button>
  </div>

  <!-- 캔버스 -->
  <div class="canvas-area" id="canvasArea">
    <div class="canvas-scroll" id="canvasScroll">
      <div class="canvas-wrap" id="canvasWrap">
        <div class="canvas-frame" id="canvasFrame">
          <iframe id="pageFrame" src="index.html" scrolling="no"></iframe>
        </div>
      </div>
    </div>
  </div>

  <!-- 우측 속성 패널 -->
  <div class="props-panel">
    <div class="props-header">📐 디자인 설정</div>
    <div class="props-content">
      
      <!-- 검정 배경 (헤더) 크기 -->
      <div class="props-section">
        <div class="props-title"><span class="props-title-icon">⬛</span> 검정 배경 크기</div>
        <div class="size-control">
          <div class="size-label">
            높이 <span class="size-value" id="headerSizeVal">150vh</span>
          </div>
          <input type="range" class="size-slider" id="headerSlider" min="50" max="300" value="150" oninput="setHeaderSize(this.value)">
          <div class="size-btns">
            <button class="size-btn" onclick="setHeaderSize(80)">작게</button>
            <button class="size-btn" onclick="setHeaderSize(150)">기본</button>
            <button class="size-btn" onclick="setHeaderSize(200)">크게</button>
          </div>
        </div>
      </div>

      <!-- 흰색 배경 (콘텐츠) -->
      <div class="props-section">
        <div class="props-title"><span class="props-title-icon">⬜</span> 흰색 배경 크기</div>
        <div class="size-control">
          <div class="size-label">
            최소 높이 <span class="size-value" id="contentSizeVal">400px</span>
          </div>
          <input type="range" class="size-slider" id="contentSlider" min="200" max="1500" value="400" oninput="setContentSize(this.value)">
          <div class="size-btns">
            <button class="size-btn" onclick="setContentSize(300)">작게</button>
            <button class="size-btn" onclick="setContentSize(600)">기본</button>
            <button class="size-btn" onclick="setContentSize(1000)">크게</button>
          </div>
        </div>
      </div>

      <!-- 색상 -->
      <div class="props-section">
        <div class="props-title"><span class="props-title-icon">🎨</span> 배경 색상</div>
        <div class="color-row">
          <div class="color-item">
            <div class="color-label">상단 배경</div>
            <input type="color" class="color-picker" id="headerColor" value="#000000" onchange="updateEditorStyles()">
          </div>
          <div class="color-item">
            <div class="color-label">하단 배경</div>
            <input type="color" class="color-picker" id="contentColor" value="#ffffff" onchange="updateEditorStyles()">
          </div>
        </div>
      </div>

      <!-- 이미지 관리 -->
      <div class="props-section">
        <div class="props-title"><span class="props-title-icon">🖼</span> 히어로 이미지</div>
        <div class="image-upload" onclick="triggerImageUpload()">
          <div class="image-upload-icon">📤</div>
          <div class="image-upload-text">클릭하여 이미지 업로드<br><small>또는 드래그 앤 드롭</small></div>
        </div>
        <input type="file" id="imageInput" accept="image/*" style="display:none" onchange="uploadImage(this)">
        <div class="image-list" id="imageList"></div>
      </div>

      <!-- 이미지 속성 -->
      <div class="props-section">
        <div class="props-title"><span class="props-title-icon">📷</span> 이미지 속성</div>
        <div class="size-control">
          <div class="size-label">투명도 <span class="size-value" id="imgOpacityVal">100%</span></div>
          <input type="range" class="size-slider" id="imgOpacitySlider" min="0" max="100" value="100" oninput="setImageOpacity(this.value)">
        </div>
      </div>

    </div>
  </div>
</div>

<!-- 하단바 -->
<div class="bottom-bar">
  <button class="zoom-btn" onclick="zoomOut()">−</button>
  <span class="zoom-val" id="zoomVal">100%</span>
  <button class="zoom-btn" onclick="zoomIn()">+</button>
  <button class="zoom-btn" onclick="zoomFit()">⤢</button>
  <span class="status" id="status">준비됨</span>
</div>

<!-- 미리보기 모달 -->
<div class="modal-bg" id="previewModal">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">👁 미리보기</span>
      <button class="modal-close" onclick="closePreview()">×</button>
    </div>
    <div class="modal-body">
      <div class="preview-controls">
        <div class="preview-device-group">
          <button class="preview-device-btn active" id="previewDesktopBtn" onclick="setPreviewMode('desktop')">Desktop</button>
          <button class="preview-device-btn" id="previewTabletBtn" onclick="setPreviewMode('tablet')">Tablet</button>
          <button class="preview-device-btn" id="previewMobileBtn" onclick="setPreviewMode('mobile')">Mobile</button>
          <button class="preview-device-btn" id="previewRotateBtn" onclick="togglePreviewOrientation()" disabled>Rotate</button>
        </div>
        <div class="preview-meta" id="previewMeta">Desktop · 1440×900</div>
      </div>
      <div class="preview-stage" id="previewStage">
        <div class="preview-scaler" id="previewScaler">
          <div class="preview-viewport desktop" id="previewViewport">
            <iframe id="previewFrame"></iframe>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closePreview()">닫기</button>
      <button class="btn primary" onclick="savePage();closePreview()">저장하기</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// State
let doc = null;
let css = '';
let zoom = 1;
let tool = 'select';
let hist = [];
let histIdx = -1;
let changed = false;
const CANVAS_WIDTH = 1440;
let previewMode = 'desktop';
let previewOrientation = 'portrait';
const PREVIEW_SIZES = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 834, height: 1194 },
  mobile: { width: 390, height: 844 }
};

// Panning state
let isPanning = false;
let panStart = { x: 0, y: 0 };
let scrollStart = { x: 0, y: 0 };

// Init
async function init() {
  const res = await fetch('/api/load');
  const data = await res.json();
  css = data.css || '';
  
  const frame = document.getElementById('pageFrame');
  
  frame.onload = () => {
    doc = frame.contentDocument;
    doc.body.classList.add('loaded');
    
    // iframe 내부 스크롤바 제거
    const iframeStyle = doc.createElement('style');
    iframeStyle.textContent = `
      html, body {
        overflow: hidden !important;
        scrollbar-width: none !important;
      }
      ::-webkit-scrollbar {
        display: none !important;
        width: 0 !important;
      }
    `;
    doc.head.appendChild(iframeStyle);
    
    // 페이지 전체 높이 계산 후 프레임 크기 설정
    setTimeout(() => {
      updateFrameSize();
      readCurrentStyles();
      loadImages();
      saveState();
      zoomFit();
      setStatus('로드 완료');
      const previewParam = new URLSearchParams(window.location.search).get('preview');
      if (previewParam === 'mobile' || previewParam === 'tablet' || previewParam === 'desktop') {
        openPreview(previewParam);
      }
    }, 500);
  };
  
  setupScrollEvents();
}

// 프레임 크기 업데이트 - 전체 페이지가 보이도록
function updateFrameSize() {
  if (!doc) return;
  
  // 헤더 높이 (vh를 px로 변환)
  const headerVh = parseInt(document.getElementById('headerSlider').value) || 150;
  const viewportHeight = window.innerHeight;
  const headerPx = (headerVh / 100) * viewportHeight;
  
  // 콘텐츠 높이
  const content = doc.querySelector('.split-content');
  let contentHeight = 600;
  if (content) {
    contentHeight = Math.max(content.scrollHeight, content.offsetHeight, 600);
  }
  
  // 전체 높이 = 헤더 + 콘텐츠 + 여유
  const totalHeight = headerPx + contentHeight + 200;
  
  // 실제 문서 높이와 비교해서 더 큰 값 사용
  const docHeight = Math.max(
    doc.body.scrollHeight,
    doc.documentElement.scrollHeight,
    doc.body.offsetHeight,
    doc.documentElement.offsetHeight
  );
  
  const finalHeight = Math.max(totalHeight, docHeight, 3000);
  
  document.getElementById('canvasFrame').style.width = CANVAS_WIDTH + 'px';
  document.getElementById('canvasFrame').style.height = finalHeight + 'px';
  
  console.log('Frame size:', CANVAS_WIDTH, 'x', finalHeight);
}

// 스크롤 이벤트 설정
function setupScrollEvents() {
  const area = document.getElementById('canvasArea');
  
  // Ctrl + 휠 = 줌
  area.addEventListener('wheel', (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      if (e.deltaY < 0) zoomIn();
      else zoomOut();
    }
  }, { passive: false });
  
  // 손 도구 드래그
  area.addEventListener('mousedown', (e) => {
    if (tool === 'hand' || e.button === 1) {
      e.preventDefault();
      isPanning = true;
      panStart = { x: e.clientX, y: e.clientY };
      scrollStart = { x: area.scrollLeft, y: area.scrollTop };
      area.style.cursor = 'grabbing';
    }
  });
  
  document.addEventListener('mousemove', (e) => {
    if (isPanning) {
      const dx = e.clientX - panStart.x;
      const dy = e.clientY - panStart.y;
      area.scrollLeft = scrollStart.x - dx;
      area.scrollTop = scrollStart.y - dy;
    }
  });
  
  document.addEventListener('mouseup', () => {
    if (isPanning) {
      isPanning = false;
      document.getElementById('canvasArea').style.cursor = tool === 'hand' ? 'grab' : 'default';
    }
  });
}

// Read current CSS values
function readCurrentStyles() {
  if (!doc) return;
  
  // CSS에서 split-header min-height 읽기
  const match = css.match(/\\.split-header\\s*\\{[^}]*min-height:\\s*(\\d+)vh/);
  if (match) {
    const val = parseInt(match[1]);
    document.getElementById('headerSlider').value = val;
    document.getElementById('headerSizeVal').textContent = val + 'vh';
  }
  
  // 이미지 투명도
  const heroImg = doc.querySelector('.split-hero-img');
  if (heroImg) {
    const cs = doc.defaultView.getComputedStyle(heroImg);
    const opacity = parseFloat(cs.opacity) * 100;
    document.getElementById('imgOpacitySlider').value = opacity;
    document.getElementById('imgOpacityVal').textContent = Math.round(opacity) + '%';
  }
}

// Set header (black section) size
function setHeaderSize(val) {
  document.getElementById('headerSlider').value = val;
  document.getElementById('headerSizeVal').textContent = val + 'vh';
  updateEditorStyles();
  changed = true;
  setTimeout(updateFrameSize, 100);
}

// Set content (white section) size
function setContentSize(val) {
  document.getElementById('contentSlider').value = val;
  document.getElementById('contentSizeVal').textContent = val + 'px';
  updateEditorStyles();
  changed = true;
  setTimeout(updateFrameSize, 100);
}

// Set image opacity
function setImageOpacity(val) {
  document.getElementById('imgOpacitySlider').value = val;
  document.getElementById('imgOpacityVal').textContent = val + '%';
  updateEditorStyles();
  changed = true;
}

// Update editor styles in iframe
function updateEditorStyles() {
  if (!doc) return;
  
  let styleEl = doc.getElementById('editor-styles');
  if (!styleEl) {
    styleEl = doc.createElement('style');
    styleEl.id = 'editor-styles';
    doc.head.appendChild(styleEl);
  }
  
  const headerHeight = document.getElementById('headerSlider').value;
  const contentHeight = document.getElementById('contentSlider').value;
  const headerColor = document.getElementById('headerColor').value;
  const contentColor = document.getElementById('contentColor').value;
  const imgOpacity = document.getElementById('imgOpacitySlider').value;
  
  styleEl.textContent = `
    .split-header {
      min-height: ${headerHeight}vh !important;
      background: ${headerColor} !important;
    }
    .split-content {
      min-height: ${contentHeight}px !important;
      background: ${contentColor} !important;
    }
    .split-hero-img {
      opacity: ${imgOpacity / 100} !important;
    }
  `;
  
  changed = true;
}

// Image functions
function triggerImageUpload() {
  document.getElementById('imageInput').click();
}

async function uploadImage(input) {
  const file = input.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = async (e) => {
    const data = e.target.result;
    const name = 'hero_' + Date.now() + '.' + file.name.split('.').pop();
    
    const res = await fetch('/api/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, data })
    });
    
    const result = await res.json();
    if (result.ok) {
      toast('이미지 업로드 완료', 'ok');
      loadImages();
      setHeroImage(result.path);
    }
  };
  reader.readAsDataURL(file);
  input.value = '';
}

async function loadImages() {
  const res = await fetch('/api/images');
  const data = await res.json();
  
  const list = document.getElementById('imageList');
  list.innerHTML = '';
  
  data.images.forEach(name => {
    const item = document.createElement('div');
    item.className = 'image-item';
    item.innerHTML = `<img src="images/home/${name}" alt="${name}"><div class="image-item-name">${name}</div>`;
    item.onclick = () => setHeroImage('images/home/' + name);
    list.appendChild(item);
  });
}

function setHeroImage(path) {
  if (!doc) return;
  
  const img = doc.querySelector('.split-hero-img');
  if (img) {
    img.src = path;
    img.onerror = null;
    changed = true;
    saveState();
    toast('히어로 이미지 변경됨', 'ok');
  }
}

// History
function saveState() {
  if (!doc) return;
  const html = '<!DOCTYPE html>\\n' + doc.documentElement.outerHTML;
  hist = hist.slice(0, histIdx + 1);
  hist.push({ html, css });
  histIdx = hist.length - 1;
  if (hist.length > 30) { hist.shift(); histIdx--; }
}

function undo() {
  if (histIdx > 0) {
    histIdx--;
    applyState(hist[histIdx]);
    toast('되돌림');
  }
}

function redo() {
  if (histIdx < hist.length - 1) {
    histIdx++;
    applyState(hist[histIdx]);
    toast('다시 적용');
  }
}

function applyState(state) {
  css = state.css;
  doc.open();
  doc.write(state.html);
  doc.close();
  setTimeout(() => {
    doc.body.classList.add('loaded');
    readCurrentStyles();
    updateFrameSize();
  }, 100);
}

// Save
async function savePage() {
  try {
    setStatus('저장 중...');
    
    const headerHeight = document.getElementById('headerSlider').value;
    
    // CSS 업데이트
    let updatedCss = css.replace(
      /(\\.split-header\\s*\\{[^}]*min-height:\\s*)\\d+vh/,
      `$1${headerHeight}vh`
    );
    
    // 에디터 스타일 제거 후 HTML 저장
    const styleEl = doc.getElementById('editor-styles');
    if (styleEl) styleEl.remove();
    
    // 스크롤바 숨김 스타일도 제거
    const scrollStyle = doc.querySelector('style:not([id])');
    if (scrollStyle && scrollStyle.textContent.includes('scrollbar')) {
      scrollStyle.remove();
    }
    
    const html = '<!DOCTYPE html>\\n' + doc.documentElement.outerHTML;
    
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html, css: updatedCss })
    });
    
    const data = await res.json();
    if (data.ok) {
      changed = false;
      css = updatedCss;
      toast('저장 완료!', 'ok');
      setStatus('저장됨');
    } else {
      throw new Error();
    }
  } catch (e) {
    toast('저장 실패', 'err');
    setStatus('오류');
  }
}

// Reset
async function resetPage() {
  if (!confirm('마지막 저장 상태로 되돌리시겠습니까?')) return;
  
  try {
    const res = await fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}'
    });
    const data = await res.json();
    if (data.ok) {
      toast('복원 완료', 'ok');
      setTimeout(() => location.reload(), 500);
    } else {
      throw new Error(data.error || '복원 실패');
    }
  } catch (e) {
    toast('복원 실패: ' + e.message, 'err');
  }
}

// Preview
function getPreviewViewportSize() {
  const preset = PREVIEW_SIZES[previewMode] || PREVIEW_SIZES.desktop;
  let width = preset.width;
  let height = preset.height;
  if (previewMode !== 'desktop' && previewOrientation === 'landscape') {
    width = preset.height;
    height = preset.width;
  }
  return { width, height };
}

function applyPreviewLayout() {
  const stage = document.getElementById('previewStage');
  const scaler = document.getElementById('previewScaler');
  const viewport = document.getElementById('previewViewport');
  const meta = document.getElementById('previewMeta');
  if (!stage || !scaler || !viewport || !meta) return;
  
  const size = getPreviewViewportSize();
  const availW = Math.max(stage.clientWidth - 32, 220);
  const availH = Math.max(stage.clientHeight - 32, 220);
  const scale = Math.min(availW / size.width, availH / size.height, 1);
  
  scaler.style.width = Math.round(size.width * scale) + 'px';
  scaler.style.height = Math.round(size.height * scale) + 'px';
  viewport.style.width = size.width + 'px';
  viewport.style.height = size.height + 'px';
  viewport.style.transform = 'scale(' + scale + ')';
  viewport.className = 'preview-viewport ' + previewMode;
  
  const modeLabel = previewMode.charAt(0).toUpperCase() + previewMode.slice(1);
  const orientationLabel = previewMode === 'desktop' ? '' : (previewOrientation === 'portrait' ? ' · Portrait' : ' · Landscape');
  meta.textContent = modeLabel + orientationLabel + ' · ' + size.width + '×' + size.height;
}

function setPreviewMode(mode) {
  previewMode = mode;
  if (mode === 'desktop') {
    previewOrientation = 'portrait';
  }
  
  document.getElementById('previewDesktopBtn').classList.toggle('active', mode === 'desktop');
  document.getElementById('previewTabletBtn').classList.toggle('active', mode === 'tablet');
  document.getElementById('previewMobileBtn').classList.toggle('active', mode === 'mobile');
  document.getElementById('previewRotateBtn').disabled = mode === 'desktop';
  
  applyPreviewLayout();
}

function togglePreviewOrientation() {
  if (previewMode === 'desktop') return;
  previewOrientation = previewOrientation === 'portrait' ? 'landscape' : 'portrait';
  applyPreviewLayout();
}

function openPreview(mode = 'desktop') {
  const html = '<!DOCTYPE html>\\n' + doc.documentElement.outerHTML;
  document.getElementById('previewFrame').srcdoc = html;
  document.getElementById('previewModal').classList.add('show');
  setPreviewMode(mode);
  requestAnimationFrame(applyPreviewLayout);
}

function closePreview() {
  document.getElementById('previewModal').classList.remove('show');
}

// Zoom
function zoomIn() { 
  zoom = Math.min(2, zoom + 0.1); 
  applyZoom(); 
}

function zoomOut() { 
  zoom = Math.max(0.1, zoom - 0.1); 
  applyZoom(); 
}

function zoomFit() {
  const area = document.getElementById('canvasArea');
  const frame = document.getElementById('canvasFrame');
  const aW = area.clientWidth - 80;
  const fH = parseInt(frame.style.height) || 3000;
  
  // 너비 기준으로 맞춤
  zoom = Math.min(aW / CANVAS_WIDTH, 0.5);
  zoom = Math.max(0.2, Math.round(zoom * 10) / 10);
  applyZoom();
}

function applyZoom() {
  document.getElementById('canvasWrap').style.transform = 'scale(' + zoom + ')';
  document.getElementById('zoomVal').textContent = Math.round(zoom * 100) + '%';
}

// Tool
function setTool(t) {
  tool = t;
  document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('tool' + t.charAt(0).toUpperCase() + t.slice(1));
  if (btn) btn.classList.add('active');
  
  const area = document.getElementById('canvasArea');
  area.style.cursor = t === 'hand' ? 'grab' : 'default';
}

// Utils
function toast(msg, type = '') {
  const t = document.getElementById('toast');
  t.innerHTML = (type === 'ok' ? '<span class="toast-icon">✓</span>' : type === 'err' ? '<span class="toast-icon">✕</span>' : '') + msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.classList.remove('show'), 2500);
}

function setStatus(txt) {
  document.getElementById('status').textContent = txt;
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  
  const ctrl = e.ctrlKey || e.metaKey;
  
  if (ctrl && e.key === 's') { e.preventDefault(); savePage(); }
  if (ctrl && e.key === 'z') { e.preventDefault(); undo(); }
  if (ctrl && e.key === 'y') { e.preventDefault(); redo(); }
  if (e.key === 'v' || e.key === 'V') { setTool('select'); }
  if (e.key === 'h' || e.key === 'H') { setTool('hand'); }
  if (ctrl && (e.key === '=' || e.key === '+')) { e.preventDefault(); zoomIn(); }
  if (ctrl && e.key === '-') { e.preventDefault(); zoomOut(); }
  if (ctrl && e.key === '0') { e.preventDefault(); zoomFit(); }
  if (e.key === 'Escape') { closePreview(); }
  
  // Space bar for temporary hand tool
  if (e.key === ' ' && !e.repeat) {
    e.preventDefault();
    setTool('hand');
  }
});

document.addEventListener('keyup', (e) => {
  if (e.key === ' ') {
    setTool('select');
  }
});

// Prevent accidental navigation
window.onbeforeunload = () => changed ? '' : null;
window.onresize = () => {
  updateFrameSize();
  if (document.getElementById('previewModal').classList.contains('show')) {
    applyPreviewLayout();
  }
};

// Drag & drop images
const canvasArea = document.getElementById('canvasArea');
canvasArea.ondragover = (e) => { e.preventDefault(); };
canvasArea.ondrop = (e) => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    const input = document.getElementById('imageInput');
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    uploadImage(input);
  }
};

init();
</script>
</body>
</html>'''


def main():
    lan_ip = _get_lan_ip()
    print(f"""
╔═══════════════════════════════════════════════════════╗
║         🎨 홈 디자인 에디터 Pro v2.1                    ║
╠═══════════════════════════════════════════════════════╣
║  http://localhost:{PORT}                                ║
║  http://{lan_ip}:{PORT}                                ║
║                                                       ║
║  ✨ 수정사항:                                          ║
║  • 흰색 배경 영역 표시 수정                             ║
║  • 오른쪽 흰색 선 제거 (iframe 스크롤바)                 ║
║  • 스크롤 기능 개선                                    ║
║                                                       ║
║  종료: Ctrl+C                                         ║
╚═══════════════════════════════════════════════════════╝
""")
    if lan_ip == "127.0.0.1":
        print("⚠ LAN IP를 찾지 못했습니다. 스마트폰 접속은 Windows 방화벽/네트워크 설정을 확인하세요.")
    
    auto_open = '--no-browser' not in sys.argv
    if auto_open:
        threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f'http://localhost:{PORT}')), daemon=True).start()
    
    with socketserver.TCPServer(("", PORT), Handler) as s:
        s.allow_reuse_address = True
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("\\n종료")


if __name__ == '__main__':
    main()
