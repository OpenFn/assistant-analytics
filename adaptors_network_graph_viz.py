import argparse
from itertools import combinations
from collections import Counter
from pathlib import Path
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("focus", nargs="?", default=None, help="Show only nodes connected to this adaptor")
args = parser.parse_args()
FOCUS = args.focus.strip().lower() if args.focus else None

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(
    r"C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv",
    usecols=["chat_session_id", "adaptors_mentioned_in_user_prompt_specifically"],
    low_memory=False,
)

EXCLUDE = {"common", "testing"}

def parse_adaptors(val):
    if not isinstance(val, str) or not val.strip():
        return []
    return list({a.strip().lower() for a in val.split(",") if a.strip() and a.strip().lower() not in EXCLUDE})

df["adaptors_list"] = df["adaptors_mentioned_in_user_prompt_specifically"].apply(parse_adaptors)

# ── Count node frequency and edge co-occurrence ───────────────────────────────
node_counts = Counter()
edge_counts = Counter()

for adaptors in df["adaptors_list"]:
    for a in adaptors:
        node_counts[a] += 1
    for pair in combinations(sorted(adaptors), 2):
        edge_counts[pair] += 1

print(f"Unique adaptors: {len(node_counts)}")
print(f"Unique co-occurrence pairs: {len(edge_counts)}")

# ── Build graph ───────────────────────────────────────────────────────────────
G = nx.Graph()
for node, count in node_counts.items():
    G.add_node(node, freq=count)
for (a, b), count in edge_counts.items():
    if count >= 1:
        G.add_edge(a, b, weight=count)

# Remove isolated nodes (mentioned alone, never paired)
G.remove_nodes_from(list(nx.isolates(G)))

# If a focus adaptor was given, keep only it and its direct neighbours
if FOCUS:
    if FOCUS not in G:
        print(f"Adaptor '{FOCUS}' not found in graph. Available: {', '.join(sorted(G.nodes()))}")
        raise SystemExit(1)
    keep = set(G.neighbors(FOCUS)) | {FOCUS}
    G = G.subgraph(keep).copy()
    print(f"Focusing on '{FOCUS}': {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
else:
    print(f"Graph after removing isolates: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# ── Layout ────────────────────────────────────────────────────────────────────
pos = nx.spring_layout(G, k=2.5, seed=42, weight="weight")

# ── Visual scaling ────────────────────────────────────────────────────────────
freqs = [G.nodes[n]["freq"] for n in G.nodes()]
max_freq = max(freqs) if freqs else 1
node_sizes = [200 + (G.nodes[n]["freq"] / max_freq) * 2000 for n in G.nodes()]

edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
max_w = max(edge_weights) if edge_weights else 1
edge_widths = [0.5 + (w / max_w) * 6 for w in edge_weights]
edge_alphas = [0.05 + (w / max_w) * 0.95 for w in edge_weights]

# Colour nodes by frequency using a blue palette
node_cmap = plt.cm.Blues
node_colours = [node_cmap(0.4 + 0.6 * (G.nodes[n]["freq"] / max_freq)) for n in G.nodes()]

# ── Draw ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(18, 14))
ax.set_facecolor("#F8F9FA")
fig.patch.set_facecolor("#F8F9FA")

# Edges (draw per-edge for individual alpha and width)
for (u, v), width, alpha in zip(G.edges(), edge_widths, edge_alphas):
    nx.draw_networkx_edges(
        G, pos, edgelist=[(u, v)], width=width, alpha=alpha,
        edge_color="#E74C3C", ax=ax
    )

nx.draw_networkx_nodes(
    G, pos, node_size=node_sizes, node_color=node_colours,
    edgecolors="#333333", linewidths=0.5, ax=ax
)
nx.draw_networkx_labels(
    G, pos, font_size=7, font_color="#111111", font_weight="bold", ax=ax
)

# Edge weight labels on heavier edges
heavy_edges = {(u, v): str(d["weight"]) for u, v, d in G.edges(data=True) if d["weight"] >= 3}
nx.draw_networkx_edge_labels(
    G, pos, edge_labels=heavy_edges, font_size=6, font_color="#888888", ax=ax
)

title = (
    f"Adaptor Co-usage Network — '{FOCUS}'\n(node size = sessions used in,  edge thickness = times used together)"
    if FOCUS else
    "Adaptor Co-usage Network\n(node size = sessions used in,  edge thickness = times used together)"
)
ax.set_title(title, fontsize=14, fontweight="bold", pad=16)
ax.axis("off")

plt.tight_layout()
out_name = f"adaptors_used_network_graph_viz_{FOCUS}.png" if FOCUS else "adaptors_used_network_graph_viz.png"
out_path = Path(r"C:\openfn\assistant-analytics\charts") / out_name
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"\nChart saved to {out_path}")
