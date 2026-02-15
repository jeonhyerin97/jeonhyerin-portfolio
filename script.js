/**
 * JEONHYERIN Portfolio
 * Minimal Architecture Archive
 * 
 * Vanilla JS for:
 * - Project overlay/modal
 * - Keyboard navigation (ESC to close, arrow keys to navigate)
 * - Focus management
 * - Smooth transitions
 */

(function() {
  'use strict';

  // ============================================
  // State
  // ============================================
  
  let currentProjectIndex = 0;
  let projectsData = [];
  let isOverlayOpen = false;
  let lastFocusedElement = null;

  // ============================================
  // DOM Elements
  // ============================================
  
  const overlay = document.getElementById('projectOverlay');
  const gridItems = document.querySelectorAll('.grid-item-btn');
  const gridItemContainers = document.querySelectorAll('.grid-item');
  const projectsDataEl = document.getElementById('projectsData');

  // ============================================
  // Initialize
  // ============================================
  
  function init() {
    // Parse project data if available
    if (projectsDataEl) {
      try {
        // JSON 문자열 내의 실제 줄바꿈을 \n으로 변환
        let jsonText = projectsDataEl.textContent;
        // 문자열 값 내부의 줄바꿈만 이스케이프 (정규식으로 "..." 사이의 줄바꿈 처리)
        jsonText = jsonText.replace(/"([^"\\]*(\\.[^"\\]*)*)"/g, (match) => {
          return match.replace(/\n/g, '\\n').replace(/\r/g, '');
        });
        projectsData = JSON.parse(jsonText);
      } catch (e) {
        console.warn('Could not parse projects data:', e);
      }
    }

    // Bind grid item clicks
    gridItems.forEach((btn, index) => {
      btn.addEventListener('click', () => openProject(index));
    });

    // Bind overlay events
    if (overlay) {
      const closeBtn = overlay.querySelector('.overlay-close');
      const backdrop = overlay.querySelector('.overlay-backdrop');
      const prevBtn = overlay.querySelector('.overlay-nav-prev');
      const nextBtn = overlay.querySelector('.overlay-nav-next');
      const topBtn = overlay.querySelector('.overlay-nav-top');

      if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
      if (backdrop) backdrop.addEventListener('click', closeOverlay);
      if (prevBtn) prevBtn.addEventListener('click', goToPrevProject);
      if (nextBtn) nextBtn.addEventListener('click', goToNextProject);
      if (topBtn) topBtn.addEventListener('click', scrollOverlayToTop);
    }

    // Global keyboard events
    document.addEventListener('keydown', handleKeyDown);

    // 스크롤 애니메이션 초기화
    initScrollReveal();
    
    // Add entrance animations to grid items
    animateGridItems();
    
    // 썸네일 이미지 fallback 처리 (thumb.jpg → cover.jpg)
    handleThumbnailFallback();
    
    // 아카이브 카운트 업데이트
    updateArchiveCount();
    
    // 푸터 프로젝트 목록 렌더링
    renderFooterProjects();
    
  }
  
  // 그리드 아이템 개수에 따라 archive-count 업데이트
  function updateArchiveCount() {
    const archiveCount = document.querySelector('.archive-count');
    if (!archiveCount) return;
    
    const visibleItems = document.querySelectorAll('.grid-item').length;
    archiveCount.textContent = visibleItems.toString().padStart(2, '0');
  }
  
  // 제목을 Title Case로 변환 (첫 글자만 대문자)
  function toTitleCase(str) {
    return str.toLowerCase().split(' ').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  }
  
  // 현재 페이지 타입 감지
  function getCurrentPageType() {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('drawings.html')) return 'drawings';
    if (path.includes('graphics.html')) return 'graphics';
    if (path.includes('study.html')) return 'study';
    if (path.includes('about.html')) return 'about';
    if (path.includes('index.html') || path.endsWith('/')) return 'index';
    return 'projects'; // projects.html
  }
  
  // 푸터 전체 렌더링
  function renderFooterProjects() {
    const pageType = getCurrentPageType();
    
    // 푸터 요소 확인 (index.html은 다른 푸터 구조 사용)
    const footerProjectList = document.getElementById('footerProjectList');
    if (!footerProjectList) return; // 푸터가 없으면 종료
    
    // footerData가 있으면 사용 (로컬 파일 시스템에서도 작동)
    const footerDataEl = document.getElementById('footerData');
    if (footerDataEl) {
      try {
        const footerData = JSON.parse(footerDataEl.textContent);
        
        // Projects 렌더링
        if (footerData.projects) {
          renderFooterFromData('footerProjectList', footerData.projects, 'projects.html', pageType === 'projects');
        }
        // Drawings 렌더링
        if (footerData.drawings) {
          renderFooterFromData('footerDrawingList', footerData.drawings, 'drawings.html', pageType === 'drawings');
        }
        // Graphics 렌더링
        if (footerData.graphics) {
          renderFooterFromData('footerGraphicList', footerData.graphics, 'graphics.html', pageType === 'graphics');
        }
        return;
      } catch (e) {
        console.warn('footerData 파싱 실패, 기존 방식 사용:', e);
      }
    }
    
    // footerData가 없으면 기존 방식 사용 (fetch)
    if (pageType === 'projects') {
      renderFooterSectionWithData('footerProjectList', projectsData, true);
      fetchAndRenderFooterSection('drawings.html', 'footerDrawingList', 'drawings.html');
      fetchAndRenderFooterSection('graphics.html', 'footerGraphicList', 'graphics.html');
    } else if (pageType === 'drawings') {
      fetchAndRenderFooterSection('projects.html', 'footerProjectList', 'projects.html');
      renderFooterSectionWithData('footerDrawingList', projectsData, true);
      fetchAndRenderFooterSection('graphics.html', 'footerGraphicList', 'graphics.html');
    } else if (pageType === 'graphics') {
      fetchAndRenderFooterSection('projects.html', 'footerProjectList', 'projects.html');
      fetchAndRenderFooterSection('drawings.html', 'footerDrawingList', 'drawings.html');
      renderFooterSectionWithData('footerGraphicList', projectsData, true);
    } else {
      // about 또는 다른 페이지: 모든 섹션을 fetch로 가져오기
      fetchAndRenderFooterSection('projects.html', 'footerProjectList', 'projects.html');
      fetchAndRenderFooterSection('drawings.html', 'footerDrawingList', 'drawings.html');
      fetchAndRenderFooterSection('graphics.html', 'footerGraphicList', 'graphics.html');
    }
  }
  
  // footerData에서 푸터 섹션 렌더링
  function renderFooterFromData(elementId, data, targetPage, isCurrentPage) {
    const footerList = document.getElementById(elementId);
    if (!footerList || !data || data.length === 0) return;
    
    footerList.innerHTML = data
      .filter(p => p.visible !== false)
      .map((project, index) => {
        const title = project.title || '';
        const formattedTitle = toTitleCase(title);
        if (isCurrentPage) {
          return `<a href="#" class="footer-project-link" data-project="${index}">${formattedTitle}</a>`;
        } else {
          return `<a href="${targetPage}" class="footer-project-link">${formattedTitle}</a>`;
        }
      })
      .join('');
    
    // 현재 페이지인 경우 클릭 이벤트 바인딩
    if (isCurrentPage) {
      footerList.querySelectorAll('.footer-project-link').forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const projectIndex = parseInt(link.dataset.project, 10);
          openProject(projectIndex);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });
    }
  }
  
  // 현재 페이지 데이터로 푸터 섹션 렌더링
  function renderFooterSectionWithData(elementId, data, isCurrentPage) {
    const footerList = document.getElementById(elementId);
    if (!footerList || !data || data.length === 0) return;
    
    footerList.innerHTML = data
      .filter(p => p.visible !== false)
      .map((project, index) => {
        const title = project.display_title || project.title;
        const formattedTitle = toTitleCase(title);
        if (isCurrentPage) {
          return `<a href="#" class="footer-project-link" data-project="${index}">${formattedTitle}</a>`;
        } else {
          return `<a href="#" class="footer-project-link">${formattedTitle}</a>`;
        }
      })
      .join('');
    
    // 현재 페이지인 경우만 클릭 이벤트 바인딩 (프로젝트 열기)
    if (isCurrentPage) {
      footerList.querySelectorAll('.footer-project-link').forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const projectIndex = parseInt(link.dataset.project, 10);
          openProject(projectIndex);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });
    }
  }
  
  // 다른 페이지에서 데이터 가져와서 푸터 섹션 렌더링
  async function fetchAndRenderFooterSection(htmlFile, elementId, targetPage) {
    const footerList = document.getElementById(elementId);
    if (!footerList) return;
    
    try {
      const response = await fetch(htmlFile);
      if (!response.ok) return;
      
      const html = await response.text();
      
      // <script type="application/json" id="projectsData"> 형태로 저장된 JSON 추출
      const match = html.match(/<script[^>]*id=["']projectsData["'][^>]*>([\s\S]*?)<\/script>/i);
      if (!match) {
        console.warn(`projectsData not found in ${htmlFile}`);
        return;
      }
      
      try {
        const data = JSON.parse(match[1].trim());
        renderFetchedFooterSection(footerList, data, targetPage);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
      }
        
    } catch (e) {
      console.error(`Failed to load footer data from ${htmlFile}:`, e);
    }
  }
  
  // fetch된 데이터로 푸터 섹션 렌더링
  function renderFetchedFooterSection(footerList, data, targetPage) {
    if (!data || data.length === 0) return;
    
    footerList.innerHTML = data
      .filter(p => p.visible !== false)
      .map((project) => {
        const title = project.display_title || project.title;
        const formattedTitle = toTitleCase(title);
        return `<a href="${targetPage}" class="footer-project-link">${formattedTitle}</a>`;
      })
      .join('');
  }
  
  // 썸네일 이미지 lazy loading + fallback 처리
  function handleThumbnailFallback() {
    const thumbs = document.querySelectorAll('.grid-thumb');
    
    // Intersection Observer로 뷰포트에 보일 때만 이미지 로드
    const observerOptions = {
      root: null,
      rootMargin: '100px', // 100px 전에 미리 로드 시작
      threshold: 0.01
    };
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const thumb = entry.target;
          loadThumbnail(thumb);
          observer.unobserve(thumb);
        }
      });
    }, observerOptions);
    
    thumbs.forEach(thumb => {
      // 초기에는 배경 이미지 제거 (placeholder만 표시)
      thumb.style.backgroundImage = 'none';
      imageObserver.observe(thumb);
    });
  }
  
  // 개별 썸네일 로드 (jpg, webp 모두 지원)
  function loadThumbnail(thumb) {
    const thumbUrl = thumb.dataset.thumb;
    const coverUrl = thumb.dataset.cover;
    
    if (!thumbUrl && !coverUrl) {
      thumb.classList.add('loaded');
      return;
    }
    
    // 확장자 변환 함수
    function getWebpUrl(url) {
      return url.replace(/\.(jpg|jpeg|png)$/i, '.webp');
    }
    
    // 이미지 로드 시도 순서: thumb.jpg → thumb.webp → cover.jpg → cover.webp
    const urlsToTry = [];
    if (thumbUrl) {
      urlsToTry.push(thumbUrl);
      urlsToTry.push(getWebpUrl(thumbUrl));
    }
    if (coverUrl) {
      urlsToTry.push(coverUrl);
      urlsToTry.push(getWebpUrl(coverUrl));
    }
    
    function tryNextUrl(index) {
      if (index >= urlsToTry.length) {
        thumb.classList.add('grid-thumb--placeholder', 'loaded');
        return;
      }
      
      const img = new Image();
      img.onload = function() {
        thumb.style.backgroundImage = `url('${urlsToTry[index]}')`;
        thumb.classList.add('loaded');
      };
      img.onerror = function() {
        tryNextUrl(index + 1);
      };
      img.src = urlsToTry[index];
    }
    
    tryNextUrl(0);
  }

  // ============================================
  // Overlay Functions
  // ============================================
  
  function openProject(index) {
    if (!overlay || !projectsData.length) return;

    currentProjectIndex = index;
    lastFocusedElement = document.activeElement;

    // Update overlay content
    renderProjectDetail(projectsData[index]);

    // Update navigation buttons
    updateNavButtons();

    // Open overlay
    isOverlayOpen = true;
    overlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('overlay-open');

    // Focus management - focus close button after transition
    setTimeout(() => {
      const closeBtn = overlay.querySelector('.overlay-close');
      if (closeBtn) closeBtn.focus();
    }, 100);

    // Scroll overlay to top
    const scrollContainer = overlay.querySelector('.overlay-scroll');
    if (scrollContainer) scrollContainer.scrollTop = 0;
  }

  function closeOverlay() {
    if (!overlay || !isOverlayOpen) return;

    isOverlayOpen = false;
    overlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('overlay-open');

    // Restore focus
    if (lastFocusedElement) {
      lastFocusedElement.focus();
    }
  }

  function goToPrevProject() {
    if (currentProjectIndex > 0) {
      currentProjectIndex--;
      renderProjectDetail(projectsData[currentProjectIndex]);
      updateNavButtons();
      scrollOverlayToTop();
    }
  }

  function goToNextProject() {
    if (currentProjectIndex < projectsData.length - 1) {
      currentProjectIndex++;
      renderProjectDetail(projectsData[currentProjectIndex]);
      updateNavButtons();
      scrollOverlayToTop();
    }
  }

  function scrollOverlayToTop() {
    const scrollContainer = overlay.querySelector('.overlay-scroll');
    if (scrollContainer) {
      scrollContainer.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  function updateNavButtons() {
    const prevBtn = overlay.querySelector('.overlay-nav-prev');
    const nextBtn = overlay.querySelector('.overlay-nav-next');

    if (prevBtn) {
      prevBtn.disabled = currentProjectIndex === 0;
    }
    if (nextBtn) {
      nextBtn.disabled = currentProjectIndex === projectsData.length - 1;
    }
  }

  // ============================================
  // Render Project Detail
  // ============================================
  
  // 캡션 데이터 캐시
  let captionsCache = {};
  
  // 캡션 데이터 로드 (캐시 무효화 포함)
  async function loadCaptions(basePath) {
    const timestamp = Date.now();
    const captionUrl = `${basePath}/captions.json?t=${timestamp}`;
    try {
      const response = await fetch(captionUrl, { cache: 'no-store' });
      if (response.ok) {
        const data = await response.json();
        console.log('Captions loaded:', data);
        return data;
      }
    } catch (e) {
      // 캡션 파일이 없으면 빈 객체 반환
    }
    return {};
  }
  
  function renderProjectDetail(project) {
    if (!overlay || !project) return;

    const detail = overlay.querySelector('.project-detail');
    if (!detail) return;

    // Determine if this is a drawings, graphics, or projects page
    const isDrawings = window.location.pathname.includes('drawings');
    const isGraphics = window.location.pathname.includes('graphics');

    // Build meta HTML based on available fields
    let metaHTML = '';

    if (project.location) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">LOCATION</span>
          <span class="meta-value">${escapeHtml(project.location)}</span>
        </div>
      `;
    }
    
    if (project.duration) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">DURATION</span>
          <span class="meta-value">${escapeHtml(project.duration)}</span>
        </div>
      `;
    }

    if (project.program) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">PROGRAM</span>
          <span class="meta-value">${escapeHtml(project.program)}</span>
        </div>
      `;
    }

    if (project.studio) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">STUDIO</span>
          <span class="meta-value">${escapeHtml(project.studio)}</span>
        </div>
      `;
    }

    // Drawing-specific fields
    if (project.year) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">YEAR</span>
          <span class="meta-value">${escapeHtml(project.year)}</span>
        </div>
      `;
    }

    if (project.medium) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">MEDIUM</span>
          <span class="meta-value">${escapeHtml(project.medium)}</span>
        </div>
      `;
    }

    if (project.series) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">SERIES</span>
          <span class="meta-value">${escapeHtml(project.series)}</span>
        </div>
      `;
    }
    
    // 커스텀 필드 렌더링
    if (project.custom_fields && Array.isArray(project.custom_fields)) {
      project.custom_fields.forEach(field => {
        if (field.label && field.value) {
          metaHTML += `
            <div class="meta-item">
              <span class="meta-label">${escapeHtml(field.label)}</span>
              <span class="meta-value">${escapeHtml(field.value)}</span>
            </div>
          `;
        }
      });
    }

    // Determine image base path
    const imageFolder = isDrawings ? 'images/drawings' : (isGraphics ? 'images/graphics' : 'images/projects');
    const slug = project.slug || project.title.toLowerCase().replace(/\s+/g, '-');
    const basePath = `${imageFolder}/${slug}`;

    // Generate sub images (01.jpg/webp - 20.jpg/webp) with lazy loading and fallback
    let subImagesHTML = '';
    for (let i = 1; i <= 20; i++) {
      const num = i.toString().padStart(2, '0');
      subImagesHTML += `
        <figure class="project-image reveal-image">
          <img data-src="${basePath}/${num}.jpg" data-src-webp="${basePath}/${num}.webp" alt="${escapeHtml(project.title)} sub ${i}" class="lazy-image" 
            onerror="if(this.dataset.srcWebp && !this.dataset.triedWebp){this.dataset.triedWebp='1';this.src=this.dataset.srcWebp;}else{this.parentElement.style.display='none';}">
        </figure>
      `;
    }

    // Generate model images (model_images/1.jpg/webp - model_images/30.jpg/webp) with lazy loading and fallback
    let modelImagesHTML = '';
    for (let i = 1; i <= 30; i++) {
      modelImagesHTML += `
        <figure class="model-image reveal-image" data-model-index="${i}">
          <img data-src="${basePath}/model_images/${i}.jpg" data-src-webp="${basePath}/model_images/${i}.webp" alt="${escapeHtml(project.title)} model ${i}" class="lazy-image" 
            onerror="if(this.dataset.srcWebp && !this.dataset.triedWebp){this.dataset.triedWebp='1';this.src=this.dataset.srcWebp;}else{this.parentElement.style.display='none';}">
        </figure>
      `;
    }

    // Generate slide images (slide_images/1.jpg/webp - slide_images/20.jpg/webp) with lazy loading and fallback
    let slideImagesHTML = '';
    for (let i = 1; i <= 20; i++) {
      slideImagesHTML += `
        <figure class="project-image reveal-image">
          <img data-src="${basePath}/slide_images/${i}.jpg" data-src-webp="${basePath}/slide_images/${i}.webp" alt="${escapeHtml(project.title)} slide ${i}" class="lazy-image" 
            onerror="if(this.dataset.srcWebp && !this.dataset.triedWebp){this.dataset.triedWebp='1';this.src=this.dataset.srcWebp;}else{this.parentElement.style.display='none';}">
        </figure>
      `;
    }

    // Render full detail - Side-by-side layout: image left, text right
    // main.jpg → main.webp → cover.jpg → cover.webp 순으로 시도
    // cover_ratio를 CSS aspect-ratio로 변환
    let aspectRatio = '16 / 10';
    if (project.cover_ratio) {
      const parts = project.cover_ratio.split(':');
      if (parts.length === 2) {
        aspectRatio = `${parts[0]} / ${parts[1]}`;
      }
    }
    
    detail.innerHTML = `
      <!-- Hero Section: Image Left, Text Right -->
      <div class="project-hero">
        <figure class="project-cover reveal-image">
          <img src="${basePath}/main.jpg" alt="${escapeHtml(project.title)} main" class="project-cover-image" 
            style="object-position: ${project.cover_position || 'center center'}; aspect-ratio: ${aspectRatio};"
            onerror="
              var self=this;
              var tryImages=['${basePath}/main.webp','${basePath}/cover.jpg','${basePath}/cover.webp'];
              var tryIndex=0;
              function tryNext(){
                if(tryIndex>=tryImages.length){self.style.display='none';self.parentElement.innerHTML='<div class=\\'image-placeholder project-cover-image\\'></div>';return;}
                self.src=tryImages[tryIndex++];
              }
              self.onerror=tryNext;
              tryNext();
            ">
        </figure>

        <div class="project-content">
          <header class="project-header">
            <h2 class="project-title">${escapeHtml(project.title)}</h2>
            ${project.description_ko ? `
            <div class="lang-toggle">
              <button class="lang-btn lang-btn--active" data-lang="en">EN</button>
              <span class="lang-divider">/</span>
              <button class="lang-btn" data-lang="kr">KR</button>
            </div>
            ` : ''}
          </header>

          <div class="project-meta">
            ${metaHTML}
          </div>

          <div class="project-description">
            <p class="description-en">${escapeHtml(project.description)}</p>
            ${project.description_ko ? `<p class="description-ko" style="display: none;">${escapeHtml(project.description_ko)}</p>` : ''}
          </div>
        </div>
      </div>

      <!-- Images Wrapper -->
      <div class="project-images-wrapper">
        ${slug === 'soft_concrete' ? `
        <!-- Model Images First for soft_concrete -->
        <div class="project-images-section project-images-section--model" style="margin-top: 0;">
          <div class="project-images project-images--model">
            ${modelImagesHTML}
          </div>
        </div>

        <!-- Sub Images -->
        <div class="project-images project-images--sub">
          ${subImagesHTML}
        </div>
        ` : `
        <!-- Sub Images (01.jpg, 02.jpg, ...) -->
        <div class="project-images project-images--sub">
          ${subImagesHTML}
        </div>

        <!-- Model Images Section -->
        <div class="project-images-section project-images-section--model">
          <div class="project-images project-images--model">
            ${modelImagesHTML}
          </div>
        </div>
        `}

        <!-- Extra Images Section -->
        <div class="project-images-section project-images-section--extra">
          <div class="project-images project-images--extra">
            ${slideImagesHTML}
          </div>
        </div>

        <!-- Overlay Footer -->
        <footer class="overlay-footer">
          <span class="overlay-footer-text">JEONHYERIN © 2026 All rights reserved.</span>
        </footer>
      </div>
    `;

    // Apply lazy loading to detail images
    initDetailLazyLoading(detail);
    
    // Wait for model images to load and adjust grid
    waitForModelImages(detail);
    
    // 스크롤 시 이미지 서서히 나타나는 애니메이션 적용
    initOverlayScrollReveal(detail);
    
    // 캡션 로드 및 이미지 로드 시 적용
    loadCaptions(basePath).then(captions => {
      captionsCache = captions;
      if (Object.keys(captions).length > 0) {
        setupCaptionObservers(detail, captions);
      }
    });
    
    // 언어 전환 버튼 이벤트 바인딩
    setupLangToggle(detail);
    
    // 오버레이 내부 이미지 reveal 애니메이션 초기화
    initOverlayRevealImages(detail);
  }
  
  // EN/KR 언어 전환 기능
  function setupLangToggle(container) {
    const langToggle = container.querySelector('.lang-toggle');
    if (!langToggle) return;
    
    const langBtns = langToggle.querySelectorAll('.lang-btn');
    const descEn = container.querySelector('.description-en');
    const descKo = container.querySelector('.description-ko');
    
    langBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const lang = btn.dataset.lang;
        
        // 버튼 활성화 상태 변경
        langBtns.forEach(b => b.classList.remove('lang-btn--active'));
        btn.classList.add('lang-btn--active');
        
        // 설명 표시/숨기기
        if (lang === 'en') {
          // EN: 영어만 표시
          if (descEn) descEn.style.display = '';
          if (descKo) descKo.style.display = 'none';
        } else {
          // KR: 영어 + 한국어 표시
          if (descEn) descEn.style.display = '';
          if (descKo) descKo.style.display = '';
        }
      });
    });
  }
  
  // 이미지 로드 성공 시 캡션 적용
  function setupCaptionObservers(container, captions) {
    console.log('Setting up caption observers with:', captions);
    
    // 서브 이미지 - 더 유연한 매칭
    const subImages = container.querySelectorAll('.project-images--sub .project-image img');
    subImages.forEach((img, idx) => {
      const src = img.dataset.src || img.src || '';
      // 여러 패턴 시도: /01.webp, /1.webp, 01.webp 등
      let num = null;
      const match = src.match(/[\/\\](\d+)\.(jpg|jpeg|webp|png)/i);
      if (match) {
        num = match[1];
      }
      
      if (num) {
        // 두 자리로 패딩하여 캡션 키 생성
        const paddedNum = num.padStart(2, '0');
        const captionKey = `sub_${paddedNum}`;
        console.log(`Sub image ${idx}: src=${src}, num=${num}, key=${captionKey}`);
        
        if (captions[captionKey]) {
          img.dataset.caption = captions[captionKey];
          img.dataset.captionKey = captionKey;
          console.log(`Caption found for ${captionKey}: ${captions[captionKey]}`);
        }
      }
    });
    
    // 슬라이드 이미지
    const slideImages = container.querySelectorAll('.project-images--extra .project-image img');
    slideImages.forEach((img, idx) => {
      const src = img.dataset.src || img.src || '';
      const match = src.match(/slide_images[\/\\](\d+)\.(jpg|jpeg|webp|png)/i);
      if (match) {
        const num = match[1];
        const captionKey = `slide_${num}`;
        if (captions[captionKey]) {
          img.dataset.caption = captions[captionKey];
          img.dataset.captionKey = captionKey;
        }
      }
    });
    
    // 지연 후 캡션 적용 (이미지 로드 대기)
    setTimeout(() => {
      applyCaptionsToLoadedImages(container);
    }, 500);
    
    // 추가 지연 적용 (느린 이미지 대비)
    setTimeout(() => {
      applyCaptionsToLoadedImages(container);
    }, 1500);
  }
  
  function applyCaptionsToLoadedImages(container) {
    const allImages = container.querySelectorAll('.project-image img[data-caption]');
    allImages.forEach(img => {
      const figure = img.closest('.project-image');
      if (figure && img.dataset.caption && !figure.dataset.captionAdded) {
        // 이미지가 보이는 상태인지 확인
        if (figure.style.display !== 'none' && figure.offsetParent !== null) {
          addCaptionToImage(figure, img.dataset.caption);
        }
      }
    });
  }
  
  // 이미지에 캡션 추가
  function addCaptionToImage(figure, captionText) {
    // 이미 캡션이 있으면 스킵
    if (figure.closest('.image-with-caption')) return;
    if (figure.parentNode && figure.parentNode.classList.contains('image-with-caption')) return;
    if (figure.dataset.captionAdded) return;
    
    // figure가 DOM에 연결되어 있는지 확인
    if (!figure.parentNode) return;
    
    // 표시 상태 확인
    if (figure.style.display === 'none') return;
    
    figure.dataset.captionAdded = 'true';
    
    // figure를 캡션 컨테이너로 감싸기
    const wrapper = document.createElement('div');
    wrapper.className = 'image-with-caption';
    figure.parentNode.insertBefore(wrapper, figure);
    wrapper.appendChild(figure);
    
    // 캡션 요소 추가
    const caption = document.createElement('div');
    caption.className = 'image-caption';
    caption.innerHTML = `<p>${escapeHtml(captionText)}</p>`;
    wrapper.appendChild(caption);
  }
  
  // Detail 페이지 이미지 lazy loading (jpg → webp fallback 지원)
  // 모델 이미지는 waitForModelImages에서 별도 처리하므로 제외
  function initDetailLazyLoading(container) {
    // 모델 이미지를 제외한 lazy-image만 선택
    const lazyImages = container.querySelectorAll('.lazy-image:not(.model-image img)');
    const nonModelImages = Array.from(container.querySelectorAll('.lazy-image')).filter(
      img => !img.closest('.model-image')
    );
    
    const observerOptions = {
      root: container.closest('.overlay-scroll'),
      rootMargin: '200px',
      threshold: 0.01
    };
    
    const lazyObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          // 이미 로드된 경우 스킵
          if (img.classList.contains('lazy-loaded') && img.src && img.complete && img.naturalWidth > 0) {
            observer.unobserve(img);
            return;
          }
          
          const srcJpg = img.dataset.src;
          const srcWebp = img.dataset.srcWebp;
          
          if (srcJpg || srcWebp) {
            // jpg → webp fallback 로직
            img.onload = function() {
              img.classList.add('lazy-loaded');
            };
            img.onerror = function() {
              if (srcWebp && !img.dataset.triedWebp) {
                img.dataset.triedWebp = '1';
                img.src = srcWebp;
              } else {
                img.parentElement.style.display = 'none';
              }
            };
            img.src = srcJpg || srcWebp;
            observer.unobserve(img);
          }
        }
      });
    }, observerOptions);
    
    // 모델 이미지를 제외한 이미지들만 관찰
    nonModelImages.forEach(img => lazyObserver.observe(img));
  }

  // Wait for model images to load then adjust grid (with lazy loading support)
  // jpg → webp fallback 지원
  function waitForModelImages(container) {
    const modelImages = container.querySelectorAll('.model-image img');
    let loadedCount = 0;
    let errorCount = 0;
    const totalImages = modelImages.length;

    if (totalImages === 0) {
      hideModelSection(container);
      return;
    }

    function checkComplete() {
      if (loadedCount + errorCount >= totalImages) {
        adjustModelImagesGrid(container, loadedCount);
      }
    }

    // 모든 모델 이미지를 즉시 로드 (그리드 계산을 위해)
    modelImages.forEach(img => {
      const srcJpg = img.dataset.src || img.src;
      const srcWebp = img.dataset.srcWebp;
      
      if (!srcJpg && !srcWebp) {
        errorCount++;
        img.parentElement.style.display = 'none';
        checkComplete();
        return;
      }
      
      // 이미 로드된 경우
      if (img.src && img.complete && img.naturalWidth > 0) {
        loadedCount++;
        img.classList.add('lazy-loaded');
        checkComplete();
        return;
      }
      
      // 로드 성공 핸들러
      function onLoadSuccess() {
        loadedCount++;
        img.classList.add('lazy-loaded');
        checkComplete();
      }
      
      // jpg 로드 시도 → 실패 시 webp 시도 → 둘 다 실패 시 숨김
      function tryLoadImage() {
        img.onload = onLoadSuccess;
        img.onerror = function() {
          // webp fallback 시도
          if (srcWebp && !img.dataset.triedWebp) {
            img.dataset.triedWebp = '1';
            img.src = srcWebp;
          } else {
            // 둘 다 실패
            errorCount++;
            img.parentElement.style.display = 'none';
            checkComplete();
          }
        };
        img.src = srcJpg || srcWebp;
      }
      
      tryLoadImage();
    });
  }

  // Adjust model images to show only multiples of 3
  function adjustModelImagesGrid(container, loadedCount) {
    const modelImages = container.querySelectorAll('.model-image');
    
    // Round down to nearest multiple of 3
    const showCount = Math.floor(loadedCount / 3) * 3;
    
    let visibleIndex = 0;
    modelImages.forEach(fig => {
      if (fig.style.display !== 'none') {
        visibleIndex++;
        if (visibleIndex > showCount) {
          fig.style.display = 'none';
        }
      }
    });

    // Hide section if no model images to show
    if (showCount === 0) {
      hideModelSection(container);
    }
  }

  function hideModelSection(container) {
    const modelSection = container.querySelector('.project-images-section--model');
    if (modelSection) {
      modelSection.style.display = 'none';
    }
  }

  // ============================================
  // Keyboard Navigation
  // ============================================
  
  function handleKeyDown(e) {
    // Only handle when overlay is open
    if (!isOverlayOpen) return;

    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        closeOverlay();
        break;

      case 'ArrowLeft':
        e.preventDefault();
        goToPrevProject();
        break;

      case 'ArrowRight':
        e.preventDefault();
        goToNextProject();
        break;

      case 'Tab':
        // Trap focus within overlay
        trapFocus(e);
        break;
    }
  }

  function trapFocus(e) {
    if (!overlay) return;

    const focusableElements = overlay.querySelectorAll(
      'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (e.shiftKey) {
      // Shift + Tab: going backwards
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      }
    } else {
      // Tab: going forwards
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }

  // ============================================
  // Scroll Reveal Animations
  // ============================================
  
  // ============================================
  // Fade-in Reveal Animation
  // ============================================
  
  let gridObserver = null;
  let overlayObserver = null;
  
  // Initialize grid items reveal on scroll
  function initScrollReveal() {
    gridObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          gridObserver.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      rootMargin: '0px 0px -50px 0px',
      threshold: 0.1
    });
  }
  
  function animateGridItems() {
    gridItemContainers.forEach((item, index) => {
      item.classList.add('reveal');
      item.style.transitionDelay = `${index * 0.05}s`;
      if (gridObserver) gridObserver.observe(item);
    });
  }
  
  // Popup opening animation
  function initOverlayScrollReveal(container) {
    const scrollContainer = overlay.querySelector('.overlay-scroll');
    if (!scrollContainer) return;
    
    // Get elements
    const cover = container.querySelector('.project-cover');
    const title = container.querySelector('.project-title');
    const meta = container.querySelector('.project-meta');
    const desc = container.querySelector('.project-description');
    
    // Add reveal class to all
    [cover, title, meta, desc].forEach(el => {
      if (el) el.classList.add('reveal');
    });
    
    // Trigger animations immediately when popup opens
    requestAnimationFrame(() => {
      // Title appears immediately
      if (title) title.classList.add('revealed');
      // Cover appears immediately
      if (cover) cover.classList.add('revealed');
      // Meta with slight delay
      setTimeout(() => {
        if (meta) meta.classList.add('revealed');
      }, 150);
      // Description after meta
      setTimeout(() => {
        if (desc) desc.classList.add('revealed');
      }, 300);
    });
    
    // Scroll-triggered images
    const scrollImages = container.querySelectorAll(
      '.project-images--sub .project-image, .model-image, .project-images--extra .project-image'
    );
    
    overlayObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
        } else {
          entry.target.classList.remove('revealed');
        }
      });
    }, {
      root: scrollContainer,
      rootMargin: '50px 0px',
      threshold: 0.1
    });
    
    scrollImages.forEach((img, index) => {
      img.classList.add('reveal');
      img.style.transitionDelay = `${(index % 3) * 0.1}s`;
      overlayObserver.observe(img);
    });
  }

  // ============================================
  // Utilities
  // ============================================
  
  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ============================================
  // Lightbox for Image Zoom
  // ============================================
  
  let lightbox = null;
  let lightboxImage = null;
  let currentZoom = 1;
  const maxZoom = 4;
  const minZoom = 1;
  const zoomStep = 0.15;

  function createLightbox() {
    // Create lightbox element
    lightbox = document.createElement('div');
    lightbox.className = 'lightbox';
    lightbox.innerHTML = `
      <button class="lightbox-close" aria-label="Close lightbox">
        <span class="close-icon"></span>
      </button>
      <div class="lightbox-image-container">
        <img class="lightbox-image" src="" alt="Enlarged image" draggable="false" oncontextmenu="return false;">
      </div>
    `;
    document.body.appendChild(lightbox);

    lightboxImage = lightbox.querySelector('.lightbox-image');
    const closeBtn = lightbox.querySelector('.lightbox-close');

    // Event listeners
    closeBtn.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox || e.target === lightboxImage) {
        if (currentZoom === 1) {
          closeLightbox();
        } else {
          resetZoom();
        }
      }
    });

    // Scroll to zoom
    lightbox.addEventListener('wheel', handleScrollZoom, { passive: false });

    // Keyboard
    document.addEventListener('keydown', handleLightboxKeydown);

    // Prevent right-click download
    lightboxImage.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  function handleScrollZoom(e) {
    if (!lightbox || !lightbox.classList.contains('active')) return;
    
    e.preventDefault();
    
    if (e.deltaY < 0) {
      // Scroll up - zoom in
      zoomIn();
    } else {
      // Scroll down - zoom out
      zoomOut();
    }
  }

  function openLightbox(imageSrc) {
    if (!lightbox) createLightbox();
    
    lightboxImage.src = imageSrc;
    currentZoom = 1;
    updateZoom();
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
    resetZoom();
  }

  function zoomIn() {
    if (currentZoom < maxZoom) {
      currentZoom = Math.min(currentZoom + zoomStep, maxZoom);
      updateZoom();
    }
  }

  function zoomOut() {
    if (currentZoom > minZoom) {
      currentZoom = Math.max(currentZoom - zoomStep, minZoom);
      updateZoom();
    }
  }

  function resetZoom() {
    currentZoom = 1;
    updateZoom();
  }

  function updateZoom() {
    if (!lightboxImage) return;
    lightboxImage.style.transform = `scale(${currentZoom})`;
    
    if (currentZoom > 1) {
      lightboxImage.classList.add('zoomed');
    } else {
      lightboxImage.classList.remove('zoomed');
    }
  }

  function handleLightboxKeydown(e) {
    if (!lightbox || !lightbox.classList.contains('active')) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      closeLightbox();
    }
  }

  // ============================================
  // Custom Cursor for Images
  // ============================================
  
  let imageCursor = null;

  function createImageCursor() {
    imageCursor = document.createElement('div');
    imageCursor.className = 'image-cursor';
    document.body.appendChild(imageCursor);
  }

  function bindImageHover() {
    createImageCursor();

    document.addEventListener('mousemove', (e) => {
      const img = e.target.closest('.project-image img, .model-image img, .project-cover-image');
      const isInLightbox = lightbox && lightbox.classList.contains('active');
      
      if ((img && img.tagName === 'IMG') || isInLightbox) {
        imageCursor.style.left = e.clientX + 'px';
        imageCursor.style.top = e.clientY + 'px';
        imageCursor.classList.add('visible');
      } else {
        imageCursor.classList.remove('visible');
      }
    });

    document.addEventListener('mouseleave', () => {
      imageCursor.classList.remove('visible');
    });
  }

  // Bind click events to project images
  function bindImageClicks() {
    document.addEventListener('click', (e) => {
      const img = e.target.closest('.project-image img, .model-image img, .project-cover-image');
      if (img && img.tagName === 'IMG' && img.src) {
        e.preventDefault();
        openLightbox(img.src, img);
      }
    });
  }

  // ============================================
  // Reveal Image Animation (Intersection Observer)
  // Fade-in + Slide-up on scroll
  // ============================================
  
  let overlayRevealObserver = null;
  
  function initRevealImages() {
    const revealImages = document.querySelectorAll('.reveal-image');
    
    if (revealImages.length === 0) return;
    
    // Toggle visibility on enter/exit so images can fade in and fade out
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
        } else {
          entry.target.classList.remove('is-visible');
        }
      });
    }, {
      root: null, // viewport
      rootMargin: '0px 0px -50px 0px', // trigger slightly before fully in view
      threshold: 0.1
    });
    
    revealImages.forEach(img => {
      revealObserver.observe(img);
    });
  }
  
  // Initialize reveal images inside overlay (uses overlay scroll container as root)
  function initOverlayRevealImages(container) {
    const scrollContainer = overlay ? overlay.querySelector('.overlay-scroll') : null;
    const revealImages = container.querySelectorAll('.reveal-image');
    
    if (revealImages.length === 0) return;
    
    // Destroy previous observer if exists
    if (overlayRevealObserver) {
      overlayRevealObserver.disconnect();
    }
    
    // Toggle visibility on enter/exit so images can fade in/out while scrolling inside overlay
    overlayRevealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
        } else {
          entry.target.classList.remove('is-visible');
        }
      });
    }, {
      root: scrollContainer, // overlay scroll container
      rootMargin: '50px 0px -30px 0px',
      threshold: 0.05
    });
    
    // Add staggered delay for visual effect
    revealImages.forEach((img, index) => {
      // Stagger delay based on position (max 0.3s)
      const delay = Math.min((index % 5) * 0.08, 0.3);
      img.style.transitionDelay = `${delay}s`;
      overlayRevealObserver.observe(img);
    });
  }

  // ============================================
  // Initialize on DOM Ready
  // ============================================
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      init();
      bindImageClicks();
      bindImageHover();
      initRevealImages();
    });
  } else {
    init();
    bindImageClicks();
    bindImageHover();
    initRevealImages();
  }

})();
