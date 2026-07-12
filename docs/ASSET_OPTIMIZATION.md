# Asset Optimization

Guidance for image and media assets in the Voya frontend, particularly the landing page.

## Current State

- **Landing assets**: Hero image (`hero-voya.jpg`), testimonial PNGs (`intro-testimonials/*.png`, `people-images/*.png`), example itinerary PNGs, How It Works images
- **Gitignore**: Exceptions allow committed PNGs/JPGs for UI; most other `*.png`/`*.jpg` are ignored
- **Impact**: Binary assets add weight to every clone. Acceptable for a small set (~4–15 images, <500KB total)

## When to Optimize

| Trigger | Action |
|---------|--------|
| < 15 images, < 500KB total | Keep current approach (PNG/JPG in repo) |
| > 15 images or > 500KB | Consider WebP conversion and/or external hosting |
| New landing sections with many assets | Re-evaluate before adding |

## Options (When Needed)

### 1. WebP Conversion

Convert PNG/JPG to WebP for smaller file sizes (often 25–50% reduction).

**Build step (e.g. Vite/Webpack):**
- Use `sharp`, `imagemin-webp`, or `vite-plugin-imagemin`
- Output `.webp` alongside or instead of originals
- Add `<picture>` with fallback for older browsers if needed

**One-off script:**
```bash
# Example with sharp (npm install sharp)
node -e "
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
// Convert images in assets/landing-page/
"
```

### 2. External Hosting

- Host images on S3 + CloudFront (or similar CDN)
- Reference by URL in components
- Reduces clone size; adds deployment and CDN dependency

### 3. Keep PNGs

- If total size stays small and image count is low, committing PNGs is fine
- Simplest approach; no extra tooling

## Decision Log

- **2026-03**: Current asset count is acceptable. Document options for future growth.
- Revisit when adding new landing sections or when total landing image size exceeds ~500KB.
