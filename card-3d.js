/**
 * IIChE Website — Universal 3D Hover Lift & Interactive Tilt Engine
 * High-performance, hardware-accelerated 3D hover effects with zero frame lag.
 */

(function () {
    'use strict';

    // Disable 3D cursor tilt on touch / mobile devices for maximum scroll FPS
    const isTouch = window.matchMedia('(pointer: coarse)').matches || ('ontouchstart' in window) || window.innerWidth < 768;

    const CARD_SELECTORS = [
        '.glass-card',
        '.liquid-glass-card',
        '.event-item',
        '.glass-box',
        '.board-card',
        '.login-card',
        '.domain-card',
        '.team-card',
        '.shine-card',
        '.department-button',
        '.bento-card',
        '[data-3d-card]'
    ].join(', ');

    const CONFIG = {
        maxTilt: 4,
        scale: 1.03,
        liftY: -5,
        liftZ: 16,
        perspective: 1000,
        transitionRest: 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease',
        transitionMove: 'transform 0.08s cubic-bezier(0.2, 0.8, 0.2, 1)'
    };

    function init3DCard(card) {
        if (card.dataset.noTilt === 'true' || card.dataset.tilt3dInitialized === 'true' || card.classList.contains('no-tilt')) return;
        card.dataset.tilt3dInitialized = 'true';

        if (isTouch) return; // Native CSS hover/active is sufficient on mobile

        let bounds = null;
        let rafId = null;
        let isHovered = false;

        const maxTilt = card.dataset.tiltMax ? parseFloat(card.dataset.tiltMax) : CONFIG.maxTilt;
        const scale = card.dataset.tiltScale ? parseFloat(card.dataset.tiltScale) : CONFIG.scale;
        const liftY = card.dataset.tiltLiftY ? parseFloat(card.dataset.tiltLiftY) : CONFIG.liftY;
        const liftZ = card.dataset.tiltLiftZ ? parseFloat(card.dataset.tiltLiftZ) : CONFIG.liftZ;

        function updateCardTransform(clientX, clientY) {
            if (!bounds || !isHovered) return;

            const x = clientX - bounds.left;
            const y = clientY - bounds.top;

            const normX = Math.max(-1, Math.min(1, ((x / bounds.width) * 2) - 1));
            const normY = Math.max(-1, Math.min(1, ((y / bounds.height) * 2) - 1));

            const rotateX = (-normY * maxTilt).toFixed(2);
            const rotateY = (normX * maxTilt).toFixed(2);

            card.style.transform = `perspective(${CONFIG.perspective}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(${liftY}px) translateZ(${liftZ}px) scale3d(${scale}, ${scale}, ${scale})`;
        }

        card.addEventListener('mouseenter', (e) => {
            isHovered = true;
            bounds = card.getBoundingClientRect();
            card.style.willChange = 'transform';
            card.style.transformStyle = 'preserve-3d';
            card.style.transition = CONFIG.transitionMove;
            card.style.zIndex = '30';
            updateCardTransform(e.clientX, e.clientY);
        }, { passive: true });

        card.addEventListener('mousemove', (e) => {
            if (!isHovered) return;
            if (rafId) cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(() => updateCardTransform(e.clientX, e.clientY));
        }, { passive: true });

        card.addEventListener('mouseleave', () => {
            isHovered = false;
            if (rafId) cancelAnimationFrame(rafId);
            card.style.transition = CONFIG.transitionRest;
            card.style.transform = `perspective(${CONFIG.perspective}px) rotateX(0deg) rotateY(0deg) translateY(0px) translateZ(0px) scale3d(1, 1, 1)`;
            card.style.zIndex = '';
            setTimeout(() => {
                if (!isHovered) card.style.willChange = 'auto';
            }, 450);
        }, { passive: true });
    }

    function scanAndApply() {
        const cards = document.querySelectorAll(CARD_SELECTORS);
        for (let i = 0; i < cards.length; i++) {
            init3DCard(cards[i]);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scanAndApply);
    } else {
        scanAndApply();
    }

    // Debounced MutationObserver prevents layout thrashing on DOM updates
    let mutationTimeout = null;
    const observer = new MutationObserver(() => {
        if (mutationTimeout) clearTimeout(mutationTimeout);
        mutationTimeout = setTimeout(scanAndApply, 200);
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    window.IIChE3D = {
        scan: scanAndApply,
        initCard: init3DCard
    };
})();
