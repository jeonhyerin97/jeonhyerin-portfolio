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
  let armedGridIndex = -1;
  let armedGridResetTimer = null;

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

    // Bind grid item clicks (desktop: one click open / touch: arm then open)
    gridItems.forEach((btn, index) => {
      btn.addEventListener('click', (e) => {
        if (isDesktopDirectOpenMode()) {
          e.preventDefault();
          clearArmedGridItem();
          openProject(index);
          return;
        }

        if (armedGridIndex === index) {
          clearArmedGridItem();
          openProject(index);
          return;
        }

        e.preventDefault();
        armGridItem(index);
      });

      btn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          clearArmedGridItem();
          openProject(index);
        }
      });
    });

    document.addEventListener('click', (e) => {
      if (e.target.closest('.grid-item-btn')) return;
      clearArmedGridItem();
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

    openProjectFromQueryParam();
    syncAboutAlignmentAxis();
    window.addEventListener('resize', syncAboutAlignmentAxis);
    window.addEventListener('load', syncAboutAlignmentAxis);
    
  }
  
  // 그리드 아이템 개수에 따라 archive-count 업데이트
  function clearArmedGridItem() {
    if (armedGridResetTimer) {
      clearTimeout(armedGridResetTimer);
      armedGridResetTimer = null;
    }

    if (armedGridIndex < 0) return;

    const armedItem = gridItemContainers[armedGridIndex];
    if (armedItem) {
      armedItem.classList.remove('grid-item--armed');
    }
    armedGridIndex = -1;
  }

  function armGridItem(index) {
    clearArmedGridItem();
    const item = gridItemContainers[index];
    if (!item) return;

    item.classList.add('grid-item--armed');
    armedGridIndex = index;

    armedGridResetTimer = setTimeout(() => {
      clearArmedGridItem();
    }, 2400);
  }

  function isDesktopDirectOpenMode() {
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches &&
      window.matchMedia('(min-width: 1025px)').matches;
  }

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

  function normalizeProjectKey(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/&/g, 'and')
      .replace(/[^a-z0-9]+/g, '');
  }

  function syncAboutAlignmentAxis() {
    if (!document.body || !document.body.classList.contains('page-about')) return;

    const logo = document.querySelector('.nav--archive .nav-logo');
    if (!logo) return;

    const logoWidth = logo.getBoundingClientRect().width;
    if (!logoWidth) return;

    document.body.style.setProperty('--about-nav-logo-width', `${logoWidth}px`);
  }

  function findProjectIndexFromParam(param) {
    const normalizedParam = normalizeProjectKey(param);
    if (!normalizedParam) return -1;

    return projectsData.findIndex((project) => {
      const keys = [
        project.slug,
        project.display_title,
        project.title,
        project.index
      ];
      return keys.some(key => normalizeProjectKey(key) === normalizedParam);
    });
  }

  function openProjectFromQueryParam() {
    if (!overlay || !projectsData.length) return;

    const params = new URLSearchParams(window.location.search);
    const projectParam = params.get('project');
    const forceOpen = params.get('autopopup') === '1';
    if (!projectParam && !forceOpen) return;

    let projectIndex = findProjectIndexFromParam(projectParam);
    if (projectIndex < 0) {
      if (!forceOpen) return;
      projectIndex = 0;
    }

    requestAnimationFrame(() => openProject(projectIndex));
  }
  
  function getCurrentPageFile() {
    const path = window.location.pathname || '';
    const file = path.split('/').pop().toLowerCase();
    return file || 'index.html';
  }

  function normalizeFooterTabsData(footerData) {
    if (footerData && Array.isArray(footerData.tabs) && footerData.tabs.length) {
      return footerData.tabs.filter(tab => tab && tab.visible !== false).map(tab => ({
        id: tab.id || '',
        name: tab.name || (tab.id || '').toUpperCase(),
        file: tab.file || '',
        items: Array.isArray(tab.items) ? tab.items : []
      }));
    }

    const legacyTabs = [
      { id: 'projects', name: 'PROJECTS', file: 'projects.html', items: footerData && Array.isArray(footerData.projects) ? footerData.projects : [] },
      { id: 'drawings', name: 'DRAWINGS', file: 'drawings.html', items: footerData && Array.isArray(footerData.drawings) ? footerData.drawings : [] },
      { id: 'graphics', name: 'GRAPHICS', file: 'graphics.html', items: footerData && Array.isArray(footerData.graphics) ? footerData.graphics : [] }
    ];

    return legacyTabs.filter(tab => tab.items.length > 0);
  }

  function applyFooterDensity(columnsEl) {
    columnsEl.classList.remove('footer-columns--compact', 'footer-columns--tight');
    if (window.matchMedia('(max-width: 768px)').matches) return;

    const columnCount = columnsEl.querySelectorAll('.footer-column').length;
    if (columnCount >= 6) {
      columnsEl.classList.add('footer-columns--compact');
    }
    if (columnCount >= 8) {
      columnsEl.classList.add('footer-columns--tight');
    }

    if (columnsEl.scrollWidth > columnsEl.clientWidth + 2) {
      columnsEl.classList.add('footer-columns--compact');
      if (columnsEl.scrollWidth > columnsEl.clientWidth + 2) {
        columnsEl.classList.add('footer-columns--tight');
      }
    }
  }

  function renderFooterColumns(columnsEl, footerTabs) {
    const currentFile = getCurrentPageFile();

    columnsEl.classList.add('footer-columns--dynamic');
    columnsEl.style.setProperty('--footer-column-count', String(Math.max(footerTabs.length, 1)));
    columnsEl.innerHTML = footerTabs
      .map((tab, tabIndex) => {
        const tabFile = String(tab.file || '').toLowerCase();
        const isCurrentTab = tabFile && tabFile === currentFile;
        const title = String(tab.name || tab.id || '').toUpperCase();
        const safeHref = tab.file || '#';

        const visibleItems = (Array.isArray(tab.items) ? tab.items : []).filter(item => item && item.visible !== false);
        const linksHtml = visibleItems.length
          ? visibleItems
              .map((item, itemIndex) => {
                const label = toTitleCase(item.title || '');
                if (isCurrentTab && overlay && projectsData.length) {
                  return `<a href="#" class="footer-project-link" data-footer-current="1" data-project="${itemIndex}">${label}</a>`;
                }
                return `<a href="${safeHref}" class="footer-project-link">${label}</a>`;
              })
              .join('')
          : `<a href="${safeHref}" class="footer-project-link">${toTitleCase(title)}</a>`;

        return `
          <div class="footer-column" data-footer-tab="${tab.id || tabIndex}">
            <div class="footer-projects-wrapper">
              <h3 class="footer-section-title">${title}</h3>
              <nav class="footer-projects">${linksHtml}</nav>
            </div>
          </div>
        `;
      })
      .join('');

    columnsEl.querySelectorAll('[data-footer-current="1"]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const projectIndex = parseInt(link.dataset.project || '-1', 10);
        if (!Number.isFinite(projectIndex) || projectIndex < 0) return;
        openProject(projectIndex);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });

    applyFooterDensity(columnsEl);
  }

  // 푸터 전체 렌더링
  function renderFooterProjects() {
    const columnsEl = document.querySelector('.site-footer .footer-columns');
    if (!columnsEl) return;

    let footerData = {};
    const footerDataEl = document.getElementById('footerData');
    if (footerDataEl) {
      try {
        footerData = JSON.parse(footerDataEl.textContent || '{}');
      } catch (e) {
        console.warn('footerData 파싱 실패:', e);
      }
    }

    const navTabs = Array.from(document.querySelectorAll('.nav-links .nav-link'))
      .map(link => ({
        id: (link.textContent || '').trim().toLowerCase(),
        name: (link.textContent || '').trim(),
        file: link.getAttribute('href') || '',
        items: []
      }))
      .filter(tab => tab.file && !tab.file.toLowerCase().includes('about.html'));
    const navFileSet = new Set(navTabs.map(tab => String(tab.file || '').toLowerCase()));

    let footerTabs = normalizeFooterTabsData(footerData);
    if (navFileSet.size) {
      footerTabs = footerTabs.filter(tab => navFileSet.has(String(tab.file || '').toLowerCase()));
    }
    if (!footerTabs.length) {
      footerTabs = navTabs;
    }
    if (!footerTabs.length) return;

    renderFooterColumns(columnsEl, footerTabs);
    window.addEventListener('resize', () => applyFooterDensity(columnsEl));
  }
  
  // 썸네일 이미지 lazy loading + fallback 처리
  function handleThumbnailFallback() {
    const thumbs = document.querySelectorAll('.grid-thumb');
    if (!thumbs.length) return;

    // iPad/Safari에서 observer 콜백 지연 시 그리드가 비어 보이지 않도록 기본 표시
    thumbs.forEach(thumb => {
      thumb.classList.add('loaded');
    });

    // Intersection Observer로 뷰포트에 보일 때 이미지 로드
    const observerOptions = {
      root: null,
      rootMargin: '100px', // 100px 전에 미리 로드 시작
      threshold: 0.01
    };

    // 구형 브라우저(일부 iPad 포함) 호환 fallback
    if (typeof IntersectionObserver !== 'function') {
      thumbs.forEach(thumb => {
        loadThumbnail(thumb);
      });
      return;
    }

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
      imageObserver.observe(thumb);
    });

    // Observer가 동작하지 않는 환경에서 최종 fallback
    window.setTimeout(() => {
      thumbs.forEach(thumb => {
        if (!thumb.classList.contains('loaded')) {
          loadThumbnail(thumb);
        }
      });
    }, 1200);
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
    clearArmedGridItem();

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

    // Eagerly load the first visible images for faster first impression
    warmupDetailImages(detail, 6);
    
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
    const lazyImages = Array.from(container.querySelectorAll('.lazy-image'));
    if (!lazyImages.length) return;

    if (typeof IntersectionObserver !== 'function') {
      lazyImages.forEach((img) => loadLazyImageWithFallback(img));
      return;
    }
    
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
    lazyImages.forEach(img => lazyObserver.observe(img));
  }

  function loadLazyImageWithFallback(img) {
    if (!img || (img.classList.contains('lazy-loaded') && img.src && img.complete && img.naturalWidth > 0)) {
      return;
    }

    const srcJpg = img.dataset.src;
    const srcWebp = img.dataset.srcWebp;
    if (!srcJpg && !srcWebp) return;

    img.onload = function() {
      img.classList.add('lazy-loaded');
    };
    img.onerror = function() {
      if (srcWebp && !img.dataset.triedWebp) {
        img.dataset.triedWebp = '1';
        img.src = srcWebp;
      } else if (img.parentElement) {
        img.parentElement.style.display = 'none';
      }
    };
    img.src = srcJpg || srcWebp;
  }

  function warmupDetailImages(container, count) {
    const warmupTargets = Array.from(container.querySelectorAll('.lazy-image')).slice(0, count);
    warmupTargets.forEach((img) => loadLazyImageWithFallback(img));
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
    if (typeof IntersectionObserver !== 'function') {
      gridObserver = null;
      return;
    }

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
    const touchLikeDevice = window.matchMedia('(hover: none), (pointer: coarse)').matches;
    const shouldRevealImmediately = touchLikeDevice || window.matchMedia('(max-width: 1024px)').matches || !gridObserver;

    gridItemContainers.forEach((item, index) => {
      item.classList.add('reveal');

      if (shouldRevealImmediately) {
        item.classList.add('revealed');
        item.style.transitionDelay = '0s';
        return;
      }

      item.style.transitionDelay = `${index * 0.05}s`;
      gridObserver.observe(item);
    });

    // Observer가 누락되거나 지연되는 환경(iPad Safari 포함)에서 안전하게 표시
    window.setTimeout(() => {
      gridItemContainers.forEach((item) => {
        if (item.classList.contains('reveal') && !item.classList.contains('revealed')) {
          item.classList.add('revealed');
        }
      });
    }, 1300);
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

    const scrollImages = container.querySelectorAll(
      '.project-images--sub .project-image, .model-image, .project-images--extra .project-image'
    );

    const disableOverlayRevealMotion =
      window.matchMedia('(hover: none), (pointer: coarse)').matches ||
      window.matchMedia('(max-width: 1024px)').matches ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    // Add reveal class to all
    [cover, title, meta, desc].forEach(el => {
      if (el) el.classList.add('reveal');
    });

    if (disableOverlayRevealMotion) {
      [cover, title, meta, desc].forEach(el => {
        if (el) el.classList.add('revealed');
      });
      scrollImages.forEach((img) => {
        img.classList.add('reveal', 'revealed');
        img.style.transitionDelay = '0s';
      });
      return;
    }
    
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
