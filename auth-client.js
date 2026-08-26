/**
 * IIChE Website — Authentication & User Profile Client SDK
 * Connects frontend pages to the real FastAPI backend API (http://localhost:8000/api/v1).
 */

(function () {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Use the production backend URL on Render
    let API_BASE = window.IIChE_API_BASE || 'https://iiche-full-stack.onrender.com/api/v1';

    // Global auth state object
    window.IIChEAuth = {
        currentUser: null,
        get apiBase() { return API_BASE; },
        set apiBase(val) { API_BASE = val; },

        // --- API Helper ---
        async request(endpoint, options = {}) {
            let url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

            // Helper to get cookie value by name
            function getCookie(name) {
                const value = `; ${document.cookie}`;
                const parts = value.split(`; ${name}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
                return null;
            }

            const headers = {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            };

            const csrfToken = getCookie('csrf_token');
            if (csrfToken && options.method && options.method.toUpperCase() !== 'GET') {
                headers['X-CSRF-Token'] = csrfToken;
            }

            const timeoutMs = options.timeout || 10000;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

            const fetchOptions = {
                method: options.method || 'GET',
                headers,
                credentials: 'include', // Send session cookies
                body: options.body ? JSON.stringify(options.body) : undefined,
                signal: controller.signal
            };

            let response;
            try {
                response = await fetch(url, fetchOptions);
                clearTimeout(timeoutId);
            } catch (networkErr) {
                clearTimeout(timeoutId);
                if (networkErr.name === 'AbortError') {
                    throw new Error('Request timed out while waiting for server response. Please try again.');
                }
                // If primary request failed at network level (e.g. localhost vs 127.0.0.1), try host fallback
                let fallbackUrl = null;
                if (url.includes('localhost:8000')) {
                    fallbackUrl = url.replace('localhost:8000', '127.0.0.1:8000');
                } else if (url.includes('127.0.0.1:8000')) {
                    fallbackUrl = url.replace('127.0.0.1:8000', 'localhost:8000');
                }

                if (fallbackUrl) {
                    try {
                        const fallbackController = new AbortController();
                        const fallbackTimeout = setTimeout(() => fallbackController.abort(), timeoutMs);
                        response = await fetch(fallbackUrl, { ...fetchOptions, signal: fallbackController.signal });
                        clearTimeout(fallbackTimeout);
                        // Update API_BASE so subsequent calls use working host
                        API_BASE = API_BASE.includes('localhost:8000')
                            ? API_BASE.replace('localhost:8000', '127.0.0.1:8000')
                            : API_BASE.replace('127.0.0.1:8000', 'localhost:8000');
                    } catch (fallbackErr) {
                        if (fallbackErr.name === 'AbortError') {
                            throw new Error('Request timed out while waiting for backend server response.');
                        }
                        throw new Error('Unable to connect to backend server. Please make sure the FastAPI server is running on http://127.0.0.1:8000.');
                    }
                } else {
                    throw new Error('Unable to connect to backend server. Please make sure the FastAPI server is running on http://127.0.0.1:8000.');
                }
            }

            let data;
            try {
                data = await response.json();
            } catch (e) {
                data = { detail: 'Server returned an invalid response' };
            }

            function formatDetailMessage(detail) {
                if (!detail) return 'API request failed';
                if (typeof detail === 'string') return detail;
                if (Array.isArray(detail)) {
                    return detail.map(err => {
                        if (typeof err === 'string') return err;
                        if (err && err.msg) {
                            const field = (err.loc && err.loc.length > 0) ? err.loc[err.loc.length - 1] : '';
                            const fieldName = (field && field !== 'body') ? field.replace(/_/g, ' ') : '';
                            let msg = err.msg.replace(/^Value error,\s*/i, '');
                            if (fieldName) {
                                return `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)}: ${msg}`;
                            }
                            return msg;
                        }
                        return typeof err === 'object' ? JSON.stringify(err) : String(err);
                    }).join('. ');
                }
                if (typeof detail === 'object') {
                    return detail.msg || detail.message || JSON.stringify(detail);
                }
                return String(detail);
            }

            if (!response.ok) {
                const errorMsg = formatDetailMessage(data.detail);
                const error = new Error(errorMsg);
                error.status = response.status;
                error.data = data;
                throw error;
            }

            return data;
        },

        // --- Auth Methods ---
        async checkAuth() {
            try {
                const user = await this.request('/auth/me');
                this.currentUser = user;
                return user;
            } catch (err) {
                this.currentUser = null;
                return null;
            }
        },

        async getCurrentUser() {
            if (this.currentUser) return this.currentUser;
            return await this.checkAuth();
        },

        async login(email, password) {
            const user = await this.request('/auth/login', {
                method: 'POST',
                body: { email, password }
            });
            this.currentUser = user;
            return user;
        },

        async signup(fullName, email, password, confirmPassword, recoveryEmail) {
            return await this.request('/auth/signup', {
                method: 'POST',
                body: {
                    full_name: fullName,
                    email: email,
                    password: password,
                    confirm_password: confirmPassword,
                    recovery_email: recoveryEmail
                }
            });
        },

        async logout() {
            try {
                await this.request('/auth/logout', { method: 'POST' });
            } catch (e) {
                console.warn('Logout request failed:', e);
            }
            this.currentUser = null;
            window.location.reload();
        },

        async updateProfile(fullName, recoveryEmail) {
            const body = {};
            if (fullName !== undefined) body.full_name = fullName;
            if (recoveryEmail !== undefined) body.recovery_email = recoveryEmail;
            const user = await this.request('/users/me', {
                method: 'PATCH',
                body
            });
            this.currentUser = user;
            return user;
        },

        async getMyRegistrations() {
            return await this.request('/users/me/registrations');
        },

        async deleteAccount() {
            const res = await this.request('/users/me', {
                method: 'DELETE'
            });
            this.currentUser = null;
            return res;
        },

        googleLogin() {
            window.location.href = `${API_BASE}/auth/google/login`;
        },

        // --- Forgot Password & OTP Methods (Recovery-Email-Verified Flow) ---
        async requestPasswordReset(email) {
            return await this.request('/auth/forgot-password/request', {
                method: 'POST',
                body: { email }
            });
        },

        async verifyRecoveryEmail(resetSessionToken, recoveryEmail) {
            return await this.request('/auth/forgot-password/verify-recovery-email', {
                method: 'POST',
                body: {
                    reset_session_token: resetSessionToken,
                    recovery_email: recoveryEmail
                }
            });
        },

        async verifyOTP(resetSessionToken, otp) {
            return await this.request('/auth/forgot-password/verify-otp', {
                method: 'POST',
                body: {
                    reset_session_token: resetSessionToken,
                    otp: otp
                }
            });
        },

        async resendOTP(resetSessionToken, recoveryEmail) {
            return await this.request('/auth/forgot-password/resend-otp', {
                method: 'POST',
                body: {
                    reset_session_token: resetSessionToken,
                    recovery_email: recoveryEmail
                }
            });
        },

        async resetPassword(resetToken, newPassword, confirmPassword) {
            return await this.request('/auth/forgot-password/reset', {
                method: 'POST',
                body: {
                    reset_token: resetToken,
                    new_password: newPassword,
                    confirm_password: confirmPassword || newPassword
                }
            });
        }
    };

    // --- UI Integration (Navbar Badge & Modals) ---
    async function setupNavbarUI() {
        const user = await window.IIChEAuth.checkAuth();

        // Check if URL has ?auth=success or ?error=
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('auth') && urlParams.get('auth') === 'success') {
            // Clean URL query string without refresh
            window.history.replaceState({}, document.title, window.location.pathname);
        }

        renderNavbarUserBadge(user);
        injectProfileModalCSS();
    }

    function getPagesUrl(pageName) {
        const path = window.location.pathname.replace(/\\/g, '/');
        if (path.includes('/pages/')) {
            return `./${pageName}`;
        }
        if (path.includes('/committee/') || path.includes('/events/')) {
            return `../pages/${pageName}`;
        }
        return `pages/${pageName}`;
    }

    function renderNavbarUserBadge(user) {
        const nav = document.querySelector('nav');
        if (!nav) return;

        // Find login button anywhere in navbar (matches login.html, pages/login.html, ../pages/login.html, etc.)
        const loginBtn = nav.querySelector('a[href*="login.html"]');

        // Remove any existing badge
        const existingBadge = document.getElementById('user-profile-badge');
        if (existingBadge) existingBadge.remove();

        if (!user) {
            // Unauthenticated state: Ensure login button is visible
            if (loginBtn) {
                loginBtn.style.display = '';
            }
            return;
        }

        // Authenticated state: Hide login button
        if (loginBtn) {
            loginBtn.style.display = 'none';
        }

        // Create User Profile Badge Pill
        const initials = user.full_name
            .split(' ')
            .filter(Boolean)
            .map(n => n[0])
            .join('')
            .toUpperCase()
            .substring(0, 2) || 'U';

        const firstName = user.full_name.split(' ')[0] || 'User';

        const badge = document.createElement('div');
        badge.id = 'user-profile-badge';
        badge.className = 'relative inline-flex items-center gap-2 cursor-pointer z-50 ml-2';
        badge.innerHTML = `
            <button id="user-profile-btn" type="button" class="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#061412]/90 border border-emerald-500/40 hover:border-emerald-400/80 transition-all text-xs font-bold text-slate-200 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.4)] focus:outline-none focus:ring-0 outline-none">
                <span class="w-7 h-7 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-400 text-[#010a08] font-black flex items-center justify-center text-xs shadow-inner">
                    ${escapeHtml(initials)}
                </span>
                <span class="max-w-[120px] truncate font-extrabold text-white">${escapeHtml(firstName)}</span>
                <svg class="w-3.5 h-3.5 text-emerald-400 transition-transform duration-200" id="badge-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"/>
                </svg>
            </button>

            <!-- Dropdown Menu -->
            <div id="user-profile-dropdown" class="dropdown-closed absolute right-0 top-full mt-3 w-64 bg-[#061412]/95 backdrop-blur-2xl border border-emerald-500/30 rounded-2xl p-4 shadow-[0_20px_50px_rgba(0,0,0,0.8),0_0_30px_rgba(16,185,129,0.15)] flex flex-col gap-3 z-50">
                <div class="flex items-center gap-3 pb-3 border-b border-white/10">
                    <span class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-400 text-[#010a08] font-black flex items-center justify-center text-sm shadow-md">
                        ${escapeHtml(initials)}
                    </span>
                    <div class="flex flex-col min-w-0">
                    <span class="text-sm font-black text-white truncate">${escapeHtml(user.full_name)}</span>
                        <span class="text-[11px] text-slate-400 truncate">${escapeHtml(user.email)}</span>
                        <span class="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 mt-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 w-max">
                            ${escapeHtml(user.role)}
                        </span>
                    </div>
                </div>

                <div class="flex flex-col gap-1 text-xs font-semibold">
                    ${user.role === 'admin' ? `
                    <a href="${getPagesUrl('admin.html')}" class="flex items-center gap-2 px-3 py-2 rounded-xl text-amber-300 hover:text-amber-200 hover:bg-amber-500/15 border border-amber-500/30 transition-all text-left">
                        <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
                        Admin Dashboard
                    </a>
                    ` : ''}

                    <button id="profile-edit-name-btn" type="button" class="flex items-center gap-2 px-3 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition-all text-left focus:outline-none outline-none">
                        <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                        Edit Profile & Recovery
                    </button>

                    <button id="profile-my-events-btn" type="button" class="flex items-center gap-2 px-3 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition-all text-left focus:outline-none outline-none">
                        <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        My Registered Events
                    </button>

                    <button id="profile-delete-account-btn" type="button" class="flex items-center gap-2 px-3 py-2 rounded-xl text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all text-left focus:outline-none outline-none cursor-pointer">
                        <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        Delete Account
                    </button>
                </div>

                <button id="profile-logout-btn" type="button" class="w-full mt-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-300 hover:text-white font-bold text-xs transition-all cursor-pointer focus:outline-none outline-none">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                    Sign Out
                </button>
            </div>
        `;

        if (loginBtn && loginBtn.parentNode) {
            loginBtn.parentNode.insertBefore(badge, loginBtn);
        } else {
            const container = nav.querySelector('div.hidden.md\\:flex') || nav.querySelector('div.hidden.lg\\:flex') || nav.querySelector('div.flex.items-center') || nav;
            container.appendChild(badge);
        }

        // Toggle dropdown with smooth open and contracting close animations
        const btn = badge.querySelector('#user-profile-btn');
        const dropdown = badge.querySelector('#user-profile-dropdown');
        const chevron = badge.querySelector('#badge-chevron');
        let isDropdownOpen = false;

        function openDropdown() {
            if (isDropdownOpen) return;
            isDropdownOpen = true;
            dropdown.classList.remove('dropdown-closed');
            dropdown.classList.add('dropdown-open');
            chevron.style.transform = 'rotate(180deg)';
        }

        function closeDropdown() {
            if (!isDropdownOpen) return;
            isDropdownOpen = false;
            dropdown.classList.remove('dropdown-open');
            dropdown.classList.add('dropdown-closed');
            chevron.style.transform = 'rotate(0deg)';
        }

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (isDropdownOpen) {
                closeDropdown();
            } else {
                openDropdown();
            }
        });

        document.addEventListener('click', () => {
            closeDropdown();
        });

        dropdown.addEventListener('click', (e) => e.stopPropagation());

        dropdown.querySelector('#profile-edit-name-btn').addEventListener('click', () => {
            closeDropdown();
            openEditNameModal(user);
        });

        dropdown.querySelector('#profile-my-events-btn').addEventListener('click', () => {
            closeDropdown();
            openMyEventsModal();
        });

        dropdown.querySelector('#profile-delete-account-btn').addEventListener('click', () => {
            closeDropdown();
            openDeleteAccountModal(user);
        });

        dropdown.querySelector('#profile-logout-btn').addEventListener('click', () => {
            window.IIChEAuth.logout();
        });

        updateMobileDrawerUser(user);
    }

    function updateMobileDrawerUser(user) {
        const drawer = document.getElementById('mobile-menu-drawer');
        if (!drawer) return;

        const mobileLoginLink = drawer.querySelector('[data-target="login"]');
        if (mobileLoginLink && user) {
            mobileLoginLink.innerHTML = `
                <i data-lucide="user" class="w-4 h-4"></i> ${escapeHtml(user.full_name.split(' ')[0])} (Logged In)
            `;
            mobileLoginLink.href = '#';
            mobileLoginLink.addEventListener('click', (e) => {
                e.preventDefault();
                openEditNameModal(user);
            });
        }
    }

    // --- Profile Edit Modal ---
    function openEditNameModal(user) {
        let modal = document.getElementById('edit-profile-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'edit-profile-modal';
            modal.className = 'fixed inset-0 z-[110] flex items-center justify-center bg-[#010a08]/85 backdrop-blur-md transition-all duration-300';
            modal.innerHTML = `
                <div class="relative w-[90%] max-w-md bg-[#061412]/95 border border-emerald-500/40 rounded-3xl p-7 sm:p-9 shadow-[0_20px_50px_rgba(0,0,0,0.9),0_0_30px_rgba(16,185,129,0.2)] flex flex-col gap-5">
                    <div class="flex justify-between items-center pb-3 border-b border-white/10">
                        <h3 class="text-xl font-black text-white tracking-tight">Edit Profile & Recovery</h3>
                        <button id="close-edit-modal" class="text-slate-400 hover:text-emerald-400 transition-colors">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>

                    <form id="edit-profile-form" class="flex flex-col gap-4">
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-bold uppercase tracking-wider text-slate-300">Full Name</label>
                            <input type="text" id="edit-name-input" class="w-full bg-[#020a08] border border-[#1b3d36] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-[#00d2c4] transition-all" required/>
                        </div>

                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-bold uppercase tracking-wider text-slate-400">Account Email (Read only)</label>
                            <input type="email" id="edit-email-input" class="w-full bg-[#020a08]/50 border border-white/5 rounded-xl px-4 py-3 text-sm text-slate-400 cursor-not-allowed" readonly/>
                        </div>

                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-bold uppercase tracking-wider text-emerald-400">Recovery Email</label>
                            <input type="email" id="edit-recovery-email-input" placeholder="your.recovery@gmail.com" autocomplete="email" required class="w-full bg-[#020a08] border border-[#1b3d36] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-[#00d2c4] transition-all"/>
                            <span class="text-[10px] text-[#789690] leading-tight">Used as a verification factor if you ever need to reset your password.</span>
                        </div>

                        <div id="edit-profile-msg" class="hidden text-xs py-2 px-3 rounded-xl"></div>

                        <div class="flex justify-end gap-3 mt-2">
                            <button type="button" id="cancel-edit-btn" class="px-5 py-2.5 rounded-xl text-xs font-bold text-slate-300 hover:bg-white/5 transition-all">Cancel</button>
                            <button type="submit" id="save-edit-btn" class="px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-400 text-[#010a08] font-extrabold text-xs rounded-xl shadow-lg hover:brightness-110 transition-all cursor-pointer">Save Changes</button>
                        </div>
                    </form>
                </div>
            `;
            document.body.appendChild(modal);

            modal.querySelector('#close-edit-modal').addEventListener('click', () => modal.classList.add('hidden'));
            modal.querySelector('#cancel-edit-btn').addEventListener('click', () => modal.classList.add('hidden'));
        }

        modal.querySelector('#edit-name-input').value = user.full_name || '';
        modal.querySelector('#edit-email-input').value = user.email || '';
        modal.querySelector('#edit-recovery-email-input').value = user.recovery_email || '';

        const form = modal.querySelector('#edit-profile-form');
        const msg = modal.querySelector('#edit-profile-msg');
        msg.className = 'hidden text-xs py-2 px-3 rounded-xl';

        form.onsubmit = async (e) => {
            e.preventDefault();
            const newName = modal.querySelector('#edit-name-input').value.trim();
            const newRecovery = modal.querySelector('#edit-recovery-email-input').value.trim();
            const saveBtn = modal.querySelector('#save-edit-btn');

            if (!newRecovery) {
                msg.className = 'text-xs py-2 px-3 rounded-xl bg-red-500/20 text-red-400 border border-red-500/30';
                msg.innerText = 'Recovery email is required.';
                msg.classList.remove('hidden');
                return;
            }

            if (newRecovery && newRecovery.toLowerCase() === user.email.toLowerCase()) {
                msg.className = 'text-xs py-2 px-3 rounded-xl bg-red-500/20 text-red-400 border border-red-500/30';
                msg.innerText = 'Recovery email must be different from your account email.';
                msg.classList.remove('hidden');
                return;
            }

            saveBtn.disabled = true;
            saveBtn.innerText = 'Saving...';

            try {
                const updated = await window.IIChEAuth.updateProfile(newName, newRecovery);
                msg.className = 'text-xs py-2 px-3 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
                msg.innerText = 'Profile updated successfully!';
                msg.classList.remove('hidden');

                setTimeout(() => {
                    modal.classList.add('hidden');
                    renderNavbarUserBadge(updated);
                }, 1000);
            } catch (err) {
                msg.className = 'text-xs py-2 px-3 rounded-xl bg-red-500/20 text-red-400 border border-red-500/30';
                msg.innerText = err.message || 'Failed to update profile';
                msg.classList.remove('hidden');
            } finally {
                saveBtn.disabled = false;
                saveBtn.innerText = 'Save Changes';
            }
        };

        modal.classList.remove('hidden');
    }

    // --- My Registered Events Modal ---
    async function openMyEventsModal() {
        let modal = document.getElementById('my-events-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'my-events-modal';
            modal.className = 'fixed inset-0 z-[110] flex items-center justify-center bg-[#010a08]/85 backdrop-blur-md transition-all duration-300';
            modal.innerHTML = `
                <div class="relative w-[90%] max-w-xl bg-[#061412]/95 border border-emerald-500/40 rounded-3xl p-7 sm:p-9 shadow-[0_20px_50px_rgba(0,0,0,0.9),0_0_30px_rgba(16,185,129,0.2)] flex flex-col max-h-[85vh]">
                    <div class="flex justify-between items-center pb-3 border-b border-white/10">
                        <h3 class="text-xl font-black text-white tracking-tight">My Registered Events</h3>
                        <button id="close-events-modal" class="text-slate-400 hover:text-emerald-400 transition-colors">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>

                    <div id="my-events-list" class="overflow-y-auto mt-4 flex flex-col gap-3 pr-1 flex-grow">
                        <div class="text-center py-8 text-slate-400 text-sm">Loading your registrations...</div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            modal.querySelector('#close-events-modal').addEventListener('click', () => modal.classList.add('hidden'));
        }

        const listContainer = modal.querySelector('#my-events-list');
        listContainer.innerHTML = '<div class="text-center py-8 text-slate-400 text-sm">Loading your registrations...</div>';
        modal.classList.remove('hidden');

        try {
            const regs = await window.IIChEAuth.getMyRegistrations();
            if (!regs || regs.length === 0) {
                listContainer.innerHTML = `
                    <div class="text-center py-10 flex flex-col items-center gap-3">
                        <svg class="w-12 h-12 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        <p class="text-slate-400 text-sm font-semibold">You have not registered for any events yet.</p>
                    </div>
                `;
            } else {
                listContainer.innerHTML = regs.map(r => `
                    <div class="p-4 rounded-2xl bg-[#020a08] border border-emerald-500/20 flex justify-between items-center">
                        <div class="flex flex-col gap-1">
                            <span class="text-sm font-bold text-white">${escapeHtml(r.event_title)}</span>
                            <span class="text-xs text-slate-400">📅 ${new Date(r.event_date).toLocaleDateString()} ${r.venue ? '• 📍 ' + r.venue : ''}</span>
                        </div>
                        <span class="px-3 py-1 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-extrabold">
                            ✓ Registered
                        </span>
                    </div>
                `).join('');
                // The event API is trusted only as data. Flatten user-controlled text
                // nodes after rendering so venue values cannot become markup.
                listContainer.querySelectorAll('span.text-xs.text-slate-400').forEach((node) => {
                    node.textContent = node.textContent;
                });
            }
        } catch (err) {
            listContainer.innerHTML = `<div class="text-center py-8 text-red-400 text-sm">Failed to load registrations: ${escapeHtml(err.message)}</div>`;
        }
    }

    // --- Delete Account Modal ---
    function openDeleteAccountModal(user) {
        let modal = document.getElementById('delete-account-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'delete-account-modal';
            modal.className = 'fixed inset-0 z-[120] flex items-center justify-center bg-[#010a08]/85 backdrop-blur-md transition-all duration-300 p-4';
            modal.innerHTML = `
                <div class="relative w-full max-w-md bg-[#061412]/95 border border-red-500/30 rounded-3xl p-7 sm:p-8 shadow-[0_20px_50px_rgba(0,0,0,0.9),0_0_30px_rgba(239,68,68,0.15)] flex flex-col gap-5">
                    <div class="flex items-center gap-3.5 pb-3 border-b border-white/10">
                        <div class="w-11 h-11 rounded-2xl bg-red-500/15 border border-red-500/30 flex items-center justify-center text-red-400 flex-shrink-0">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                        </div>
                        <div>
                            <h3 class="text-lg font-black text-white tracking-tight">Delete Account</h3>
                            <p class="text-xs text-red-400/80 font-medium">Permanent & Irreversible Action</p>
                        </div>
                    </div>

                    <div class="text-slate-300 text-xs sm:text-sm space-y-2.5 leading-relaxed">
                        <p>Are you sure you want to permanently delete your account (<strong class="text-white" id="delete-modal-email"></strong>)?</p>
                        <div class="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs leading-relaxed">
                            ⚠️ <strong>Warning:</strong> Deleting your account will immediately purge your profile, revoke login access, and cancel all your active event registrations from the database.
                        </div>
                    </div>

                    <div id="delete-account-msg" class="hidden text-xs py-2.5 px-3.5 rounded-xl"></div>

                    <div class="flex items-center justify-end gap-3 pt-2">
                        <button type="button" id="cancel-delete-account-btn" class="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-300 hover:bg-white/5 hover:text-white transition-all cursor-pointer">
                            Cancel
                        </button>
                        <button type="button" id="confirm-delete-account-btn" class="px-5 py-2.5 bg-red-500 hover:bg-red-600 text-white font-black text-xs rounded-xl shadow-lg shadow-red-500/20 hover:shadow-red-500/40 transition-all cursor-pointer flex items-center gap-2">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                            <span id="confirm-delete-account-text">Yes, Delete My Account</span>
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            modal.querySelector('#cancel-delete-account-btn').addEventListener('click', () => {
                modal.classList.add('hidden');
            });
        }

        modal.querySelector('#delete-modal-email').innerText = user.email;
        const msg = modal.querySelector('#delete-account-msg');
        msg.className = 'hidden text-xs py-2.5 px-3.5 rounded-xl';

        const confirmBtn = modal.querySelector('#confirm-delete-account-btn');
        const cancelBtn = modal.querySelector('#cancel-delete-account-btn');
        const btnText = modal.querySelector('#confirm-delete-account-text');

        confirmBtn.disabled = false;
        cancelBtn.disabled = false;
        btnText.innerText = 'Yes, Delete My Account';

        confirmBtn.onclick = async () => {
            confirmBtn.disabled = true;
            cancelBtn.disabled = true;
            btnText.innerText = 'Deleting account...';

            try {
                const result = await window.IIChEAuth.deleteAccount();
                msg.className = 'text-xs py-2.5 px-3.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
                msg.innerText = result.message || 'Account successfully deleted from database.';
                msg.classList.remove('hidden');

                setTimeout(() => {
                    window.location.reload();
                }, 1200);
            } catch (err) {
                confirmBtn.disabled = false;
                cancelBtn.disabled = false;
                btnText.innerText = 'Yes, Delete My Account';
                msg.className = 'text-xs py-2.5 px-3.5 rounded-xl bg-red-500/20 text-red-300 border border-red-500/30';
                msg.innerText = err.message || 'Failed to delete account. Please try again.';
                msg.classList.remove('hidden');
            }
        };

        modal.classList.remove('hidden');
    }

    function injectProfileModalCSS() {
        if (document.getElementById('iiche-auth-styles')) return;
        const style = document.createElement('style');
        style.id = 'iiche-auth-styles';
        style.innerText = `
            #user-profile-dropdown {
                transform-origin: top right;
                transition: opacity 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                            transform 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                            visibility 0.28s linear;
                will-change: opacity, transform;
            }
            #user-profile-dropdown.dropdown-open {
                opacity: 1;
                transform: translateY(0) scale(1);
                visibility: visible;
                pointer-events: auto;
            }
            #user-profile-dropdown.dropdown-closed {
                opacity: 0;
                transform: translateY(-14px) scale(0.92);
                visibility: hidden;
                pointer-events: none;
            }
        `;
        document.head.appendChild(style);
    }

    // Auto init on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupNavbarUI);
    } else {
        setupNavbarUI();
    }
})();
