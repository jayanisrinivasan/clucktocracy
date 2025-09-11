# ui/pixel_map.py
import streamlit as st
from PIL import Image
import os

# Preload chicken sprites (place PNGs in /assets/)
SPRITES = {
    "hen": "assets/chicken.png",
    "gossip": "assets/chat.png",
    "peck": "assets/peck.png",
    "ally": "assets/ally.png",
    "sanction": "assets/sanction.png",
}

def render_pixel_map(rows, agents):
    """Render chickens as pixel sprites in a grid with overlays for recent actions."""
    grid_w, grid_h = 600, 400
    cell_size = 100
    base = Image.new("RGBA", (grid_w, grid_h), (20, 20, 30, 255))

    positions = {}
    for i, a in enumerate(agents):
        x = (i % 6) * cell_size + 40
        y = (i // 6) * cell_size + 40
        positions[a.name] = (x, y)

        if os.path.exists(SPRITES["hen"]):
            sprite = Image.open(SPRITES["hen"]).resize((60, 60))
            base.paste(sprite, (x, y), sprite)

    # Overlay last 10 actions
    for r in rows[-10:]:
        actn = r["action"].lower()
        overlay_key = None
        if actn in ("gossip","spread_rumor"): overlay_key = "gossip"
        elif actn in ("peck","initiate_fight"): overlay_key = "peck"
        elif actn == "ally": overlay_key = "ally"
        elif actn == "sanction": overlay_key = "sanction"
        if overlay_key and r["agent"] in positions:
            x, y = positions[r["agent"]]
            if os.path.exists(SPRITES[overlay_key]):
                ov = Image.open(SPRITES[overlay_key]).resize((30, 30))
                base.paste(ov, (x+40, y), ov)

    st.image(base, caption="Pixel Coop Map")
