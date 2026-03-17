import os
from dotenv import load_dotenv
load_dotenv()

# ─── API KEYS ─────────────────────────────────────────────────────────────────
GROQ_API_KEY       = os.environ.get('GROQ_API_KEY', '')
FREEPIK_API_KEY    = os.environ.get('FREEPIK_API_KEY', '')
SCRAPER_API_KEY    = os.environ.get('SCRAPER_API_KEY', '')
AMAZON_TAG         = os.environ.get('AMAZON_TAG', 'lovelyhomepicks-20')
GEMINI_API_KEY     = os.environ.get('GEMINI_API_KEY', '')
BLOGGER_BLOG_ID    = os.environ.get('BLOGGER_BLOG_ID', '8466477651147836095')
MAKE_WEBHOOK_URL   = os.environ.get('MAKE_WEBHOOK_URL', '')
GOOGLE_CREDENTIALS  = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
GOOGLE_SHEET_URL    = os.environ.get('GOOGLE_SHEET_URL', '')

# ─── GROQ ─────────────────────────────────────────────────────────────────────
GROQ_MODEL = 'llama-3.3-70b-versatile'

# ─── FREEPIK ──────────────────────────────────────────────────────────────────
IMAGE_WIDTH  = 1000
IMAGE_HEIGHT = 1440

# ─── PINTEREST BOARDS ─────────────────────────────────────────────────────────
# Fill in board IDs after creating boards on Pinterest
BOARDS = {
    'living'    : '',
    'bedroom'   : '',
    'kitchen'   : '',
    'bathroom'  : '',
    'office'    : '',
    'budget'    : '',
    'luxury'    : '',
    'wall_art'  : '',
    'small_space': '',
    'cozy'      : '',
    'general'   : '',
    'amazon'    : '',
}

# ─── PINTEREST TOPIC TAGS ─────────────────────────────────────────────────────
TOPIC_TAGS = {
    'living'    : ['home_decor', 'interior_design', 'living_room', 'furniture', 'home_improvement'],
    'bedroom'   : ['home_decor', 'interior_design', 'bedroom', 'bedroom_decor', 'cozy_home'],
    'kitchen'   : ['home_decor', 'kitchen', 'kitchen_design', 'interior_design', 'home_improvement'],
    'bathroom'  : ['home_decor', 'bathroom', 'bathroom_decor', 'interior_design', 'home_improvement'],
    'office'    : ['home_decor', 'home_office', 'interior_design', 'productivity', 'office_decor'],
    'budget'    : ['home_decor', 'budget_decorating', 'interior_design', 'affordable_home', 'diy_and_crafts'],
    'luxury'    : ['home_decor', 'luxury_home', 'interior_design', 'dream_home', 'home_inspiration'],
    'wall_art'  : ['home_decor', 'wall_art', 'interior_design', 'gallery_wall', 'art'],
    'small_space': ['home_decor', 'small_space', 'interior_design', 'apartment_decor', 'space_saving'],
    'cozy'      : ['home_decor', 'cozy_home', 'interior_design', 'hygge', 'home_inspiration'],
    'general'   : ['home_decor', 'interior_design', 'home_inspiration', 'dream_home', 'home_improvement'],
    'amazon'    : ['home_decor', 'amazon_finds', 'interior_design', 'budget_decorating', 'home_improvement'],
}

# ─── BLOG ─────────────────────────────────────────────────────────────────────
BLOG_URL = 'https://lovelyhomepicks.blogspot.com'
