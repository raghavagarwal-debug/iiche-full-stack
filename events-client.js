/**
 * IIChE Website — Public Events & Dynamic Registration Client SDK
 * Automatically links public event pages (workshop.html, talks.html, coalescnece.26.html, index.html)
 * to the backend API & Admin Dashboard state.
 */

(function () {
    const EVENT_TITLE_MAPPINGS = [
        {
            dbTitle: "Coalescence 26 Flagship Fest",
            aliases: ["coalescence 26", "coalescence'26", "coalescence symposium", "coalescence flagship fest", "coalescence"]
        },
        {
            dbTitle: "MATLAB and Simulink for Chemical Engineers",
            aliases: ["matlab workshop, numeric and scripting and simulators", "matlab workshop: numeric scripting & simulators", "matlab workshop", "matlab and simulink", "matlab & simulink", "simulink"]
        },
        {
            dbTitle: "Design Workshop Layout and Design Tools",
            aliases: ["design workshop layout and design", "design workshop : layouts & design tools", "design workshop", "layouts & design tools", "layout and design tools"]
        },
        {
            dbTitle: "Alumni and Career Guidance Talk",
            aliases: ["alumni placement talks and preparation for core and software roles", "alumni placement talks: preparations for core & software roles", "alumni placement talks", "alumni and career guidance talk", "alumni talks"]
        },
        {
            dbTitle: "IICHE Talks GATE Preparation Series",
            aliases: ["iiche talks: gate preparation series", "iiche talks gate preparation series", "gate preparation series", "gate series", "gate preparation"]
        }
    ];

    document.addEventListener('DOMContentLoaded', async () => {
        // Wait briefly for auth-client.js to resolve user state
        setTimeout(initEventsIntegration, 100);
    });

    async function initEventsIntegration() {
        if (!window.IIChEAuth) return;

        let activeEvents = [];
        let userRegistrations = [];
        let currentUser = null;

        // 1. Fetch current user and user registrations (if logged in)
        try {
            currentUser = await window.IIChEAuth.getCurrentUser();
            if (currentUser) {
                userRegistrations = await window.IIChEAuth.request('/users/me/registrations');
            }
        } catch (e) {
            currentUser = null;
            userRegistrations = [];
        }

        // 2. Fetch all public events from backend
        try {
            activeEvents = await window.IIChEAuth.request('/events');
        } catch (e) {
            console.warn("Could not fetch events from backend API:", e);
            return;
        }

        if (!Array.isArray(activeEvents) || activeEvents.length === 0) return;

        const registeredEventIds = new Set((userRegistrations || []).map(r => r.event_id));

        // Helper function to resolve backend event for a given button/card
        function resolveEventForElement(btn) {
            // A. Check explicit data attributes on button
            const directTitle = btn.dataset.eventTitle;
            const directId = btn.dataset.eventId;

            if (directId) {
                const found = activeEvents.find(e => e.id === directId);
                if (found) return found;
            }

            if (directTitle) {
                const normDirect = directTitle.trim().toLowerCase();
                const found = activeEvents.find(e => e.title.toLowerCase() === normDirect);
                if (found) return found;

                // Check mappings
                for (const map of EVENT_TITLE_MAPPINGS) {
                    if (map.dbTitle.toLowerCase() === normDirect || map.aliases.some(a => a === normDirect)) {
                        const m = activeEvents.find(e => e.title.toLowerCase() === map.dbTitle.toLowerCase());
                        if (m) return m;
                    }
                }
            }

            // B. Check parent card / container headings and content
            const card = btn.closest('section, .w-full, .grid, .relative, div') || btn.parentElement;
            if (!card) return null;

            // Check card data attributes
            if (card.dataset && card.dataset.eventTitle) {
                const normCardTitle = card.dataset.eventTitle.trim().toLowerCase();
                const found = activeEvents.find(e => e.title.toLowerCase() === normCardTitle);
                if (found) return found;
            }

            const headings = card.querySelectorAll('h1, h2, h3, h4, h5, span, p');
            const cardTexts = Array.from(headings).map(h => h.textContent.trim().toLowerCase());

            for (const map of EVENT_TITLE_MAPPINGS) {
                const dbEvent = activeEvents.find(e => e.title.toLowerCase() === map.dbTitle.toLowerCase());
                if (!dbEvent) continue;

                // Exact or substring match in headings
                for (const text of cardTexts) {
                    if (text.includes(map.dbTitle.toLowerCase())) return dbEvent;
                    for (const alias of map.aliases) {
                        if (text.includes(alias)) return dbEvent;
                    }
                }
            }

            // Fallback direct match with any active event title
            for (const ev of activeEvents) {
                const evTitle = ev.title.toLowerCase();
                for (const text of cardTexts) {
                    if (text.includes(evTitle) || evTitle.includes(text)) return ev;
                }
            }

            return null;
        }

        // 3. Scan & update existing static event cards on the page
        const comingSoonButtons = document.querySelectorAll('a, button');

        comingSoonButtons.forEach(btn => {
            const btnText = (btn.textContent || '').trim().toLowerCase();

            // Target buttons that are actionable event links or placeholders
            if (btn.dataset.eventTitle || btn.dataset.eventId || btnText.includes('coming soon') || btnText.includes('register') || btnText.includes('join the symposium')) {
                const matchedEvent = resolveEventForElement(btn);
                if (matchedEvent) {
                    updateButtonForEvent(btn, matchedEvent, registeredEventIds.has(matchedEvent.id), currentUser);
                }
            }
        });

        // 4. Auto-register & scroll into view if returning from Login redirect with event_id
        const urlParams = new URLSearchParams(window.location.search);
        const autoEventId = urlParams.get('event_id') || sessionStorage.getItem('pending_event_id');

        if (currentUser && autoEventId && !registeredEventIds.has(autoEventId)) {
            const targetEvent = activeEvents.find(e => e.id === autoEventId);
            if (targetEvent && (targetEvent.registration_status === 'open' || targetEvent.registration_open)) {
                try {
                    await window.IIChEAuth.request(`/events/${targetEvent.id}/register`, { method: 'POST' });
                    registeredEventIds.add(targetEvent.id);
                    showToast(`🎉 Success! You are registered for ${targetEvent.title}`, 'success');

                    // Update UI button immediately if matching card exists
                    const matchedBtn = Array.from(document.querySelectorAll('a, button')).find(b => b.dataset.eventId === targetEvent.id);
                    if (matchedBtn) {
                        updateButtonForEvent(matchedBtn, targetEvent, true, currentUser);
                        matchedBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                } catch (err) {
                    showToast(err.message || 'Auto-registration failed', 'error');
                }
            }
            // Clean URL query param & storage
            sessionStorage.removeItem('pending_event_id');
            urlParams.delete('event_id');
            const newSearch = urlParams.toString();
            const newUrl = window.location.pathname + (newSearch ? `?${newSearch}` : '') + window.location.hash;
            window.history.replaceState({}, document.title, newUrl);
        }
    }

    function updateButtonForEvent(btn, event, isRegistered, currentUser) {
        btn.dataset.eventId = event.id;
        btn.dataset.eventTitle = event.title;

        const regStatus = event.registration_status || (event.registration_open ? 'open' : 'coming_soon');

        if (isRegistered) {
            // State: Already Registered
            btn.textContent = '✓ Registered';
            btn.href = 'javascript:void(0)';
            btn.className = 'px-6 py-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-xs font-bold text-emerald-300 uppercase tracking-widest cursor-default inline-flex items-center gap-1.5 shadow-lg shadow-emerald-500/10';
            btn.onclick = (e) => e.preventDefault();
        } else if (regStatus === 'open') {
            // State: Registration Open
            btn.textContent = 'Register Now';
            btn.href = 'javascript:void(0)';
            btn.className = 'px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-xs font-extrabold text-slate-950 uppercase tracking-widest hover:brightness-110 hover:shadow-[0_0_20px_rgba(16,185,129,0.4)] transition-all cursor-pointer inline-flex items-center gap-1.5 active:scale-95';

            btn.onclick = async (e) => {
                e.preventDefault();
                if (!currentUser) {
                    sessionStorage.setItem('pending_event_id', event.id);
                    showToast('Please sign in to register for this event.', 'info');
                    setTimeout(() => {
                        const path = window.location.pathname.replace(/\\/g, '/');
                        let loginUrl = 'pages/login.html';
                        if (path.includes('/pages/')) {
                            loginUrl = './login.html';
                        } else if (path.includes('/committee/') || path.includes('/events/')) {
                            loginUrl = '../pages/login.html';
                        }
                        const returnUrl = `${loginUrl}?redirect=${encodeURIComponent(window.location.pathname)}&event_id=${encodeURIComponent(event.id)}`;
                        window.location.href = returnUrl;
                    }, 800);
                    return;
                }

                btn.textContent = 'Registering...';
                btn.style.pointerEvents = 'none';

                try {
                    await window.IIChEAuth.request(`/events/${event.id}/register`, {
                        method: 'POST'
                    });

                    showToast(`🎉 Success! You are registered for ${event.title}`, 'success');
                    btn.textContent = '✓ Registered';
                    btn.className = 'px-6 py-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-xs font-bold text-emerald-300 uppercase tracking-widest cursor-default inline-flex items-center gap-1.5 shadow-lg shadow-emerald-500/10';
                    btn.onclick = (ev) => ev.preventDefault();

                } catch (err) {
                    showToast(err.message || 'Registration failed', 'error');
                    btn.textContent = 'Register Now';
                    btn.style.pointerEvents = '';
                }
            };
        } else if (regStatus === 'closed') {
            // State: Registration Closed
            btn.textContent = 'Registration Closed';
            btn.href = 'javascript:void(0)';
            btn.className = 'px-6 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs font-bold text-red-300 uppercase tracking-widest cursor-not-allowed opacity-75 inline-flex items-center gap-1.5';
            btn.onclick = (e) => {
                e.preventDefault();
                showToast(`Registration for ${event.title} has closed.`, 'info');
            };
        } else {
            // State: Coming Soon
            btn.textContent = 'Coming Soon ...';
            btn.href = 'javascript:void(0)';
            btn.className = 'px-6 py-3 rounded-xl bg-slate-800/60 border border-slate-700 text-xs font-bold text-slate-400 uppercase tracking-widest cursor-not-allowed inline-flex items-center gap-1.5';
            btn.onclick = (e) => {
                e.preventDefault();
                showToast(`Registration for ${event.title} is coming soon!`, 'info');
            };
        }
    }

    function showToast(message, type = 'info') {
        let toast = document.getElementById('events-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'events-toast';
            toast.className = 'fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-2xl text-xs font-bold text-white shadow-2xl backdrop-blur-xl transition-all duration-300 transform translate-y-10 opacity-0 flex items-center gap-2 border';
            document.body.appendChild(toast);
        }

        if (type === 'success') {
            toast.className = 'fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-2xl text-xs font-bold text-white shadow-2xl backdrop-blur-xl transition-all duration-300 transform translate-y-10 opacity-0 flex items-center gap-2 border bg-emerald-950/90 border-emerald-500/40 text-emerald-200';
        } else if (type === 'error') {
            toast.className = 'fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-2xl text-xs font-bold text-white shadow-2xl backdrop-blur-xl transition-all duration-300 transform translate-y-10 opacity-0 flex items-center gap-2 border bg-red-950/90 border-red-500/40 text-red-200';
        } else {
            toast.className = 'fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-2xl text-xs font-bold text-white shadow-2xl backdrop-blur-xl transition-all duration-300 transform translate-y-10 opacity-0 flex items-center gap-2 border bg-slate-900/90 border-cyan-500/40 text-cyan-200';
        }

        toast.innerText = message;
        toast.classList.remove('translate-y-10', 'opacity-0');

        setTimeout(() => {
            toast.classList.add('translate-y-10', 'opacity-0');
        }, 4000);
    }
})();

