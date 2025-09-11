import matplotlib.pyplot as plt
import streamlit as st

def render_pixel_map(rows, agents):
    fig, ax = plt.subplots(figsize=(6,4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    colors = ["red", "blue", "green", "orange", "purple", "yellow"]
    positions = {}

    for i, a in enumerate(agents):
        x, y = (i % 5) * 2 + 1, (i // 5) * 2 + 1
        positions[a.name] = (x,y)
        ax.scatter(x, y, c=colors[i % len(colors)], s=800, marker="o")
        ax.text(x, y+0.5, a.name, ha="center", color="white", fontsize=10)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#1e1e1e")
    st.pyplot(fig)
