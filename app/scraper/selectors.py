"""ALL Google Maps DOM selectors live here and ONLY here (see SOUL.md #3).

Patterns studied from reference/Google-Maps-Scrapper/main.py (read-only).
When Google changes the DOM, this is the only file that should need fixing.
Verify with: python -m app.scraper --smoke-test
"""

# --- Search results feed ---
FEED = 'div[role="feed"]'
PLACE_LINK = 'a[href*="/maps/place/"]'

# --- Place detail pane ---
NAME = "h1.DUwDvf"
CATEGORY = "button.DkEaL"
ADDRESS = 'button[data-item-id="address"] div.fontBodyMedium'
WEBSITE = 'a[data-item-id="authority"]'
PHONE = 'button[data-item-id^="phone:tel:"]'
# rating block: first span holds the number, the aria-label span holds review count
RATING_CONTAINER = "div.F7nice"

# --- Block / interstitial detection ---
BLOCK_URL_FRAGMENTS = ("/sorry/", "consent.google.com")
BLOCK_TEXT_MARKERS = ("unusual traffic", "not a robot")
