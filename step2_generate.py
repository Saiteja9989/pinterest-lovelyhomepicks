"""
step2_generate.py — Run after step1_add_products.py
Reads blog_input.json → generates blog + 10 pins + images → adds to pins_queue.json

Usage: python step2_generate.py
"""
import json
import os
from groq_gen import generate_blog_html, generate_pin_content
from freepik_gen import generate_10_images
from blogger_up import upload_blog_post

INPUT_FILE        = 'blog_input.json'
QUEUE_FILE        = 'pins_queue_new.json'   # new queue — swap to pins_queue.json when current runs out
USED_PRODUCTS_FILE = 'used_products.json'
GITHUB_RAW        = 'https://raw.githubusercontent.com/Saiteja9989/pinterest-automation/main'


def check_duplicate_products(products):
    """Warn if any affiliate link was already used in a previous blog."""
    if not os.path.exists(USED_PRODUCTS_FILE):
        return
    with open(USED_PRODUCTS_FILE, 'r') as f:
        used = json.load(f)
    for p in products:
        link = p.get('affiliate_link', '')
        if link in used:
            print(f"  ⚠️  DUPLICATE: '{p['name'][:50]}' was already used in {used[link]}")


def save_used_products(blog_number, products):
    """Record this blog's affiliate links in used_products.json."""
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


def load_input():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # New queue: posting paused by default until you run start_posting.py
    return {"posting_enabled": False, "pins": []}


def save_queue(queue):
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def run():
    data = load_input()
    blog_number = data["blog_number"]
    blog_title  = data["blog_title"]
    category    = data["category"]
    products    = data["products"]

    print(f"\n{'='*60}")
    print(f"Blog #{blog_number}: {blog_title}")
    print(f"Category: {category} | Products: {len(products)}")
    print(f"{'='*60}")

    # Check for duplicate products
    print("\nChecking for duplicate products...")
    check_duplicate_products(products)

    # Step 1: Generate blog HTML
    print("\n[1/4] Generating blog HTML with Gemini...")
    html = generate_blog_html(blog_title, category, products, blog_number)
    print(f"Blog HTML generated ({len(html)} chars)")

    # Affiliate links are embedded directly in the prompt by generate_blog_html()
    # — no replacement needed here.

    # Step 2: Upload to Blogger
    print("\n[2/4] Uploading to Blogger...")
    blog_url = upload_blog_post(blog_title, html)
    if not blog_url:
        print("ERROR: Blog upload failed!")
        return

    # Step 3: Generate 10 pin titles, descriptions, prompts
    print("\n[3/4] Generating 10 pin contents with Gemini...")
    pins = generate_pin_content(blog_title, category, blog_url, products, blog_number, blog_html=html)
    print(f"Generated {len(pins)} pin contents")

    if not pins:
        print("\n❌ ERROR: 0 pins generated. Fix the JSON error above and run retry_pins.py.")
        return

    # Step 4: Generate + download 10 pin images (saved to images/ folder)
    print("\n[4/4] Generating 10 pin images with Freepik...")
    pins = generate_10_images(pins, blog_number)

    # Add blog_number to each pin
    for pin in pins:
        pin["blog_number"] = blog_number

    # Save used products so future blogs can detect duplicates
    save_used_products(blog_number, products)

    # Append to queue (still has local image paths at this point)
    queue = load_queue()
    queue["pins"].extend(pins)
    save_queue(queue)

    total = len(queue["pins"])
    pending = sum(1 for p in queue["pins"] if not p.get("posted", False))

    print(f"\n{'='*60}")
    print(f"✅ Done! Blog #{blog_number} complete")
    print(f"   Blog URL: {blog_url}")
    print(f"   Pins added: {len(pins)}")
    print(f"   Total pins in queue: {total}")
    print(f"   Pending to post: {pending}")
    print(f"{'='*60}\n")

    # Push images + queue to GitHub
    print("Pushing to GitHub...")
    os.system(f'git add images/ {QUEUE_FILE} blogs.md')
    os.system(f'git commit -m "Add Blog #{blog_number} pins to queue"')
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

    # Now convert local image paths → permanent GitHub raw URLs in queue
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
        os.system(f'git commit -m "Update Blog #{blog_number} image URLs to GitHub raw"')
        push_ret3 = os.system('git push')
        if push_ret3 != 0:
            os.system('git pull --rebase')
            os.system('git push')
        print(f"✅ {updated} image URLs updated to permanent GitHub links.")

    print("\nPins will start posting automatically via GitHub Actions.")


if __name__ == "__main__":
    run()
