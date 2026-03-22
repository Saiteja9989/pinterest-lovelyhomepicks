"""
Automate Blogger layout: inject navigation bar into LovelyHomePicks theme.
Run: python setup_layout.py
A browser window will open — log in to Google if prompted.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BLOG_ID  = '8466477651147836095'
BLOG_URL = 'https://lovelyhomepicks.blogspot.com'

PAGES_NAV = [
    ("Home",               BLOG_URL),
    ("About Us",           f"{BLOG_URL}/p/about-us.html"),
    ("Contact",            f"{BLOG_URL}/p/contact.html"),
    ("Privacy Policy",     f"{BLOG_URL}/p/privacy-policy.html"),
    ("Affiliate Disclaimer", f"{BLOG_URL}/p/affiliate-disclaimer.html"),
]

# ─── NAV HTML/CSS ─────────────────────────────────────────────────────────────
NAV_CSS = """
/* LovelyHomePicks Navigation Bar */
.lhp-nav {
  background: #c0392b;
  padding: 12px 0;
  text-align: center;
  width: 100%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}
.lhp-nav a {
  color: #fff;
  text-decoration: none;
  margin: 0 16px;
  font-family: Georgia, serif;
  font-size: 13px;
  letter-spacing: 0.6px;
  font-weight: bold;
  text-transform: uppercase;
}
.lhp-nav a:hover { opacity: 0.8; text-decoration: underline; }
@media (max-width: 600px) {
  .lhp-nav a { margin: 0 8px; font-size: 11px; }
}
"""

nav_links = "  ".join(
    f'<a href="{url}">{title}</a>' for title, url in PAGES_NAV
)
NAV_HTML = f'<div class="lhp-nav">{nav_links}</div>'

# Persistent browser session so you stay logged in between runs
USER_DATA_DIR = str(Path.home() / '.lhp_browser_session')


# ─── INJECT NAV INTO TEMPLATE XML ─────────────────────────────────────────────
def inject_nav(xml: str) -> tuple[str, bool]:
    changed = False

    # 1. CSS into <b:skin>
    if '.lhp-nav' not in xml:
        for skin_close in [']]></b:skin>', '</b:skin>']:
            if skin_close in xml:
                xml = xml.replace(skin_close, NAV_CSS + skin_close, 1)
                changed = True
                print("  CSS injected into <b:skin>")
                break

    # 2. Nav HTML after header / before main content
    if 'lhp-nav' not in xml:
        injection_points = [
            '</header>',
            '</Header>',
            "id='header-wrapper'",
            'id="header-wrapper"',
            "class='header-outer'",
            'class="header-outer"',
            "<div id='main-wrapper'>",
            '<div id="main-wrapper">',
            "<div class='main-wrapper'>",
            '<div class="main-wrapper">',
        ]
        for marker in injection_points:
            if marker in xml:
                xml = xml.replace(marker, marker + '\n' + NAV_HTML, 1)
                changed = True
                print(f"  Nav HTML injected after: {marker}")
                break
        else:
            # Last resort: after opening <body>
            xml = re.sub(r'(<body[^>]*>)', r'\1\n' + NAV_HTML, xml, count=1)
            changed = True
            print("  Nav HTML injected after <body> (fallback)")

    return xml, changed


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def setup_layout():
    theme_url = f'https://www.blogger.com/blog/theme/edit/{BLOG_ID}'

    with sync_playwright() as p:
        print("Launching browser (persistent session)...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=['--start-maximized'],
            no_viewport=True,
        )
        page = ctx.new_page()

        print(f"Opening Blogger theme editor...")
        page.goto(theme_url, wait_until='domcontentloaded')

        # Handle Google login if needed
        if 'accounts.google.com' in page.url:
            print("\nPlease log in to Google in the browser window.")
            print("Waiting up to 2 minutes...")
            page.wait_for_url('**/blogger.com/**', timeout=120_000)

        page.wait_for_load_state('networkidle', timeout=30_000)
        print("Theme editor loaded.")

        # ── Click 'Edit HTML' button ──────────────────────────────────────────
        edit_selectors = [
            'button:has-text("Edit HTML")',
            'a:has-text("Edit HTML")',
            '[data-action="customize"]',
            'button[title="Edit HTML"]',
        ]
        clicked = False
        for sel in edit_selectors:
            btn = page.locator(sel)
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(2000)
                clicked = True
                print("  Clicked 'Edit HTML'")
                break

        if not clicked:
            print("  'Edit HTML' button not found — trying direct URL...")
            page.goto(f'https://www.blogger.com/blog/theme/edit/{BLOG_ID}#html')
            page.wait_for_timeout(3000)

        # ── Read current template ─────────────────────────────────────────────
        print("Reading current template XML...")
        xml = None

        # Try CodeMirror (used in newer Blogger editor)
        try:
            xml = page.evaluate("""() => {
                const cm = document.querySelector('.CodeMirror');
                return cm ? cm.CodeMirror.getValue() : null;
            }""")
        except Exception:
            pass

        # Fallback: textarea
        if not xml:
            for sel in ['textarea.html-editor', 'textarea#custom-template-text', 'textarea']:
                ta = page.locator(sel)
                if ta.count() > 0:
                    xml = ta.first.input_value()
                    break

        if not xml or len(xml) < 100:
            print("\n❌ Could not read template. Manual steps:")
            print("   1. Go to Blogger Dashboard → Theme → Edit HTML")
            print("   2. Copy all XML, paste into template.xml here")
            print("   3. Run: python setup_layout.py --from-file")
            ctx.close()
            return

        print(f"  Template read: {len(xml):,} chars")

        # ── Inject nav ────────────────────────────────────────────────────────
        new_xml, changed = inject_nav(xml)

        if not changed:
            print("Navigation bar already present — no changes needed.")
            ctx.close()
            return

        # ── Write back into editor ────────────────────────────────────────────
        print("Writing updated template...")
        try:
            page.evaluate("""(newXml) => {
                const cm = document.querySelector('.CodeMirror');
                if (cm) { cm.CodeMirror.setValue(newXml); return; }
                const ta = document.querySelector('textarea.html-editor, textarea');
                if (ta) { ta.value = newXml; ta.dispatchEvent(new Event('input')); }
            }""", new_xml)
        except Exception as e:
            print(f"  Write error: {e}")

        page.wait_for_timeout(1500)

        # ── Save ──────────────────────────────────────────────────────────────
        save_selectors = [
            'button:has-text("Save Theme")',
            'button:has-text("Save")',
            '[data-action="save"]',
        ]
        saved = False
        for sel in save_selectors:
            btn = page.locator(sel)
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(4000)
                saved = True
                print(f"  Clicked Save")
                break

        if saved:
            print(f"\n✅ Layout updated! View your blog: {BLOG_URL}")
        else:
            print("\n⚠️  Could not find Save button. Please save manually in the browser.")
            input("Press Enter after saving to close...")

        ctx.close()


if __name__ == "__main__":
    setup_layout()
