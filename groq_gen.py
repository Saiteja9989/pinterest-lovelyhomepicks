import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, BOARDS, TOPIC_TAGS

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def ask_gemini(prompt, temperature=0.5, max_tokens=8192, grounding=True):
    """Call Gemini 2.5 Flash. max_tokens up to 65536. grounding=False for JSON-only calls."""
    import time as _time
    gen_config = {"temperature": temperature, "maxOutputTokens": max_tokens}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config
    }
    if grounding:
        body["tools"] = [{"google_search": {}}]

    for attempt in range(4):
        r = requests.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=body, timeout=120)
        data = r.json()
        if r.status_code == 200:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        err = data.get("error", {})
        if r.status_code == 429:
            wait = 30
            import re as _re
            m = _re.search(r'retry.*?(\d+)s', err.get("message", ""), _re.IGNORECASE)
            if m:
                wait = int(m.group(1)) + 3
            print(f"    Gemini rate limit — waiting {wait}s (attempt {attempt+1}/4)...")
            _time.sleep(wait)
            continue
        if r.status_code in (500, 502, 503, 504):
            wait = 20 * (attempt + 1)
            print(f"    Gemini server error {r.status_code} — waiting {wait}s (attempt {attempt+1}/4)...")
            _time.sleep(wait)
            continue
        raise RuntimeError(f"Gemini error: {err}")
    raise RuntimeError("Gemini rate limit: max retries exceeded")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

WEBSITE = "smarthomeorganizing.com"

# ─── Map blog title keywords → specific room phrase for Freepik prompts ───────
TOPIC_ROOM = {
    # Kitchen sub-spaces (sorted longest-first for matching priority)
    'trash can'   : 'kitchen trash area',
    'trash bin'   : 'kitchen trash area',
    'garbage can' : 'kitchen trash area',
    'pull-out trash': 'kitchen trash area',
    'under counter': 'kitchen trash area',
    'pantry door' : 'pantry door',
    'under sink'  : 'under-sink cabinet',
    'lazy susan'  : 'kitchen turntable cabinet',
    'food container': 'kitchen pantry',
    'refrigerator': 'refrigerator',
    'countertop'  : 'kitchen countertop',
    'countertops' : 'kitchen countertop',
    'fridge'      : 'refrigerator',
    'freezer'     : 'freezer',
    'cabinet'     : 'kitchen cabinet',
    'pantry'      : 'pantry',
    'drawer'      : 'kitchen drawer',
    'drawers'     : 'kitchen drawer',
    'counter'     : 'kitchen countertop',
    'spice'       : 'spice cabinet',
    'pot'         : 'pot and pan cabinet',
    'shelf'       : 'kitchen shelf',
    'shelves'     : 'kitchen shelf',
    # Bathroom
    'medicine'    : 'medicine cabinet',
    'makeup'      : 'makeup vanity',
    'vanity'      : 'bathroom vanity',
    'shower'      : 'shower',
    'bathroom'    : 'bathroom',
    'toilet'      : 'bathroom',
    'hair'        : 'bathroom styling station',
    # Bedroom
    'under bed'   : 'under-bed storage',
    'closet'      : 'closet',
    'wardrobe'    : 'wardrobe',
    'dresser'     : 'dresser',
    'jewelry'     : 'jewelry vanity',
    'shoe'        : 'shoe storage area',
    'bedroom'     : 'bedroom',
    # Office
    'cable'       : 'desk cable management',
    'cord'        : 'desk cord area',
    'desk'        : 'home office desk',
    'file'        : 'home office',
    # Living / Entryway
    'coffee table': 'living room',
    'entryway'    : 'entryway',
    'living room' : 'living room',
    'toy'         : 'playroom',
    'toys'        : 'playroom',
    # Laundry / Garage
    'mudroom'     : 'mudroom',
    'linen'       : 'linen closet',
    'laundry'     : 'laundry room',
    'garage'      : 'garage',
    'tool'        : 'garage tool wall',
    'bike'        : 'garage',
}

# ─── Specific visual scene for each room (used in Freepik prompts) ────────────
# Makes images look unique per blog topic instead of all being generic "kitchen"
ROOM_VISUAL = {
    'pantry door'          : 'interior view of pantry door with over-door tiered wire rack organizers holding spice jars, canned goods, and bottles in metal baskets',
    'pantry'               : 'well-stocked pantry shelves with clear labeled containers, wicker baskets, and organized canned goods on white shelving',
    'refrigerator'         : 'open refrigerator interior with clear stackable bins on glass shelves, labeled produce drawers, and neatly sorted condiments',
    'kitchen drawer'       : "bird's-eye view of organized kitchen drawer with bamboo dividers neatly separating utensils, cutlery, and gadgets",
    'spice cabinet'        : 'pull-out tiered spice drawer insert with two rows of labeled spice jars in perfect alphabetical order',
    'kitchen countertop'   : 'clean minimalist kitchen countertop with matching canisters, one appliance, and a small tray corralling oils and vinegars',
    'kitchen cabinet'      : 'open kitchen cabinet with pull-out shelf organizer, stacked matching plates, and labeled pantry containers',
    'kitchen shelf'        : 'organized floating kitchen shelf with matching labeled containers, cookbooks, and potted herb plants',
    'kitchen turntable cabinet': 'kitchen corner cabinet open showing lazy susan turntable spinning with organized condiments, oils, and spices on tiered levels',
    'under-sink cabinet'   : 'organized under-sink cabinet with two-tier sliding shelf system, labeled cleaning spray bottles, and a caddy holder',
    'pot and pan cabinet'  : 'organized deep cabinet with vertical lid holder rack, pots stacked with pan protectors, and pans hung on inner door',
    'bathroom vanity'      : 'organized bathroom vanity countertop with acrylic makeup organizer, brush holders, and skincare bottles neatly arranged',
    'makeup vanity'        : 'aesthetic makeup vanity with acrylic multi-drawer organizer, brush holder, and cosmetics displayed under warm lighting',
    'shower'               : 'clean shower corner with rust-proof wall-mounted caddy organizer holding shampoo, conditioner, and soap bars on tiered shelves',
    'bathroom'             : 'organized bathroom with labeled fabric baskets under sink, acrylic toiletry organizer on counter, and towels folded on rack',
    'medicine cabinet'     : 'open medicine cabinet interior with labeled medicine bottles in small bins, first aid supplies sorted, and vitamins in clear containers',
    'bathroom styling station': 'organized bathroom countertop with heat-resistant hair tool holder, blow dryer stored vertically, and styling products in caddy',
    'closet'               : 'organized walk-in closet with matching slim velvet hangers, labeled fabric shelf bins, and shoe rack visible on floor',
    'wardrobe'             : 'organized wardrobe interior with color-coordinated hanging clothes on matching hangers, folded sweaters on shelves, labeled bins',
    'dresser'              : "bird's-eye view of opened dresser drawer with velvet drawer dividers separating neatly folded t-shirts, socks, and underwear",
    'under-bed storage'    : 'under-bed area showing slim wheeled storage containers being pulled out, labeled by season, maximizing floor space',
    'jewelry vanity'       : 'jewelry organizer on dressing table with earring display stand, ring dish, necklace hooks, and tiered bracelet holder',
    'shoe storage area'    : 'organized shoe rack with pairs aligned by color, clear stackable shoe boxes with photo labels on front',
    'bedroom'              : 'cozy organized bedroom with nightstand organizer tray, closet partially visible showing hanging pockets and labeled bins',
    'home office desk'     : 'organized home office desk with vertical file holder, cable management box, multi-compartment desk organizer, and plant',
    'desk cable management': 'clean desk setup with all cables routed through cable management spine, velcro ties, and mounted power strip hidden from view',
    'desk cord area'       : 'desk with zero visible cords — all cables managed through cord clips, box organizer, and adhesive cable holders',
    'home office'          : 'organized home office with upright file folder organizer, labeled color-coded folders, desk drawer with supply caddy',
    'living room'          : 'organized living room with storage ottoman open showing folded blankets, floating shelves with labeled decorative baskets',
    'entryway'             : 'organized entryway with wall-mounted key hook rack, mail sorter, slim shoe rack, and labeled fabric cubby bins',
    'playroom'             : 'colorful organized playroom with labeled toy bins on low white shelves, rolling art cart, and labeled toy chest',
    'mudroom'              : 'organized mudroom with labeled cubbies for each family member, wall hooks for bags and coats, boot tray, bench storage',
    'linen closet'         : 'organized linen closet with towels folded and stacked in labeled wire bins and sheets in clear labeled storage bags',
    'laundry room'         : 'organized laundry room with wall-mounted detergent dispenser shelf, labeled sorting bins, and folding station on counter',
    'garage'               : 'organized garage with pegboard tool wall, labeled clear storage bins on metal shelving, two bikes hung on wall hooks',
    'garage tool wall'     : 'pegboard wall with outlined tool silhouettes, double-hook holders for hammers and pliers, labeled bin accessories row',
    'kitchen'              : 'organized bright white kitchen with matching labeled containers on open shelves, clear countertops, and visible organized cabinet',
    'kitchen trash area'   : 'modern organized kitchen showing a sleek stainless steel step trash can beside cabinets, pull-out under-cabinet trash bin visible, clean white kitchen background with natural light',
}


def extract_product_type(blog_title):
    """Extract the 2-3 word specific product type from the blog title.
    e.g. 'cutting board organizer' from 'The $18 Cutting Board Organizer That Saves Drawer Space'
         'countertop organizers' from 'Amazon Best Countertop Organizers Under $25'
    """
    import re as _re
    title = _re.sub(r'\$\s*\d+|\b20\d\d\b|\b\d+\b', '', blog_title)
    skip = {
        'the', 'a', 'an', 'that', 'which', 'your', 'this', 'these', 'those',
        'for', 'of', 'in', 'on', 'at', 'to', 'by', 'with', 'and', 'or',
        'best', 'top', 'real', 'actually', 'finally', 'instantly', 'ridiculously',
        'saves', 'save', 'helps', 'makes', 'gets', 'doubles', 'tested', 'ranked',
        'space', 'time', 'money', 'home', 'house', 'room', 'storage', 'amazon',
        'under', 'over', 'below', 'above', 'budget', 'cheap', 'affordable',
        'double', 'triple', 'every', 'never', 'stop', 'always', 'ever',
        # room/location words — not part of the product name
        'kitchen', 'kitchens', 'bathroom', 'bathrooms', 'bedroom', 'bedrooms',
        'office', 'offices', 'living', 'garage', 'pantry', 'laundry', 'mudroom',
        'counter', 'countertop', 'countertops', 'cabinet', 'cabinets',
        'drawer', 'drawers', 'closet', 'closets', 'shelf', 'shelves',
        'small', 'zero', 'without', 'limited', 'tiny', 'rental', 'apartment',
    }
    words = _re.findall(r'[a-zA-Z]+', title.lower())
    product_words = [w for w in words if len(w) >= 4 and w not in skip]
    return ' '.join(product_words[:3]) if product_words else blog_title.lower()[:30]


def extract_topic(blog_title, category):
    """Return a specific room/sub-topic phrase from the blog title for image prompts.
    Falls back to category name if no keyword matched.
    """
    title_lower = blog_title.lower()
    for keyword in sorted(TOPIC_ROOM.keys(), key=len, reverse=True):
        if keyword in title_lower:
            return TOPIC_ROOM[keyword]
    return category


def get_room_visual(room):
    """Return a specific visual scene description. Falls back to generic if not in dict."""
    return ROOM_VISUAL.get(room, None)


def get_visual_scene(blog_title, product_type, category):
    """Get the best visual scene description for this blog topic.
    1. Try hardcoded TOPIC_ROOM → ROOM_VISUAL lookup (instant, no API call).
    2. If no specific match found, ask Gemini to generate a custom visual (works for ANY future topic).
    """
    room = extract_topic(blog_title, category)
    visual = get_room_visual(room)

    if visual:
        # Known topic — use cached description
        print(f"  Room visual: '{room}' (cached)")
        return room, visual

    # Unknown topic — ask Gemini for a specific visual scene description
    print(f"  Room visual: '{room}' not in cache — generating with Gemini...")
    prompt = (
        f'Describe a specific, photorealistic interior scene (1 sentence, max 25 words) for a Pinterest pin about "{blog_title}". '
        f'The main subject must be "{product_type}" shown organized and in use. '
        f'Focus on the product itself, lighting, and setting. No people. '
        f'Example format: "organized kitchen countertop with stainless steel step trash can beside white cabinets, warm natural window light"'
    )
    try:
        scene = ask_gemini(prompt, temperature=0.3, max_tokens=100, grounding=False).strip()
        # Strip quotes if Gemini added them
        scene = scene.strip('"\'')
        print(f"  Generated scene: {scene[:80]}")
        return room, scene
    except Exception as e:
        print(f"  Scene generation failed ({e}) — using fallback")
        return room, f'beautifully organized {category} space featuring {product_type}, clean and tidy with natural lighting'


def _get_style_definitions_UNUSED(room, category, n_products, n1, n2, n3, pr1, pr2, pr3, r1, r2, r3):
    """UNUSED — kept for reference only."""
    cat_t = category.title()
    room_t = room.title()
    cat_u = category.upper()
    room_visual = get_room_visual(room)
    return [
        # 0: LIFESTYLE PHOTO
        {
            "name": "LIFESTYLE PHOTO",
            "title_rule": (
                f'MUST start with a number. Use "{room_t}" specifically — NOT generic "{cat_t} organizer". '
                f'Angle: "N Best {room_t}s for [SPECIFIC BENEFIT] — 2026 Amazon Picks". '
                f'image_headline must say "{room_t.upper()} PICKS" or similar — never just "KITCHEN ORGANIZATION".'
            ),
            "freepik": (
                f'Lifestyle interior photography Pinterest pin, portrait 2:3 ratio. '
                f'Real interior photo showing {room_visual}, '
                f'warm natural window light, shot from slightly above at 45 degree angle. '
                f'Dark semi-transparent gradient overlay on bottom 40% of image. '
                f'Bold white sans-serif text reading \'[6-WORD HEADLINE]\' centered on overlay. '
                f'Smaller white subtext below reading \'STEP BY STEP GUIDE INSIDE\'. '
                f'Dark navy blue bar at very bottom with white text \'smarthomeorganizing.com\'. '
                f'Sharp focus, high resolution, real home interior, lifestyle photography.'
            ),
        },
        # 1: COMPARISON RANKED
        {
            "name": "COMPARISON RANKED",
            "title_rule": (
                f'MUST start with "How to Choose" or "Which". '
                f'Reference the SPECIFIC product type from the blog (e.g. "spice drawer insert", "pull-out fridge bin"). '
                f'Angle: comparison/decision-helper framing. Must feel different from other blogs.'
            ),
            "freepik": (
                f'Pinterest pin graphic design poster, portrait 2:3 ratio, clean pure white background. '
                f'Bold black sans-serif headline text at top reading \'[6-WORD HEADLINE]\'. '
                f'Three {room} organizer product images stacked vertically center-aligned with clear spacing. '
                f'Gold circular badge overlaid on product 1 with text \'#1 BEST {pr1}\'. '
                f'Gold badge on product 2 \'#2 TOP VALUE {pr2}\'. '
                f'Gold badge on product 3 \'#3 BUDGET {pr3}\'. '
                f'Row of 5 yellow star icons beside each product. '
                f'Dark navy blue footer bar at bottom with white text \'smarthomeorganizing.com\'. '
                f'Professional product comparison infographic.'
            ),
        },
        # 2: STOP HOOK
        {
            "name": "STOP HOOK",
            "title_rule": (
                f'MUST start with "Stop" or "Never". '
                f'Name a SPECIFIC mistake people make with {room_t}s (e.g. "Stop Buying {room_t}s That Waste Space", "Never Use This {room_t} Trick Again"). '
                f'image_headline must start with STOP or NEVER and mention {room_t.upper().split()[0]}. Do NOT write "BAD KITCHEN ORGANIZERS".'
            ),
            "freepik": (
                f'Pinterest pin graphic poster, portrait 2:3 ratio. '
                f'Bold bright red full-width banner at top with large white Impact font text reading \'STOP!\'. '
                f'Clean white background below. Bold black uppercase text reading \'[5-WORD WARNING HEADLINE]\'. '
                f'Three product images in a horizontal row center. '
                f'Bold black text \'WE TESTED {n_products} ON AMAZON\'. '
                f'Dark navy blue footer \'smarthomeorganizing.com\'. '
                f'High contrast urgent graphic design style.'
            ),
        },
        # 3: TIPS LIST
        {
            "name": "TIPS LIST",
            "title_rule": (
                f'MUST start with a number + "Tips", "Secrets", or "Hacks". '
                f'Focus specifically on {room_t}s (e.g. "7 {room_t} Hacks That Actually Work", "5 Secrets to a Clutter-Free {room_t}"). '
                f'image_headline must reference {room_t.upper().split()[0]} — not generic KITCHEN HACKS.'
            ),
            "freepik": (
                f'Pinterest pin design, portrait 2:3 ratio. '
                f'Top 40% real interior photo of beautifully organized {room} with clear containers, natural light. '
                f'Bottom 60% clean white section. Bold dark navy sans-serif headline \'[5-WORD TIPS HEADLINE]\'. '
                f'Clean numbered list in dark text: \'1. [SPECIFIC TIP]\', \'2. [SPECIFIC TIP]\', \'3. [SPECIFIC TIP]\'. '
                f'Dark navy footer bar \'smarthomeorganizing.com\'. Minimal clean editorial design.'
            ),
        },
        # 4: BEFORE/AFTER
        {
            "name": "BEFORE/AFTER",
            "title_rule": (
                f'MUST start with "I" — first-person transformation story. '
                f'Mention the SPECIFIC product from this blog and actual price {pr1}. '
                f'Angle: personal experience with THIS exact product type. Different from "I organized my kitchen" — be specific.'
            ),
            "freepik": (
                f'Pinterest pin lifestyle photography, portrait 2:3 ratio. '
                f'Vertical split design. Top half: cluttered messy {room} interior, items piled randomly, '
                f'poor organization, real interior photo. Bold red rounded label \'BEFORE\' top-left. '
                f'Bottom half: same {room} beautifully organized, clear labeled bins, everything in place, '
                f'warm light, real interior photo. Bold green label \'AFTER\' bottom-left. '
                f'Bold white text centered on divider reading \'THIS {pr1} AMAZON PRODUCT DID THIS\'. '
                f'Dark navy footer \'smarthomeorganizing.com\'. Real interior photography.'
            ),
        },
        # 5: DARK MOODY
        {
            "name": "DARK MOODY",
            "title_rule": (
                f'MUST be aspirational/aesthetic/emotional. No numbers. '
                f'Paint a visual dream specifically around the {room_t} (e.g. "The {room_t} That Changed My Mornings", "Your Dream {room_t} Starts Here"). '
                f'image_headline must mention {room_t.upper().split()[0]} — NEVER write "DREAM KITCHEN AESTHETIC" or generic kitchen text.'
            ),
            "freepik": (
                f'Pinterest pin cinematic interior photography, portrait 2:3 ratio. '
                f'Dramatic dark moody scene: {room_visual}, shot with dark charcoal walls and warm amber accent lighting. '
                f'Deep shadows on sides, warm golden light highlighting the organized storage. Dark atmospheric aesthetic. '
                f'Large bold white sans-serif headline centered \'[6-WORD ASPIRATIONAL HEADLINE]\'. '
                f'Small gold italic text below \'Full Amazon links inside\'. '
                f'Dark navy footer \'smarthomeorganizing.com\'. '
                f'Cinematic editorial photography, dramatic shadows, high contrast, moody interior.'
            ),
        },
        # 6: BUDGET PRICE
        {
            "name": "BUDGET PRICE",
            "title_rule": (
                f'MUST lead with a price, deal, or budget angle using the actual cheapest product price. '
                f'Name the SPECIFIC product type, not generic "{room_t} organizer". '
                f'Angle: "N [SPECIFIC PRODUCT TYPE] Under {pr1} That Actually Work — 2026 Amazon Finds".'
            ),
            "freepik": (
                f'Pinterest pin graphic design, portrait 2:3 ratio, bright white background. '
                f'Large bold bright red circle badge at top center with white text \'ONLY {pr1}\' in large Impact font. '
                f'Organized {room} photo below the badge, natural lighting, clear bins visible. '
                f'Bold black sans-serif text \'[5-WORD DEAL HEADLINE]\'. '
                f'Row of 5 solid yellow star icons. Small dark text \'{r1}/5 stars from Amazon buyers\'. '
                f'Dark navy footer \'smarthomeorganizing.com\'. Eye-catching deal graphic design.'
            ),
        },
        # 7: AUTHORITY RANKED — dark editorial magazine style (visually distinct from lifestyle)
        {
            "name": "AUTHORITY RANKED",
            "title_rule": (
                f'MUST lead with credibility — review count, Amazon ranking, or expert testing. '
                f'Name the SPECIFIC product from this blog. '
                f'Angle: "N [SPECIFIC PRODUCT] Ranked by Thousands of Amazon Buyers" or "We Tested Every [PRODUCT] on Amazon — Here Are the Winners".'
            ),
            "freepik": (
                f'Pinterest pin editorial magazine cover graphic design, portrait 2:3 ratio. '
                f'Dark charcoal slate background, NO white background, NO lifestyle photo. '
                f'Bold large white serif headline at top: \'[3-WORD HEADLINE]\'. '
                f'Thin horizontal gold divider line below headline. '
                f'Center panel: three {room} organizer product photographs on dark background with soft studio lighting and drop shadows. '
                f'Gold award ribbon badge overlaid on center product reading \'AMAZON #1 PICK 2026\'. '
                f'White bold ranking text below: \'1 — BEST OVERALL  2 — BEST VALUE  3 — BUDGET PICK\'. '
                f'Row of 5 filled gold star icons with text \'RANKED BY {r1}★ VERIFIED REVIEWS\'. '
                f'Dark navy footer bar: \'smarthomeorganizing.com\'. '
                f'Premium dark editorial magazine aesthetic, no white space, high contrast typography.'
            ),
        },
        # 8: PROBLEM/SOLUTION
        {
            "name": "PROBLEM/SOLUTION",
            "title_rule": (
                f'MUST start with "Why Your". '
                f'Name a SPECIFIC problem with {room_t}s (e.g. "Why Your {room_t} Is Always a Mess", "Why Your {room_t} Is Causing Food Waste"). '
                f'image_headline must reference {room_t.upper().split()[0]} — not generic MESSY KITCHEN.'
            ),
            "freepik": (
                f'Pinterest pin editorial graphic design, portrait 2:3 ratio, cream off-white background. '
                f'Bold red full-width top bar white text \'THE PROBLEM:\'. '
                f'Bold black text \'[5-WORD PROBLEM STATEMENT]\'. Thin red horizontal divider line. '
                f'Bold forest green full-width bar white text \'THE SOLUTION:\'. '
                f'Real interior photo of organized {room}, clear bins, neat labels. '
                f'Three bullet points below photo in clean dark typography: '
                f'\'• {n1[:20]} {pr1}\', \'• {n2[:20]} {pr2}\', \'• {n3[:20]} {pr3}\'. '
                f'Dark navy footer \'smarthomeorganizing.com\'. Clean editorial poster.'
            ),
        },
        # 9: SOCIAL PROOF
        {
            "name": "SOCIAL PROOF",
            "title_rule": (
                f'MUST start with a star rating ({r1}★) or "Amazon Verified" or review count. '
                f'Name THIS blog\'s specific top product ({n1[:30]}). '
                f'Angle: social proof + specific product, not generic. E.g. "{r1}★ — This {pr1} [SPECIFIC PRODUCT] Has 10,000 Five-Star Reviews for a Reason".'
            ),
            "freepik": (
                f'Pinterest pin trust graphic design, portrait 2:3 ratio. '
                f'Bright orange full-width top banner white text \'★ AMAZON VERIFIED ★\'. '
                f'Dark {room} interior photo background with dark overlay for text readability. '
                f'Bold large white sans-serif headline \'[6-WORD SOCIAL PROOF HEADLINE]\'. '
                f'Large yellow star rating graphic \'{r1} / 5 STARS\'. '
                f'White text list: \'{n1[:25]}\', \'{n2[:25]}\', \'{n3[:25]}\'. '
                f'Bright red rounded rectangle button graphic with white text \'FULL GUIDE + AMAZON LINKS\'. '
                f'Dark navy footer \'smarthomeorganizing.com\'. Trust and authority graphic.'
            ),
        },
    ]


def get_trending_keywords(topic, category):
    """Fetch trending keywords: Google Suggest (always) + pytrends (if available)"""
    suggestions = []
    seen = set()

    # 1. Google Suggest — always works, no key needed
    queries = [
        f"best {category} organizer 2026",
        f"best {category} organization ideas",
        f"amazon {category} organizer",
    ]
    for q in queries[:2]:
        try:
            url = "https://suggestqueries.google.com/complete/search"
            params = {"client": "firefox", "hl": "en", "gl": "us", "q": q}
            res = requests.get(url, params=params, timeout=6)
            for s in res.json()[1][:6]:
                s = s.strip()
                if s and s not in seen:
                    suggestions.append(s)
                    seen.add(s)
        except Exception:
            pass

    # 2. pytrends — richer related queries (US, last 7 days)
    if PYTRENDS_AVAILABLE and len(suggestions) < 8:
        try:
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
            kw = f"{category} organizer"
            pytrends.build_payload([kw], timeframe='now 7-d', geo='US')
            related = pytrends.related_queries()
            if kw in related and related[kw].get('top') is not None:
                for _, row in related[kw]['top'].head(5).iterrows():
                    q = str(row['query']).strip()
                    if q and q not in seen:
                        suggestions.append(q)
                        seen.add(q)
        except Exception as e:
            print(f"  pytrends skipped: {e}")

    return suggestions[:10]


def ask_groq(prompt, max_tokens=4096, json_mode=False):
    import time as _time
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    for attempt in range(5):
        res = requests.post(GROQ_URL, headers=headers, json=body)
        data = res.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        err = data.get("error", {})
        # Rate limit — parse retry-after from message or default to 30s
        if err.get("code") == "rate_limit_exceeded":
            msg = err.get("message", "")
            wait = 30
            import re as _re
            m = _re.search(r'try again in ([0-9.]+)s', msg)
            if m:
                wait = float(m.group(1)) + 2
            print(f"    Rate limit hit — waiting {wait:.0f}s (attempt {attempt+1}/5)...")
            _time.sleep(wait)
            continue
        print(f"    Groq API error: {data}")
        raise RuntimeError(f"Groq API error: {err}")
    raise RuntimeError("Groq rate limit: max retries exceeded")


BLOG_INTRO_HOOKS = [
    # Hook 0 — Problem/frustration opener (standard)
    "Hook with a relatable frustration the reader faces right now. Use <strong> for key phrases. End paragraph 2 with: \"I spent hours researching the top-rated, most-reviewed products on Amazon to bring you this ranked list.\"",
    # Hook 1 — Personal story opener
    "Open with a short first-person story: 'Last month I finally tackled my [specific space]...' Make it relatable and conversational. Reveal the solution at the end of paragraph 2. End with: \"After testing and reading thousands of Amazon reviews, here are the only products worth your money.\"",
    # Hook 2 — Surprising statistic or question opener
    "Open with a surprising question or bold statement (e.g. 'Most people waste $40 on [product] that breaks in 3 months.'). Build tension in paragraph 1. End paragraph 2 with: \"I ranked every top-rated option on Amazon so you don't have to waste another dollar.\"",
]

def generate_blog_html(blog_title, category, products, blog_number=1):
    """Generate full SEO-optimized blog post HTML.
    Provides all product data as structured facts — Gemini writes every word.
    No placeholder brackets. Uses 65k token limit so all products are fully written.
    """
    import re as _re
    n = len(products)
    intro_hook = BLOG_INTRO_HOOKS[blog_number % len(BLOG_INTRO_HOOKS)]
    product_type = extract_product_type(blog_title)

    # Dynamic ranking labels based on product count
    ranking_labels = [
        "Best Overall", "Best Value", "Best Premium",
        "Best Budget Pick", "Best for Small Spaces", "Best Hands-Free",
        "Best Heavy-Duty", "Best Smart Pick", "Best Eco-Friendly",
        "Best Stylish Design", "Best for Families", "Best Compact"
    ]

    # Product data block — all real data, clearly structured
    product_data_block = ""
    for i, p in enumerate(products):
        label = ranking_labels[i] if i < len(ranking_labels) else f"Pick #{i+1}"
        product_data_block += f"""
PRODUCT #{i+1} — Label: "{label}"
  Name: {p['name']}
  Price: {p['price']}
  Rating: {p['rating']}★
  Image URL: {p['image_url']}
  Affiliate Link: {p['affiliate_link']}
"""

    # Quick shop list — links already embedded, only need best-for labels
    quick_shop_items = "\n".join([
        f'<li><a href="{p["affiliate_link"]}" target="_blank" rel="noopener" style="color:#1976d2;font-weight:600">{p["name"]}</a> — [write 3-4 word best-for label] — {p["price"]}</li>'
        for p in products
    ])

    prompt = f"""You are a senior affiliate content writer for smarthomeorganizing.com — a US home organization blog.
Write a COMPLETE, professional, SEO-optimized blog post in pure HTML. Every section must be fully written with real, specific content.

━━━ BLOG INFO ━━━
Title: "{blog_title}"
Category: {category}
Product type: {product_type}
Target keywords: {blog_title.lower()}, best {product_type} 2026, amazon {product_type}
Audience: US homeowners aged 28–55 shopping on Amazon, value-conscious, want honest recommendations
Tone: Friendly expert — knowledgeable friend who tested everything, conversational but authoritative
Date: March 2026
Word count target: 3000–3800 words

━━━ PRODUCT DATA (use these EXACT links, images, prices, ratings — do NOT modify any URL) ━━━
{product_data_block}

━━━ WRITE ALL 11 SECTIONS BELOW — FULLY WRITTEN, NO PLACEHOLDER BRACKETS ━━━

SECTION 1 — AFFILIATE DISCLOSURE
Output this HTML exactly:
<div style="background:#fff8e1;border-left:4px solid #ffc107;padding:14px 18px;margin:24px 0;border-radius:6px;font-size:14px"><strong>Disclosure:</strong> This post contains affiliate links. As an Amazon Associate I earn from qualifying purchases at no extra cost to you. I only recommend products I've researched thoroughly.</div>

SECTION 2 — INTRO (3 paragraphs, 180–220 words total)
{intro_hook}
- Paragraph 1: Hook with a relatable frustration US homeowners face about {product_type}s. Use <strong> for 2–3 key phrases. Make it feel real and specific.
- Paragraph 2: Why this matters in 2026 — mention the specific problem this product solves. Mention Amazon naturally.
- Paragraph 3 must end with: "I spent hours researching thousands of Amazon reviews to bring you this ranked list — updated March 2026."

SECTION 3 — QUICK ANSWER BOX
<div style="background:#e3f2fd;border-left:5px solid #1976d2;padding:16px 20px;margin:24px 0;border-radius:6px">
<strong>Quick Answer (2026):</strong> Write one sharp sentence per product: best overall is Product #1 (mention its actual price and rating), budget pick is the cheapest product (name + price), premium pick is the most expensive (name).
</div>

SECTION 4 — BUYER'S GUIDE
<h2>What to Look for in a {product_type.title()} (2026 Buyer's Guide)</h2>
Write 4 buying criteria specific to {product_type}. Each criterion:
<h3>[Specific criterion name]</h3>
<p>2–3 sentences — include real measurements, materials, or use-case scenarios specific to this product type</p>

SECTION 5 — COMPARISON TABLE
<h2>All {n} {product_type.title()} Picks at a Glance</h2>
<div style="overflow-x:auto">
<table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:15px">
<thead><tr style="background:#1976d2;color:#fff;text-align:left">
<th style="padding:12px 14px">#</th>
<th style="padding:12px 14px">Product</th>
<th style="padding:12px 14px">Best For</th>
<th style="padding:12px 14px">Price</th>
<th style="padding:12px 14px">Rating</th>
</tr></thead>
<tbody>
Write ALL {n} rows. Alternate row background: odd rows #ffffff, even rows #f5f5f5, padding:11px 14px. Use exact prices and ratings from product data above.
</tbody>
</table>
</div>

SECTION 6 — PRODUCT REVIEWS (write ALL {n} reviews — this is the main section, be thorough)
For EACH of the {n} products, write this HTML block with REAL content (no brackets left unfilled):

<h2>#[N] — [Label]: [Full Product Name]</h2>
<img src="[exact image_url from product data]" style="float:right;width:240px;margin:0 0 16px 24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.12)" alt="[product name]">
<p>[Write 2–3 sentences: Product's #1 standout feature (mention specific measurement, capacity, or material). Then who it's best for and one specific real-world use case.]</p>
<p>[Write 2 sentences: Reference what Amazon buyers say — mention the rating and what they love most. Be specific, not vague.]</p>
<p><strong>Best for:</strong> [Very specific person or household scenario]</p>
<h3>Pros</h3>
<ul>
<li>[Pro 1: specific feature with real measurement or material — e.g. "Fingerprint-resistant brushed steel stays clean"]</li>
<li>[Pro 2: practical everyday benefit]</li>
<li>[Pro 3: value, durability, or convenience angle]</li>
<li>[Pro 4: unique differentiator vs other products in this list]</li>
<li>[Pro 5: confirmed by Amazon buyer reviews — something real buyers mention]</li>
</ul>
<h3>Cons</h3>
<ul>
<li>[Con 1: honest real limitation — specific, not vague like "price may vary"]</li>
<li>[Con 2: second real drawback]</li>
</ul>
<div style="background:#f9f9f9;border:1px solid #e0e0e0;border-radius:6px;padding:14px 18px;margin:16px 0">
<strong>Bottom Line:</strong> [1 punchy sentence — who should buy this, why it's worth [exact price], and what makes it stand out]
</div>
<p style="color:#555;font-size:15px"><strong>Price:</strong> [exact price] &nbsp;|&nbsp; <strong>Rating:</strong> [exact rating]★ &nbsp;|&nbsp; <strong>Reviews:</strong> [realistic number like 2,300+ or 7,000+] on Amazon</p>
<div style="clear:both"></div>
<div style="text-align:center;margin:24px 0">
<a href="[exact affiliate_link]" target="_blank" rel="noopener" style="background:#ff9900;color:#fff;padding:13px 28px;border-radius:6px;text-decoration:none;display:inline-block;font-weight:700;font-size:16px;letter-spacing:0.3px">Check Price on Amazon</a>
</div>
<hr style="margin:32px 0;border:none;border-top:1px solid #ececec">

SECTION 7 — PRO TIPS
<h2>5 Pro Tips to Get the Most Out of Your {product_type.title()}</h2>
<ol>
Write 5 actionable tips. Each: <li><strong>[Tip Name]:</strong> 2 practical sentences relevant to this specific product type for US households.</li>
</ol>

SECTION 8 — FAQ
<h2>Frequently Asked Questions About {product_type.title()}s</h2>
Write 5 Q&A pairs. Questions phrased how a US buyer searches Google:
<h3>[Question ending in ?]</h3>
<p>[Answer: 3–4 specific sentences with measurements, price ranges, or comparisons]</p>

SECTION 9 — FINAL VERDICT
<h2>Final Verdict — Which {product_type.title()} Should You Buy?</h2>
<p>[Recommend Product #1 for most people — 2 specific sentences on why it wins]</p>
<p>[Budget vs premium guidance: exactly who should pick each option and why]</p>
<p>[Closing motivation — 1–2 sentences on how this purchase genuinely improves daily life]</p>

SECTION 10 — QUICK SHOP
<h2>Shop All {n} {product_type.title()} Picks on Amazon</h2>
<ol>
{quick_shop_items}
</ol>

SECTION 11 — DISCLAIMER
<p style="font-size:13px;color:#888;margin-top:32px;border-top:1px solid #eee;padding-top:16px">Last updated: March 2026. As an Amazon Associate I earn from qualifying purchases. Prices are approximate and subject to change — always verify on Amazon before purchasing.</p>

━━━ NON-NEGOTIABLE RULES ━━━
1. Return ONLY the HTML body content — no ```html fences, no <html>/<head>/<body> tags, no explanation text
2. ALL {n} product reviews in Section 6 must be COMPLETE — every product gets full content
3. Every product gets EXACTLY 5 pros and EXACTLY 2 cons — count them
4. Use the EXACT href and src URLs from the product data above — never invent or modify URLs
5. NEVER leave bracket placeholders like [write here] — every bracket must be replaced with real content
6. Zero author names, bylines, or "Anna Williams" or any attribution
7. Use HTML only — NEVER markdown (**bold** is wrong, use <strong>bold</strong>)
8. Use "2026" at least 5 times naturally throughout
9. US English, conversational expert tone, no generic filler phrases"""

    print(f"  Calling Gemini (max 65k tokens, {n} products)...")
    html = ask_gemini(prompt, temperature=0.5, max_tokens=65536, grounding=False)

    # Fix any leaked markdown
    html = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html, flags=_re.DOTALL)
    html = _re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', html)
    # Strip any accidental ```html fences
    html = _re.sub(r'^```html?\s*', '', html.strip())
    html = _re.sub(r'\s*```$', '', html.strip())

    # Verify all affiliate links are present
    print(f"\n  {'─'*55}")
    print(f"  AFFILIATE LINKS CHECK")
    print(f"  {'─'*55}")
    all_ok = True
    for i, p in enumerate(products):
        asin = p['affiliate_link'].split('/dp/')[1].split('?')[0] if '/dp/' in p['affiliate_link'] else '?'
        present = asin in html
        icon = "✅" if present else "❌"
        if not present:
            all_ok = False
        print(f"  {icon} #{i+1:>2}  ASIN:{asin}  {p['name'][:40]}")
    if not all_ok:
        print(f"  ⚠️  Some links missing — Gemini may have modified them. Check HTML.")
    print(f"  {'─'*55}\n")

    return html




# ─── REMOVED: PIN_DESIGN_TEMPLATES — Gemini now generates freepik_prompt dynamically per pin ───────────────────────────
if False:
    PIN_DESIGN_TEMPLATES = {
    # lifestyle_hero — full-bleed photo, dark bottom gradient, white text
    "lifestyle_hero": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Background: full-bleed photorealistic lifestyle photo of <<SCENE>>, warm natural window light, "
        "sharp focus, no people, styled and clean. "
        "Black-to-transparent gradient overlay from bottom 55% upward. "
        "On gradient: bold large white uppercase sans-serif text '<<L1>>' centered, "
        "letter-spacing 3px. White medium text '<<L2>>' below. "
        "Small white text '<<L3>>' with right-arrow symbol. "
        "Solid navy blue rounded-pill badge at very bottom center: small white text 'smarthomeorganizing.com'. "
        "High-resolution, editorial lifestyle photography, Canva hero pin style."
    ),
    # split_panel — top product photo, bottom navy text panel
    "split_panel": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Top 55%: photorealistic close-up photo of <<SCENE>>, bright clean natural light, sharp focus, no people. "
        "Bottom 45%: solid deep navy blue #1a2a6c rectangle panel. "
        "On navy panel: bold extra-large white uppercase sans-serif text '<<L1>>' at top-center. "
        "Thin yellow #f5c518 horizontal separator line. "
        "White medium-weight text '<<L2>>' below separator. White small text '<<L3>>'. "
        "Small white text 'smarthomeorganizing.com' at bottom-center. "
        "Crisp line dividing photo and panel. Clean Canva split-panel pin."
    ),
    # dark_editorial — charcoal bg, gold lines, product center
    "dark_editorial": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Dark charcoal #1c1c1e solid background, no photo in background. "
        "Thin gold #c9a84c horizontal rule near top (40px from edge). "
        "Bold large white uppercase serif text '<<L1>>' centered in top third. "
        "Center: photorealistic product image of <<SCENE>>, soft golden rim light, drop shadow, "
        "product isolated on dark background. "
        "Thin gold horizontal rule below product. "
        "White medium sans-serif text '<<L2>>' centered below rule. Gold small text '<<L3>>'. "
        "Thin gold rule at bottom. Small white text 'smarthomeorganizing.com' below. "
        "Premium dark editorial magazine aesthetic, luxury feel."
    ),
    # bold_graphic — solid color bg, typography-forward, product card inset
    "bold_graphic": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Solid burnt-orange #e64a19 background, no background photo. "
        "Very large bold white uppercase sans-serif text '<<L1>>' centered in top 35%, tight letter-spacing. "
        "White horizontal rule divider line. "
        "White rounded-corner card (#fffde7 cream fill, subtle shadow) in center. "
        "Inside card: photorealistic product image of <<SCENE>>, white background look, centered. "
        "Inside card below photo: dark navy small text '<<L2>>'. "
        "Below card on orange: white bold text '<<L3>>'. "
        "Small white text 'smarthomeorganizing.com' at very bottom. "
        "Bold graphic, typography-forward, modern Canva pin."
    ),
    # magazine_cover — full-bleed photo, white top band, white bottom panel
    "magazine_cover": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Full-bleed photorealistic photo of <<SCENE>>, 70% brightness, no people. "
        "White semi-transparent #ffffffee band across top 22% full width. "
        "On white band: bold large dark navy serif text '<<L1>>', left-aligned 40px margin. "
        "Thin navy rule below white band. "
        "Bottom 28%: white #ffffffee semi-transparent panel. "
        "On bottom panel: dark navy medium sans-serif text '<<L2>>', left-aligned. "
        "Small dark navy text '<<L3>>'. Small dark text 'smarthomeorganizing.com'. "
        "Upscale editorial magazine cover pin, elegant and high-end."
    ),
    # checklist_card — white bg, product top, checklist items
    "checklist_card": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Clean white #ffffff background, light gray #eeeeee thin border. "
        "Top 30%: photorealistic product photo of <<SCENE>>, centered, white studio look, drop shadow, rounded corners. "
        "Bold dark navy #1a2a6c large uppercase text '<<L1>>' below photo, centered. "
        "Thin teal #00897b divider line. "
        "Three checklist rows with teal circle-checkmark icons and dark text (one item per row, left-aligned in center area). "
        "Dark medium text '<<L2>>' below checklist. "
        "Solid navy footer bar at bottom: white text 'smarthomeorganizing.com' left, white small text '<<L3>>' right. "
        "Clean minimal Canva checklist card pin."
    ),
    # price_badge — white bg, red price circle, product, stars, CTA button
    "price_badge": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Clean white #ffffff background. "
        "Large bold red #d32f2f circle badge at top-center, diameter 200px, bold white price text inside. "
        "Bold large dark #1a2a6c uppercase sans-serif text '<<L1>>' below badge, centered. "
        "Photorealistic product photo of <<SCENE>>, centered, white background, clean drop shadow. "
        "Row of 5 solid gold star icons. Small dark gray text '<<L2>>'. "
        "Teal #00897b rounded-rectangle button with bold white text '<<L3>>' centered. "
        "Navy footer bar: white text 'smarthomeorganizing.com'. "
        "Eye-catching deal/price Canva pin."
    ),
    # before_after — vertical split, messy top, organized bottom
    "before_after": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Vertical split composition. "
        "Top 44%: realistic photo of cluttered disorganized <<ROOM>> — messy items piled randomly, chaotic real interior. "
        "Bold red #d32f2f rounded-pill label 'BEFORE' top-left corner, white text. "
        "Center band 12%: solid dark navy #1a2a6c full-width strip, bold white centered text '<<L1>>'. "
        "Bottom 44%: same <<ROOM>> beautifully organized with <<SCENE>>, clean, warm light, styled. "
        "Bold green #2e7d32 rounded-pill label 'AFTER' bottom-left corner, white text. "
        "White medium text '<<L2>>' overlaid on bottom section. "
        "Navy footer bar: white text 'smarthomeorganizing.com', white small text '<<L3>>'. "
        "Dramatic split-screen transformation Canva pin."
    ),
    # problem_solution — red top band, white center photo, green bottom band
    "problem_solution": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Top 28%: solid deep red #b71c1c band. Small white uppercase text 'THE PROBLEM' above bold large white text '<<L1>>'. "
        "Middle 44%: clean white/cream #fafafa background with photorealistic product photo of <<SCENE>>, centered, subtle shadow. "
        "Bottom 28%: solid forest green #1b5e20 band. Small white uppercase text 'THE SOLUTION' above bold large white text '<<L2>>'. "
        "Small white text '<<L3>>'. Small white text 'smarthomeorganizing.com' at very bottom. "
        "Bold two-tone problem/solution Canva pin."
    ),
    # soft_aesthetic — sage/beige bg, centered product, elegant quote-style text
    "soft_aesthetic": (
        "Pinterest pin, portrait 2:3, 1000x1500px. "
        "Soft sage green #e8f5e9 solid background. "
        "Center-top: photorealistic product photo of <<SCENE>>, clean white studio background look, drop shadow, rounded corners. "
        "Large bold dark #263238 text '<<L1>>' below product, centered, elegant sans-serif. "
        "Thin green #81c784 decorative horizontal rule. "
        "Italic dark gray medium text '<<L2>>' — insight or quote style. "
        "Small dark text '<<L3>>'. Small dark text 'smarthomeorganizing.com' at bottom. "
        "Soft, aesthetic, Pinterest-worthy Canva style."
    ),
}


def generate_pin_content(blog_title, category, blog_url, products, blog_number=1, blog_html=None):
    """Generate 10 fully dynamic Pinterest pins from blog content.
    Gemini reads the blog, generates content + a custom Seedream image prompt per pin.
    No fixed templates — every pin layout, colors, and composition is generated fresh.
    """
    import re as _re

    product_lines = [
        f"  #{i+1}: {p.get('name', '')} | {p.get('price', '?')} | {p.get('rating', '?')}★"
        for i, p in enumerate(products)
    ]
    product_summary = "\n".join(product_lines)

    def _to_float(price_str):
        import re as _r
        m = _r.search(r'[\d]+\.?\d*', price_str.replace(',', ''))
        return float(m.group()) if m else 9999.0
    cheapest_price = min(
        (p.get('price', '$99') for p in products),
        key=_to_float,
        default='$29'
    )

    blog_text = ""
    if blog_html:
        blog_text = _re.sub(r'<[^>]+>', ' ', blog_html)
        blog_text = _re.sub(r'\s+', ' ', blog_text).strip()[:7000]
    if not blog_text:
        blog_text = f"Blog: {blog_title}\nCategory: {category}\nProducts:\n{product_summary}"

    default_board = BOARDS.get(category, BOARDS['general'])
    budget_board  = BOARDS.get('budget', default_board)
    amazon_board  = BOARDS.get('amazon', default_board)
    topic_tags    = TOPIC_TAGS.get(category, TOPIC_TAGS["general"])

    prompt = f"""You are a Pinterest Marketing Expert AND a professional AI image prompt writer.
Analyze this blog completely, then generate 10 fully custom Pinterest pins — each with unique content AND a unique image generation prompt.

════════════════════════════════════════
BLOG
════════════════════════════════════════
TITLE: "{blog_title}"
CATEGORY: {category}
CHEAPEST PRODUCT PRICE: {cheapest_price}

PRODUCTS:
{product_summary}

BLOG CONTENT:
{blog_text}

════════════════════════════════════════
FOR EACH PIN GENERATE:
════════════════════════════════════════

1. title — SEO Pinterest title (max 100 chars), keyword-rich, specific to THIS blog
2. description — 2-3 sentences with real facts from the blog + 5 hashtags. End: "Save this pin!"
3. text_on_pin:
     line1 — bold headline (max 5 words, ALL CAPS, SPECIFIC to this blog — never generic)
     line2 — supporting detail (max 5 words, ALL CAPS, real fact from blog)
     line3 — CTA (max 4 words, ALL CAPS)
4. board — one of: "{category}" / "budget" / "amazon"
5. freepik_prompt — A complete Seedream 4.5 AI image generation prompt for a PREMIUM Pinterest pin.
     RULES for freepik_prompt:
     - Start with: "Pinterest pin, portrait 2:3, 1000x1500px."
     - Describe the EXACT background image using the SPECIFIC product from this blog (not generic "organizer")
       e.g. "slim stainless steel step trash can beside white lower kitchen cabinet"
       e.g. "tiered bamboo spice rack with labeled glass jars on marble countertop"
     - Describe a UNIQUE layout and color scheme matching the pin's angle:
       * LISTICLE/TOP PICKS → full-bleed product lifestyle photo, dark gradient overlay bottom half, bold white text
       * HOW-TO → split panel: product photo top, info panel bottom in deep navy or forest green
       * BOLD STATEMENT → solid vivid color background (pick a color that fits the product), huge typography
       * KEY INSIGHT/STAT → dark editorial: charcoal bg, gold accent lines, product centered with rim light
       * PRICE/DEAL → white bg, large colored price badge circle at top, product photo, gold stars, CTA button
       * CHECKLIST → clean white bg, product photo top, checkmark list rows below
       * BEFORE/AFTER → vertical split: cluttered room top half (BEFORE label), organized with product bottom (AFTER label)
       * PROBLEM/SOLUTION → bold red top band (THE PROBLEM), product photo center, green bottom band (THE SOLUTION)
       * SOFT/AESTHETIC → soft pastel bg matching product color palette, centered product, elegant italic text
       * SECOND LISTICLE → magazine cover style: full-bleed photo, white semi-transparent top + bottom bands
     - Include text overlays: describe EXACTLY what text appears where on the image, using line1/line2/line3 values
     - Include: "Small text 'smarthomeorganizing.com' at bottom"
     - CONTRAST RULE: text color MUST contrast with background — use dark navy/charcoal text on white/light/pastel/soft backgrounds; use white text ONLY on dark backgrounds or when a dark gradient/overlay explicitly covers the text area
     - NO people, sharp focus, high resolution, professional photography/design
     - Each pin must have a VISUALLY DISTINCT prompt from all other 9 pins

════════════════════════════════════════
10 PINS — ANGLES (all specific to THIS blog's actual products)
════════════════════════════════════════

Pin 1:  LISTICLE — "X Best [exact product type]..." (use actual count from blog)
Pin 2:  LISTICLE 2 — Different angle on same products (budget / small space / top-rated)
Pin 3:  HOW-TO — "How to [specific task with this exact product]"
Pin 4:  BOLD STATEMENT — Attention-grabbing question or hook about THIS product
Pin 5:  KEY INSIGHT — Surprising stat or fact found in the blog
Pin 6:  STAT/PRICE — Lead with exact cheapest price ({cheapest_price}) from the product list
Pin 7:  CHECKLIST — "Before You Buy: [product type] Checklist"
Pin 8:  BEFORE/AFTER — Messy space vs organized with THIS product
Pin 9:  PROBLEM/SOLUTION — Specific pain point + this blog's solution
Pin 10: SOFT/ASPIRATIONAL — Emotional or aesthetic angle on THIS product

════════════════════════════════════════
RETURN ONLY VALID JSON — no explanation, no markdown fences
════════════════════════════════════════
{{
  "pins": [
    {{
      "pin_number": 1,
      "pin_type": "listicle",
      "title": "9 Trash Can Organizers That Actually Fit Small Kitchens — Amazon 2026",
      "description": "Tight on space? These 9 trash can organizers fit under cabinets, inside drawers, or slim beside appliances — all under $40 on Amazon with thousands of 5-star reviews. #KitchenOrganization #TrashCan #SmallKitchen #AmazonFinds #HomeOrganization Save this pin!",
      "text_on_pin": {{
        "line1": "9 TRASH CANS TESTED",
        "line2": "FITS ANY KITCHEN SIZE",
        "line3": "SHOP AMAZON NOW"
      }},
      "board": "{category}",
      "freepik_prompt": "Pinterest pin, portrait 2:3, 1000x1500px. Background: full-bleed photorealistic lifestyle photo of slim stainless steel step trash can placed beside white lower kitchen cabinet, pull-out dual-bin trash organizer partially visible inside open cabinet door, warm natural window light from left, clean marble countertops, no people, styled minimal kitchen. Dark-to-transparent gradient overlay from bottom 55% upward. On gradient: bold large white uppercase sans-serif text '9 TRASH CANS TESTED' centered, letter-spacing 3px. White medium text 'FITS ANY KITCHEN SIZE' below. White small text 'SHOP AMAZON NOW' with right-arrow. Solid navy rounded-pill badge bottom center: small white text 'smarthomeorganizing.com'. High-resolution editorial lifestyle photography, Canva hero pin style."
    }}
  ]
}}"""

    print("  Generating 10 dynamic pins with Gemini...")
    raw = ask_gemini(prompt, temperature=0.7, max_tokens=32768, grounding=False)

    def _clean_raw(r):
        r = r.strip()
        r = _re.sub(r'^```json\s*', '', r)
        r = _re.sub(r'\s*```$', '', r)
        m2 = _re.search(r'\{[\s\S]+\}', r)
        return m2.group(0) if m2 else r

    def _repair_json(s):
        """Fix common LLM JSON issues."""
        # Remove trailing commas before } or ]
        s = _re.sub(r',\s*([}\]])', r'\1', s)
        return s

    def _try_parse(r):
        data = json.loads(r)
        return data.get('pins', [])

    pins_data = []
    for attempt in range(3):
        try:
            cleaned = _clean_raw(raw)
            try:
                pins_data = _try_parse(cleaned)
            except Exception:
                pins_data = _try_parse(_repair_json(cleaned))
            if pins_data:
                print(f"  Generated {len(pins_data)} pins")
                break
            else:
                raise ValueError("Empty pins list")
        except Exception as e:
            if attempt < 2:
                print(f"  [!] JSON parse error (attempt {attempt+1}): {e} — retrying Gemini...")
                raw = ask_gemini(prompt, temperature=0.7, max_tokens=32768, grounding=False)
            else:
                print(f"  [!] JSON parse failed after 3 attempts: {e}\n  Raw: {raw[:300]}")
                pins_data = []

    board_map = {
        category: default_board,
        'budget':  budget_board,
        'amazon':  amazon_board,
    }

    pins = []
    for i, pin in enumerate(pins_data):
        board_key      = pin.get("board", category)
        top            = pin.get("text_on_pin", {})
        l1             = top.get("line1", "")
        l2             = top.get("line2", "")
        l3             = top.get("line3", "")
        freepik_prompt = pin.get("freepik_prompt", "")

        # Safety: ensure the exact text values are in the image prompt.
        # If Gemini wrote placeholder-style text or missed them, append a hard override.
        if l1 and l1 not in freepik_prompt:
            freepik_prompt += (
                f" Text on image: bold large uppercase white sans-serif '{l1}' as main headline, "
                f"medium white text '{l2}' below, small white text '{l3}' at bottom."
            )

        pins.append({
            "pin_number":     i + 1,
            "pin_type":       pin.get("pin_type", ""),
            "title":          pin.get("title", ""),
            "description":    pin.get("description", ""),
            "text_on_pin":    top,
            "freepik_prompt": freepik_prompt,
            "link":           blog_url,
            "board_id":       board_map.get(board_key, default_board),
            "topic_tags":     topic_tags,
            "category":       category,
            "image_url":      "",
            "posted":         False
        })

    return pins
