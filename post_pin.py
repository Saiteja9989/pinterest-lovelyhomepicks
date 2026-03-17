"""
post_pin.py — Run by GitHub Actions 20 times/day
Picks the next unposted pin using round-robin across blogs.

Strategy: 10 blogs × 10 pins = 100 pins queued
  Round-robin posts Pin#1 from all blogs first, then Pin#2, etc.
  = 2 pins/day per blog when triggered 20 times/day
  = all 100 pins exhausted in 5 days
"""
import json
import requests
from config import MAKE_WEBHOOK_URL

QUEUE_FILE = 'pins_queue.json'


def load_queue():
    with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def post_to_pinterest(pin):
    """Send pin data to Make.com webhook"""
    alt_text = f"{pin.get('style', '')} — {pin.get('title', '')[:80]}"

    payload = {
        "title":       pin["title"],
        "description": pin["description"],   # full description + hashtags combined
        "image_url":   pin["image_url"],
        "link":        pin["link"],
        "board_id":    pin["board_id"],
        "alt_text":    alt_text,
    }
    res = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=30)
    if res.status_code != 200:
        print(f"Webhook HTTP error: {res.status_code} — {res.text[:200]}")
        return False
    # Make.com instant webhook always returns 200 with {"accepted": true}
    # It does NOT confirm Pinterest succeeded — Pinterest errors happen async.
    # To detect Pinterest failures, configure Make.com to use a synchronous
    # Webhook Response module that returns {"status": "ok"} on success.
    body = res.json() if res.text else {}
    if isinstance(body, dict) and body.get("status") == "ok":
        return True
    print(f"Make.com did not confirm success: {body}")
    return False



def pick_next_pin(pins):
    """Round-robin selection across blogs.

    Picks the unposted pin with the smallest pin_number,
    breaking ties by smallest blog_number.
    Skips pins whose image URL is empty or returns non-200.
    """
    best_idx = None
    best_pin = None

    for i, pin in enumerate(pins):
        if pin.get("posted", False):
            continue
        url = pin.get("image_url", "")
        if not url or not url.startswith("http"):
            continue
        if best_pin is None:
            best_idx, best_pin = i, pin
        else:
            curr_pnum = pin.get("pin_number", 999)
            curr_bnum = pin.get("blog_number", 999)
            best_pnum = best_pin.get("pin_number", 999)
            best_bnum = best_pin.get("blog_number", 999)
            if curr_pnum < best_pnum or (curr_pnum == best_pnum and curr_bnum < best_bnum):
                best_idx, best_pin = i, pin

    return best_idx, best_pin


def run():
    queue = load_queue()
    pins = queue.get("pins", [])

    # Safety gate: don't post until explicitly enabled
    if not queue.get("posting_enabled", False):
        pending = sum(1 for p in pins if not p.get("posted", False))
        blogs = len(set(p.get("blog_number") for p in pins if not p.get("posted", False)))
        print(f"⏸  Posting is PAUSED. Queue has {pending} pins across {blogs} blogs.")
        print(f"   When ready, run: python start_posting.py")
        return

    next_index, next_pin = pick_next_pin(pins)

    if next_pin is None:
        print("No pending pins in queue. Generate more blogs!")
        return

    print(f"\nPosting pin #{next_pin.get('pin_number')} from Blog #{next_pin.get('blog_number')}: {next_pin['title'][:60]}...")
    print(f"Style: {next_pin.get('style', 'N/A')}")
    print(f"Image: {next_pin['image_url']}")

    success = post_to_pinterest(next_pin)

    if success:
        pins[next_index]["posted"] = True
        queue["pins"] = pins
        save_queue(queue)
        print("✅ Pin posted successfully!")

        # Stats
        remaining = sum(1 for p in pins if not p.get("posted", False))
        blogs_active = len(set(p.get("blog_number") for p in pins if not p.get("posted", False)))
        print(f"Pins remaining: {remaining} across {blogs_active} blogs")
    else:
        print("❌ Failed to post pin. Will retry next run.")


if __name__ == "__main__":
    run()
