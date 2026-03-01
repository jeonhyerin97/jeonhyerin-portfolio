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
  const heroImagePreloadCache = new Map();
  const heroImageResolvedSrc = new Map();
  const APP_VERSION = '20260302-mobile-image-fast';
  const VERSIONED_HTML_FILES = new Set([
    'index.html',
    'projects.html',
    'drawings.html',
    'graphics.html',
    'about.html',
    'study.html',
    'dd.html',
    'd.html'
  ]);

  // ============================================
  // DOM Elements
  // ============================================
  
  const overlay = document.getElementById('projectOverlay');
  const gridItems = document.querySelectorAll('.grid-item-btn');
  const gridItemContainers = document.querySelectorAll('.grid-item');
  const projectsDataEl = document.getElementById('projectsData');

  function runInitStep(label, callback) {
    try {
      callback();
    } catch (error) {
      console.warn(`${label} failed:`, error);
    }
  }

  function appendVersionParam(rawHref) {
    if (!rawHref || rawHref === '#') return rawHref;
    if (/^(mailto:|tel:|javascript:)/i.test(rawHref)) return rawHref;

    let resolvedUrl;
    try {
      resolvedUrl = new URL(rawHref, window.location.href);
    } catch (error) {
      return rawHref;
    }

    if (resolvedUrl.origin !== window.location.origin) return rawHref;

    const fileName = (resolvedUrl.pathname.split('/').pop() || '').toLowerCase();
    if (!VERSIONED_HTML_FILES.has(fileName)) return rawHref;

    resolvedUrl.searchParams.set('v', APP_VERSION);
    return `${fileName}${resolvedUrl.search}${resolvedUrl.hash}`;
  }

  function versionInternalDocumentLinks() {
    document.querySelectorAll('a[href]').forEach(link => {
      const href = link.getAttribute('href');
      const versionedHref = appendVersionParam(href);
      if (versionedHref && versionedHref !== href) {
        link.setAttribute('href', versionedHref);
      }
    });
  }

  // ============================================
  // Initialize
  // ============================================
  
  function init() {
    runInitStep('versionInternalDocumentLinks', versionInternalDocumentLinks);

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
      const preloadHero = () => {
        const project = projectsData[index];
        if (project) preloadProjectHeroImage(project);
      };

      btn.addEventListener('pointerenter', preloadHero);
      btn.addEventListener('focus', preloadHero);
      btn.addEventListener('touchstart', preloadHero, { passive: true });

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

    runInitStep('renderFooterProjects', renderFooterProjects);
    runInitStep('initScrollReveal', initScrollReveal);
    runInitStep('animateGridItems', animateGridItems);
    runInitStep('handleThumbnailFallback', handleThumbnailFallback);
    runInitStep('updateArchiveCount', updateArchiveCount);
    runInitStep('primeInitialHeroImages', primeInitialHeroImages);
    runInitStep('openProjectFromQueryParam', openProjectFromQueryParam);
    runInitStep('applyAboutAffiliationMobileBreak', applyAboutAffiliationMobileBreak);
    runInitStep('syncAboutAlignmentAxis', syncAboutAlignmentAxis);
    const handleAboutResponsiveLayout = () => {
      runInitStep('syncAboutAlignmentAxis', syncAboutAlignmentAxis);
      runInitStep('applyAboutAffiliationMobileBreak', applyAboutAffiliationMobileBreak);
    };
    window.addEventListener('resize', handleAboutResponsiveLayout);
    window.addEventListener('load', handleAboutResponsiveLayout);
    
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

  function applyAboutAffiliationMobileBreak() {
    if (!document.body || !document.body.classList.contains('page-about')) return;

    const affiliation = document.querySelector('.about-affiliation');
    if (!affiliation) return;

    if (!affiliation.dataset.originalHtml) {
      affiliation.dataset.originalHtml = affiliation.innerHTML;
    }

    const originalHtml = affiliation.dataset.originalHtml || '';
    const isMobile = window.matchMedia('(max-width: 640px)').matches;

    if (!isMobile) {
      affiliation.innerHTML = originalHtml;
      return;
    }

    const mobileHtml = originalHtml.replace(
      /,\s*Dept\. of\s*/i,
      ',<br>Dept. of '
    );
    affiliation.innerHTML = mobileHtml;
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

  function getPageFileName(rawRef) {
    if (!rawRef) return '';

    try {
      const resolvedUrl = new URL(rawRef, window.location.href);
      return (resolvedUrl.pathname.split('/').pop() || '').toLowerCase();
    } catch (error) {
      return String(rawRef || '').split('?')[0].split('#')[0].split('/').pop().toLowerCase();
    }
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
        const tabFile = getPageFileName(tab.file || '');
        const isCurrentTab = tabFile && tabFile === currentFile;
        const title = String(tab.name || tab.id || '').toUpperCase();
        const safeHref = appendVersionParam(tab.file || '#');

        const visibleItems = (Array.isArray(tab.items) ? tab.items : []).filter(item => item && item.visible !== false);
        const linksHtml = visibleItems.length
          ? visibleItems
              .map((item, itemIndex) => {
                const label = toTitleCase(item.title || '');
                const projectParam = encodeURIComponent(String(item.title || ''));
                const popupHref = projectParam
                  ? `${safeHref}${safeHref.includes('?') ? '&' : '?'}project=${projectParam}&autopopup=1`
                  : safeHref;
                if (isCurrentTab && overlay && projectsData.length) {
                  return `<a href="#" class="footer-project-link" data-footer-current="1" data-project="${itemIndex}">${label}</a>`;
                }
                return `<a href="${popupHref}" class="footer-project-link">${label}</a>`;
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
      .filter(tab => {
        const pageFile = getPageFileName(tab.file || '');
        return pageFile && pageFile !== 'about.html';
      });
    const navFileSet = new Set(navTabs.map(tab => getPageFileName(tab.file || '')));

    let footerTabs = normalizeFooterTabsData(footerData);
    if (navFileSet.size) {
      footerTabs = footerTabs.filter(tab => navFileSet.has(getPageFileName(tab.file || '')));
    }
    const hasVisibleFooterItems = footerTabs.some(tab =>
      Array.isArray(tab.items) && tab.items.some(item => item && item.visible !== false)
    );
    if (!footerTabs.length || !hasVisibleFooterItems) return;

    renderFooterColumns(columnsEl, footerTabs);
    window.addEventListener('resize', () => applyFooterDensity(columnsEl));
  }
  
  // 썸네일 이미지 lazy loading + fallback 처리
  function handleThumbnailFallback() {
    const thumbs = document.querySelectorAll('.grid-thumb');
    if (!thumbs.length) return;
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    thumbs.forEach(thumb => {
      thumb.classList.add('loaded');
      const hasInlineBg = String(thumb.style.backgroundImage || '').includes('url(');
      if (isMobile && hasInlineBg) return;
      loadThumbnail(thumb);
    });
  }

  function getProjectImageBasePath(project) {
    if (!project) return '';

    const isDrawings = window.location.pathname.includes('drawings');
    const isGraphics = window.location.pathname.includes('graphics');
    const imageFolder = isDrawings ? 'images/drawings' : (isGraphics ? 'images/graphics' : 'images/projects');
    const slug = project.slug || project.title.toLowerCase().replace(/\s+/g, '-');
    return `${imageFolder}/${slug}`;
  }

  function getProjectHeroCandidates(project) {
    const basePath = getProjectImageBasePath(project);
    if (!basePath) return [];

    return [
      `${basePath}/main.jpg`,
      `${basePath}/main.webp`,
      `${basePath}/cover.jpg`,
      `${basePath}/cover.webp`,
      `${basePath}/thumb.jpg`,
      `${basePath}/thumb.webp`
    ];
  }

  function preloadImageSequence(candidates) {
    if (!candidates.length) return Promise.resolve('');

    return new Promise((resolve) => {
      const tryLoad = (index) => {
        if (index >= candidates.length) {
          resolve('');
          return;
        }

        const img = new Image();
        img.onload = () => resolve(candidates[index]);
        img.onerror = () => tryLoad(index + 1);
        img.src = candidates[index];
      };

      tryLoad(0);
    });
  }

  function preloadProjectHeroImage(project) {
    const basePath = getProjectImageBasePath(project);
    if (!basePath) return Promise.resolve('');

    if (heroImagePreloadCache.has(basePath)) {
      return heroImagePreloadCache.get(basePath);
    }

    const preloadPromise = preloadImageSequence(getProjectHeroCandidates(project)).then((resolvedSrc) => {
      if (resolvedSrc) {
        heroImageResolvedSrc.set(basePath, resolvedSrc);
      }
      return resolvedSrc;
    });

    heroImagePreloadCache.set(basePath, preloadPromise);
    return preloadPromise;
  }

  function primeInitialHeroImages() {
    if (!projectsData.length) return;

    if (window.matchMedia('(max-width: 768px)').matches) return;

    const preloadCount = 2;
    const kickoff = () => {
      projectsData.slice(0, preloadCount).forEach((project, index) => {
        window.setTimeout(() => {
          preloadProjectHeroImage(project);
        }, index * 120);
      });
    };

    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(kickoff, { timeout: 1200 });
      return;
    }

    window.setTimeout(kickoff, 120);
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
    
    const urlsToTry = [];
    const seenUrls = new Set();
    function pushCandidate(url) {
      if (!url || seenUrls.has(url)) return;
      seenUrls.add(url);
      urlsToTry.push(url);
    }
    function pushCandidates(url) {
      if (!url) return;
      const isWebp = /\.webp($|\?)/i.test(url);
      if (isWebp) {
        pushCandidate(url);
        pushCandidate(url.replace(/\.webp($|\?)/i, '.jpg$1'));
        return;
      }
      pushCandidate(getWebpUrl(url));
      pushCandidate(url);
    }

    // Prefer smaller webp assets first to reduce mobile transfer size.
    pushCandidates(thumbUrl);
    pushCandidates(coverUrl);
    
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
    preloadProjectHeroImage(projectsData[index]);

    // Update overlay content
    renderProjectDetail(projectsData[index]);

    // Update navigation buttons
    updateNavButtons();

    // Open overlay
    isOverlayOpen = true;
    overlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('overlay-open');

    const detail = overlay.querySelector('.project-detail');
    if (detail) {
      requestOverlayRevealRefresh(detail);
    }

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
      const detail = overlay ? overlay.querySelector('.project-detail') : null;
      if (detail) {
        requestOverlayRevealRefresh(detail);
      }
    }
  }

  function goToNextProject() {
    if (currentProjectIndex < projectsData.length - 1) {
      currentProjectIndex++;
      renderProjectDetail(projectsData[currentProjectIndex]);
      updateNavButtons();
      scrollOverlayToTop();
      const detail = overlay ? overlay.querySelector('.project-detail') : null;
      if (detail) {
        requestOverlayRevealRefresh(detail);
      }
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
    detail.classList.add('project-detail--desktop-sidebar');
    detail.classList.remove('project-detail--lang-kr');

    // Build meta HTML based on available fields
    let metaHTML = '';

    const baseMetaFields = [
      { key: 'location', label: 'LOCATION' },
      { key: 'duration', label: 'DURATION' },
      { key: 'program', label: 'PROGRAM' },
      { key: 'studio', label: 'STUDIO' },
    ];
    const reservedMetaLabels = new Set([
      'LOCATION',
      'DURATION',
      'PROGRAM',
      'STUDIO'
    ]);
    const baseMetaFieldMap = new Map(baseMetaFields.map((field) => [field.key, field]));
    const customMetaFields = Array.isArray(project.custom_fields)
      ? project.custom_fields
          .filter((field) => {
            if (!field || !field.label || !field.value) return false;
            return !reservedMetaLabels.has(String(field.label).trim().toUpperCase());
          })
          .map((field, index) => {
            const fieldId = typeof field.id === 'string' && field.id ? field.id : `index-${index}`;
            const normalizedLabel = String(field.label || '').trim().toUpperCase();
            const aliases = new Set([
              fieldId,
              `custom:${fieldId}`,
              normalizedLabel ? `label:${normalizedLabel}` : ''
            ]);
            return {
              id: fieldId,
              token: `custom:${fieldId}`,
              label: field.label,
              value: field.value,
              aliases,
            };
          })
      : [];
    const customMetaFieldMap = new Map(customMetaFields.map((field) => [field.token, field]));
    const orderedMetaKeys = [];

    if (project.team && !customMetaFields.some((field) => String(field.label || '').trim().toUpperCase() === 'TEAM')) {
      const teamField = {
        id: 'legacy-team',
        token: 'custom:legacy-team',
        label: 'TEAM',
        value: project.team,
        aliases: new Set(['legacy-team', 'custom:legacy-team', 'label:TEAM'])
      };
      customMetaFields.push(teamField);
      customMetaFieldMap.set(teamField.token, teamField);
    }

    function resolveCustomMetaField(key) {
      const normalizedKey = String(key || '').trim();
      if (!normalizedKey) return null;

      if (customMetaFieldMap.has(normalizedKey)) {
        return customMetaFieldMap.get(normalizedKey);
      }

      const prefixedKey = normalizedKey.startsWith('custom:') ? normalizedKey : `custom:${normalizedKey}`;
      if (customMetaFieldMap.has(prefixedKey)) {
        return customMetaFieldMap.get(prefixedKey);
      }

      const normalizedLabelKey = normalizedKey.startsWith('label:')
        ? `label:${normalizedKey.slice(6).toUpperCase()}`
        : `label:${normalizedKey.toUpperCase()}`;

      return customMetaFields.find((field) => field.aliases.has(normalizedKey) || field.aliases.has(prefixedKey) || field.aliases.has(normalizedLabelKey)) || null;
    }

    if (Array.isArray(project.meta_field_order)) {
      project.meta_field_order.forEach((key) => {
        let normalizedKey = key;
        const customField = resolveCustomMetaField(key);
        if (!baseMetaFieldMap.has(normalizedKey) && customField) {
          normalizedKey = customField.token;
        }
        if ((baseMetaFieldMap.has(normalizedKey) || customMetaFieldMap.has(normalizedKey)) && !orderedMetaKeys.includes(normalizedKey)) {
          orderedMetaKeys.push(normalizedKey);
        }
      });
    }

    baseMetaFields.forEach((field) => {
      if (!orderedMetaKeys.includes(field.key)) {
        orderedMetaKeys.push(field.key);
      }
    });
    customMetaFields.forEach((field) => {
      if (!orderedMetaKeys.includes(field.token)) {
        orderedMetaKeys.push(field.token);
      }
    });

    orderedMetaKeys.forEach((key) => {
      const baseField = baseMetaFieldMap.get(key);
      if (baseField) {
        const value = project[key];
        if (!value) return;

        metaHTML += `
          <div class="meta-item">
            <span class="meta-label">${baseField.label}</span>
            <span class="meta-value">${renderLinkedText(value)}</span>
          </div>
        `;
        return;
      }

      const customField = customMetaFieldMap.get(key);
      if (!customField || !customField.value) return;

      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">${escapeHtml(customField.label)}</span>
          <span class="meta-value">${renderLinkedText(customField.value)}</span>
        </div>
      `;
    });

    // 커스텀 필드 렌더링
    const slug = project.slug || project.title.toLowerCase().replace(/\s+/g, '-');
    if (project.year) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">YEAR</span>
          <span class="meta-value">${renderLinkedText(project.year)}</span>
        </div>
      `;
    }
    if (project.medium) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">MEDIUM</span>
          <span class="meta-value">${renderLinkedText(project.medium)}</span>
        </div>
      `;
    }
    if (project.series) {
      metaHTML += `
        <div class="meta-item">
          <span class="meta-label">SERIES</span>
          <span class="meta-value">${renderLinkedText(project.series)}</span>
        </div>
      `;
    }
    const basePath = getProjectImageBasePath(project);
    const heroCandidates = getProjectHeroCandidates(project);
    const heroInitialSrc = heroImageResolvedSrc.get(basePath) || heroCandidates[0] || '';
    const heroFallbackSources = heroCandidates.filter((src) => src !== heroInitialSrc);

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

    // Generate initial slide images (additional slides are discovered and appended after render)
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
          <img src="${heroInitialSrc}" alt="${escapeHtml(project.title)} main" class="project-cover-image"
            style="object-position: ${project.cover_position || 'center center'}; aspect-ratio: ${aspectRatio};"
            loading="eager" fetchpriority="high" decoding="async">
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

          ${(project.description || project.description_ko) ? `
          <div class="project-description">
            ${project.description ? `<p class="description-en">${renderLinkedText(project.description)}</p>` : ''}
            ${project.description_ko ? `<p class="description-ko" style="display: none;">${renderLinkedText(project.description_ko)}</p>` : ''}
          </div>
          ` : ''}
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

    const coverImage = detail.querySelector('.project-cover-image');
    setImageLoadingState(coverImage, true);
    attachHeroImageFallback(coverImage, heroFallbackSources);

    const detailImages = Array.from(detail.querySelectorAll('.lazy-image'));
    if (window.matchMedia('(max-width: 768px)').matches) {
      initDetailLazyLoading(detail);
      scheduleDetailWarmup(detail, 4);
      eagerLoadPriorityDetailImages(detail);
    } else {
      eagerLoadAllDetailImages(detailImages);
    }
    
    // 스크롤 시 이미지 서서히 나타나는 애니메이션 적용
    initOverlayScrollReveal(detail);
    
    // 캡션 로드 및 이미지 로드 시 적용
    loadCaptions(basePath).then(captions => {
      captionsCache = captions;
      if (Object.keys(captions).length > 0) {
        setupCaptionObservers(detail, captions);
      }
      discoverExtraSlideImages(detail, basePath, project.title, captions);
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

  async function discoverExtraSlideImages(container, basePath, projectTitle, captions) {
    const slideContainer = container.querySelector('.project-images--extra');
    if (!slideContainer) return;

    const existingSlides = slideContainer.querySelectorAll('.project-image').length;
    let nextIndex = Math.max(existingSlides + 1, 21);

    while (container.isConnected) {
      const resolvedSrc = await preloadImageSequence([
        `${basePath}/slide_images/${nextIndex}.jpg`,
        `${basePath}/slide_images/${nextIndex}.webp`
      ]);

      if (!resolvedSrc || !container.isConnected) {
        break;
      }

      const figure = document.createElement('figure');
      figure.className = 'project-image reveal-image';

      const img = document.createElement('img');
      img.className = 'lazy-image';
      img.alt = `${projectTitle} slide ${nextIndex}`;
      img.dataset.src = `${basePath}/slide_images/${nextIndex}.jpg`;
      img.dataset.srcWebp = `${basePath}/slide_images/${nextIndex}.webp`;

      const captionKey = `slide_${nextIndex}`;
      if (captions && captions[captionKey]) {
        img.dataset.caption = captions[captionKey];
        img.dataset.captionKey = captionKey;
      }

      figure.appendChild(img);
      slideContainer.appendChild(figure);

      setImageLoadingState(img, true);
      loadLazyImageWithFallback(img);

      if (img.dataset.caption) {
        const attachCaption = () => addCaptionToImage(figure, img.dataset.caption);
        if (img.complete && img.naturalWidth > 0) {
          attachCaption();
        } else {
          img.addEventListener('load', attachCaption, { once: true });
        }
      }

      requestOverlayRevealRefresh(container);
      nextIndex += 1;
    }
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
    caption.innerHTML = `<p>${renderLinkedText(captionText)}</p>`;
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
      rootMargin: window.matchMedia('(max-width: 768px)').matches ? '320px' : '200px',
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
      setImageLoadingState(img, false);
      return;
    }

    const srcJpg = img.dataset.src;
    const srcWebp = img.dataset.srcWebp;
    if (!srcJpg && !srcWebp) return;

    img.onload = function() {
      img.classList.add('lazy-loaded');
      setImageLoadingState(img, false);
    };
    img.onerror = function() {
      if (srcWebp && !img.dataset.triedWebp) {
        img.dataset.triedWebp = '1';
        img.src = srcWebp;
      } else if (img.parentElement) {
        setImageLoadingState(img, false);
        img.parentElement.style.display = 'none';
      }
    };
    img.src = srcJpg || srcWebp;
  }

  function eagerLoadAllDetailImages(images) {
    if (!images || !images.length) return;

    images.forEach((img, index) => {
      if (!img) return;
      setImageLoadingState(img, true);
      img.setAttribute('loading', 'eager');
      img.setAttribute('fetchpriority', index < 24 ? 'high' : 'auto');
      img.setAttribute('decoding', 'async');
      loadLazyImageWithFallback(img);
    });
  }

  function setImageLoadingState(img, isLoading) {
    if (!img) return;

    const frame = img.closest('.project-image, .model-image, .project-cover');
    if (!frame) return;

    frame.classList.toggle('image-loading', Boolean(isLoading));
    frame.classList.toggle('image-ready', !isLoading);
  }

  function warmupDetailImages(container, count) {
    const warmupTargets = Array.from(container.querySelectorAll('.lazy-image')).slice(0, count);
    warmupTargets.forEach((img) => loadLazyImageWithFallback(img));
  }

  function eagerLoadPriorityDetailImages(container) {
    if (!container) return;

    const loadSlides = () => {
      const slideImages = Array.from(
        container.querySelectorAll('.project-images--extra .lazy-image')
      );
      if (!slideImages.length) return;

      const eagerCount = window.matchMedia('(max-width: 768px)').matches
        ? Math.min(slideImages.length, 4)
        : Math.min(slideImages.length, 12);

      slideImages.slice(0, eagerCount).forEach((img, index) => {
        window.setTimeout(() => {
          loadLazyImageWithFallback(img);
        }, Math.min(index * 24, 240));
      });
    };

    const kickoff = () => {
      waitForModelImages(container);
      loadSlides();
    };

    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(() => {
        window.setTimeout(kickoff, 40);
      });
      return;
    }

    window.setTimeout(kickoff, 40);
  }

  function scheduleDetailWarmup(container, count) {
    const runWarmup = () => warmupDetailImages(container, count);

    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(runWarmup, { timeout: 900 });
      return;
    }

    window.setTimeout(runWarmup, 180);
  }

  function attachHeroImageFallback(img, fallbackSources) {
    if (!img) return;

    const sources = Array.isArray(fallbackSources) ? fallbackSources.slice() : [];
    let nextIndex = 0;

    const swapToPlaceholder = () => {
      const figure = img.parentElement;
      if (!figure) return;
      figure.classList.remove('image-loading');
      figure.classList.add('image-ready');
      figure.innerHTML = '<div class="image-placeholder project-cover-image"></div>';
    };

    const tryNextSource = () => {
      if (nextIndex >= sources.length) {
        img.onerror = null;
        swapToPlaceholder();
        return;
      }

      const nextSrc = sources[nextIndex++];
      img.src = nextSrc;
    };

    img.onerror = tryNextSource;

    img.onload = function() {
      setImageLoadingState(img, false);
    };

    if (!img.getAttribute('src')) {
      tryNextSource();
    } else if (img.complete && img.naturalWidth > 0) {
      setImageLoadingState(img, false);
    }
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
    const title = container.querySelector('.project-title');
    const meta = container.querySelector('.project-meta');
    const desc = container.querySelector('.project-description');

    const disableOverlayRevealMotion =
      window.matchMedia('(hover: none), (pointer: coarse)').matches ||
      window.matchMedia('(max-width: 1024px)').matches ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    // Add reveal class to all
    [title, meta, desc].forEach(el => {
      if (el) el.classList.add('reveal');
    });

    if (disableOverlayRevealMotion) {
      [title, meta, desc].forEach(el => {
        if (el) el.classList.add('revealed');
      });
      return;
    }
    
    // Trigger animations immediately when popup opens
    requestAnimationFrame(() => {
      // Title appears immediately
      if (title) title.classList.add('revealed');
      // Meta with slight delay
      setTimeout(() => {
        if (meta) meta.classList.add('revealed');
      }, 150);
      // Description after meta
      setTimeout(() => {
        if (desc) desc.classList.add('revealed');
      }, 300);
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

  function renderLinkedText(text) {
    if (!text) return '';

    const pattern = /\[size=(\d{2,3})\]([\s\S]*?)\[\/size\]|\[([^\]]+)\]\s*\(([^)]+)\)/g;
    let result = '';
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(text)) !== null) {
      result += escapeHtml(text.slice(lastIndex, match.index));

      if (match[1]) {
        const sizePercent = Number.parseInt(match[1], 10);
        const safeSize = Number.isFinite(sizePercent) ? Math.max(70, Math.min(sizePercent, 200)) : 125;
        const innerText = match[2] || '';
        result += `<span class="text-size-adjust" style="font-size: ${(safeSize / 100).toFixed(2)}em;">${renderLinkedText(innerText)}</span>`;
      } else {
        const linkText = match[3];
        const urlPart = match[4];
        const dividerIndex = urlPart.lastIndexOf('|');
        const rawUrl = dividerIndex >= 0 ? urlPart.slice(0, dividerIndex).trim() : urlPart.trim();
        const rawStyle = dividerIndex >= 0 ? urlPart.slice(dividerIndex + 1).trim().toLowerCase() : 'highlight';
        const className = rawStyle === 'underline' ? 'link-underline' : 'link-highlight';

        result += `<a href="${escapeHtml(rawUrl)}" class="${className}" target="_blank" rel="noopener">${escapeHtml(linkText)}</a>`;
      }
      lastIndex = pattern.lastIndex;
    }

    result += escapeHtml(text.slice(lastIndex));
    return result;
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

    if (typeof IntersectionObserver !== 'function' || !scrollContainer) {
      revealImages.forEach((img) => {
        img.classList.add('is-visible');
        img.style.transitionDelay = '0s';
      });
      return;
    }
    
    // Destroy previous observer if exists
    if (overlayRevealObserver) {
      overlayRevealObserver.disconnect();
    }
    
    // Toggle visibility on enter/exit so all overlay images can fade in and out while scrolling.
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
      rootMargin: '80px 0px -6% 0px',
      threshold: 0.01
    });
    
    // Add staggered delay for visual effect
    revealImages.forEach((img, index) => {
      // Stagger delay based on position (max 0.3s)
      const delay = Math.min((index % 5) * 0.08, 0.3);
      img.style.transitionDelay = `${delay}s`;
      overlayRevealObserver.observe(img);
    });

    revealImages.forEach((img) => {
      if (isRevealImageVisible(img, scrollContainer)) {
        img.classList.add('is-visible');
      } else {
        img.classList.remove('is-visible');
      }
    });
  }

  function isRevealImageVisible(el, scrollContainer) {
    if (!el) return false;

    const rect = el.getBoundingClientRect();
    if (scrollContainer) {
      const rootRect = scrollContainer.getBoundingClientRect();
      return rect.bottom > rootRect.top + 24 && rect.top < rootRect.bottom - 24;
    }

    return rect.bottom > 0 && rect.top < window.innerHeight;
  }

  function requestOverlayRevealRefresh(container) {
    if (!container) return;

    const refresh = () => initOverlayRevealImages(container);
    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(refresh);
      });
      return;
    }

    window.setTimeout(refresh, 32);
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
