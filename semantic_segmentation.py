"""
semantic_segmentation.py
------------------------
Provides region segmentation for stimulus images using Meta's
Segment Anything Model (SAM).  SAM works on *any* image —
landscapes, textures, abstract scenes — without needing predefined
class labels, making it ideal as a fallback when YOLO finds nothing.

Public API
----------
run_segmentation(image_bgr, model_dir, points_per_side=16)
    -> list[dict]   # one dict per segment, sorted largest→smallest

build_segmentation_figure(image_rgb, segments)
    -> plotly.graph_objects.Figure
"""

import os
import numpy as np
import cv2
import plotly.graph_objects as go
import plotly.express as px

# SAM model checkpoint stored alongside other models
SAM_CHECKPOINT = "sam_vit_b_01ec64.pth"
SAM_MODEL_TYPE = "vit_b"

# ---------------------------------------------------------------------------
# Colour palette – visually distinct colours for up to 80 segments
# ---------------------------------------------------------------------------
_PALETTE = [
    (230, 25, 75),  (60, 180, 75),   (255, 225, 25), (0, 130, 200),
    (245, 130, 48), (145, 30, 180),  (70, 240, 240),  (240, 50, 230),
    (210, 245, 60), (250, 190, 212), (0, 128, 128),   (220, 190, 255),
    (170, 110, 40), (255, 250, 200), (128, 0, 0),     (170, 255, 195),
    (128, 128, 0),  (255, 215, 180), (0, 0, 128),     (128, 128, 128),
    (255, 80, 80),  (80, 255, 80),   (80, 80, 255),   (255, 180, 0),
    (0, 200, 200),  (200, 0, 200),   (100, 200, 100), (200, 100, 100),
    (100, 100, 200),(255, 140, 200), (140, 255, 200), (200, 255, 140),
]


def _colour_for_idx(idx: int):
    return _PALETTE[idx % len(_PALETTE)]


# ---------------------------------------------------------------------------
# Model cache
# ---------------------------------------------------------------------------
_SAM_PREDICTOR = None


def _load_sam(model_dir: str):
    """Load (and cache) SAM automatic mask generator."""
    global _SAM_PREDICTOR
    if _SAM_PREDICTOR is not None:
        return _SAM_PREDICTOR

    try:
        from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
    except ImportError as exc:
        raise RuntimeError(
            "segment-anything not installed. Run: "
            "pip install git+https://github.com/facebookresearch/segment-anything.git"
        ) from exc

    checkpoint_path = os.path.join(model_dir, SAM_CHECKPOINT)
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(
            f"SAM checkpoint not found at {checkpoint_path}. "
            "Download from: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
        )

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[sem_seg] Loading SAM ({SAM_MODEL_TYPE}) on {device} …")

    sam = sam_model_registry[SAM_MODEL_TYPE](checkpoint=checkpoint_path)
    sam.to(device=device)

    # Automatic mask generator — no prompts needed
    from segment_anything import SamAutomaticMaskGenerator
    _SAM_PREDICTOR = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=16,          # grid density (↑ = more segments, slower)
        pred_iou_thresh=0.86,        # keep only high-quality masks
        stability_score_thresh=0.92,
        box_nms_thresh=0.7,
        min_mask_region_area=500,    # ignore tiny regions (< 500 px²)
    )
    return _SAM_PREDICTOR


# ---------------------------------------------------------------------------
# Core segmentation function
# ---------------------------------------------------------------------------
def run_segmentation(image_bgr: np.ndarray, model_dir: str, points_per_side: int = 16):
    """Run SAM on *image_bgr* and return a list of segment dicts.

    Each dict contains:
        mask        (ndarray, bool) – H×W boolean mask
        area        (int)           – number of pixels in the mask
        area_frac   (float)         – fraction of total image area
        bbox        (list)          – [x, y, w, h] bounding box
        colour      (tuple)         – (R, G, B) display colour
        label       (str)           – "Region N"
    Segments are returned sorted largest → smallest.
    """
    if image_bgr is None or image_bgr.size == 0:
        return []

    try:
        generator = _load_sam(model_dir)
    except Exception as exc:
        print(f"[sem_seg] Could not load SAM: {exc}")
        return []

    # SAM expects RGB
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB) if image_bgr.ndim == 3 else image_bgr

    try:
        masks = generator.generate(image_rgb)
    except Exception as exc:
        print(f"[sem_seg] SAM inference failed: {exc}")
        return []

    h, w = image_rgb.shape[:2]
    total_px = h * w

    # Sort largest → smallest so we can layer them nicely
    masks_sorted = sorted(masks, key=lambda m: m["area"], reverse=True)

    segments = []
    for idx, m in enumerate(masks_sorted):
        bool_mask = m["segmentation"].astype(bool)
        area      = int(bool_mask.sum())
        bbox_xywh = [int(v) for v in m["bbox"]]   # SAM gives [x, y, w, h]

        segments.append({
            "mask":      bool_mask,
            "area":      area,
            "area_frac": area / total_px,
            "bbox":      bbox_xywh,
            "colour":    _colour_for_idx(idx),
            "label":     f"Region {idx + 1}",
        })

    print(f"[sem_seg] SAM found {len(segments)} regions.")
    return segments


# ---------------------------------------------------------------------------
# Figure builder
# ---------------------------------------------------------------------------
def build_segmentation_figure(image_rgb: np.ndarray, segments: list):
    """Overlay SAM masks on *image_rgb* and return a Plotly figure.

    Produces a vivid, colour-coded overlay where each segment is
    painted with a semi-transparent colour.  Bounding boxes are
    omitted to keep the landscape view clean; instead, the legend
    lists the top-10 largest regions by area %.
    """
    if len(segments) == 0:
        fig = px.imshow(image_rgb)
        fig.update_layout(
            title="Semantic Segmentation (SAM): no regions found",
            title_x=0.5,
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    # ---- build colour overlay ----
    overlay = image_rgb.copy().astype(np.float32)
    alpha = 0.50   # mask opacity

    for seg in segments:
        mask = seg["mask"]
        r, g, b = seg["colour"]
        overlay[mask, 0] = overlay[mask, 0] * (1 - alpha) + r * alpha
        overlay[mask, 1] = overlay[mask, 1] * (1 - alpha) + g * alpha
        overlay[mask, 2] = overlay[mask, 2] * (1 - alpha) + b * alpha

    overlay = np.clip(overlay, 0, 255).astype(np.uint8)

    fig = px.imshow(overlay)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    # ---- draw contours for the largest segments ----
    for seg in segments[:20]:     # contours only for top-20 largest
        mask_u8 = seg["mask"].astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        r, g, b = seg["colour"]
        colour_hex = f"rgb({r},{g},{b})"
        for cnt in contours:
            if len(cnt) < 3:
                continue
            pts = cnt.squeeze()
            if pts.ndim < 2:
                continue
            xs = pts[:, 0].tolist() + [pts[0, 0]]
            ys = pts[:, 1].tolist() + [pts[0, 1]]
            fig.add_trace(go.Scatter(
                x=xs, y=ys,
                mode="lines",
                line=dict(color=colour_hex, width=1.5),
                showlegend=False,
                hoverinfo="skip",
            ))

    # ---- legend: top-10 regions by area ----
    for idx, seg in enumerate(segments[:10]):
        r, g, b = seg["colour"]
        colour_hex = f"rgb({r},{g},{b})"
        pct = seg["area_frac"] * 100
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=14, color=colour_hex, symbol="square"),
            name=f"{seg['label']} ({pct:.1f}%)",
            showlegend=True,
        ))

    # ---- title ----
    total_area_covered = sum(s["area_frac"] for s in segments) * 100
    fig.update_layout(
        title=(
            f"SAM Segmentation — {len(segments)} region(s) detected "
            f"| ~{min(total_area_covered, 100):.0f}% of image covered"
        ),
        title_x=0.5,
        legend=dict(
            orientation="v",
            x=1.01, y=1,
            bgcolor="rgba(0,0,0,0.55)",
            font=dict(color="white", size=11),
            title=dict(text="Top regions", font=dict(color="white")),
        ),
        margin=dict(r=200),
        paper_bgcolor="black",
        plot_bgcolor="black",
    )

    return fig
