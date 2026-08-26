
import os, re

base_dir = r"c:\Users\BIT\OneDrive - Amity University\Desktop\iiche"

html_files = [
    "index.html",
    os.path.join("pages", "admin.html"),
    os.path.join("pages", "committee.html"),
    os.path.join("pages", "departments.html"),
    os.path.join("pages", "events.html"),
    os.path.join("pages", "forgot-password.html"),
    os.path.join("pages", "login.html"),
    os.path.join("pages", "more.html"),
    os.path.join("pages", "reset-password.html"),
    os.path.join("pages", "verify-otp.html"),
    os.path.join("events", "coalescnece.25.html"),
    os.path.join("events", "coalescnece.26.html"),
    os.path.join("events", "otherevents.html"),
    os.path.join("events", "talks.html"),
    os.path.join("events", "workshop.html")
]

preconnect_block = """    <!-- High-Speed CDN & Font Preconnects -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <link rel="preconnect" href="https://cdnjs.cloudflare.com">
    <link rel="preconnect" href="https://res.cloudinary.com">
    <link rel="dns-prefetch" href="https://cdn.jsdelivr.net">
    <link rel="dns-prefetch" href="https://cdnjs.cloudflare.com">
    <link rel="dns-prefetch" href="https://res.cloudinary.com">"""

for rel_path in html_files:
    full_path = os.path.join(base_dir, rel_path)
    if not os.path.exists(full_path):
        print(f"Skipping missing file: {rel_path}")
        continue
        
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    
    # 1. Update Lenis CDN from unpkg to jsdelivr fast CDN
    content = content.replace(
        "https://unpkg.com/lenis@1.1.13/dist/lenis.min.js",
        "https://cdn.jsdelivr.net/npm/lenis@1.1.18/dist/lenis.min.js"
    )
    content = re.sub(
        r'https://unpkg\.com/lenis@[^/]+/dist/lenis\.min\.js',
        'https://cdn.jsdelivr.net/npm/lenis@1.1.18/dist/lenis.min.js',
        content
    )
    
    # 2. Update Lucide from unpkg@latest (which causes 302 redirects) to pinned fast jsdelivr CDN
    content = content.replace(
        "https://unpkg.com/lucide@latest",
        "https://cdn.jsdelivr.net/npm/lucide@0.468.0/dist/umd/lucide.min.js"
    )
    
    # 3. Update GSAP CDN to latest 3.12.5
    content = content.replace(
        "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"
    )

    # 4. Ensure Preconnect Block in <head>
    if "<!-- High-Speed CDN & Font Preconnects -->" not in content:
        # Check for existing font preconnects and replace or inject
        old_preconnect = re.search(r'<link rel=["\']preconnect["\'] href=["\']https://fonts\.googleapis\.com["\'][^>]*>\s*(<link rel=["\']preconnect["\'] href=["\']https://fonts\.gstatic\.com["\'][^>]*>)?', content)
        if old_preconnect:
            content = content.replace(old_preconnect.group(0), preconnect_block, 1)
        elif "<head>" in content:
            content = content.replace("<head>", "<head>\n" + preconnect_block, 1)

    # 5. Cloudinary image URLs in HTML: add auto format and quality
    # E.g. https://res.cloudinary.com/.../upload/v1234/... -> https://res.cloudinary.com/.../upload/f_auto,q_auto/v1234/...
    def optimize_cloudinary_img(match):
        prefix = match.group(1) # e.g. https://res.cloudinary.com/dobshyhdz/image/upload/
        rest = match.group(2)
        if "f_auto" in rest or "q_auto" in rest:
            return match.group(0)
        return f"{prefix}f_auto,q_auto/{rest}"

    content = re.sub(r'(https://res\.cloudinary\.com/[^/]+/image/upload/)(v\d+/[^\s"\'>]+)', optimize_cloudinary_img, content)

    if content != original:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Optimized CDN in: {rel_path}")
    else:
        print(f"No changes needed in: {rel_path}")
