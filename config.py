import os
from dotenv import load_dotenv
load_dotenv()

# ─── API KEYS ─────────────────────────────────────────────────────────────────
GROQ_API_KEY       = os.environ.get('GROQ_API_KEY', '')
FREEPIK_API_KEY    = os.environ.get('FREEPIK_API_KEY', '')
SCRAPER_API_KEY    = os.environ.get('SCRAPER_API_KEY', '')
AMAZON_TAG         = os.environ.get('AMAZON_TAG', 'smarthomeorg-20')
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
    'living'    : '1144829236467500689',  # Living Room Decor Ideas
    'bedroom'   : '1144829236467500690',  # Bedroom Decor Inspiration
    'budget'    : '1144829236467500691',  # Home Decor on a Budget
    'wall_art'  : '1144829236467500693',  # Wall Art & Gallery Wall Ideas
    'cozy'      : '1144829236467500696',  # Cozy Home Aesthetic
    'kitchen'   : '1144829236467500699',  # Kitchen & Dining Decor
    'boho'      : '1144829236467500703',  # Boho Home Decor
    'luxury'    : '1144829236467500706',  # Luxury Home Decor Finds
    'office'    : '1144829236467500708',  # Home Office Decor
    'outdoor'   : '1144829236467500709',  # Outdoor & Patio Decor
    'general'   : '1144829236467500689',  # fallback → Living Room
    'amazon'    : '1144829236467500691',  # fallback → Budget
}

# ─── PINTEREST TOPIC TAGS ─────────────────────────────────────────────────────
TOPIC_TAGS = {
    'living'    : ['home_decor', 'interior_design', 'living_room', 'furniture', 'cozy_home'],
    'bedroom'   : ['home_decor', 'interior_design', 'bedroom', 'bedroom_decor', 'cozy_home'],
    'kitchen'   : ['home_decor', 'kitchen', 'kitchen_design', 'interior_design', 'dining_room'],
    'bathroom'  : ['home_decor', 'bathroom', 'bathroom_decor', 'interior_design', 'spa'],
    'office'    : ['home_decor', 'home_office', 'interior_design', 'office_decor', 'productivity'],
    'budget'    : ['home_decor', 'budget_decorating', 'interior_design', 'affordable_home', 'amazon_finds'],
    'luxury'    : ['home_decor', 'luxury_home', 'interior_design', 'dream_home', 'home_inspiration'],
    'wall_art'  : ['home_decor', 'wall_art', 'interior_design', 'gallery_wall', 'art'],
    'cozy'      : ['home_decor', 'cozy_home', 'interior_design', 'hygge', 'home_inspiration'],
    'boho'      : ['home_decor', 'boho_decor', 'interior_design', 'bohemian', 'natural_home'],
    'outdoor'   : ['home_decor', 'outdoor_decor', 'patio', 'garden', 'outdoor_living'],
    'lighting'  : ['home_decor', 'interior_design', 'lighting', 'home_lighting', 'ambiance'],
    'general'   : ['home_decor', 'interior_design', 'home_inspiration', 'dream_home', 'home_improvement'],
    'amazon'    : ['home_decor', 'amazon_finds', 'interior_design', 'budget_decorating', 'home_improvement'],
}

# ─── BLOG ─────────────────────────────────────────────────────────────────────
BLOG_URL = 'https://lovelyhomepicks.blogspot.com'
