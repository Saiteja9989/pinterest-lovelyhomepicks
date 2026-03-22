"""
regen_pin.py — Regenerate the image for a single pin.

Usage: python regen_pin.py
  → Asks for blog number and pin number
  → Shows the current Freepik prompt
  → Lets you edit the prompt or use it as-is
  → Regenerates the image (overwrites images/blog{N}_pin{M}.jpg)
  → Pushes to GitHub and updates the URL in the queue
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from freepik_gen import generate_image

QUEUE_FILES  = ['pins_queue_new.json', 'pins_queue.json']
IMAGES_DIR   = 'images'
GITHUB_RAW   = 'https://raw.githubusercontent.com/Saiteja9989/pinterest-automation/main'


def load_queue(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_queue(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_pin(blog_num, pin_num):
    """Return (queue_path, queue_data, pin_index) or (None, None, None)."""
    for qpath in QUEUE_FILES:
        q = load_queue(qpath)
        if not q:
            continue
        for i, pin in enumerate(q.get('pins', [])):
            if pin.get('blog_number') == blog_num and pin.get('pin_number') == pin_num:
                return qpath, q, i
    return None, None, None


def main():
    print('\n' + '=' * 60)
    print('  PIN IMAGE REGENERATOR')
    print('=' * 60)

    # ── Input ──────────────────────────────────────────────────
    try:
        blog_num = int(input('\nBlog number: ').strip())
        pin_num  = int(input('Pin number:  ').strip())
    except ValueError:
        print('Invalid input — must be integers.')
        sys.exit(1)

    # ── Find pin in queue ──────────────────────────────────────
    qpath, queue, idx = find_pin(blog_num, pin_num)
    if qpath is None:
        print(f'\n❌  Pin not found: blog {blog_num} / pin {pin_num}')
        print(f'   Searched: {", ".join(QUEUE_FILES)}')
        sys.exit(1)

    pin = queue['pins'][idx]
    filename = f'blog{blog_num}_pin{pin_num}.jpg'
    filepath = os.path.join(IMAGES_DIR, filename)

    print(f'\n✅  Found in {qpath}')
    print(f'   Title : {pin.get("title", "")[:70]}')
    print(f'   Type  : {pin.get("pin_type", "")}')
    print(f'   File  : {filepath}')

    # ── Show / edit prompt ─────────────────────────────────────
    current_prompt = pin.get('freepik_prompt', '')
    print(f'\n── Current Freepik prompt ──────────────────────────────')
    print(current_prompt)
    print('────────────────────────────────────────────────────────')

    choice = input('\nUse this prompt? [Y = yes / N = enter new prompt]: ').strip().lower()
    if choice == 'n':
        print('Paste new prompt (press Enter twice when done):')
        lines = []
        while True:
            line = input()
            if line == '' and lines and lines[-1] == '':
                break
            lines.append(line)
        new_prompt = '\n'.join(lines).strip()
        if not new_prompt:
            print('Empty prompt — aborting.')
            sys.exit(1)
        prompt = new_prompt
    else:
        prompt = current_prompt

    if not prompt:
        print('No prompt available — aborting.')
        sys.exit(1)

    # ── Regenerate ─────────────────────────────────────────────
    print(f'\nRegenerating image for blog{blog_num}_pin{pin_num}...')

    # Delete old file so freepik_gen doesn't skip it
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f'  Removed old: {filepath}')

    local_path = generate_image(prompt, save_filename=filename)

    if not local_path:
        print('❌  Image generation failed.')
        sys.exit(1)

    print(f'✅  New image saved: {local_path}')

    # ── Update queue ───────────────────────────────────────────
    new_github_url = f'{GITHUB_RAW}/{IMAGES_DIR}/{filename}'
    queue['pins'][idx]['freepik_prompt'] = prompt
    queue['pins'][idx]['image_url'] = new_github_url
    save_queue(qpath, queue)
    print(f'✅  Queue updated: {qpath}')

    # ── Push to GitHub ─────────────────────────────────────────
    print('\nPushing to GitHub...')
    os.system(f'git add -f {filepath} {qpath}')
    os.system(f'git commit -m "Regen image: blog{blog_num}_pin{pin_num}"')
    ret = os.system('git push')
    if ret != 0:
        print('  Pull and retry...')
        os.system('git pull --rebase')
        os.system('git push')

    print(f'\n{"=" * 60}')
    print(f'  Done! blog{blog_num}_pin{pin_num} regenerated.')
    print(f'  GitHub URL: {new_github_url}')
    print(f'{"=" * 60}\n')


if __name__ == '__main__':
    main()
