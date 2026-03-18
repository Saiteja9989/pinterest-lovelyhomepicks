"""
start.py — Master workflow controller (FULLY AUTOMATIC).

Run: python start.py
Run: python start.py 13   ← target specific blog number

Flow:
  1. Reads next pending blog title from blogs.md
  2. Groq suggests N search queries (N from blog title)
  3. ScraperAPI searches Amazon for each query → picks top product
  4. Scrapes product details (name, price, rating, image)
  5. Builds affiliate link: amazon.com/dp/{ASIN}?tag=smarthomeorg-20
  6. Writes blog_input.json — no manual steps
  7. Generates blog HTML → uploads to Blogger
  8. Generates 10 pins + images → adds to pins_queue_new.json
"""
import json
import os
import re
import sys
import subprocess
from urllib.parse import quote_plus

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
from config import GROQ_API_KEY, GROQ_MODEL, SCRAPER_API_KEY, GEMINI_API_KEY

BLOGS_FILE     = 'blogs.md'
INPUT_FILE     = 'blog_input.json'
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
AMAZON_TAG     = "smarthomeorg-20"  # shared tag for all niches
SCRAPER_BASE   = "http://api.scraperapi.com"

# Words describing blog angle/style — not product identifiers
RELEVANCE_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'for', 'of', 'in', 'on', 'at', 'to', 'by',
    'with', 'from', 'into', 'that', 'this', 'these', 'those', 'its',
    'i', 'my', 'your', 'you', 'we', 'our', 'they', 'them', 'their', 'it',
    'is', 'are', 'was', 'were', 'have', 'will', 'get', 'gets', 'got',
    'need', 'needs', 'make', 'makes', 'save', 'saves', 'work', 'works',
    'buy', 'buying', 'stop', 'never', 'always', 'ever', 'only', 'just',
    'best', 'good', 'bad', 'cheap', 'secret', 'entire', 'whole', 'tested',
    'ranked', 'professional', 'real', 'actual', 'clutter', 'free', 'worthy',
    'pinterest', 'worth', 'amazon', 'how', 'why', 'what', 'which', 'here',
    'there', 'instead', 'again', 'forever', 'finally', 'every', 'only',
    'look', 'looks', 'people', 'thing', 'things', 'using', 'swear',
    'instantly', 'ridiculously', 'expensive', 'actually', 'create', 'double',
    # Price/budget words — not product identifiers
    'under', 'over', 'below', 'above', 'budget', 'affordable', 'price',
    'less', 'than', 'most', 'some', 'many', 'much', 'more',
}

MIN_PRODUCT_RATING = 3.5  # Skip products rated below this on Amazon


def kw_in_text(kw, text):
    """Keyword match that handles simple plural/singular: 'organizers' matches 'organizer'."""
    if kw in text:
        return True
    # Strip trailing 's' to match singular forms (organizers→organizer, bins→bin)
    if kw.endswith('s') and len(kw) > 4 and kw[:-1] in text:
        return True
    return False


def get_topic_keywords(blog_title, category=''):
    """Extract product-relevant keywords from the blog title ONLY.
    Category keywords caused false positives — e.g. "countertop organizers" blog
    was accepting spice racks because 'spice' is a kitchen category keyword.
    Title keywords are specific to what the blog is actually about.
    Category keywords used only as a last-resort fallback if title yields < 2 words.
    """
    words = re.findall(r'[a-zA-Z]+', blog_title.lower())
    title_kws = [w for w in words if len(w) >= 4 and w not in RELEVANCE_STOPWORDS]

    if len(title_kws) >= 2:
        return title_kws  # title alone is specific enough

    # Very short title — fall back to a few core category terms only
    cat_kws = [kw for kw in CATEGORY_KEYWORDS.get(category, [])
               if ' ' not in kw and len(kw) >= 4]
    combined = title_kws[:]
    for kw in cat_kws[:5]:  # max 5 category terms, not the full list
        if kw not in combined:
            combined.append(kw)
    return combined


CATEGORY_KEYWORDS = {
    'living'   : ['sofa', 'couch', 'coffee table', 'throw pillow', 'area rug', 'rug', 'curtain',
                  'accent chair', 'living room', 'bookshelf', 'ottoman', 'side table', 'lamp'],
    'bedroom'  : ['bedroom', 'bedding', 'duvet', 'comforter', 'throw blanket', 'nightstand',
                  'headboard', 'dresser', 'mirror', 'vanity', 'bed frame', 'pillow'],
    'kitchen'  : ['kitchen', 'dining', 'table runner', 'centerpiece', 'candle', 'pendant light',
                  'bar stool', 'kitchen decor', 'kitchen curtain'],
    'bathroom' : ['bathroom', 'bath mat', 'towel', 'shower curtain', 'bath decor', 'vanity mirror'],
    'office'   : ['desk', 'home office', 'office decor', 'desk lamp', 'bookcase'],
    'wall'     : ['wall art', 'gallery wall', 'wall decor', 'picture frame', 'canvas print', 'tapestry'],
    'lighting' : ['lamp', 'pendant', 'chandelier', 'sconce', 'floor lamp', 'table lamp', 'string light'],
    'outdoor'  : ['patio', 'outdoor', 'garden', 'outdoor furniture', 'outdoor rug', 'planter'],
    'general'  : ['home decor', 'interior design', 'aesthetic', 'cozy home', 'home styling'],
}

# Words that disqualify a product from a category.
# e.g. a kitchen blog must NOT get makeup/bathroom/office/garage products.
CATEGORY_EXCLUSIONS = {
    'living'   : ['garage', 'tool', 'drill', 'outdoor furniture', 'patio', 'garden'],
    'bedroom'  : ['kitchen', 'garage', 'outdoor', 'patio'],
    'kitchen'  : ['bedroom', 'bathroom', 'garage', 'outdoor', 'tool'],
    'bathroom' : ['kitchen', 'garage', 'outdoor', 'tool', 'bedroom'],
    'office'   : ['kitchen', 'bathroom', 'garage', 'outdoor', 'tool'],
    'wall'     : ['garage', 'tool', 'outdoor', 'kitchen'],
    'lighting' : ['garage', 'tool', 'outdoor furniture'],
    'outdoor'  : ['bedroom', 'kitchen', 'bathroom'],
    'general'  : [],
}


# ── HELPERS ────────────────────────────────────────────────────────────────────

def detect_category(title):
    t = title.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in t for k in kws):
            return cat
    return 'general'


def get_next_pending_blog():
    if not os.path.exists(BLOGS_FILE):
        return None, None
    with open(BLOGS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    matches = re.findall(r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*⬜ Pending\s*\|', content)
    if not matches:
        return None, None
    num, title = matches[0]
    return int(num), title.strip()


def get_blog_by_number(target_num):
    if not os.path.exists(BLOGS_FILE):
        return None, None
    with open(BLOGS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    for num, title in re.findall(r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(?:⬜ Pending|✅ Done)\s*\|', content):
        if int(num) == target_num:
            return int(num), title.strip()
    return None, None


def mark_blog_done(blog_number):
    with open(BLOGS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if re.match(rf'\|\s*{blog_number}\s*\|', line) and '⬜ Pending' in line:
            lines[i] = line.replace('⬜ Pending', '✅ Done')
            break
    with open(BLOGS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def extract_product_count(blog_title):
    # Leading number is always the product count (e.g. "9 Cheap Kitchen...")
    m = re.match(r'^(\d+)\s', blog_title)
    if m:
        return int(m.group(1))
    # Remove price patterns first so "$25" or "under $25" numbers are ignored
    title_no_price = re.sub(r'(\$\s*\d+|\bunder\s+\$?\d+|\bover\s+\$?\d+|\bbelow\s+\$?\d+|\babove\s+\$?\d+)', '', blog_title, flags=re.IGNORECASE)
    for m in re.finditer(r'\b(\d+)\b', title_no_price):
        n = int(m.group(1))
        if not (2000 <= n <= 2099):
            return n
    return 7


def extract_price_limit(blog_title):
    """Return max price if title contains 'under $N', 'below $N', etc. Else None."""
    m = re.search(r'\b(?:under|below|less than)\s+\$?(\d+)', blog_title, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


# ── GROQ ───────────────────────────────────────────────────────────────────────

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def suggest_queries(blog_title, count, max_price=None):
    """Use Gemini + Google Search to find N real Amazon product names for the blog.
    Gemini searches the web and returns actual amazon.com product listings.
    If a product isn't found by ScraperAPI, suggest_retry_query (Groq) handles that slot.
    """
    if not GEMINI_API_KEY:
        print("  ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)
    return _suggest_queries_gemini(blog_title, count, max_price)


def _suggest_queries_gemini(blog_title, count, max_price=None):
    """Gemini 2.5 Flash with Google Search grounding — finds real Amazon product names."""
    price_note = f" priced under ${max_price:.0f}" if max_price else ""
    prompt = (
        f'Search Amazon.com and list exactly {count} real product names{price_note} '
        f'for this blog: "{blog_title}". '
        f'Every product must be directly relevant to the blog topic. '
        f'Return only a numbered list of exact Amazon product names, nothing else.'
    )

    r = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2}
        },
        timeout=120
    )
    r.raise_for_status()

    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]

    # Parse numbered list: "1. Product Name" → ["Product Name", ...]
    queries = []
    for line in raw.splitlines():
        line = line.strip()
        m = re.match(r'^\d+[\.\)]\s*\*{0,2}(.+?)\*{0,2}$', line)
        if m:
            name = m.group(1).strip()
            if name:
                queries.append(name)

    if not queries:
        raise ValueError(f"Gemini returned no parseable products. Raw: {raw[:200]}")

    print(f"  (Gemini found {len(queries)} real Amazon products via Google Search)")
    return queries[:count]


def suggest_retry_query(blog_title, failed_query, used_queries, max_price=None):
    """Ask Gemini for ONE replacement Amazon product name when a slot fails."""
    price_note = f" priced under ${max_price:.0f}" if max_price else ""
    used_str = ", ".join(f'"{q}"' for q in used_queries)
    prompt = (
        f'Search Amazon.com and find 1 real product name{price_note} for the blog: "{blog_title}". '
        f'The following products already failed or were already used — do NOT suggest them: {used_str}. '
        f'Return only the exact Amazon product name, nothing else.'
    )

    r = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.4}
        },
        timeout=120
    )
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Strip numbering if Gemini adds it
    raw = re.sub(r'^\d+[\.\)]\s*', '', raw)
    return raw.strip()


# ── AMAZON SEARCH + SCRAPE ─────────────────────────────────────────────────────

def scraper_get(url):
    """Fetch a URL via ScraperAPI (US IP)."""
    r = requests.get(SCRAPER_BASE,
        params={'api_key': SCRAPER_API_KEY, 'url': url, 'country_code': 'us'},
        timeout=60)
    return r.text


def _extract_price(html):
    """Try multiple patterns to extract price from Amazon product page HTML."""
    patterns = [
        # Primary: priceToPay block (most reliable, current price)
        r'apex-pricetopay-value[^>]*>.*?<span class="a-offscreen">\$?([\d,]+\.?\d*)<',
        # Secondary: any a-offscreen span with dollar amount
        r'<span class="a-offscreen">\$?([\d,]+\.\d{2})</span>',
        # Tertiary: priceblock_ourprice / deal price
        r'id="priceblock_ourprice"[^>]*>\s*\$?([\d,]+\.\d{2})',
        r'id="priceblock_dealprice"[^>]*>\s*\$?([\d,]+\.\d{2})',
        # JSON embedded data
        r'"priceAmount"\s*:\s*"?([\d.]+)"?',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL)
        if m:
            raw = m.group(1).replace(',', '')
            try:
                float(raw)  # validate it's a real number
                return '$' + raw
            except ValueError:
                continue
    return ''


def _extract_image(html):
    """Try multiple patterns to extract the best product image URL."""
    patterns = [
        # Best: hiRes from colorImages JSON
        r'"hiRes"\s*:\s*"(https://m\.media-amazon\.com/images/I/[^"]+)"',
        # Large from colorImages JSON
        r'"large"\s*:\s*"(https://m\.media-amazon\.com/images/I/[^"]+)"',
        # landingImage data attributes
        r'id="landingImage"[^>]+data-old-hires="(https://[^"]+)"',
        r'id="landingImage"[^>]+src="(https://[^"]+)"',
        # imgTagWrapper
        r'id="imgTagWrapper"[^>]*>.*?<img[^>]+src="(https://m\.media-amazon\.com/images/I/[^"]+)"',
        # Any media-amazon image in the page (fallback)
        r'"mainUrl"\s*:\s*"(https://m\.media-amazon\.com/images/I/[^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL)
        if m:
            url = m.group(1)
            # Filter out tiny thumbnails (SX/SY dimensions in URL)
            if '_SX38_' in url or '_SY38_' in url or 'sprite' in url.lower():
                continue
            return url
    return ''


def search_and_scrape(query, used_asins=None, topic_keywords=None, max_price=None, category=''):
    """Search Amazon → find first unused, relevant, quality product → return dict.

    Criteria (in order):
      1. ASIN not already used this run (no duplicates)
      2. Product name must contain at least one topic keyword (relevance)
      3. Rating >= MIN_PRODUCT_RATING if available (quality)
      4. Price <= max_price if a price limit is set (e.g. "Under $25")
      5. Name must be non-empty
    Tries up to 8 ASINs from the search results before giving up.
    If query is a bare ASIN (10-char alphanumeric), skip search and scrape directly.
    """
    if used_asins is None:
        used_asins = set()

    # ── If Gemini returned a direct ASIN, scrape it immediately ──
    if re.match(r'^[A-Z0-9]{10}$', query.strip()):
        asin = query.strip()
        print(f"    Direct ASIN: {asin}")
        unique_asins = [asin]
    else:
        # ── Search ──
        search_url = f"https://www.amazon.com/s?k={quote_plus(query)}&sort=review-rank"
        print(f"    Searching: {query}")
        html = scraper_get(search_url)
        unique_asins = None  # set below

    if unique_asins is None:
        # Extract ASINs ONLY from genuine product result divs (not ads/related/JS variables).
        # Amazon marks real search results with data-component-type="s-search-result".
        result_divs = re.findall(
            r'<div\b[^>]*?data-component-type="s-search-result"[^>]*?>',
            html, re.DOTALL
        )
        asins = []
        for div in result_divs:
            m = re.search(r'data-asin="([A-Z0-9]{10})"', div)
            if m:
                asins.append(m.group(1))

        if not asins:
            asins = re.findall(r'data-asin="([A-Z0-9]{10})"[^>]*data-index="\d+"', html)
        if not asins:
            asins = re.findall(r'data-asin="([A-Z0-9]{10})"', html)

        seen = set()
        unique_asins = []
        for a in asins:
            if a and a != 'undefined' and a not in seen:
                seen.add(a)
                unique_asins.append(a)

    if not unique_asins:
        print(f"    No ASINs found in search results")
        return None

    # Try candidates — max 8 scrapes per query
    scrape_count = 0

    for asin in unique_asins:
        if asin in used_asins:
            continue
        if scrape_count >= 8:
            break

        scrape_count += 1
        used_asins.add(asin)
        print(f"    ASIN: {asin} (attempt {scrape_count})")

        # ── Scrape product page ──
        html2 = scraper_get(f"https://www.amazon.com/dp/{asin}")

        if 'api-services-support@amazon.com' in html2:
            print(f"    Bot-blocked, trying next...")
            continue

        # ── Name ──
        name = ''
        m = re.search(r'id="productTitle"[^>]*>\s*(.*?)\s*</span>', html2, re.DOTALL)
        if m:
            name = re.sub(r'\s+', ' ', m.group(1)).strip()

        if not name:
            print(f"    No product name found, trying next...")
            continue

        # ── Relevance: at least one topic keyword in product name ──
        name_lower = name.lower()
        if topic_keywords:
            if not any(kw_in_text(kw, name_lower) for kw in topic_keywords):
                print(f"    [IRRELEVANT] '{name[:50]}' — trying next...")
                continue

        # ── Category exclusion: reject products from wrong category ──
        exclusions = CATEGORY_EXCLUSIONS.get(category, [])
        if exclusions:
            hit = next((w for w in exclusions if w in name_lower), None)
            if hit:
                print(f"    [WRONG CATEGORY] '{name[:50]}' contains '{hit}' — trying next...")
                continue

        # ── Rating ──
        rating = ''
        m = re.search(r'([\d.]+) out of 5 stars', html2)
        if m:
            rating = m.group(1)

        # ── Quality filter ──
        if rating:
            try:
                if float(rating) < MIN_PRODUCT_RATING:
                    print(f"    [LOW QUALITY] {rating}★ < {MIN_PRODUCT_RATING} — trying next...")
                    continue
            except ValueError:
                pass

        # ── Canonical ASIN (fixes redirect issue) ──
        # Amazon search results return child/variant ASINs that redirect to the parent.
        # Extract the true canonical ASIN from the product page so the affiliate link
        # points directly to the correct product without any redirect.
        canonical_asin = asin
        m = re.search(r'<link rel="canonical"[^>]+href="https://www\.amazon\.com/[^/]*/dp/([A-Z0-9]{10})/', html2)
        if not m:
            m = re.search(r'<link rel="canonical"[^>]+href="https://www\.amazon\.com/dp/([A-Z0-9]{10})/', html2)
        if m:
            canonical_asin = m.group(1)
            if canonical_asin != asin:
                print(f"    Canonical ASIN: {canonical_asin} (was {asin})")
                used_asins.add(canonical_asin)  # prevent another query picking this too

        # ── Price ──
        price = _extract_price(html2)

        # ── Image ──
        image = _extract_image(html2)

        # ── Price limit filter (e.g. "Under $25") ──
        if max_price and price:
            try:
                actual = float(re.sub(r'[^\d.]', '', price))
                if actual > max_price:
                    print(f"    [OVER BUDGET] {price} > ${max_price:.0f} — trying next...")
                    continue
            except ValueError:
                pass

        # ── Report ──
        missing = [k for k, v in [('price', price), ('rating', rating), ('image', image)] if not v]
        status = "✅" if not missing else f"⚠️  MISSING: {', '.join(missing)}"
        affiliate = f"https://www.amazon.com/dp/{canonical_asin}?tag={AMAZON_TAG}"
        print(f"    {status}")
        print(f"    NAME  : {name[:70]}")
        print(f"    PRICE : {price or '—'}  |  RATING: {rating or '—'}★  |  IMG: {'✓' if image else '✗'}")
        print(f"    ASIN  : {canonical_asin}")
        print(f"    LINK  : {affiliate}")

        return {
            'name':           name,
            'price':          price,
            'rating':         rating,
            'affiliate_link': affiliate,
            'image_url':      image
        }

    print(f"    All candidates exhausted for: {query}")
    return None


# ── MAIN ───────────────────────────────────────────────────────────────────────

def run():
    print("\n" + "=" * 62)
    print("  LOVELY HOME PICKS — FULL AUTOMATION")
    print("=" * 62)

    # ── STEP 1: Read blog ────────────────────────────────────────────────────
    target = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if target:
        print(f"\n[1/4] Loading Blog #{target}...")
        blog_num, blog_title = get_blog_by_number(target)
    else:
        print("\n[1/4] Reading next pending blog...")
        blog_num, blog_title = get_next_pending_blog()

    if not blog_title:
        print(f"  {'Blog #' + str(target) + ' not found!' if target else 'No pending blogs!'}")
        return

    category = detect_category(blog_title)
    product_count = extract_product_count(blog_title)
    topic_keywords = get_topic_keywords(blog_title, category)
    max_price = extract_price_limit(blog_title)

    print(f"\n{'─' * 62}")
    print(f"  Blog #{blog_num}: {blog_title}")
    print(f"  Category: {category}  |  Products: {product_count}")
    if max_price:
        print(f"  Price limit: under ${max_price:.0f}")
    print(f"  Topic keywords: {topic_keywords}")
    print(f"{'─' * 62}")

    # ── STEP 2: Gemini → find real Amazon product names ─────────────────────
    print(f"\n[2/4] Getting {product_count} product names from Gemini Search...")
    try:
        queries = suggest_queries(blog_title, product_count, max_price)
    except Exception as e:
        print(f"  Gemini error: {e}")
        return

    print(f"\n  Queries:")
    for i, q in enumerate(queries, 1):
        print(f"    {i}. {q}")

    # ── STEP 3: Search + scrape each product ────────────────────────────────
    print(f"\n[3/4] Searching Amazon & scraping {product_count} products...\n")
    products = []
    used_asins = set()
    used_queries = list(queries)  # track all tried queries to avoid repeats

    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{product_count}] {query}")
        data = search_and_scrape(query, used_asins, topic_keywords, max_price, category)

        if not data:
            # Step 1: ask Gemini for a replacement product and retry
            print(f"    → Asking Gemini for replacement product...")
            try:
                retry_query = suggest_retry_query(blog_title, query, used_queries, max_price)
                if retry_query:
                    used_queries.append(retry_query)
                    print(f"    → Retry: {retry_query}")
                    data = search_and_scrape(retry_query, used_asins, topic_keywords, max_price, category)
            except Exception as e:
                print(f"    → Retry failed: {e}")

        if not data and max_price:
            # Step 2: retry query also failed — relax price limit by 50% for this slot only
            relaxed = max_price * 1.5
            print(f"    → Relaxing price to ${relaxed:.0f} for this slot...")
            try:
                retry_query2 = suggest_retry_query(blog_title, query, used_queries, relaxed)
                if retry_query2:
                    used_queries.append(retry_query2)
                    print(f"    → Relaxed retry: {retry_query2}")
                    data = search_and_scrape(retry_query2, used_asins, topic_keywords, relaxed, category)
            except Exception as e:
                print(f"    → Relaxed retry failed: {e}")

        if data:
            products.append(data)
        else:
            print(f"    SKIP — no result after all retries\n")
        print()

    if not products:
        print("  No products found. Check ScraperAPI key or try again.")
        return

    # ── Product summary table ──────────────────────────────────────────────
    print(f"\n{'═' * 62}")
    print(f"  PRODUCT SUMMARY — {len(products)}/{product_count} found")
    print(f"{'═' * 62}")
    for i, p in enumerate(products, 1):
        asin = p['affiliate_link'].split('/dp/')[1].split('?')[0]
        flag = "✅" if p['price'] and p['rating'] and p['image_url'] else "⚠️ "
        print(f"  {flag} #{i:>2}  {p['name'][:52]}")
        print(f"        {p['price'] or 'no price':8}  {(p['rating'] or '?') + '★':6}  ASIN: {asin}")
        print(f"        {p['affiliate_link']}")
    print(f"{'═' * 62}\n")

    missing_products = [p for p in products if not p['price'] or not p['rating'] or not p['image_url']]
    if missing_products:
        print(f"  ⚠️  {len(missing_products)} product(s) have missing data.")
        print(f"  Fix manually in blog_input.json before continuing.\n")

    # Write blog_input.json
    blog_data = {
        "blog_number": blog_num,
        "blog_title":  blog_title,
        "category":    category,
        "products":    products
    }
    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(blog_data, f, indent=2, ensure_ascii=False)

    mark_blog_done(blog_num)
    print(f"  ✅ blog_input.json saved — {len(products)} products")

    if missing_products:
        input("\n  → Fix blog_input.json then press Enter to continue: ")

    # ── STEP 4: Generate blog + pins + images ────────────────────────────────
    print(f"\n[4/4] Generating blog, pins and images (~10 min)...")
    result = subprocess.run([sys.executable, 'step2_generate.py'], capture_output=False)
    if result.returncode != 0:
        print("  step2_generate.py failed.")
        return

    print(f"\n{'=' * 62}")
    print(f"  Blog #{blog_num} complete!")
    print(f"  ✅ Blog published to Blogger")
    print(f"  ✅ 10 pins added to pins_queue_new.json")
    print(f"  ✅ Images pushed to GitHub")
    print(f"{'=' * 62}\n")


if __name__ == "__main__":
    run()
