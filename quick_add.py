"""
quick_add.py — Paste affiliate links in input.md → auto-scrape → create blog_input.json

Usage:
    python quick_add.py          — auto picks next pending blog
    python quick_add.py 9        — jump to blog #9 specifically
"""

import json
import os
import re
import sys

# Force UTF-8 output so Amazon product names with Unicode chars don't crash on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BLOGS_FILE  = 'blogs.md'
INPUT_FILE  = 'blog_input.json'
LINKS_FILE  = 'input.md'

CATEGORY_KEYWORDS = {
    'living'   : ['sofa', 'couch', 'coffee table', 'throw pillow', 'area rug', 'rug',
                  'curtain', 'accent chair', 'living room', 'bookshelf', 'ottoman', 'lamp'],
    'bedroom'  : ['bedroom', 'bedding', 'duvet', 'comforter', 'throw blanket', 'nightstand',
                  'headboard', 'dresser', 'mirror', 'vanity', 'bed frame', 'pillow'],
    'kitchen'  : ['kitchen', 'dining', 'table runner', 'centerpiece', 'candle', 'pendant',
                  'bar stool', 'kitchen decor', 'kitchen curtain'],
    'bathroom' : ['bathroom', 'bath mat', 'towel', 'shower curtain', 'bath decor'],
    'office'   : ['desk', 'home office', 'office decor', 'desk lamp', 'bookcase'],
    'wall'     : ['wall art', 'gallery wall', 'wall decor', 'picture frame', 'canvas', 'tapestry'],
    'lighting' : ['lamp', 'pendant', 'chandelier', 'sconce', 'floor lamp', 'string light'],
    'outdoor'  : ['patio', 'outdoor', 'garden', 'planter', 'outdoor rug'],
    'boho'     : ['boho', 'macrame', 'rattan', 'wicker', 'jute', 'woven', 'natural'],
    'cozy'     : ['cozy', 'hygge', 'blanket', 'candle', 'throw', 'warm', 'aesthetic'],
    'luxury'   : ['luxury', 'designer', 'statement', 'premium', 'elegant', 'linen', 'velvet'],
}


def detect_category(title):
    t = title.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in t for k in kws):
            return cat
    return 'general'


def read_next_blog(target_num=None):
    if not os.path.exists(BLOGS_FILE):
        return None, None, None
    with open(BLOGS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*⬜ Pending\s*\|'
    matches = re.findall(pattern, content)
    if not matches:
        return None, None, None
    if target_num is not None:
        for num, title in matches:
            if int(num) == target_num:
                return int(num), title.strip(), detect_category(title)
        return None, None, None
    num, title = matches[0]
    return int(num), title.strip(), detect_category(title)


def mark_blog_done(blog_number):
    with open(BLOGS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f'| {blog_number} |') and '⬜ Pending' in line:
            lines[i] = line.replace('⬜ Pending', '✅ Done')
            break
    with open(BLOGS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"  blogs.md: Blog #{blog_number} marked Done")


def read_links_from_file():
    """Read affiliate links from input.md — skip comment lines and blank lines."""
    if not os.path.exists(LINKS_FILE):
        print(f"  ERROR: {LINKS_FILE} not found.")
        return []
    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    entries = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        url = parts[0]
        if not url.startswith('http'):
            continue
        price = ""
        if len(parts) > 1:
            raw_price = parts[1].lstrip('$')
            if re.match(r'^\d+\.?\d*$', raw_price):
                price = f"${raw_price}"
        entries.append((url, price))
    return entries


def scrape_amazon(affiliate_link):
    """Scrape Amazon via ScraperAPI (US IP) — gets name, price, rating, image.
    Always stores the original affiliate_link (amzn.to), NOT the resolved Amazon URL."""
    import requests as _req
    from config import SCRAPER_API_KEY

    # Resolve short link → full URL (needed for ScraperAPI to land on correct variant)
    try:
        resp = _req.get(affiliate_link, allow_redirects=True, timeout=10,
                        headers={"User-Agent": "Mozilla/5.0"})
        full_url = resp.url
    except Exception:
        full_url = affiliate_link

    print(f"    URL: {full_url[:80]}")

    # Fetch via ScraperAPI (US IP, bypasses bot block + price geo-restriction)
    try:
        r = _req.get(
            'http://api.scraperapi.com',
            params={'api_key': SCRAPER_API_KEY, 'url': full_url, 'country_code': 'us'},
            timeout=60
        )
        html = r.text
    except Exception as e:
        print(f"    ScraperAPI error: {e}")
        return None

    if 'api-services-support@amazon.com' in html:
        print("    Amazon bot block even via ScraperAPI")
        return None

    # Store original affiliate link, not resolved URL
    result = {'name': '', 'price': '', 'rating': '', 'image': '', 'affiliate_link': affiliate_link}

    # Name
    m = re.search(r'id="productTitle"[^>]*>\s*(.*?)\s*</span>', html, re.DOTALL)
    if m:
        result['name'] = re.sub(r'\s+', ' ', m.group(1)).strip()

    # Rating
    m = re.search(r'([\d.]+) out of 5 stars', html)
    if m:
        result['rating'] = m.group(1)

    # Image — hiRes from JS object, then data-old-hires, then landing image src
    m = re.search(r'"hiRes"\s*:\s*"(https://m\.media-amazon\.com/images/I/[^"]+)"', html)
    if m:
        result['image'] = m.group(1)
    else:
        m = re.search(r'id="landingImage"[^>]+data-old-hires="([^"]+)"', html)
        if m:
            result['image'] = m.group(1)
        else:
            m = re.search(r'id="landingImage"[^>]+src="([^"]+)"', html)
            if m:
                result['image'] = m.group(1)

    # Price — apex-pricetopay-value offscreen span (USD price)
    m = re.search(r'apex-pricetopay-value[^>]*>.*?<span class="a-offscreen">\$?([\d,]+\.?\d*)<', html, re.DOTALL)
    if m:
        result['price'] = '$' + m.group(1)
    else:
        m = re.search(r'class="a-offscreen">\$?([\d,]+\.\d{2})</span>', html)
        if m:
            result['price'] = '$' + m.group(1)

    # Debug: show what's missing
    missing = [k for k in ('name', 'price', 'rating', 'image') if not result[k]]
    if missing:
        print(f"    [MISSING] {', '.join(missing)}")

    return result


def run():
    print(f"\n{'='*62}")
    print(f"  QUICK ADD — Reading links from {LINKS_FILE}")
    print(f"{'='*62}")

    target_num = None
    if len(sys.argv) > 1:
        try:
            target_num = int(sys.argv[1])
        except ValueError:
            pass

    blog_number, blog_title, category = read_next_blog(target_num)

    if not blog_title:
        if target_num:
            print(f"\n  Blog #{target_num} not found or already done!")
        else:
            print("\n  No pending blogs!")
        return

    print(f"\n  Blog #{blog_number}: {blog_title}")
    print(f"  Category: {category}")

    entries = read_links_from_file()
    if not entries:
        print(f"\n  No links found in {LINKS_FILE}!")
        print(f"  Paste your affiliate links there (one per line) and rerun.")
        return

    print(f"  Links found: {len(entries)}")
    print(f"\n  Scraping {len(entries)} products (~10s each)...\n")

    products = []
    for i, (link, paste_price) in enumerate(entries):
        print(f"  [{i+1}/{len(entries)}] {link}")
        data = scrape_amazon(link)

        if data is None:
            print(f"    SKIP — scrape failed\n")
            continue

        name          = data.get('name', '')
        rating        = data.get('rating', '')
        image         = data.get('image', '')
        scraped_price = data.get('price', '')

        # Price: prefer paste price, then scraped price
        price = paste_price or scraped_price

        # --- STOP and ask for any missing field — no dummy values ---
        if not price:
            print(f"    [!] Price missing — open Amazon page and enter exact price:")
            raw = input("        Price (e.g. 19.99): $").strip().lstrip('$')
            price = f"${raw}" if raw else ""

        if not rating:
            print(f"    [!] Rating missing — check Amazon page:")
            raw = input("        Rating (e.g. 4.5): ").strip()
            rating = raw if raw else ""

        if not name:
            print(f"    [!] Name missing — enter product name:")
            name = input("        Name: ").strip()

        if not image:
            print(f"    [!] Image URL missing — paste from Amazon page source:")
            image = input("        Image URL: ").strip()

        status = "[OK]" if (name and price and rating and image) else "[!] "
        print(f"    {status} {name[:55]}")
        print(f"       Price: {price or 'MISSING'}  Rating: {rating or 'MISSING'}  Image: {'OK' if image else 'MISSING'}\n")

        products.append({
            "name":           name,
            "price":          price,
            "rating":         rating,
            "affiliate_link": link,      # original amzn.to link
            "image_url":      image
        })

    if not products:
        print("No products collected.")
        return

    # Summary
    print(f"{'─'*62}")
    print(f"  SUMMARY — {len(products)} products for Blog #{blog_number}")
    for i, p in enumerate(products):
        img_ok = "OK" if p["image_url"] else "NO IMG"
        print(f"  {i+1}. [IMG:{img_ok}] {p['name'][:48]}  {p['price']}  {p['rating']}*")

    # Save blog_input.json
    blog_data = {
        "blog_number": blog_number,
        "blog_title":  blog_title,
        "category":    category,
        "products":    products
    }
    with open(INPUT_FILE, 'w') as f:
        json.dump(blog_data, f, indent=2)

    mark_blog_done(blog_number)

    print(f"\n  [DONE] Saved {INPUT_FILE} -- {len(products)} products")
    print(f"  Next: python step2_generate.py")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    run()
