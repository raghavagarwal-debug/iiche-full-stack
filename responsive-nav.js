(function () {
    // Gracefully close open WebSockets before page enters Back-Forward Cache to prevent console errors
    const activeSockets = new Set();
    const OrigWebSocket = window.WebSocket;
    if (OrigWebSocket) {
        window.WebSocket = function (url, protocols) {
            const ws = new OrigWebSocket(url, protocols);
            activeSockets.add(ws);
            ws.addEventListener('close', () => activeSockets.delete(ws));
            return ws;
        };
        window.WebSocket.prototype = OrigWebSocket.prototype;
        Object.assign(window.WebSocket, OrigWebSocket);

        window.addEventListener('pagehide', () => {
            activeSockets.forEach(ws => {
                if (ws.readyState === OrigWebSocket.OPEN || ws.readyState === OrigWebSocket.CONNECTING) {
                    ws.close();
                }
            });
        });
    }

    const path = window.location.pathname.replace(/\\/g, '/');
    const isPagesDir = path.includes('/pages/');
    const isSubDir = path.includes('/committee/') || path.includes('/events/');

    let homeUrl = '';
    let aboutUrl = '';
    let committeeUrl = '';
    let departmentsUrl = '';
    let eventsUrl = '';
    let blogsUrl = '';
    let contactUrl = '';
    let loginUrl = '';
    let recruitmentUrl = '';
    let logoPath = '';

    if (isPagesDir) {
        homeUrl = '../index.html#hero-section';
        aboutUrl = '../index.html#about-section';
        committeeUrl = 'committee.html';
        departmentsUrl = 'departments.html';
        eventsUrl = 'events.html';
        blogsUrl = '../index.html#blogs-section';
        contactUrl = 'more.html';
        loginUrl = 'login.html';
        logoPath = '../assets/logo.png';
    } else if (isSubDir) {
        homeUrl = '../index.html#hero-section';
        aboutUrl = '../index.html#about-section';
        committeeUrl = '../pages/committee.html';
        departmentsUrl = '../pages/departments.html';
        eventsUrl = '../pages/events.html';
        blogsUrl = '../index.html#blogs-section';
        contactUrl = '../pages/more.html';
        loginUrl = '../pages/login.html';
        logoPath = '../assets/logo.png';
    } else {
        homeUrl = '#hero-section';
        aboutUrl = '#about-section';
        committeeUrl = 'pages/committee.html';
        departmentsUrl = 'pages/departments.html';
        eventsUrl = 'pages/events.html';
        blogsUrl = '#blogs-section';
        contactUrl = 'pages/more.html';
        loginUrl = 'pages/login.html';
        logoPath = 'assets/logo.png';
    }
    const cssStyles = `
    html, body {
        overflow-x: hidden !important;
        max-width: 100vw !important;
    }
    .mobile-nav-lock {
        overflow: hidden !important;
    }
    #mobile-menu-overlay {
        transition: opacity 0.3s ease-out;
    }
    #mobile-menu-drawer {
        box-shadow: -15px 0 50px rgba(0, 0, 0, 0.8), -5px 0 25px rgba(16, 185, 129, 0.04);
        transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .mobile-nav-link {
        position: relative;
        transition: color 0.25s ease, padding-left 0.25s ease;
    }
    .mobile-nav-link::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 0;
        height: 2px;
        background: linear-gradient(to right, #10b981, #06b6d4);
        transition: width 0.25s ease;
    }
    .mobile-nav-link:hover::after, .mobile-nav-link.active::after {
        width: 100%;
    }
    .mobile-nav-link:hover {
        color: #10b981;
        padding-left: 6px;
    }
    .mobile-nav-link.active {
        background: linear-gradient(to right, #34d399, #06b6d4);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    `;

    const styleSheet = document.createElement("style");
    styleSheet.innerText = cssStyles;
    document.head.appendChild(styleSheet);
    function initResponsiveNav() {
        const nav = document.querySelector('nav');
        if (!nav) return;
        const desktopLinks = nav.querySelector('div.hidden.md\\:flex');
        if (desktopLinks) {
            desktopLinks.classList.remove('hidden', 'md:flex');
            desktopLinks.classList.add('hidden', 'lg:flex');
        }
        const backBtn = nav.querySelector('div.md\\:hidden');
        if (backBtn) {
            backBtn.classList.remove('md:hidden');
            backBtn.classList.add('hidden', 'lg:hidden');
        }
        if (document.getElementById('mobile-menu-btn')) return;

        const navContainer = nav.querySelector('.px-4') || nav.querySelector('.justify-between') || nav;
        const hamburgerBtn = document.createElement('button');
        hamburgerBtn.id = 'mobile-menu-btn';
        hamburgerBtn.className = 'lg:hidden flex items-center justify-center p-2 text-slate-300 hover:text-emerald-400 focus:outline-none transition-colors ml-auto mr-2 sm:mr-4 relative z-50';
        hamburgerBtn.setAttribute('aria-label', 'Toggle menu');
        hamburgerBtn.innerHTML = '<i data-lucide="menu" class="w-7 h-7"></i>';
        navContainer.appendChild(hamburgerBtn);
        const overlay = document.createElement('div');
        overlay.id = 'mobile-menu-overlay';
        overlay.className = 'fixed inset-0 bg-[#010a08]/75 backdrop-blur-sm z-[98] opacity-0 pointer-events-none';
        document.body.appendChild(overlay);
        const drawer = document.createElement('div');
        drawer.id = 'mobile-menu-drawer';
        drawer.className = 'fixed top-0 right-0 h-full w-[80%] max-w-[340px] bg-[#010a08]/85 backdrop-blur-2xl border-l border-white/10 z-[99] transform translate-x-full flex flex-col p-8 rounded-l-3xl';

        drawer.innerHTML = `
            <!-- Header with Close Icon -->
            <div class="flex justify-between items-center mb-12">
                <div class="flex items-center gap-3">
                    <img src="${logoPath}" alt="Logo" class="w-9 h-9 object-contain">
                    <span class="text-xl font-black tracking-tighter text-gradient">IIChE</span>
                </div>
                <button id="mobile-menu-close" class="p-2 text-slate-300 hover:text-emerald-400 focus:outline-none transition-colors" aria-label="Close menu">
                    <i data-lucide="x" class="w-7 h-7"></i>
                </button>
            </div>
            <!-- Navigation Links -->
            <div class="flex flex-col gap-6 text-sm font-bold uppercase tracking-widest">
                <a href="${homeUrl}" class="mobile-nav-link text-slate-300 py-2 border-b border-white/5 transition-all" data-target="home">Home</a>
                <a href="${committeeUrl}" class="mobile-nav-link text-slate-300 py-2 border-b border-white/5 transition-all" data-target="committee">Committee</a>
                <a href="${departmentsUrl}" class="mobile-nav-link text-slate-300 py-2 border-b border-white/5 transition-all" data-target="departments">Departments</a>
                <a href="${eventsUrl}" class="mobile-nav-link text-slate-300 py-2 border-b border-white/5 transition-all" data-target="events">Events</a>
                <a href="${blogsUrl}" class="mobile-nav-link text-slate-300 py-2 border-b border-white/5 transition-all" data-target="blogs">Blogs</a>
                <a href="${contactUrl}" class="mobile-nav-link text-slate-300 py-2 border-b border-white/5 transition-all" data-target="contact">Contact Us</a>
                <a href="${loginUrl}" class="mobile-nav-link text-emerald-400 font-black py-2 border-b border-white/5 transition-all flex items-center gap-2" data-target="login">
                    <i data-lucide="log-in" class="w-4 h-4"></i> Login
                </a>
            </div>
        `;
        document.body.appendChild(drawer);
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
        const links = drawer.querySelectorAll('.mobile-nav-link');
        highlightActiveLink();

        let isOpen = false;

        function openMenu() {
            if (isOpen) return;
            isOpen = true;
            document.body.classList.add('mobile-nav-lock');
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.style.overflow = 'hidden';
            }
            if (window.lenis) {
                window.lenis.stop();
            }
            if (typeof gsap !== 'undefined') {
                gsap.to(overlay, {
                    opacity: 1,
                    pointerEvents: 'auto',
                    duration: 0.3,
                    ease: 'power2.out'
                });
                gsap.to(drawer, {
                    x: 0,
                    duration: 0.35,
                    ease: 'power3.out'
                });
            } else {
                overlay.style.opacity = '1';
                overlay.style.pointerEvents = 'auto';
                drawer.style.transform = 'translateX(0)';
            }
        }

        function closeMenu() {
            if (!isOpen) return;
            isOpen = false;

            document.body.classList.remove('mobile-nav-lock');
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.style.overflow = '';
            }
            if (window.lenis) {
                window.lenis.start();
            }

            if (typeof gsap !== 'undefined') {
                gsap.to(overlay, {
                    opacity: 0,
                    pointerEvents: 'none',
                    duration: 0.25,
                    ease: 'power2.inOut'
                });
                gsap.to(drawer, {
                    x: '100%',
                    duration: 0.3,
                    ease: 'power3.inOut'
                });
            } else {
                overlay.style.opacity = '0';
                overlay.style.pointerEvents = 'none';
                drawer.style.transform = 'translateX(100%)';
            }
        }
        hamburgerBtn.addEventListener('click', openMenu);
        document.getElementById('mobile-menu-close').addEventListener('click', closeMenu);
        overlay.addEventListener('click', closeMenu);

        // Legal modal system
        function initLegalModal() {
            if (document.getElementById('legal-modal')) return;

            const modalDiv = document.createElement('div');
            modalDiv.id = 'legal-modal';
            modalDiv.className = 'fixed inset-0 z-[100] flex items-center justify-center bg-[#010a08]/85 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-300';
            modalDiv.innerHTML = `
            <div class="relative w-[90%] max-w-2xl bg-[#021814]/95 border border-emerald-500/30 rounded-3xl p-8 sm:p-10 shadow-[0_20px_50px_rgba(16,185,129,0.2)] transform scale-95 transition-all duration-300 flex flex-col max-h-[85vh]">
                <div class="flex justify-between items-center pb-4 border-b border-white/5">
                    <h3 id="legal-title" class="text-2xl font-black text-white tracking-tight">Document Title</h3>
                    <button id="legal-close-x" class="text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer" aria-label="Close modal">
                        <i data-lucide="x" class="w-6 h-6"></i>
                    </button>
                </div>
                <div id="legal-content" class="overflow-y-auto pr-2 mt-6 text-sm text-slate-300 leading-relaxed font-light flex-grow">
                </div>
                <div class="mt-8 pt-4 border-t border-white/5 flex justify-end">
                    <button id="legal-close-btn" class="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-cyan-500 rounded-xl text-xs font-bold text-white shadow-lg active:scale-95 cursor-pointer">
                        Close
                    </button>
                </div>
            </div>
        `;
            document.body.appendChild(modalDiv);

            const legalTexts = {
                privacy: {
                    title: "Privacy Policy",
                    content: `
                    <p class="mb-4">At IIChE Student Chapter BIT Mesra, we value and respect your privacy. This Privacy Policy details how we collect, use, and safeguard any information you provide while interacting with our official website.</p>
                    <h4 class="text-emerald-400 font-bold mt-6 mb-2">1. Information Collection</h4>
                    <p class="mb-4">We do not collect any personal identifier information from standard visitors browsing our site. For event registrations, workshops, or membership inquiries, we collect basic details such as name, email address, roll number, and department.</p>
                    <h4 class="text-emerald-400 font-bold mt-6 mb-2">2. Use of Information</h4>
                    <p class="mb-4">Any data collected is strictly used to coordinate event attendance, issue certificates, and send chapter announcements. We never share, rent, or sell your information to third-party organizations.</p>
                    <h4 class="text-emerald-400 font-bold mt-6 mb-2">3. Cookies & Analytics</h4>
                    <p class="mb-4">Our site may use basic session cookies and analytics tools to track website performance, load times, and page popularity, helping us optimize user experience.</p>
                    <p class="mt-8 text-slate-400 text-md">For any privacy questions or requests, please contact us at <a href="mailto:iiche@bitm.ac.in" class="text-cyan-400 underline">iiche@bitm.ac.in</a>.</p>
                `
                },
                terms: {
                    title: "Terms of Service",
                    content: `
                    <p class="mb-4">Welcome to the official website of the IIChE Student Chapter, BIT Mesra. By accessing or using this website, you agree to comply with and be bound by the following Terms of Service.</p>
                    <h4 class="text-cyan-400 font-bold mt-6 mb-2">1. Use License</h4>
                    <p class="mb-4">Permission is granted to temporarily access and download public information and research articles on this website for personal, non-commercial viewing only.</p>
                    <h4 class="text-cyan-400 font-bold mt-6 mb-2">2. User Conduct</h4>
                    <p class="mb-4">You agree not to disrupt or attempt to hack our website resources, inject malicious code, or submit false registrations for events and workshops.</p>
                    <h4 class="text-cyan-400 font-bold mt-6 mb-2">3. Disclaimers & Updates</h4>
                    <p class="mb-4">All academic resources and research details are provided on an "as is" basis. IIChE BIT Mesra reserves the right to modify event details, registrations, or rules at any time without prior notice.</p>
                    <p class="mt-8 text-slate-400 text-md">For any terms inquiries, please contact us at <a href="mailto:iiche@bitm.ac.in" class="text-cyan-400 underline">iiche@bitm.ac.in</a>.</p>
                `
                }
            };

            const legalTitle = document.getElementById('legal-title');
            const legalContent = document.getElementById('legal-content');

            function openLegalModal(type) {
                const doc = legalTexts[type];
                if (!doc) return;
                legalTitle.innerText = doc.title;
                legalContent.innerHTML = doc.content;

                modalDiv.classList.remove('opacity-0', 'pointer-events-none');
                modalDiv.querySelector('.relative').classList.remove('scale-95');
                modalDiv.querySelector('.relative').classList.add('scale-100');

                if (window.lenis) window.lenis.stop();
            }

            function closeLegalModal() {
                modalDiv.classList.add('opacity-0', 'pointer-events-none');
                modalDiv.querySelector('.relative').classList.remove('scale-100');
                modalDiv.querySelector('.relative').classList.add('scale-95');

                if (window.lenis) window.lenis.start();
            }

            document.getElementById('legal-close-x').addEventListener('click', closeLegalModal);
            document.getElementById('legal-close-btn').addEventListener('click', closeLegalModal);
            modalDiv.addEventListener('click', (e) => {
                if (e.target === modalDiv) closeLegalModal();
            });

            document.querySelectorAll('footer a').forEach(a => {
                const text = a.textContent.trim().toLowerCase();
                if (text === 'privacy policy') {
                    a.addEventListener('click', (e) => {
                        e.preventDefault();
                        openLegalModal('privacy');
                    });
                } else if (text === 'terms of service') {
                    a.addEventListener('click', (e) => {
                        e.preventDefault();
                        openLegalModal('terms');
                    });
                }
            });

            if (typeof lucide !== 'undefined') {
                lucide.createIcons({
                    attrs: {
                        class: 'lucide'
                    },
                    nameAttr: 'data-lucide'
                });
            }
        }

        initLegalModal();
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                closeMenu();

                const href = link.getAttribute('href');
                if (href.startsWith('#')) {
                    e.preventDefault();
                    if (window.lenis) {
                        window.lenis.scrollTo(href, {
                            duration: 1.2,
                            ease: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
                        });
                    } else {
                        const el = document.querySelector(href);
                        if (el) {
                            el.scrollIntoView({ behavior: 'smooth' });
                        }
                    }
                    links.forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                }
            });
        });
        window.addEventListener('resize', () => {
            if (window.innerWidth >= 1024 && isOpen) {
                closeMenu();
            }
        });

        function highlightActiveLink() {
            links.forEach(l => l.classList.remove('active'));

            const currentFile = window.location.pathname.replace(/\\/g, '/');
            const currentHash = window.location.hash;

            if (currentFile.includes('committee.html')) {
                const item = drawer.querySelector('[data-target="committee"]');
                if (item) item.classList.add('active');
            } else if (currentFile.includes('departments.html')) {
                const item = drawer.querySelector('[data-target="departments"]');
                if (item) item.classList.add('active');
            } else if (currentFile.includes('events.html')) {
                const item = drawer.querySelector('[data-target="events"]');
                if (item) item.classList.add('active');
            } else if (currentFile.includes('more.html')) {
                const item = drawer.querySelector('[data-target="contact"]');
                if (item) item.classList.add('active');
            } else {
                if (currentHash === '#blogs-section') {
                    const item = drawer.querySelector('[data-target="blogs"]');
                    if (item) item.classList.add('active');
                } else if (currentHash === '#recruitment-section') {
                    const item = drawer.querySelector('[data-target="recruitment"]');
                    if (item) item.classList.add('active');
                } else {
                    const item = drawer.querySelector('[data-target="home"]');
                    if (item) item.classList.add('active');
                }
            }
        }
    }
    const isHome = !path.includes('/pages/') && !path.includes('/committee/') && !path.includes('/events/');
    if (isHome) {
        const hash = window.location.hash;
        if (hash && (hash === '#blogs-section' || hash === '#about-section' || hash === '#contact-section' || hash === '#hero-section' || hash === '#recruitment-section')) {
            const checkLenis = setInterval(() => {
                if (window.lenis) {
                    clearInterval(checkLenis);
                    setTimeout(() => {
                        window.lenis.scrollTo(hash, {
                            duration: 1.2,
                            ease: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
                        });
                    }, 400);
                }
            }, 100);
            setTimeout(() => clearInterval(checkLenis), 5000);
        }
    }
    function loadLucideAndInit() {
        if (typeof lucide === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/lucide@0.468.0/dist/umd/lucide.min.js';
            script.onload = () => {
                initResponsiveNav();
            };
            document.head.appendChild(script);
        } else {
            initResponsiveNav();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadLucideAndInit);
    } else {
        loadLucideAndInit();
    }
})();
