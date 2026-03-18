"""
step3_start_posting.py — Run this ONCE when all your blogs are queued and ready.
Enables GitHub Actions to start posting pins automatically.

Usage: python step3_start_posting.py
"""
import json
import os

QUEUE_FILE = 'pins_queue.json'

with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
    queue = json.load(f)

pins  = queue.get("pins", [])
total = len(pins)
pending = sum(1 for p in pins if not p.get("posted", False))
blogs   = sorted(set(p.get("blog_number") for p in pins if not p.get("posted", False)))

print(f"\n{'='*50}")
print(f"  Queue status:")
print(f"  Total pins  : {total}")
print(f"  Ready to post: {pending}")
print(f"  Blog numbers : {blogs}")
print(f"{'='*50}")

if pending == 0:
    print("\n  Queue is empty — generate blogs first!")
else:
    confirm = input(f"\n  Enable posting? All {pending} pins will start going live. [y/n]: ").strip().lower()
    if confirm == 'y':
        queue["posting_enabled"] = True
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        os.system('git add pins_queue.json')
        os.system('git commit -m "Enable Pinterest posting"')
        os.system('git push')
        print(f"\n  ✅ Posting ENABLED! GitHub Actions will now post 20 pins/day.")
        print(f"  First pin posts at next scheduled time (check Actions tab).")
    else:
        print("\n  Cancelled. Run again when ready.")
