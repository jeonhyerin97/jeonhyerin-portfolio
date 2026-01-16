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
        projectsData = JSON.parse(projectsDataEl.textContent);
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

      if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
      if (backdrop) backdrop.addEventListener('click', closeOverlay);
      if (prevBtn) prevBtn.addEventListener('click', goToPrevProject);
      if (nextBtn) nextBtn.addEventListener('click', goToNextProject);
    }

    // Global keyboard events
    document.addEventListener('keydown', handleKeyDown);

    // Add entrance animations to grid items
    animateGridItems();
    
    // 썸네일 이미지 fallback 처리 (thumb.jpg → cover.jpg)
    handleThumbnailFallback();
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
  
  // 개별 썸네일 로드
  function loadThumbnail(thumb) {
    const thumbUrl = thumb.dataset.thumb;
    const coverUrl = thumb.dataset.cover;
    
    if (!thumbUrl && !coverUrl) {
      thumb.classList.add('loaded');
      return;
    }
    
    const img = new Image();
    
    img.onload = function() {
      thumb.style.backgroundImage = `url('${thumbUrl}')`;
      thumb.classList.add('loaded');
    };
    
    img.onerror = function() {
      // thumb.jpg 실패시 cover.jpg로 fallback
      if (coverUrl) {
        const fallbackImg = new Image();
        fallbackImg.onload = function() {
          thumb.style.backgroundImage = `url('${coverUrl}')`;
          thumb.classList.add('loaded');
        };
        fallbackImg.onerror = function() {
          // 둘 다 실패시 placeholder
          thumb.classList.add('grid-thumb--placeholder', 'loaded');
        };
        fallbackImg.src = coverUrl;
      } else {
        thumb.classList.add('grid-thumb--placeholder', 'loaded');
      }
    };
    
    img.src = thumbUrl;
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
  
  function renderProjectDetail(project) {
    if (!overlay || !project) return;

    const detail = overlay.querySelector('.project-detail');
    if (!detail) return;

    // Determine if this is a drawings page or projects page
    const isDrawings = window.location.pathname.includes('drawings');

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

    // Determine image base path
    const imageFolder = isDrawings ? 'images/drawings' : 'images/projects';
    const slug = project.slug || project.title.toLowerCase().replace(/\s+/g, '-');
    const basePath = `${imageFolder}/${slug}`;

    // Generate sub images (01.jpg - 20.jpg) with lazy loading
    let subImagesHTML = '';
    for (let i = 1; i <= 20; i++) {
      const num = i.toString().padStart(2, '0');
      subImagesHTML += `
        <figure class="project-image">
          <img data-src="${basePath}/${num}.jpg" alt="${escapeHtml(project.title)} sub ${i}" class="lazy-image" onerror="this.parentElement.style.display='none';">
        </figure>
      `;
    }

    // Generate model images (model_images/1.jpg - model_images/30.jpg) with lazy loading
    let modelImagesHTML = '';
    for (let i = 1; i <= 30; i++) {
      modelImagesHTML += `
        <figure class="model-image" data-model-index="${i}">
          <img data-src="${basePath}/model_images/${i}.jpg" alt="${escapeHtml(project.title)} model ${i}" class="lazy-image" onerror="this.parentElement.style.display='none';">
        </figure>
      `;
    }

    // Generate slide images (slide_images/1.jpg - slide_images/20.jpg) with lazy loading
    let slideImagesHTML = '';
    for (let i = 1; i <= 20; i++) {
      slideImagesHTML += `
        <figure class="project-image">
          <img data-src="${basePath}/slide_images/${i}.jpg" alt="${escapeHtml(project.title)} slide ${i}" class="lazy-image" onerror="this.parentElement.style.display='none';">
        </figure>
      `;
    }

    // Render full detail - Side-by-side layout: image left, text right
    // main.jpg를 먼저 시도하고, 없으면 cover.jpg로 fallback
    detail.innerHTML = `
      <!-- Hero Section: Image Left, Text Right -->
      <div class="project-hero">
        <figure class="project-cover">
          <img src="${basePath}/main.jpg" alt="${escapeHtml(project.title)} main" class="project-cover-image" onerror="this.src='${basePath}/cover.jpg'; this.onerror=function(){this.style.display='none'; this.parentElement.innerHTML='<div class=\\'image-placeholder project-cover-image\\'></div>';};">
        </figure>

        <div class="project-content">
          <header class="project-header">
            <h2 class="project-title">${escapeHtml(project.title)}</h2>
          </header>

          <div class="project-meta">
            ${metaHTML}
          </div>

          <div class="project-description">
            <p>${escapeHtml(project.description)}</p>
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
  }
  
  // Detail 페이지 이미지 lazy loading
  function initDetailLazyLoading(container) {
    const lazyImages = container.querySelectorAll('.lazy-image');
    
    const observerOptions = {
      root: container.closest('.overlay-scroll'),
      rootMargin: '200px',
      threshold: 0.01
    };
    
    const lazyObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.classList.add('lazy-loaded');
            observer.unobserve(img);
          }
        }
      });
    }, observerOptions);
    
    lazyImages.forEach(img => lazyObserver.observe(img));
  }

  // Wait for model images to load then adjust grid (with lazy loading support)
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
      const src = img.dataset.src || img.src;
      if (!src) {
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
      
      // 새로 로드
      img.src = src;
      img.classList.add('lazy-loaded');
      
      img.addEventListener('load', () => {
        loadedCount++;
        checkComplete();
      });
      img.addEventListener('error', () => {
        errorCount++;
        img.parentElement.style.display = 'none';
        checkComplete();
      });
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
  // Animations
  // ============================================
  
  function animateGridItems() {
    gridItemContainers.forEach((item, index) => {
      item.style.opacity = '0';
      item.style.transform = 'translateY(20px)';
      
      setTimeout(() => {
        item.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        item.style.opacity = '1';
        item.style.transform = 'translateY(0)';
      }, 100 + (index * 80));
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
  // Initialize on DOM Ready
  // ============================================
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      init();
      bindImageClicks();
      bindImageHover();
    });
  } else {
    init();
    bindImageClicks();
    bindImageHover();
  }

})();
