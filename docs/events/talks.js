const placementDiarySpeakers = [
    {
        name: "Khusi Mandal",
        company: "ZS Associates",
        role: "Decision Analytics Associate",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783518153/khusi_mandal_ghdeni.jpg",
        linkedin: "https://www.linkedin.com/in/khushi-mandal-47b295293/"
    },
    {
        name: "Saloni Singh",
        company: "PwC India",
        role: "Associate Consultant",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783518134/WhatsApp_Image_2026-07-08_at_18.34.14_hh3b8z.jpg",
        linkedin: "https://www.linkedin.com/in/salonisingh28/"
    },
    {
        name: "Mayank Giri",
        company: "Iris Aerial Innovations",
        role: "Business Analyst",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783518165/mayank_giri_rxnyaq.jpg",
        linkedin: "https://www.linkedin.com/in/mayank-giri-66b24321b/"
    },
    {
        name: "Saarim Sohail",
        company: "Urban Company, Ex-Polycab",
        role: "Category Manager",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527736/1744592849795_y6usuf.jpg",
        linkedin: "https://www.linkedin.com/in/mohammad-saarim-sohail/"
    },
    {
        name: "Dev Kumar",
        company: "Urban Company, Ex-Vedanta",
        role: "Manager - Buisness Analytics",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527736/1700302810464_xbje6f.jpg",
        linkedin: "https://www.linkedin.com/in/dev-kumar-2355a9229/"
    },
    {
        name: "Rupam Tirkey",
        company: "TSS Advertising",
        role: "Business Development Executive",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527746/1783183058955_nsr7tb.png",
        linkedin: "https://www.linkedin.com/in/rupam-tirkey-50b05a23a/"
    },
    {
        name: "Shayan Hamza",
        company: "IOCL, Ex-Vedanta",
        role: "Grade- A Officer",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527746/1774948049697_pl90pp.png",
        linkedin: "https://www.linkedin.com/in/shayan-hamza-58201b233/"
    },
    {
        name: "Umang Raj",
        company: "Maruti Suzuki",
        role: "Graduate Engineer Trainee",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527738/1756495230971_mg9lta.png",
        linkedin: "https://www.linkedin.com/in/umang-raj-a18b931bb/"
    },
    {
        name: "Tushar Aryan",
        company: "Reliance, Ex-AtomGrid",
        role: "Graduate Engineer Trainee",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527736/1762494020185_y9jf49.jpg",
        linkedin: "https://www.linkedin.com/in/tushar-aryan/"
    },
    {
        name: "Shem Vishal",
        company: "Tata Steel",
        role: "Graduate Engineer Trainee",
        image: "https://res.cloudinary.com/dobshyhdz/image/upload/v1783527740/1657019610842_ghfy2r.jpg",
        linkedin: "https://www.linkedin.com/in/shem-vishal-79a61b232/"
    }
];

function initSpeakersMarquee() {
    const marqueeTrack = document.getElementById('speakers-marquee-track');
    if (!marqueeTrack) {
        console.warn("Could not find speakers marquee track (#speakers-marquee-track)");
        return;
    }
    const totalSets = 2;
    let htmlContent = '';

    for (let set = 0; set < totalSets; set++) {
        placementDiarySpeakers.forEach((speaker) => {
            htmlContent += `
                <a href="${speaker.linkedin}" target="_blank" rel="noopener noreferrer" 
                   class="w-[200px] sm:w-[240px] shrink-0 bg-[#021814]/75 backdrop-blur-xl border border-amber-500/10 hover:border-amber-500/40 rounded-2xl p-5 flex flex-col items-center text-center transition-all duration-300 hover:shadow-[0_10px_35px_rgba(245,158,11,0.12)] group/card cursor-pointer relative overflow-hidden">
                    
                    <!-- Card Glow Effect on Hover -->
                    <div class="absolute -inset-px bg-gradient-to-r from-amber-500/0 via-amber-500/5 to-amber-500/0 opacity-0 group-hover/card:opacity-100 transition-opacity pointer-events-none rounded-2xl"></div>
                    
                    <!-- Image Container -->
                    <div class="relative w-32 h-32 sm:w-36 sm:h-36 rounded-full overflow-hidden mb-4 border-2 border-amber-500/15 group-hover/card:border-amber-500/50 transition-all duration-300 shadow-[0_0_20px_rgba(245,158,11,0.05)] shrink-0">
                        <img src="${speaker.image}" alt="${speaker.name}" class="w-full h-full object-cover transition-transform duration-500 group-hover/card:scale-110">
                        
                        <!-- Hover LinkedIn Overlay -->
                        <div class="absolute inset-0 bg-black/60 opacity-0 group-hover/card:opacity-100 transition-opacity flex items-center justify-center">
                            <svg class="w-6 h-6 sm:w-8 sm:h-8 fill-amber-400" viewBox="0 0 24 24">
                                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.779-1.75-1.75s.784-1.75 1.75-1.75 1.75.779 1.75 1.75-.784 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                            </svg>
                        </div>
                    </div>
                    
                    <!-- Text Details -->
                    <h5 class="text-white font-bold text-sm sm:text-base group-hover/card:text-amber-400 transition-colors line-clamp-1">${speaker.name}</h5>
                    <p class="text-slate-400 text-[11px] sm:text-xs mt-1 font-light leading-snug line-clamp-2">${speaker.role}</p>
                    
                    <!-- Company Badge -->
                    <div class="mt-3 px-3 py-1 rounded bg-amber-500/5 border border-amber-500/10 text-[10px] font-semibold text-amber-400 tracking-wider uppercase group-hover/card:bg-amber-500/10 group-hover/card:border-amber-500/20 transition-all">
                        ${speaker.company}
                    </div>
                </a>
            `;
        });
    }

    marqueeTrack.innerHTML = htmlContent;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSpeakersMarquee);
} else {
    initSpeakersMarquee();
}
