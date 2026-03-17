"""
retry_pins.py — Re-run ONLY the pin generation + image download step.
Use after step2_generate.py crashes mid-image-generation.

Usage:
  python retry_pins.py              ← uses blog_input.json, auto-detects blog_url
  python retry_pins.py 5            ← start generating images from pin 5 onwards
  python retry_pins.py 5 https://...← start from pin 5 with explicit blog URL

The script:
  1. Reads blog_input.json for blog data
  2. Re-generates 10 pin titles/descriptions/prompts with Gemini
  3. Downloads images for pins >= start_from (skips already-downloaded files)
  4. Appends to pins_queue_new.json
  5. Git commit + push
"""
import json
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from groq_gen import generate_pin_content
from freepik_gen import generate_10_images

INPUT_FILE         = 'blog_input.json'
QUEUE_FILE         = 'pins_queue_new.json'
USED_PRODUCTS_FILE = 'used_products.json'
GITHUB_RAW         = 'https://raw.githubusercontent.com/Saiteja9989/pinterest-automation/main'


def load_blog_url_from_blogger(blog_number):
    """Try to find the blog URL from blogs.md if it was saved there."""
    if not os.path.exists('blogs.md'):
        return None
    with open('blogs.md', 'r', encoding='utf-8') as f:
        content = f.read()
    # Look for a URL in the same row as the blog number
    pattern = rf'\|\s*{blog_number}\s*\|[^|]*\|[^|]*\|(https?://[^\s|]+)'
    m = re.search(pattern, content)
    if m:
        return m.group(1).strip()
    return None


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"posting_enabled": False, "pins": []}


def save_queue(queue):
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def save_used_products(blog_number, products):
    used = {}
    if os.path.exists(USED_PRODUCTS_FILE):
        with open(USED_PRODUCTS_FILE, 'r') as f:
            used = json.load(f)
    for p in products:
        link = p.get('affiliate_link', '')
        if link:
            used[link] = f"blog{blog_number}"
    with open(USED_PRODUCTS_FILE, 'w') as f:
        json.dump(used, f, indent=2)


def run():
    # ── Parse args ──
    start_from = 1
    blog_url_override = None

    args = sys.argv[1:]
    for arg in args:
        if arg.startswith('http'):
            blog_url_override = arg
        else:
            try:
                start_from = int(arg)
            except ValueError:
                pass

    # ── Load blog_input.json ──
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found. Run start.py first.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    blog_number = data["blog_number"]
    blog_title  = data["blog_title"]
    category    = data["category"]
    products    = data["products"]

    print(f"\n{'='*60}")
    print(f"RETRY PINS — Blog #{blog_number}: {blog_title}")
    print(f"Category: {category} | Products: {len(products)}")
    print(f"Generating images from pin {start_from} onwards")
    print(f"{'='*60}")

    # ── Get blog URL ──
    blog_url = blog_url_override or load_blog_url_from_blogger(blog_number)
    if not blog_url:
        blog_url = input(f"\nPaste the Blogger URL for Blog #{blog_number}: ").strip()
        if not blog_url:
            print("ERROR: Blog URL required.")
            return

    print(f"\nBlog URL: {blog_url}")

    # ── Check which images already exist ──
    existing = []
    missing = []
    for n in range(1, 11):
        path = f"images/blog{blog_number}_pin{n}.jpg"
        if os.path.exists(path):
            existing.append(n)
        else:
            missing.append(n)

    print(f"\nExisting images: {existing}")
    print(f"Missing images:  {missing}")

    # ── Generate pin content ──
    print(f"\n[1/3] Generating 10 pin contents with Gemini...")
    pins = generate_pin_content(blog_title, category, blog_url, products, blog_number)
    print(f"Generated {len(pins)} pins")

    if not pins:
        print("\n❌ ERROR: 0 pins generated. Gemini JSON failed 3 times. Try again.")
        return

    # ── Generate images (skip existing, start from start_from) ──
    print(f"\n[2/3] Generating images (pin {start_from}+)...")
    pins = generate_10_images(pins, blog_number, start_from=start_from)

    # Add blog_number to each pin
    for pin in pins:
        pin["blog_number"] = blog_number

    # ── Save used products ──
    save_used_products(blog_number, products)

    # ── Remove any existing blog13 pins from queue before re-adding ──
    queue = load_queue()
    before = len(queue["pins"])
    queue["pins"] = [p for p in queue["pins"] if p.get("blog_number") != blog_number]
    removed = before - len(queue["pins"])
    if removed:
        print(f"\n  Removed {removed} existing blog#{blog_number} pins from queue (replacing with fresh ones)")

    queue["pins"].extend(pins)
    save_queue(queue)

    total   = len(queue["pins"])
    pending = sum(1 for p in queue["pins"] if not p.get("posted", False))

    print(f"\n{'='*60}")
    print(f"Done! Blog #{blog_number} pins ready")
    print(f"   Blog URL:       {blog_url}")
    print(f"   Pins added:     {len(pins)}")
    print(f"   Queue total:    {total}")
    print(f"   Pending to post:{pending}")
    print(f"{'='*60}\n")

    # ── Push to GitHub ──
    print("Pushing to GitHub...")
    os.system(f'git add images/ {QUEUE_FILE} {USED_PRODUCTS_FILE}')
    os.system(f'git commit -m "Add Blog #{blog_number} pins to queue (retry)"')
    push_ret = os.system('git push')
    if push_ret != 0:
        print("  ⚠️  Push rejected — pulling remote changes first...")
        os.system('git pull --rebase')
        push_ret2 = os.system('git push')
        if push_ret2 != 0:
            print("  ❌ Push still failed. Run: git pull && git push manually.")
        else:
            print("✅ Pushed (after rebase)!")
    else:
        print("✅ Pushed!")

    # ── Update image URLs to GitHub raw ──
    print("Updating image URLs to permanent GitHub raw links...")
    queue = load_queue()
    updated = 0
    for pin in queue["pins"]:
        local = pin.get("image_url", "")
        if local.startswith("images/") and not local.startswith("http"):
            pin["image_url"] = f"{GITHUB_RAW}/{local}"
            updated += 1
    if updated:
        save_queue(queue)
        os.system(f'git add {QUEUE_FILE}')
        os.system(f'git commit -m "Update Blog #{blog_number} image URLs to GitHub raw (retry)"')
        push_ret3 = os.system('git push')
        if push_ret3 != 0:
            os.system('git pull --rebase')
            os.system('git push')
        print(f"✅ {updated} image URLs updated to permanent GitHub links.")

    print("\nPins will start posting automatically via GitHub Actions.")


if __name__ == "__main__":
    run()
