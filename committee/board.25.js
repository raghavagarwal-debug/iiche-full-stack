const boardMembers = [
    {
        name: "Sakshi Sinha",
        designation: "President",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930026/IMG_20260531_224101.jpg_kojv5r.jpg",
        linkedin: "https://www.linkedin.com/in/sakshisinha7856/",
        instagram: "https://www.instagram.com/sakshi_sinha285/"
    },
    {
        name: "Jatin Gupta",
        designation: "Joint-President",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930021/WhatsApp_Image_2026-07-01_at_13.53.24_1_zatcnp.jpg",
        linkedin: "https://www.linkedin.com/in/jatingupta11/",
        instagram: "https://www.instagram.com/official_jk11/"
    },
    {
        name: "Harsh Kumar",
        designation: "Joint-President",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930015/WhatsApp_Image_2026-07-01_at_13.53.22_tqkwbv.jpg",
        linkedin: "https://www.linkedin.com/in/harsh-kumar-62129526b/",
        instagram: "https://www.instagram.com/hhaarshyadav/"
    },
    {
        name: "Nishant Kumar",
        designation: "Vice-President",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782929991/WhatsApp_Image_2026-07-01_at_13.53.21_tscn57.jpg",
        linkedin: "https://www.linkedin.com/in/nishant-kumar-ba9ba8184/",
        instagram: "https://www.instagram.com/i_nishant_swarnkar/"
    },
    {
        name: "Purushottam Kumar",
        designation: "Vice-President",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930023/WhatsApp_Image_2026-07-01_at_13.53.22_1_nd6hul.jpg",
        linkedin: "https://www.linkedin.com/in/purushottam-kumar-3823a0264/",
        instagram: "https://www.instagram.com/purushottam.singh18/"
    },
    {
        name: "Vivek Raj Sinha",
        designation: "Vice-President",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930020/WhatsApp_Image_2026-07-01_at_13.53.24_ogpkrc.jpg",
        linkedin: "https://www.linkedin.com/in/vivekrajsinha0003official/",
        instagram: "https://www.instagram.com/viveksinha_7856/"
    },
    {
        name: "Srishti Kishore",
        designation: "Director",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930017/WhatsApp_Image_2026-07-01_at_13.53.23_mcsxxj.jpg",
        linkedin: "https://www.linkedin.com/in/srishti-kishor-83a4902a3/",
        instagram: "#"
    },
    {
        name: "Siddhart Kaushal",
        designation: "Director",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1782930010/WhatsApp_Image_2026-07-01_at_13.53.20_aq3ce5.jpg",
        linkedin: "https://www.linkedin.com/in/siddharth-kaushal-4a6a7627a/",
        instagram: "https://www.instagram.com/siddharthkaushal326/"
    }
];

function createMemberCardHtml(member) {
    const hasValidImage = member.image && member.image !== '#' && member.image !== '';
    return `
        <div class="board-card liquid-glass-card opacity-0 translate-y-8 relative rounded-[2.5rem] overflow-hidden shadow-[0_15px_35px_rgba(0,0,0,0.6)] group aspect-[3/4] w-full transition-all duration-500">
            <!-- Background Image or Fallback -->
            ${hasValidImage ? `
            <img src="${member.image}" alt="${member.name}" class="absolute inset-0 w-full h-full object-cover transform scale-100 group-hover:scale-105 transition-all duration-700 ease-out" loading="lazy" decoding="async">
            ` : `
            <div class="absolute inset-0 bg-gradient-to-br from-slate-800 via-slate-900 to-black flex flex-col items-center justify-center text-slate-500">
                <svg class="w-16 h-16 opacity-40 mb-2" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                <span class="text-xs tracking-widest uppercase font-semibold text-slate-400">IIChE BITM</span>
            </div>
            `}
            
            <!-- Dark Gradient Bottom Overlay -->
            <div class="absolute inset-0 bg-gradient-to-t from-black/95 via-black/45 to-transparent flex flex-col justify-end p-6 sm:p-8">
                <!-- Name -->
                <h3 class="text-xl sm:text-2xl font-bold text-white tracking-tight leading-snug drop-shadow-md">
                    ${member.name}
                </h3>
                
                <!-- Designation -->
                <p class="text-[#a3e635] font-bold text-xs sm:text-sm mt-1.5 uppercase tracking-widest font-sans drop-shadow-sm">
                    ${member.designation}
                </p>
                
                <!-- Social Connect Buttons -->
                <div class="flex flex-row items-center gap-3 mt-5">
                    <!-- LinkedIn Pill -->
                    <a href="${member.linkedin}" target="_blank" class="flex items-center gap-2 bg-white/10 hover:bg-emerald-500/20 border border-white/15 hover:border-emerald-500/40 rounded-xl px-4 py-2.5 text-xs font-semibold text-white transition-all backdrop-blur-md shadow-sm active:scale-95">
                        <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                            <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                        </svg>
                        <span>Connect on LinkedIn</span>
                    </a>
                    
                    <!-- Instagram Circular Button -->
                    <a href="${member.instagram}" target="_blank" class="flex items-center justify-center bg-white/10 hover:bg-cyan-500/20 border border-white/15 hover:border-cyan-500/40 rounded-xl p-2.5 text-white transition-all backdrop-blur-md shadow-sm active:scale-95" title="Connect on Instagram">
                        <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
                            <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                        </svg>
                    </a>
                </div>
            </div>
        </div>
    `;
}

function renderBoardMembers() {
    const gridContainer = document.getElementById('board-grid-container');
    if (!gridContainer) return;

    gridContainer.innerHTML = boardMembers.map(createMemberCardHtml).join('');

    if (typeof gsap !== 'undefined') {
        gsap.to('.board-card', {
            opacity: 1,
            y: 0,
            duration: 0.5,
            stagger: 0.04,
            ease: "power2.out"
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    renderBoardMembers();
});
