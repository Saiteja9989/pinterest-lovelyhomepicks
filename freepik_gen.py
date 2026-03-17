import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import base64
import os
from io import BytesIO
from PIL import Image
from config import FREEPIK_API_KEY, IMAGE_WIDTH, IMAGE_HEIGHT

FREEPIK_URL    = "https://api.freepik.com/v1/ai/text-to-image/seedream-v4-5"
REFERENCE_PHOTO = "reference.jpg"
IMAGES_DIR     = "images"  # local folder — committed to GitHub for permanent URLs


def load_reference_image():
    """Load reference.jpg as base64 if it exists"""
    if os.path.exists(REFERENCE_PHOTO):
        with open(REFERENCE_PHOTO, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return None


def _strip_metadata(filepath):
    """Re-encode image to remove all AI/C2PA metadata that triggers Pinterest's 'AI Modified' label."""
    try:
        img   = Image.open(filepath)
        clean = Image.new(img.mode, img.size)
        clean.putdata(list(img.getdata()))
        clean.save(filepath, "JPEG", quality=95, optimize=True)
    except Exception as e:
        print(f"  Metadata strip warning: {e}")


def download_image(cdn_url, filename):
    """Download image from Freepik CDN to images/ folder before URL expires."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    filepath = os.path.join(IMAGES_DIR, filename)
    try:
        res = requests.get(cdn_url, timeout=60)
        if res.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(res.content)
            _strip_metadata(filepath)
            print(f"  Downloaded: {filepath}")
            return filepath
        else:
            print(f"  Download failed: HTTP {res.status_code}")
            return None
    except Exception as e:
        print(f"  Download error: {e}")
        return None


def generate_image(prompt, save_filename=None):
    """Submit image generation task to Freepik, download immediately, return local path."""
    headers = {
        "x-freepik-api-key": FREEPIK_API_KEY,
        "Content-Type": "application/json"
    }
    # Only add photo keywords for lifestyle/photo prompts
    if any(kw in prompt.lower() for kw in ["lifestyle photo", "dslr", "photography", "real photo", "interior photo"]):
        prompt = prompt + ", sharp focus, high resolution, natural lighting"

    # Seedream v4.5 has a ~1000 char prompt limit — truncate cleanly at sentence boundary
    if len(prompt) > 950:
        prompt = prompt[:950].rsplit('.', 1)[0] + '.'

    body = {
        "prompt": prompt,
        "aspect_ratio": "portrait_2_3",   # Seedream param — 2:3 = Pinterest optimal
        "enable_safety_checker": False,
    }

    res = requests.post(FREEPIK_URL, headers=headers, json=body)
    if not res.text.strip():
        print(f"  Freepik error: empty response (HTTP {res.status_code})")
        return None
    try:
        data = res.json()
    except Exception:
        print(f"  Freepik error: non-JSON response (HTTP {res.status_code}): {res.text[:200]}")
        return None

    if "data" not in data:
        print(f"Freepik error: {data}")
        return None

    task_id = data["data"].get("task_id")
    if not task_id:
        return None

    print(f"  Freepik task submitted: {task_id}")

    # Poll until complete
    for attempt in range(30):
        time.sleep(10)
        try:
            poll = requests.get(
                f"{FREEPIK_URL}/{task_id}",
                headers={"x-freepik-api-key": FREEPIK_API_KEY},
                timeout=30
            )
            poll_data = poll.json()
        except Exception as e:
            print(f"  Network error on attempt {attempt+1}, retrying... ({e})")
            time.sleep(5)
            continue

        status = poll_data.get("data", {}).get("status", "")

        if status == "COMPLETED":
            try:
                generated = poll_data["data"]["generated"]
                if isinstance(generated, list) and len(generated) > 0:
                    item = generated[0]
                    cdn_url = item if isinstance(item, str) else item["url"]
                else:
                    cdn_url = generated if isinstance(generated, str) else generated["url"]

                print(f"  Image ready on CDN: {cdn_url[:60]}...")

                # Download immediately before SAS token expires
                if save_filename:
                    local_path = download_image(cdn_url, save_filename)
                    return local_path  # return local path, not CDN URL

                return cdn_url  # fallback if no filename given
            except Exception as e:
                print(f"  Parse error: {e} | Response: {poll_data}")
                return None
        elif status == "FAILED":
            print(f"  Freepik task failed")
            return None
        else:
            print(f"  Waiting... ({attempt+1}/30) status: {status}")

    print("  Freepik timed out")
    return None


def generate_10_images(pins, blog_number, start_from=1):
    """Generate and download images for all 10 pins.
    Saves to images/blog{N}_pin{M}.jpg — committed to GitHub for permanent URLs.
    Skips pins where the file already exists (safe to re-run after a crash).
    start_from — only generate pins with pin_number >= this value (default=1 = all).
    """
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"\nGenerating pin images with Freepik (start_from pin {start_from})...")
    for i, pin in enumerate(pins):
        pin_num = pin.get("pin_number", i + 1)
        filename = f"blog{blog_number}_pin{pin_num}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)

        # Skip pins before start_from — assign existing file path if present
        if pin_num < start_from:
            pins[i]["image_url"] = filepath if os.path.exists(filepath) else ""
            print(f"\nImage {i+1}/{len(pins)}: SKIP pin {pin_num} (before start_from={start_from})")
            continue

        # Skip if file already exists on disk (resume after crash)
        if os.path.exists(filepath):
            pins[i]["image_url"] = filepath
            print(f"\nImage {i+1}/{len(pins)}: SKIP pin {pin_num} (file exists) — {filename}")
            continue

        print(f"\nImage {i+1}/{len(pins)}: {pin.get('title', '')[:50]}...")
        local_path = generate_image(pin["freepik_prompt"], save_filename=filename)
        if local_path:
            pins[i]["image_url"] = local_path
        else:
            pins[i]["image_url"] = ""
            print(f"  Warning: No image for pin {pin_num}")
    return pins
