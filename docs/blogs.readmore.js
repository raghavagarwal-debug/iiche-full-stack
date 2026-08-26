
const blogLinks = [
    "https://www.instagram.com/p/DMIV0imzs6K/?img_index=1",
    "https://www.instagram.com/p/DLR3vfRzbCm/?img_index=1",
    "https://www.instagram.com/p/DIc-MHDTDDa/?img_index=1",
    "https://www.instagram.com/p/DGMyUaHoIiZ/?img_index=1",
    "https://www.instagram.com/p/DFpxzvmzPDy/?img_index=1",
    "https://www.instagram.com/p/DEzhnk0zuEf/?img_index=1",
    "https://www.instagram.com/p/DEhaywBzO7S/?img_index=1",
    "https://www.instagram.com/p/DD9CY0-TXnr/?img_index=1",
    "https://www.instagram.com/p/DFITPHYqLQ_/?img_index=1",
    "https://www.instagram.com/p/DLj-ZtcTJZL/?img_index=1",
    "https://www.instagram.com/p/DFXbCiDTLKm/?img_index=1",
    "https://www.instagram.com/p/DK_Y-5zTEmK/?img_index=1",
];
const blogImages = [
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750780/safety-roller-crash-barrier_zopvzs.webp",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750780/nuclear-waste-1471361_1920.jpg.optimal_efwsyp.jpg",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750760/Are-Plants-Intelligent_wmjdk7.avif",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750761/Coco-bean-roaster-1024x683_d9p2xr.jpg",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750759/1lR2vmBPF3jh4r0oVEmXGqQ-scaled_fdljvw.jpg",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750760/1615132857304_oynus4.jpg",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782751334/ChatGPT_Image_Jun_29_2026_10_12_02_PM_uqgh5h.png",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782751276/ChatGPT_Image_Jun_29_2026_10_10_51_PM_xdlvnu.png",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750762/ChatGPT_Image_Jun_29_2026_10_02_11_PM_htfdy1.png",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750779/r1275777_17230771_kd3mvu.jpg",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750779/Future-of-Manufacturing-with-Industry-4.0_i5dmea.jpg",
    "https://res.cloudinary.com/dobshyhdz/image/upload/v1782750762/ChatGPT_Image_Jun_29_2026_09_56_50_PM_wkzfh4.png",
];

function connectBlogReadMoreLinks() {
    const marqueeTrack = document.querySelector('#blogs-section .animate-blogs-marquee');
    if (!marqueeTrack) {
        console.warn("Could not find blogs marquee container (#blogs-section .animate-blogs-marquee)");
        return;
    }

    const cards = marqueeTrack.children;
    if (cards.length === 0) return;

    for (let i = 0; i < cards.length; i++) {
        const linkIndex = i % 12;
        const imageUrl = blogImages[linkIndex];
        const innerWrapper = cards[i].querySelector('div');
        if (innerWrapper && imageUrl) {
            if (!innerWrapper.querySelector('.blog-card-image')) {
                const imgWrapper = document.createElement('div');
                imgWrapper.className = "relative w-full aspect-[16/10] overflow-hidden rounded-xl bg-slate-950 mb-4 blog-card-image";

                const img = document.createElement('img');
                img.src = imageUrl;
                img.alt = "Blog Image";
                img.className = "w-full h-full object-cover transition-transform duration-500 group-hover/card:scale-105";

                imgWrapper.appendChild(img);
                innerWrapper.insertBefore(imgWrapper, innerWrapper.firstChild);
            }
        }
        const readMoreBtn = cards[i].querySelector('a');
        if (readMoreBtn) {
            const targetLink = blogLinks[linkIndex];

            if (targetLink && targetLink !== "#" && targetLink !== "") {
                readMoreBtn.href = targetLink;
                if (targetLink.startsWith('http://') || targetLink.startsWith('https://')) {
                    readMoreBtn.target = "_blank";
                    readMoreBtn.rel = "noopener noreferrer";
                }
            }
        }
    }
}

function initBlogsSlider() {
    const wrapper = document.querySelector('.blogs-marquee-wrapper');
    const track = document.querySelector('#blogs-section .animate-blogs-marquee');
    if (!wrapper || !track) return;

    // Turn off pure CSS keyframe animation to let JS manage continuous transform
    track.style.animation = 'none';
    wrapper.style.cursor = 'grab';
    wrapper.style.touchAction = 'pan-y';

    let halfWidth = track.scrollWidth / 2;
    const firstCard = track.children[0];
    let cardStep = firstCard ? (firstCard.offsetWidth + 24) : 374;

    function updateMetrics() {
        if (track.scrollWidth > 0) {
            halfWidth = track.scrollWidth / 2;
        }
        if (track.children.length > 0) {
            cardStep = track.children[0].offsetWidth + 24;
        }
    }

    updateMetrics();
    window.addEventListener('resize', updateMetrics);
    setTimeout(updateMetrics, 500);

    let pos = -halfWidth / 2; // initial starting position
    let autoSpeed = 0.6; // auto scroll px per frame
    let isHovered = false;
    let isDragging = false;
    let hasDragged = false;
    let startX = 0;
    let startPos = 0;
    let lastX = 0;
    let lastTime = 0;
    let velocity = 0;
    let targetScrollOffset = null;

    function normalizePos() {
        if (halfWidth <= 0) return;
        while (pos > 0) pos -= halfWidth;
        while (pos < -halfWidth) pos += halfWidth;
    }

    function step() {
        if (!isDragging) {
            if (targetScrollOffset !== null) {
                const diff = targetScrollOffset - pos;
                if (Math.abs(diff) > 0.5) {
                    pos += diff * 0.12;
                } else {
                    pos = targetScrollOffset;
                    targetScrollOffset = null;
                }
            } else if (Math.abs(velocity) > 0.05) {
                pos += velocity;
                velocity *= 0.92;
            } else {
                velocity = 0;
                if (!isHovered && !isWheelScrolling) {
                    pos += autoSpeed;
                }
            }
            normalizePos();
            track.style.transform = `translate3d(${pos}px, 0, 0)`;
        }
        requestAnimationFrame(step);
    }

    requestAnimationFrame(step);

    // Hover state
    wrapper.addEventListener('mouseenter', () => { isHovered = true; });
    wrapper.addEventListener('mouseleave', () => {
        isHovered = false;
        if (isDragging) endDrag();
    });

    // Pointer Drag & Swipe logic
    function startDrag(clientX) {
        updateMetrics();
        targetScrollOffset = null;
        isDragging = true;
        hasDragged = false;
        startX = clientX;
        lastX = clientX;
        startPos = pos;
        lastTime = performance.now();
        velocity = 0;
        wrapper.style.cursor = 'grabbing';
    }

    function moveDrag(clientX) {
        if (!isDragging) return;
        const now = performance.now();
        const dt = now - lastTime;
        const dx = clientX - startX;

        if (Math.abs(dx) > 5) {
            hasDragged = true;
        }

        if (dt > 0) {
            const instVel = (clientX - lastX) / (dt / 16.6);
            velocity = velocity * 0.3 + instVel * 0.7;
        }

        lastX = clientX;
        lastTime = now;

        pos = startPos + dx;
        normalizePos();
        track.style.transform = `translate3d(${pos}px, 0, 0)`;
    }

    function endDrag() {
        if (!isDragging) return;
        isDragging = false;
        wrapper.style.cursor = 'grab';
        if (velocity > 18) velocity = 18;
        if (velocity < -18) velocity = -18;
    }

    // Mouse events
    wrapper.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        startDrag(e.clientX);
    });

    window.addEventListener('mousemove', (e) => {
        if (isDragging) {
            moveDrag(e.clientX);
        }
    });

    window.addEventListener('mouseup', () => {
        if (isDragging) {
            endDrag();
        }
    });

    // Touch events (for phone view)
    wrapper.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
            startDrag(e.touches[0].clientX);
        }
    }, { passive: true });

    wrapper.addEventListener('touchmove', (e) => {
        if (isDragging && e.touches.length === 1) {
            moveDrag(e.touches[0].clientX);
        }
    }, { passive: true });

    wrapper.addEventListener('touchend', () => {
        if (isDragging) {
            endDrag();
        }
    });

    wrapper.addEventListener('touchcancel', () => {
        if (isDragging) {
            endDrag();
        }
    });

    let wheelTimeout = null;
    let isWheelScrolling = false;

    // Touchpad / Trackpad scroll (two-finger horizontal swipe or wheel) without clicking
    wrapper.addEventListener('wheel', (e) => {
        let delta = 0;

        if (Math.abs(e.deltaX) > 0) {
            delta = e.deltaX;
            e.preventDefault(); // Prevent browser back/forward swipe gesture
        } else if (e.shiftKey && Math.abs(e.deltaY) > 0) {
            delta = e.deltaY;
            e.preventDefault();
        }

        if (delta !== 0) {
            updateMetrics();
            targetScrollOffset = null;
            pos -= delta;
            normalizePos();
            track.style.transform = `translate3d(${pos}px, 0, 0)`;

            isWheelScrolling = true;
            clearTimeout(wheelTimeout);
            wheelTimeout = setTimeout(() => {
                isWheelScrolling = false;
            }, 800);
        }
    }, { passive: false });

    // Intercept card clicks if user was dragging
    wrapper.addEventListener('click', (e) => {
        if (hasDragged) {
            e.preventDefault();
            e.stopPropagation();
            hasDragged = false;
        }
    }, true);

    // Prevent default ghost image/link drag
    track.querySelectorAll('img, a').forEach(el => {
        el.addEventListener('dragstart', (e) => e.preventDefault());
    });
}

function initBlogs() {
    connectBlogReadMoreLinks();
    initBlogsSlider();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBlogs);
} else {
    initBlogs();
}

