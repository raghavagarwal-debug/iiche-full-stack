function initLenisScroll() {
    // Inject custom scrollbar style globally
    const style = document.createElement('style');
    style.innerHTML = `
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #010a08;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(16, 185, 129, 0.2);
            border-radius: 9999px;
            border: 2px solid #010a08;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(16, 185, 129, 0.45);
        }
        * {
            scrollbar-width: thin;
            scrollbar-color: rgba(16, 185, 129, 0.2) #010a08;
        }
    `;
    document.head.appendChild(style);

    if (typeof Lenis === 'undefined') {
        console.warn('Lenis Smooth Scroll CDN is not loaded.');
        return;
    }

    const scrollContainer = document.getElementById('main-content');
    let lenis;

    const isTouchDevice = window.matchMedia('(pointer: coarse)').matches || ('ontouchstart' in window) || window.innerWidth < 768;

    if (isTouchDevice) {
        // Use native momentum scrolling on mobile touch devices for ultra-smooth 60-120fps touch scrolling
        if (scrollContainer) {
            scrollContainer.style.scrollBehavior = 'smooth';
            scrollContainer.style.webkitOverflowScrolling = 'touch';
        } else {
            document.documentElement.style.scrollBehavior = 'smooth';
        }
        window.lenis = {
            scroll: scrollContainer ? scrollContainer.scrollTop : window.scrollY,
            scrollTo: function (target, options) {
                let elem = typeof target === 'string' ? document.querySelector(target) : target;
                if (elem) {
                    elem.scrollIntoView({ behavior: 'smooth' });
                } else if (typeof target === 'number') {
                    (scrollContainer || window).scrollTo({ top: target, behavior: 'smooth' });
                }
            },
            stop: function () { },
            start: function () { },
            on: function (event, callback) {
                const container = scrollContainer || window;
                container.addEventListener('scroll', () => {
                    callback({ scroll: container.scrollTop || window.scrollY });
                }, { passive: true });
            }
        };
        const updateScrollVal = () => {
            window.lenis.scroll = scrollContainer ? scrollContainer.scrollTop : window.scrollY;
        };
        (scrollContainer || window).addEventListener('scroll', updateScrollVal, { passive: true });
    } else {
        if (scrollContainer) {
            // used in index.html for desktop wheel smooth scrolling
            const scrollContent = document.getElementById('scroll-content');
            lenis = new Lenis({
                wrapper: scrollContainer,
                content: scrollContent || scrollContainer,
                lerp: 0.06,
                smoothWheel: true,
                wheelMultiplier: 1.0,
                touchMultiplier: 0
            });
        } else {
            // used in other pages on desktop
            lenis = new Lenis({
                lerp: 0.06,
                smoothWheel: true,
                wheelMultiplier: 1.0,
                touchMultiplier: 0
            });
        }
        function raf(time) {
            lenis.raf(time);
            requestAnimationFrame(raf);
        }
        requestAnimationFrame(raf);
        if (typeof ScrollTrigger !== 'undefined') {
            lenis.on('scroll', ScrollTrigger.update);

            ScrollTrigger.scrollerProxy(scrollContainer || document.body, {
                scrollTop(value) {
                    return arguments.length ? lenis.scrollTo(value, { immediate: true }) : lenis.scroll;
                },
                getBoundingClientRect() {
                    return {
                        top: 0,
                        left: 0,
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                }
            });
        }
        window.lenis = lenis;
    }
    if (scrollContainer && window.location.hash === '#blogs-section') {
        lenis.scrollTo(0, { immediate: true });
    }
    const wrapper = document.querySelector('.relative.z-10');
    if (wrapper && !scrollContainer) {
        gsap.to(wrapper, { opacity: 1, duration: 1.2, ease: 'power2.out' });
    }

    // Dynamically insert back-to-top button if not present in the DOM
    setTimeout(() => {
        let backToTopBtn = document.getElementById('back-to-top');
        if (!backToTopBtn) {
            backToTopBtn = document.createElement('button');
            backToTopBtn.id = 'back-to-top';
            backToTopBtn.title = 'Scroll to Top';
            backToTopBtn.className = 'fixed bottom-8 right-8 z-50 w-12 h-12 rounded-full bg-gradient-to-tr from-emerald-600 to-cyan-500 text-white flex items-center justify-center shadow-[0_10px_25px_-5px_rgba(16,185,129,0.4)] border border-emerald-400/20 hover:border-emerald-400/50 hover:shadow-[0_15px_30px_rgba(16,185,129,0.6)] hover:-translate-y-1 opacity-0 translate-y-4 pointer-events-none transition-all duration-500 active:scale-95 cursor-pointer';
            backToTopBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
                </svg>
            `;
            const container = document.getElementById('main-content') || document.body;
            container.appendChild(backToTopBtn);
        }

        backToTopBtn.addEventListener('click', () => {
            if (window.lenis) {
                const target = document.getElementById('hero-section') || 0;
                window.lenis.scrollTo(target, {
                    duration: 1.2,
                    ease: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
                });
            }
        });
    }, 100);

    setupGlowSeparators();
}

function setupGlowSeparators() {
    const separators = Array.from(document.querySelectorAll('.glow-separator, div[class*="h-[1px]"][class*="bg-gradient"]'));

    separators.forEach(sep => {
        const computedStyle = window.getComputedStyle(sep);
        if (computedStyle.position === 'static') {
            sep.style.position = 'relative';
        }
        sep.style.overflow = 'hidden';

        let glowColor = 'rgba(16, 185, 129, 0.7)';
        const className = sep.getAttribute('class') || '';
        if (className.includes('via-amber')) {
            glowColor = 'rgba(245, 158, 11, 0.7)';
        } else if (className.includes('via-cyan')) {
            glowColor = 'rgba(6, 182, 212, 0.7)';
        } else if (className.includes('via-emerald-500/20')) {
            glowColor = 'rgba(16, 185, 129, 0.5)';
        } else if (className.includes('via-emerald-500/25')) {
            glowColor = 'rgba(16, 185, 129, 0.7)';
        } else if (className.includes('via-emerald-500/40')) {
            glowColor = 'rgba(16, 185, 129, 0.8)';
        } else if (className.includes('via-[#10b981]') || className.includes('via-emerald-500')) {
            glowColor = 'rgba(16, 185, 129, 0.9)';
        }

        const glow = document.createElement('div');
        glow.className = 'absolute top-0 bottom-0 pointer-events-none';
        glow.style.width = '30%';
        glow.style.height = '100%';
        glow.style.background = `linear-gradient(to right, transparent, ${glowColor}, transparent)`;
        glow.style.transform = 'translate3d(-100%, 0, 0)';
        glow.style.willChange = 'transform';

        sep.appendChild(glow);
        sep._glowElement = glow;
        sep._isVisible = false;
    });

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                entry.target._isVisible = entry.isIntersecting;
            });
        }, { threshold: 0 });

        separators.forEach(sep => observer.observe(sep));
    } else {
        separators.forEach(sep => sep._isVisible = true);
    }

    const updatePositions = () => {
        const viewportHeight = window.innerHeight;
        separators.forEach(sep => {
            if (!sep._isVisible) return;
            const rect = sep.getBoundingClientRect();

            const totalRange = viewportHeight + rect.height;
            const currentPosition = viewportHeight - rect.top;
            let progress = currentPosition / totalRange;

            progress = Math.max(0, Math.min(1, progress));

            const translationPercent = (progress * 4.3333 - 1) * 100;
            if (sep._glowElement) {
                sep._glowElement.style.transform = `translate3d(${translationPercent}%, 0, 0)`;
            }
        });
    };

    const handleScrollEffects = () => {
        const scrollTop = window.lenis ? window.lenis.scroll : (document.getElementById('main-content')?.scrollTop || window.scrollY);

        const nav = document.querySelector('nav');
        if (nav) {
            if (scrollTop > 50) {
                nav.classList.remove('top-8', 'bg-[#010a08]/50');
                nav.classList.add('top-4', 'bg-[#010a08]/85', 'border-emerald-500/20', 'shadow-[0_20px_50px_rgba(0,0,0,0.6)]');
            } else {
                nav.classList.add('top-8', 'bg-[#010a08]/50');
                nav.classList.remove('top-4', 'bg-[#010a08]/85', 'border-emerald-500/20', 'shadow-[0_20px_50px_rgba(0,0,0,0.6)]');
            }
        }

        const backToTopBtn = document.getElementById('back-to-top');
        if (backToTopBtn) {
            if (scrollTop > 500) {
                backToTopBtn.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-4');
                backToTopBtn.classList.add('opacity-100', 'translate-y-0');
            } else {
                backToTopBtn.classList.add('opacity-0', 'pointer-events-none', 'translate-y-4');
                backToTopBtn.classList.remove('opacity-100', 'translate-y-0');
            }
        }
    };

    let ticking = false;
    const requestTick = () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                updatePositions();
                handleScrollEffects();
                ticking = false;
            });
            ticking = true;
        }
    };

    window.addEventListener('scroll', requestTick, { passive: true });

    const scrollContainer = document.getElementById('main-content');
    if (scrollContainer) {
        scrollContainer.addEventListener('scroll', requestTick, { passive: true });
    }

    if (window.lenis) {
        window.lenis.on('scroll', requestTick);
    }

    updatePositions();
    setTimeout(updatePositions, 100);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLenisScroll);
} else {
    initLenisScroll();
}
