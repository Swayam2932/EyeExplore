import pandas as pd
import dash
from PIL import Image
from dash import dcc, html, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import coassociation_matrix as compute_coa
import FixaTons
from FixaTons import COLLECTION_PATH
import flask
import glob
import os
import ssl
import urllib.request
import warnings
import requests
import numpy as np
import cv2
import zipfile
import json
import base64
import io
from scipy import signal
from scipy.ndimage import gaussian_filter
import skimage.io as sio
from plotly.subplots import make_subplots
from skimage import data, draw
from scipy import ndimage
from ultralytics import YOLO
import semantic_segmentation as sem_seg
import upload_panel
import scanpath_converter as sc
import k_dataset
import k_visualizations

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
DETECTION_MODEL = None

PLOT_TYPES = [
    {'value': 'stimulus',      'label': 'Stimulus Image',        'icon': 'bi-image'},
    {'value': 'scanpath',      'label': 'Scanpath Animation',    'icon': 'bi-geo-alt-fill'},
    {'value': 'scanpath_overlay', 'label': 'Scanpath Overlay',   'icon': 'bi-share-fill'},
    {'value': 'attention',     'label': 'Attention Map',         'icon': 'bi-fire'},
    {'value': 'scarf',         'label': 'Scarf Plot',            'icon': 'bi-bar-chart-steps'},
    {'value': 'aoi_timeline',  'label': 'AOI Timeline',          'icon': 'bi-graph-up'},
    {'value': '3d_scanpath',   'label': '3D Scanpath',           'icon': 'bi-box'},
    {'value': '3d_scatter',    'label': '3D Scatter',            'icon': 'bi-diamond-fill'},
    {'value': 'coassociation', 'label': 'Co-association Matrix', 'icon': 'bi-grid-3x3-gap-fill'},
    {'value': 'detection',     'label': 'Object Detection',      'icon': 'bi-bounding-box'},
    {'value': 'transition',    'label': 'Transition Matrix',     'icon': 'bi-arrow-left-right'},
    {'value': 'k_video',       'label': 'Synced Video + K-Timeline', 'icon': 'bi-play-circle-fill'},
    {'value': 'k_timeline',    'label': 'K-Coefficient Timeline','icon': 'bi-activity'}
]

DROPDOWN_OPTIONS = [{'label': pt['label'], 'value': pt['value']} for pt in PLOT_TYPES]

datasets_list = [d for d in FixaTons.info.datasets() if not d.startswith('.')]

AOI = []
AOI_type = "rect"

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL LOADING & UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_detection_model():
    global DETECTION_MODEL
    if DETECTION_MODEL is not None:
        return DETECTION_MODEL

    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, 'yolov8n.pt')
    DETECTION_MODEL = YOLO(model_path)
    return DETECTION_MODEL


def suppress_overlapping_boxes(detections, iou_threshold=0.3, io_min_threshold=0.5):
    # Sort detections by confidence descending
    sorted_dets = sorted(detections, key=lambda d: d['confidence'], reverse=True)
    accepted = []

    for det in sorted_dets:
        box = det['box']
        overlap = False
        for acc in accepted:
            acc_box = acc['box']

            # Intersection coordinates
            x1 = max(box[0], acc_box[0])
            y1 = max(box[1], acc_box[1])
            x2 = min(box[0] + box[2], acc_box[0] + acc_box[2])
            y2 = min(box[1] + box[3], acc_box[1] + acc_box[3])

            inter_w = max(0, x2 - x1)
            inter_h = max(0, y2 - y1)
            inter_area = inter_w * inter_h

            if inter_area > 0:
                area_box = box[2] * box[3]
                area_acc = acc_box[2] * acc_box[3]
                union_area = area_box + area_acc - inter_area

                iou = inter_area / union_area if union_area > 0 else 0
                io_min = inter_area / min(area_box, area_acc) if min(area_box, area_acc) > 0 else 0

                if iou > iou_threshold or io_min > io_min_threshold:
                    overlap = True
                    break

        if not overlap:
            accepted.append(det)

    return accepted


def detect_objects(image, confidence_threshold=0.4):
    try:
        model = load_detection_model()
    except Exception as exc:
        print(f'Failed to load detection model: {exc}')
        return []

    if image is None or image.size == 0:
        return []

    results = model(image, conf=confidence_threshold, verbose=False)

    detections = []
    if len(results) > 0:
        result = results[0]
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls = int(box.cls[0].cpu().numpy())
            label = model.names[cls]
            w = x2 - x1
            h = y2 - y1
            detections.append({
                'label': label,
                'confidence': conf,
                'box': [int(x1), int(y1), int(w), int(h)]
            })

    return suppress_overlapping_boxes(detections)


def build_detection_figure(image_rgb, detections):
    fig = px.imshow(image_rgb)
    for det in detections:
        x, y, w, h = det['box']
        fig.add_shape(
            type='rect',
            x0=x, y0=y, x1=x + w, y1=y + h,
            line=dict(color='red', width=3)
        )
        fig.add_annotation(
            x=x, y=max(y - 5, 0),
            text=f" <b>{det['label']} {det['confidence']:.2f}</b> ",
            showarrow=False,
            font=dict(color='white', size=12),
            bgcolor='red',
            opacity=0.85,
            xanchor='left',
            yanchor='bottom'
        )
    if detections:
        fig.update_layout(title=f'Detected {len(detections)} objects', title_x=0.5)
    else:
        fig.update_layout(title='No objects detected', title_x=0.5)
    return fig


def path_to_indices(path):
    """From SVG path to numpy array of coordinates, each row being a (row, col) point
    """
    indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in path.split("L")]
    return np.rint(np.array(indices_str, dtype=float)).astype(np.int32)


def path_to_mask(path, shape):
    """From SVG path to a boolean array where all pixels enclosed by the path
    are True, and the other pixels are False.
    """
    cols, rows = path_to_indices(path).T
    rr, cc = draw.polygon(rows, cols)
    mask = np.zeros(shape, dtype=np.bool_)
    mask[rr, cc] = True
    mask = ndimage.binary_fill_holes(mask)
    return mask


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH GENERATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def empty_figure(message="Select options to visualize"):
    """Return a placeholder figure with a centered message."""
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=15, color="#9e9e9e")
        )],
        paper_bgcolor='#fafafa',
        plot_bgcolor='#fafafa',

        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def make_stimulus_figure(db_name, stimulus, aoi_list, aoi_type_val):
    """Stimulus image with AOI drawing tools and existing shapes rendered."""
    img = np.array(FixaTons.get.stimulus(db_name, stimulus))
    if img.ndim == 3 and img.shape[2] == 4:
        img = img[..., :3]
    fig = px.imshow(img)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        dragmode="drawrect",
        newshape=dict(fillcolor="cyan", opacity=0.3, line=dict(color="darkblue", width=8)),
        margin=dict(l=0, r=0, t=35, b=0),
        title="Stimulus — Draw AOI regions",
        title_x=0.5, title_font_size=13,

    )
    # Render existing AOI shapes
    for aoi_item in aoi_list:
        if aoi_type_val == 'rect' and isinstance(aoi_item, list) and len(aoi_item) == 4:
            x0, y0, x1, y1 = aoi_item
            fig.add_shape(type='rect', x0=x0, y0=y0, x1=x1, y1=y1,
                          fillcolor="cyan", opacity=0.3,
                          line=dict(color="darkblue", width=4))
        else:
            try:
                pts = np.array(aoi_item)
                path_str = "M" + "L".join([f"{p[0]},{p[1]}" for p in pts]) + "Z"
                fig.add_shape(type='path', path=path_str,
                              fillcolor="cyan", opacity=0.3,
                              line=dict(color="darkblue", width=4))
            except Exception:
                pass
    return fig


def make_scanpath_figure(db_name, stimulus, participants, aoi_list, aoi_type_val):
    """Multi-user animated scanpath overlaid on the stimulus image."""
    image_width, image_height = FixaTons.get.stimulus_size(db_name, stimulus)
    encoded_string = FixaTons.get.stimulus_base64_encoding(db_name, stimulus)
    image_url = f'data:image/png;base64,{encoded_string}'

    df = FixaTons.get.scanpath_aoi(db_name, stimulus, participants, aoi_list, aoi_type_val)
    df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]
    # Resample for synchronized multi-user animation (includes interpolation and BUBBLE_SIZE=15)
    df = sc.resample_scanpaths(df, fps=10)

    fig = px.scatter(df, x="X", y="Y", animation_frame="FRAME_TIME",
                     animation_group="SUBJECT",
                     size="BUBBLE_SIZE", color="SUBJECT", hover_name="SUBJECT",
                     size_max=15,
                     range_x=[0, image_width], range_y=[0, image_height])
    fig.update_traces(marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    fig.add_layout_image(source=image_url, xref="x", yref="y", x=0, y=image_height,
                         sizex=image_width, sizey=image_height,
                         sizing="stretch", opacity=1, layer="below")
    fig.update_xaxes(visible=False, constrain="domain")
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1, constrain="domain")
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=35, b=10),
        title=f"Scanpath Animation",
        title_x=0.5, title_font_size=13,

    )
    if fig.layout.sliders:
        fig.layout.sliders[0].pad = {"t": 20, "r": 10, "b": 10}
    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].pad = {"t": 20, "r": 10, "b": 10}
    return fig


def make_scanpath_overlay_figure(db_name, stimulus, participant, aoi_list, aoi_type_val):
    """Static scanpath overlay — numbered fixation circles (sized by dwell time)
    connected by directional arrows, drawn on top of the stimulus image."""
    img = np.array(FixaTons.get.stimulus(db_name, stimulus))
    if img.ndim == 3 and img.shape[2] == 4:
        img = img[..., :3]
    image_width, image_height = FixaTons.get.stimulus_size(db_name, stimulus)

    df = FixaTons.get.scanpath_aoi(db_name, stimulus, [participant], aoi_list, aoi_type_val)
    df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]

    fig = px.imshow(img)

    # ---------- arrows (connecting lines) ----------
    for i in range(len(df) - 1):
        x1, y1 = df.iloc[i]["X"], df.iloc[i]["Y"]
        x2, y2 = df.iloc[i + 1]["X"], df.iloc[i + 1]["Y"]
        fig.add_trace(
            go.Scatter(
                x=[x1, x2], y=[y1, y2],
                mode="lines",
                line=dict(color="blue", width=2),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # ---------- arrowheads (direction markers) ----------
    for i in range(1, len(df)):
        fig.add_trace(
            go.Scatter(
                x=[df.iloc[i]["X"]], y=[df.iloc[i]["Y"]],
                mode="markers",
                marker=dict(symbol="triangle-up", size=12, color="blue"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # ---------- numbered fixation circles ----------
    marker_sizes = np.clip(df["ELAPSED_TIME"] * 150, 12, 60)
    fig.add_trace(
        go.Scatter(
            x=df["X"], y=df["Y"],
            mode="markers+text",
            text=[str(i + 1) for i in range(len(df))],
            textposition="middle center",
            marker=dict(
                size=marker_sizes,
                color="red",
                opacity=0.6,
                line=dict(color="black", width=2),
            ),
            showlegend=False,
        )
    )

    fig.update_xaxes(visible=False, range=[0, image_width], constrain="domain")
    fig.update_yaxes(visible=False, range=[image_height, 0], scaleanchor="x", scaleratio=1, constrain="domain")
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=35, b=0),
        title=f"Scanpath Overlay — {participant}",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_attention_figure(db_name, stimulus, participants=None):
    """Attention heatmap overlaid on the stimulus image.
    Falls back to Gaussian fixation density when saliency maps are unavailable."""
    try:
        attention_img = FixaTons.show.attention_map(db_name, stimulus)
    except (FileNotFoundError, OSError, Exception):
        # Saliency maps not available — compute from scanpath fixations
        img = FixaTons.get.stimulus(db_name, stimulus)
        if participants:
            scanpath_dfs = []
            for p in participants:
                try:
                    sp = FixaTons.get.scanpath(db_name, stimulus, p)
                    df = pd.DataFrame(sp, columns=['X', 'Y', 'TIME_FROM', 'TIME_TO'])
                    df['SUBJECT'] = p
                    scanpath_dfs.append(df)
                except Exception:
                    pass
            if scanpath_dfs:
                attention_img = sc.compute_custom_attention_map(img, scanpath_dfs)
            else:
                attention_img = img
        else:
            attention_img = img
    fig = px.imshow(attention_img)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=35, b=0),
        title="Attention Map",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_scarf_figure(db_name, stimulus, participants, aoi_list, aoi_type_val):
    """Scarf plot showing AOI visits per participant over time."""
    df = FixaTons.get.scanpath_aoi(db_name, stimulus, participants, aoi_list, aoi_type_val)
    df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]
    df["AOI"] = df["AOI"].astype(str)

    fig = px.bar(df, x="TIME_FROM", y="SUBJECT", color="AOI",
                 color_discrete_sequence=px.colors.qualitative.Vivid,
                 hover_data=["SUBJECT", "AOI"], orientation='h')
    fig.update_yaxes(categoryorder='category ascending')
    fig.update_layout(
        margin=dict(l=0, r=0, t=35, b=0),
        title="Scarf Plot",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_timeline_figure(db_name, stimulus, participants, aoi_list, aoi_type_val):
    """Line plot of temporal AOI evolution across participants."""
    df = FixaTons.get.scanpath_aoi(db_name, stimulus, participants, aoi_list, aoi_type_val)
    df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]
    df["AOI"] = df["AOI"].astype(str)

    fig = px.line(df, x='TIME_FROM', y='AOI', color='SUBJECT')
    fig.update_layout(
        margin=dict(l=0, r=0, t=35, b=0),
        title="AOI Timeline",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_3d_scanpath_figure(db_name, stimulus, participants, aoi_list, aoi_type_val):
    """3D line plot with time on Z-axis, stimulus image as ground surface."""
    df = FixaTons.get.scanpath_aoi(db_name, stimulus, participants, aoi_list, aoi_type_val)
    df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]

    stimulus_image = FixaTons.get.stimulus(db_name, stimulus)
    eight_bit_img = Image.fromarray(stimulus_image).convert('P', palette='WEB', dither=None)
    z = np.zeros(stimulus_image.shape[:2])

    fig = px.line_3d(df, x="X", y="Y", z="TIME_FROM", color='SUBJECT')
    fig.add_surface(z=z, surfacecolor=np.flipud(eight_bit_img), showscale=False)
    camera = dict(up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=0),
                  eye=dict(x=-1.25, y=-1.25, z=0.5))
    fig.update_layout(
        scene_camera=camera,
        margin=dict(l=0, r=0, t=35, b=0),
        title="3D Scanpath",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_3d_scatter_figure(db_name, stimulus, participants, aoi_list, aoi_type_val):
    """3D scatter plot with fixation duration as bubble size."""
    df = FixaTons.get.scanpath_aoi(db_name, stimulus, participants, aoi_list, aoi_type_val)
    df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]

    stimulus_image = FixaTons.get.stimulus(db_name, stimulus)
    eight_bit_img = Image.fromarray(stimulus_image).convert('P', palette='WEB', dither=None)
    z = np.zeros(stimulus_image.shape[:2])

    fig = px.scatter_3d(df, x='X', y='Y', z='TIME_FROM',
                        color='SUBJECT', size='ELAPSED_TIME', size_max=18)
    fig.add_surface(z=z, surfacecolor=np.flipud(eight_bit_img), showscale=False)
    camera = dict(up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=0),
                  eye=dict(x=-1.25, y=-1.25, z=0.5))
    fig.update_layout(
        scene_camera=camera,
        margin=dict(l=0, r=0, t=35, b=0),
        title="3D Scatter",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_coassociation_figure(db_name, stimulus, participants):
    """Co-association matrix heatmap based on clustering similarity."""
    coa_matrix, coa_rows, coa_cols = compute_coa.compute_coasso(
        db_name, STIMULUS_SET=[stimulus], subjects=participants
    )

    if len(coa_rows) > 0:
        fig = px.imshow(
            np.array(coa_matrix),
            labels=dict(x="Subject", y="Subject"),
            x=coa_cols, y=coa_rows,
            color_continuous_scale='balance',
            range_color=[0, 1]
        )
    else:
        fig = empty_figure("No matching participants found in dataset")

    fig.update_layout(
        margin=dict(l=0, r=0, t=35, b=0),
        title="Co-association Matrix",
        title_x=0.5, title_font_size=13,

    )
    return fig


def make_detection_figure_wrapper(db_name, stimulus):
    """Object detection (YOLO) with fallback to semantic segmentation (SAM)."""
    img = np.array(FixaTons.get.stimulus(db_name, stimulus))
    if img.ndim == 3 and img.shape[2] == 4:
        img = img[..., :3]
    bgr_img = img.copy()
    if img.ndim == 3:
        try:
            bgr_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        except Exception:
            bgr_img = img.copy()
    elif img.ndim == 2:
        bgr_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    detections = detect_objects(bgr_img)

    if len(detections) > 0:
        fig = build_detection_figure(img, detections)
        fig.update_layout(title=f'Detected {len(detections)} object(s)', title_x=0.5)
    else:
        print(f'[app] No YOLO detections for {stimulus}; running semantic segmentation …')
        try:
            segments = sem_seg.run_segmentation(bgr_img, MODEL_DIR)
            fig = sem_seg.build_segmentation_figure(img, segments)
        except Exception as exc:
            print(f'[app] Segmentation error: {exc}')
            fig = empty_figure("Segmentation unavailable")

    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig


def make_transition_figure(db_name, stimulus, aoi_list, aoi_type_val):
    """AOI transition probability matrix."""
    df_transition = FixaTons.stats.AOI_transition_matrix(db_name, stimulus, aoi_list, aoi_type_val)
    z_mat = np.array(df_transition)
    labels = df_transition.columns.values

    fig = px.imshow(z_mat, text_auto=True, x=labels, y=labels,
                    labels=dict(x="AOI", y="AOI"), range_color=[0, 1],
                    color_continuous_scale='balance')
    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
        yaxis=dict(tickmode='linear', tick0=0, dtick=1),
        margin=dict(l=0, r=0, t=35, b=0),
        title="AOI Transition Matrix",
        title_x=0.5, title_font_size=13,

    )
    return fig


def generate_figure(plot_type, db_name, stimulus, participants, aoi_list, aoi_type_val):
    """Master dispatcher — route to the correct graph generator."""
    if not db_name or not stimulus:
        return empty_figure("Select a dataset and stimulus to begin")

    try:
        if plot_type == 'stimulus':
            return make_stimulus_figure(db_name, stimulus, aoi_list, aoi_type_val)

        elif plot_type == 'scanpath':
            if not participants or len(participants) == 0:
                return empty_figure("Select at least one participant")
            return make_scanpath_figure(db_name, stimulus, participants, aoi_list, aoi_type_val)

        elif plot_type == 'scanpath_overlay':
            if not participants or len(participants) == 0:
                return empty_figure("Select at least one participant")
            return make_scanpath_overlay_figure(db_name, stimulus, participants[0], aoi_list, aoi_type_val)

        elif plot_type == 'attention':
            return make_attention_figure(db_name, stimulus, participants)

        elif plot_type == 'scarf':
            if not participants or len(participants) == 0:
                return empty_figure("Select participants for scarf plot")
            return make_scarf_figure(db_name, stimulus, participants, aoi_list, aoi_type_val)

        elif plot_type == 'aoi_timeline':
            if not participants or len(participants) == 0:
                return empty_figure("Select participants for AOI timeline")
            return make_timeline_figure(db_name, stimulus, participants, aoi_list, aoi_type_val)

        elif plot_type == '3d_scanpath':
            if not participants or len(participants) == 0:
                return empty_figure("Select participants for 3D scanpath")
            return make_3d_scanpath_figure(db_name, stimulus, participants, aoi_list, aoi_type_val)

        elif plot_type == '3d_scatter':
            if not participants or len(participants) == 0:
                return empty_figure("Select participants for 3D scatter")
            return make_3d_scatter_figure(db_name, stimulus, participants, aoi_list, aoi_type_val)

        elif plot_type == 'coassociation':
            if not participants or len(participants) < 2:
                return empty_figure("Select at least 2 participants")
            return make_coassociation_figure(db_name, stimulus, participants)

        elif plot_type == 'detection':
            return make_detection_figure_wrapper(db_name, stimulus)

        elif plot_type == 'transition':
            if not aoi_list:
                return empty_figure("Draw AOI regions on the stimulus first")
            return make_transition_figure(db_name, stimulus, aoi_list, aoi_type_val)

        else:
            return empty_figure(f"Unknown plot type: {plot_type}")

    except Exception as e:
        print(f"[app] Error generating {plot_type}: {e}")
        return empty_figure(f"Error: {str(e)}")


def _decode_custom_image(custom_image_store):
    """Decode custom image from store data to numpy array and metadata."""
    if not custom_image_store or not custom_image_store.get('b64'):
        return None, custom_image_store.get('width', 1920) if custom_image_store else 1920, custom_image_store.get('height', 1080) if custom_image_store else 1080, custom_image_store.get('url') if custom_image_store else None
        
    b64 = custom_image_store['b64']
    decoded = base64.b64decode(b64)
    img = Image.open(io.BytesIO(decoded)).convert('RGB')
    img_array = np.array(img)
    width = custom_image_store.get('width', img.width)
    height = custom_image_store.get('height', img.height)
    content_type = custom_image_store.get('content_type', 'data:image/png;base64')
    image_url = f'{content_type},{b64}'
    return img_array, width, height, image_url


def _get_custom_scanpath_dfs(custom_scanpaths_store, participants, custom_image_store=None, override_dfs=None, auto_scale_w_h=None):
    """Deserialize selected participants' DataFrames from the store (or override_dfs) and filter by keyframe time window if active."""
    dfs = []

    kf_start = None
    kf_end = None
    if custom_image_store and isinstance(custom_image_store, dict):
        kf_start = custom_image_store.get('keyframe_time_start')
        kf_end = custom_image_store.get('keyframe_time_end')
        
        # Fallback to image dimensions if auto_scale_w_h not explicitly provided
        if not auto_scale_w_h:
            w = custom_image_store.get('width')
            h = custom_image_store.get('height')
            if w and h:
                auto_scale_w_h = (w, h)

    store = json.loads(custom_scanpaths_store) if custom_scanpaths_store else {}

    for p in (participants or []):
        df = None
        if override_dfs is not None and p in override_dfs:
            df = override_dfs[p].copy()
        elif p in store and store[p] != 'k':
            try:
                df = pd.read_json(io.StringIO(store[p]), orient='split')
            except Exception:
                continue
                
        if df is None or df.empty:
            continue

        if kf_start is not None:
            max_t = df['TIME_TO'].max() if not df.empty else 0
            # Smart time unit detection:
            # If scanpath max_t is > 50 and keyframe start is in seconds, scanpath is in ms
            scale = 1000.0 if (max_t > 50.0 and kf_start < 50.0) else 1.0

            t0 = kf_start * scale
            t1 = kf_end * scale if kf_end is not None else None

            # Step 1: Strict time window filter
            if t1 is not None:
                filtered_df = df[(df['TIME_TO'] >= t0) & (df['TIME_FROM'] <= t1)].copy()
            else:
                filtered_df = df[df['TIME_TO'] >= t0].copy()

            # Step 2: Fallback - Fixation active AT t0
            if filtered_df.empty and not df.empty:
                active_at_t0 = df[(df['TIME_FROM'] <= t0) & (df['TIME_TO'] >= t0)]
                if not active_at_t0.empty:
                    filtered_df = active_at_t0.copy()

            # Step 3: Fallback - Most recent fixation up to t0 (or t1)
            if filtered_df.empty and not df.empty:
                target_time = t1 if t1 is not None else t0
                up_to_target = df[df['TIME_FROM'] <= target_time]
                if not up_to_target.empty:
                    filtered_df = up_to_target.tail(1).copy()
                else:
                    filtered_df = df.head(1).copy()

            df = filtered_df

        if not df.empty:
            dfs.append(df)
            
    # Auto-scale percentages to pixels if requested and detected
    if auto_scale_w_h:
        w, h = auto_scale_w_h
        if w and h and w > 200 and h > 200:
            for i, df in enumerate(dfs):
                if not df.empty and df['X'].max() <= 100.01 and df['Y'].max() <= 100.01:
                    scaled = df.copy()
                    scaled['X'] = scaled['X'] / 100.0 * w
                    scaled['Y'] = scaled['Y'] / 100.0 * h
                    dfs[i] = scaled

    return dfs


def generate_figure_custom(plot_type, custom_image_store, custom_scanpaths_store,
                           participants, aoi_list, aoi_type_val, override_dfs=None):
    """Master dispatcher for custom-mode — uses uploaded data instead of FixaTons."""
    if not custom_image_store:
        return empty_figure("Upload a stimulus image to begin")

    try:
        img_array, image_width, image_height, image_url = _decode_custom_image(
            custom_image_store)

        # ── Stimulus ──
        if plot_type == 'stimulus':
            if img_array is not None:
                fig = px.imshow(img_array)
                fig.update_xaxes(visible=False)
                fig.update_yaxes(visible=False)
            elif image_url:
                fig = go.Figure()
                fig.add_layout_image(
                    source=image_url,
                    xref="x", yref="y", x=0, y=0,
                    sizex=image_width, sizey=image_height,
                    sizing="stretch", layer="below"
                )
                fig.update_xaxes(visible=False, range=[0, image_width])
                fig.update_yaxes(visible=False, range=[image_height, 0], scaleanchor="x", scaleratio=1)
            else:
                return empty_figure("No image available")
                
            fig.update_layout(
                dragmode="drawrect",
                newshape=dict(fillcolor="cyan", opacity=0.3,
                              line=dict(color="darkblue", width=8)),
                margin=dict(l=0, r=0, t=35, b=0),
                title="Stimulus — Draw AOI regions",
                title_x=0.5, title_font_size=13,
            )
            for aoi_item in aoi_list:
                if aoi_type_val == 'rect' and isinstance(aoi_item, list) and len(aoi_item) == 4:
                    x0, y0, x1, y1 = aoi_item
                    fig.add_shape(type='rect', x0=x0, y0=y0, x1=x1, y1=y1,
                                  fillcolor="cyan", opacity=0.3,
                                  line=dict(color="darkblue", width=4))
                else:
                    try:
                        pts = np.array(aoi_item)
                        path_str = "M" + "L".join(
                            [f"{p[0]},{p[1]}" for p in pts]) + "Z"
                        fig.add_shape(type='path', path=path_str,
                                      fillcolor="cyan", opacity=0.3,
                                      line=dict(color="darkblue", width=4))
                    except Exception:
                        pass
            return fig

        # ── Scanpath Animation ──
        elif plot_type == 'scanpath':
            if not participants or (not custom_scanpaths_store and not override_dfs):
                return empty_figure("Upload scanpath files and select participants")
            dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, participants, custom_image_store, override_dfs=override_dfs)
            if not dfs:
                return empty_figure("No data for selected participants")
            
            combined = pd.concat(dfs, ignore_index=True)
            combined = sc.assign_aoi(combined, aoi_list, aoi_type_val)
            combined["ELAPSED_TIME"] = combined["TIME_TO"] - combined["TIME_FROM"]

            # Normalize to seconds if timestamps are in milliseconds
            # resample_scanpaths uses 1/fps (0.1s) step — only correct for second-based data
            max_t = combined['TIME_TO'].max() if not combined.empty else 0
            if max_t > 50.0:
                combined['TIME_FROM'] = combined['TIME_FROM'] / 1000.0
                combined['TIME_TO'] = combined['TIME_TO'] / 1000.0
                combined['ELAPSED_TIME'] = combined['ELAPSED_TIME'] / 1000.0

            # Use keyframe time bounds for animation range (if video frame selected)
            anim_start = None
            anim_end = None
            if custom_image_store and isinstance(custom_image_store, dict):
                anim_start = custom_image_store.get('keyframe_time_start')
                anim_end = custom_image_store.get('keyframe_time_end')

            # Resample for synchronized multi-user animation (includes interpolation and BUBBLE_SIZE=15)
            combined = sc.resample_scanpaths(combined, fps=10,
                                             time_start=anim_start,
                                             time_end=anim_end)

            fig = px.scatter(combined, x="X", y="Y", animation_frame="FRAME_TIME",
                             animation_group="SUBJECT",
                             size="BUBBLE_SIZE", color="SUBJECT", hover_name="SUBJECT",
                             size_max=15,
                             range_x=[0, image_width], range_y=[0, image_height])
            fig.update_traces(marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
            fig.add_layout_image(source=image_url, xref="x", yref="y",
                                 x=0, y=image_height,
                                 sizex=image_width, sizey=image_height,
                                 sizing="stretch", opacity=1, layer="below")
            fig.update_xaxes(visible=False, constrain="domain")
            fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1, constrain="domain")
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=35, b=10),
                title=f"Scanpath Animation",
                title_x=0.5, title_font_size=13,

            )
            if fig.layout.sliders:
                fig.layout.sliders[0].pad = {"t": 20, "r": 10, "b": 10}
            if fig.layout.updatemenus:
                fig.layout.updatemenus[0].pad = {"t": 20, "r": 10, "b": 10}
            return fig

        # ── Scanpath Overlay ──
        elif plot_type == 'scanpath_overlay':
            if img_array is None:
                return empty_figure("Scanpath overlay requires an uploaded image.")
            if not participants or (not custom_scanpaths_store and not override_dfs):
                return empty_figure("Upload scanpath files and select a participant")
            dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, [participants[0]], custom_image_store, override_dfs=override_dfs)
            if not dfs:
                return empty_figure("No data for selected participant")
            df = sc.assign_aoi(dfs[0], aoi_list, aoi_type_val)
            df["ELAPSED_TIME"] = df["TIME_TO"] - df["TIME_FROM"]
            fig = px.imshow(img_array)
            for i in range(len(df) - 1):
                x1, y1 = df.iloc[i]["X"], df.iloc[i]["Y"]
                x2, y2 = df.iloc[i + 1]["X"], df.iloc[i + 1]["Y"]
                fig.add_trace(go.Scatter(
                    x=[x1, x2], y=[y1, y2], mode="lines",
                    line=dict(color="blue", width=2),
                    hoverinfo="skip", showlegend=False))
            for i in range(1, len(df)):
                fig.add_trace(go.Scatter(
                    x=[df.iloc[i]["X"]], y=[df.iloc[i]["Y"]],
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=12, color="blue"),
                    hoverinfo="skip", showlegend=False))
            marker_sizes = np.clip(df["ELAPSED_TIME"] * 150, 12, 60)
            fig.add_trace(go.Scatter(
                x=df["X"], y=df["Y"], mode="markers+text",
                text=[str(i + 1) for i in range(len(df))],
                textposition="middle center",
                marker=dict(size=marker_sizes, color="red", opacity=0.6,
                            line=dict(color="black", width=2)),
                showlegend=False))
            fig.update_xaxes(visible=False, range=[0, image_width], constrain="domain")
            fig.update_yaxes(visible=False, range=[image_height, 0],
                             scaleanchor="x", scaleratio=1, constrain="domain")
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=35, b=0),
                title=f"Scanpath Overlay — {participants[0]}",
                title_x=0.5, title_font_size=13,

            )
            return fig

        # ── Attention Map ──
        elif plot_type == 'attention':
            if img_array is None:
                return empty_figure("Attention map requires an uploaded image.")
            if not custom_scanpaths_store and not override_dfs:
                return empty_figure("Upload scanpath files for attention map")
            parts_to_use = list(override_dfs.keys()) if override_dfs else list(json.loads(custom_scanpaths_store).keys())
            all_dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, parts_to_use, custom_image_store, override_dfs=override_dfs)
            if not all_dfs:
                return empty_figure("No data available for attention map")
            attention_img = sc.compute_custom_attention_map(img_array, all_dfs)
            fig = px.imshow(attention_img)
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=35, b=0),
                title="Attention Map (Custom)", title_x=0.5,
                title_font_size=13,
            )
            return fig

        # ── Scarf Plot ──
        elif plot_type == 'scarf':
            if not participants or (not custom_scanpaths_store and not override_dfs):
                return empty_figure("Select participants for scarf plot")
            dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, participants, custom_image_store, override_dfs=override_dfs)
            if not dfs:
                return empty_figure("No data for selected participants")
            combined = pd.concat(dfs, ignore_index=True)
            combined = sc.assign_aoi(combined, aoi_list, aoi_type_val)
            combined["ELAPSED_TIME"] = combined["TIME_TO"] - combined["TIME_FROM"]
            combined["AOI"] = combined["AOI"].astype(str)
            fig = px.bar(combined, x="TIME_FROM", y="SUBJECT", color="AOI",
                         color_discrete_sequence=px.colors.qualitative.Vivid,
                         hover_data=["SUBJECT", "AOI"], orientation='h')
            fig.update_yaxes(categoryorder='category ascending')
            fig.update_layout(
                margin=dict(l=0, r=0, t=35, b=0),
                title="Scarf Plot", title_x=0.5, title_font_size=13,

            )
            return fig

        # ── AOI Timeline ──
        elif plot_type == 'aoi_timeline':
            if not participants or (not custom_scanpaths_store and not override_dfs):
                return empty_figure("Select participants for AOI timeline")
            dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, participants, custom_image_store, override_dfs=override_dfs)
            if not dfs:
                return empty_figure("No data for selected participants")
            combined = pd.concat(dfs, ignore_index=True)
            combined = sc.assign_aoi(combined, aoi_list, aoi_type_val)
            combined["AOI"] = combined["AOI"].astype(str)
            fig = px.line(combined, x='TIME_FROM', y='AOI', color='SUBJECT')
            fig.update_layout(
                margin=dict(l=0, r=0, t=35, b=0),
                title="AOI Timeline", title_x=0.5, title_font_size=13,

            )
            return fig

        # ── 3D Scanpath ──
        elif plot_type == '3d_scanpath':
            if not participants or (not override_dfs and not custom_scanpaths_store):
                return empty_figure("Select participants for 3D scanpath")
            dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, participants, custom_image_store, override_dfs=override_dfs)
            if not dfs:
                return empty_figure("No data for selected participants")
            combined = pd.concat(dfs, ignore_index=True)
            combined = sc.assign_aoi(combined, aoi_list, aoi_type_val)
            combined["ELAPSED_TIME"] = combined["TIME_TO"] - combined["TIME_FROM"]
            eight_bit_img = Image.fromarray(img_array).convert(
                'P', palette='WEB', dither=None)
            z = np.zeros(img_array.shape[:2])
            fig = px.line_3d(combined, x="X", y="Y", z="TIME_FROM",
                             color='SUBJECT')
            fig.add_surface(z=z, surfacecolor=np.flipud(eight_bit_img),
                            showscale=False)
            camera = dict(up=dict(x=0, y=0, z=1),
                          center=dict(x=0, y=0, z=0),
                          eye=dict(x=-1.25, y=-1.25, z=0.5))
            fig.update_layout(
                scene_camera=camera,
                margin=dict(l=0, r=0, t=35, b=0),
                title="3D Scanpath", title_x=0.5, title_font_size=13,

            )
            return fig

        # ── 3D Scatter ──
        elif plot_type == '3d_scatter':
            if not participants or (not override_dfs and not custom_scanpaths_store):
                return empty_figure("Select participants for 3D scatter")
            dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, participants, custom_image_store, override_dfs=override_dfs)
            if not dfs:
                return empty_figure("No data for selected participants")
            combined = pd.concat(dfs, ignore_index=True)
            combined = sc.assign_aoi(combined, aoi_list, aoi_type_val)
            combined["ELAPSED_TIME"] = combined["TIME_TO"] - combined["TIME_FROM"]
            eight_bit_img = Image.fromarray(img_array).convert(
                'P', palette='WEB', dither=None)
            z = np.zeros(img_array.shape[:2])
            fig = px.scatter_3d(combined, x='X', y='Y', z='TIME_FROM',
                                color='SUBJECT', size='ELAPSED_TIME',
                                size_max=18)
            fig.add_surface(z=z, surfacecolor=np.flipud(eight_bit_img),
                            showscale=False)
            camera = dict(up=dict(x=0, y=0, z=1),
                          center=dict(x=0, y=0, z=0),
                          eye=dict(x=-1.25, y=-1.25, z=0.5))
            fig.update_layout(
                scene_camera=camera,
                margin=dict(l=0, r=0, t=35, b=0),
                title="3D Scatter", title_x=0.5, title_font_size=13,

            )
            return fig

        # ── Co-association (disabled in custom mode) ──
        elif plot_type == 'coassociation':
            return empty_figure("Co-association Matrix is not available "
                                "in custom data mode")

        # ── Object Detection ──
        elif plot_type == 'detection':
            if img_array.ndim == 3 and img_array.shape[2] == 4:
                img_array = img_array[..., :3]
            bgr_img = img_array.copy()
            if img_array.ndim == 3:
                try:
                    bgr_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                except Exception:
                    pass
            elif img_array.ndim == 2:
                bgr_img = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            detections = detect_objects(bgr_img)
            if len(detections) > 0:
                fig = build_detection_figure(img_array, detections)
            else:
                try:
                    segments = sem_seg.run_segmentation(bgr_img, MODEL_DIR)
                    fig = sem_seg.build_segmentation_figure(img_array, segments)
                except Exception:
                    fig = empty_figure("No objects detected / segmentation unavailable")
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            return fig

        # ── Transition Matrix ──
        elif plot_type == 'transition':
            if not aoi_list:
                return empty_figure("Draw AOI regions on the stimulus first")
            if not override_dfs and not custom_scanpaths_store:
                return empty_figure("Upload scanpath files first")
            if override_dfs:
                all_dfs = [df for p, df in override_dfs.items() if str(p) in [str(x) for x in participants]]
            else:
                store = json.loads(custom_scanpaths_store)
                all_dfs = _get_custom_scanpath_dfs(custom_scanpaths_store, list(store.keys()), custom_image_store)
            if not all_dfs:
                return empty_figure("No transitions found")
            df_transition = sc.compute_custom_transition_matrix(
                all_dfs, aoi_list, aoi_type_val)
            if df_transition.empty:
                return empty_figure("No transitions found")
            z_mat = np.array(df_transition)
            labels = [str(c) for c in df_transition.columns]
            fig = px.imshow(z_mat, text_auto=True, x=labels, y=labels,
                            labels=dict(x="AOI", y="AOI"), range_color=[0, 1],
                            color_continuous_scale='balance')
            fig.update_layout(
                xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                yaxis=dict(tickmode='linear', tick0=0, dtick=1),
                margin=dict(l=0, r=0, t=35, b=0),
                title="AOI Transition Matrix", title_x=0.5,
                title_font_size=13,
            )
            return fig

        else:
            return empty_figure(f"Unknown plot type: {plot_type}")

    except Exception as e:
        print(f"[app] Error generating custom {plot_type}: {e}")
        return empty_figure(f"Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def make_icon_button(panel, pt):
    """Create a single icon button for the sidebar."""
    css_class = 'icon-btn' if panel == 'left' else 'icon-btn icon-btn-right'
    return html.Button(
        html.I(className=f"bi {pt['icon']}"),
        id={'type': f'{panel}-icon', 'plot': pt['value']},
        className=css_class,
        title=pt['label'],
        n_clicks=0,
    )


def make_sidebar():
    """Build the icon sidebar with LEFT and RIGHT sections."""
    return html.Div([
        # Logo / branding
        html.Div(
            html.Span('👁', style={'fontSize': '26px'}),
            style={'textAlign': 'center', 'padding': '14px 0 6px'}
        ),
        html.Hr(style={'margin': '0 10px 6px', 'borderColor': '#e0e0e0'}),

        # ---- LEFT PANEL icons ----
        html.Div('LEFT', style={
            'textAlign': 'center', 'fontSize': '9px', 'fontWeight': '800',
            'color': '#3f51b5', 'letterSpacing': '1.5px', 'padding': '4px 0 2px',
        }),
        *[make_icon_button('left', pt) for pt in PLOT_TYPES],

        html.Hr(style={'margin': '6px 10px', 'borderColor': '#e0e0e0'}),

        # ---- RIGHT PANEL icons ----
        html.Div('RIGHT', style={
            'textAlign': 'center', 'fontSize': '9px', 'fontWeight': '800',
            'color': '#e53935', 'letterSpacing': '1.5px', 'padding': '4px 0 2px',
        }),
        *[make_icon_button('right', pt) for pt in PLOT_TYPES],

    ], className='sidebar-scroll', style={
        'width': '62px',
        'minWidth': '62px',
        'background': '#fafbfc',
        'borderRight': '1px solid #e0e0e0',
        'overflowY': 'auto',
        'flexShrink': 0,
        'paddingBottom': '16px',
    })


GRAPH_CONFIG = {
    "modeBarButtonsToAdd": ["drawclosedpath", "drawrect"],
    "displaylogo": False,
}


# ═══════════════════════════════════════════════════════════════════════════════
# APP INITIALIZATION & LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

BOOTSTRAP_ICONS_CSS = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, BOOTSTRAP_ICONS_CSS],
    suppress_callback_exceptions=True
)

app.layout = html.Div([
    # Injected CSS


    # Data stores
    dcc.Store(id='aoi-store', data=0),
    dcc.Store(id='data-source-mode', data='builtin'),
    dcc.Store(id='custom-image-store'),
    dcc.Store(id='custom-scanpaths-store'),
    dcc.Store(id='custom-raw-scanpaths-store'),
    dcc.ConfirmDialog(id='aoi-error-dialog', message=""),

    # ──── Top Navbar ────
    html.Div([
        html.Div([
            html.Span('👁', style={'fontSize': '24px', 'marginRight': '8px'}),
            html.Span('EyeExplore', style={
                'fontSize': '20px', 'fontWeight': '700', 'letterSpacing': '0.5px'
            }),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Span('Visual Eyetracking Dashboard', style={
            'fontSize': '13px', 'opacity': '0.85', 'letterSpacing': '0.5px',
        }),
    ], style={
        'background': 'linear-gradient(135deg, #3f51b5, #1a237e)',
        'color': 'white',
        'padding': '12px 24px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'space-between',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.15)',
        'zIndex': '100',
        'position': 'relative',
    }),

    # ──── Main Body: Content ────
    html.Div([

        # Content area
        html.Div([

            # ── Controls bar ──
            html.Div([
                # Mode toggle
                upload_panel.make_mode_toggle(),

                # Built-in controls (shown by default)
                html.Div([
                    # Dataset
                    html.Div([
                        html.Label('Dataset', className='control-label'),
                        dcc.Dropdown(
                            id='ddDB',
                            options=[{'label': n, 'value': n} for n in datasets_list],
                            value=datasets_list[0] if datasets_list else None,
                            clearable=False,
                            style={'fontSize': '13px'},
                        ),
                    ], style={'flex': '1', 'minWidth': '140px'}),

                    # Stimulus
                    html.Div([
                        html.Label('Stimulus', className='control-label'),
                        dcc.Dropdown(id='image-dropdown', style={'fontSize': '13px'}),
                    ], style={'flex': '1', 'minWidth': '160px'}),
                ], id='builtin-controls-container', style={'display': 'contents'}),

                # Custom controls (hidden by default)
                upload_panel.make_custom_controls(),
                
                # K-Dataset controls (hidden by default)
                html.Div([
                    html.Div([
                        html.Label('Video', className='control-label'),
                        dcc.Dropdown(
                            id='k-video-dropdown',
                            options=[{'label': str(p), 'value': str(p)} for p in k_dataset.K_PARTICIPANTS],
                            value=str(k_dataset.K_PARTICIPANTS[0]) if k_dataset.K_PARTICIPANTS else None,
                            placeholder='Select a video...',
                            clearable=False,
                            style={'fontSize': '13px'}
                        ),
                    ], style={'flex': '1', 'minWidth': '160px'}),
                    html.Div([
                        html.Label('Key Frames', className='control-label'),
                        dcc.Dropdown(
                            id='k-keyframe-dropdown',
                            placeholder='Select a key frame...',
                            clearable=True,
                            style={'fontSize': '13px'}
                        ),
                    ], style={'flex': '1', 'minWidth': '160px'}),
                    dcc.Store(id='k-keyframes-store'),
                    dcc.Store(id='k-image-store'),
                    html.Div(id='k-fixation-data', style={'display': 'none'}),
                    dcc.Store(id='custom-video-store')
                ], id='k-controls-container', style={'display': 'none', 'flex': '1', 'minWidth': '320px', 'gap': '10px'}),

                # Key Frames dropdown (shown only when video is uploaded in custom mode)
                html.Div([
                    html.Label('Key Frames', className='control-label'),
                    dcc.Dropdown(
                        id='keyframe-dropdown',
                        placeholder='Select a key frame...',
                        clearable=True,
                        style={'fontSize': '13px'},
                    ),
                ], id='keyframe-dropdown-container', style={
                    'display': 'none', 'flex': '1', 'minWidth': '160px'
                }),



                # AOI controls
                html.Div([
                    html.Div([
                        html.Span('AOIs: ', style={'fontSize': '12px', 'color': '#555', 'fontWeight': '600'}),
                        html.Span(id='aoi-count-badge', children='0', className='aoi-badge'),
                    ], style={'marginBottom': '6px'}),
                    html.Button('Clear AOIs', id='btn-clear-aoi', n_clicks=0,
                                className='btn-clear-aoi'),
                ], style={'minWidth': '100px', 'display': 'flex', 'flexDirection': 'column',
                          'justifyContent': 'center'}),

            ], style={
                'display': 'flex',
                'gap': '16px',
                'alignItems': 'flex-end',
                'padding': '14px 20px',
                'background': 'white',
                'borderBottom': '1px solid #e0e0e0',
                'flexWrap': 'wrap',
            }),

            # ── Column Mapping Panel (custom mode) ──
            upload_panel.make_mapping_panel(),

            # ── Split Panels ──
            html.Div([
                
                # (K-Dataset video panel removed)
                # ──── LEFT PANEL ────
                html.Div([
                    # Panel header
                    html.Div([
                        html.Span('LEFT PANEL', style={'flexShrink': '0'}),
                        dcc.Dropdown(
                            id='left-plot-type',
                            options=DROPDOWN_OPTIONS,
                            value='stimulus',
                            clearable=False,
                            style={'flex': '1', 'fontSize': '12px', 'minWidth': '140px'},
                        ),
                    ], className='panel-header-left'),
                    # Per-panel participants
                    html.Div([
                        html.Label('Participants', style={'fontSize': '11px', 'fontWeight': '600', 'color': '#3f51b5', 'marginRight': '6px', 'whiteSpace': 'nowrap'}),
                        dcc.Dropdown(id='ddParticipants-left', multi=True, style={'fontSize': '12px', 'flex': '1'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '4px 10px', 'gap': '6px', 'borderBottom': '1px solid #e8e8e8', 'background': '#f8f9ff'}),

                    # Video player container (hidden by default, shown for k_video)
                    html.Div([
                        html.Video(
                            id='k-video-player',
                            controls=True,
                            style={'width': '100%', 'height': '100%', 'objectFit': 'contain',
                                   'backgroundColor': '#000', 'borderRadius': '6px'},
                        ),
                        # Fixation dot overlay
                        html.Div(id='k-fixation-dot', style={
                            'position': 'absolute',
                            'width': '16px', 'height': '16px',
                            'borderRadius': '50%',
                            'backgroundColor': 'rgba(59, 130, 246, 0.9)',
                            'border': '2px solid white',
                            'boxShadow': '0 0 8px rgba(0,0,0,0.5)',
                            'pointerEvents': 'none',
                            'transform': 'translate(-50%, -50%)',
                            'display': 'none',
                            'zIndex': '10',
                            'transition': 'left 0.08s linear, top 0.08s linear',
                        }),
                        # Trail dots container
                        html.Div(id='k-fixation-trail', style={
                            'position': 'absolute', 'top': '0', 'left': '0',
                            'width': '100%', 'height': '100%',
                            'pointerEvents': 'none', 'zIndex': '9',
                        }),
                    ], id='k-video-container', style={
                        'display': 'none', 'flex': '1', 'position': 'relative',
                        'overflow': 'hidden', 'margin': '4px',
                    }),

                    # Graph area
                    html.Div(
                        dcc.Loading(
                            dcc.Graph(id='left-graph',
                                      figure=empty_figure("Select a stimulus to begin"),
                                      config=GRAPH_CONFIG,
                                      responsive=True,
                                      style={'height': '100%', 'width': '100%'}),
                            type="cube", color="#3f51b5",
                            parent_style={'flex': '1', 'display': 'flex', 'flexDirection': 'column'}
                        ),
                        id='left-graph-container',
                        style={'flex': '1', 'overflow': 'auto', 'padding': '4px', 'display': 'flex', 'flexDirection': 'column'},
                    ),
                    html.Div(
                        [
                            html.Div("Animation Participants (Max 5)", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': '#555', 'marginBottom': '4px'}),
                            dcc.Checklist(id='left-anim-participants', inline=True, inputStyle={'marginRight': '4px', 'marginLeft': '8px'}, style={'fontSize': '12px'}),
                        ],
                        id='left-anim-participants-container',
                        style={'display': 'none'}
                    ),
                ], id='left-panel', className='panel-card', style={
                    'flex': 'var(--left-panel-flex, 1)', 'margin': '10px 0px 10px 10px',
                }),

                # ──── DRAG DIVIDER ────
                html.Div(id='drag-divider', style={
                    'width': '6px',
                    'cursor': 'col-resize',
                    'backgroundColor': '#e8e8e8',
                    'margin': '10px 5px',
                    'borderRadius': '3px',
                    'flexShrink': '0',
                    'zIndex': '10',
                    'transition': 'background-color 0.2s',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                }, children=[
                    html.Div(style={
                        'width': '2px',
                        'height': '30px',
                        'backgroundColor': '#ccc',
                        'borderRadius': '1px'
                    })
                ]),

                # ──── RIGHT PANEL ────
                html.Div([
                    # Panel header
                    html.Div([
                        html.Span('RIGHT PANEL', style={'flexShrink': '0'}),
                        dcc.Dropdown(
                            id='right-plot-type',
                            options=DROPDOWN_OPTIONS,
                            value='attention',
                            clearable=False,
                            style={'flex': '1', 'fontSize': '12px', 'minWidth': '140px'},
                        ),
                    ], className='panel-header-right'),
                    # Per-panel participants
                    html.Div([
                        html.Label('Participants', style={'fontSize': '11px', 'fontWeight': '600', 'color': '#e53935', 'marginRight': '6px', 'whiteSpace': 'nowrap'}),
                        dcc.Dropdown(id='ddParticipants-right', multi=True, style={'fontSize': '12px', 'flex': '1'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '4px 10px', 'gap': '6px', 'borderBottom': '1px solid #e8e8e8', 'background': '#fff8f8'}),

                    # Graph area
                    html.Div(
                        dcc.Loading(
                            dcc.Graph(id='right-graph',
                                      figure=empty_figure("Select a stimulus to begin"),
                                      config=GRAPH_CONFIG,
                                      responsive=True,
                                      style={'height': '100%', 'width': '100%'}),
                            type="cube", color="#e53935",
                            parent_style={'flex': '1', 'display': 'flex', 'flexDirection': 'column'}
                        ),
                        style={'flex': '1', 'overflow': 'auto', 'padding': '4px', 'display': 'flex', 'flexDirection': 'column'},
                    ),
                    html.Div(
                        [
                            html.Div("Animation Participants (Max 5)", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': '#555', 'marginBottom': '4px'}),
                            dcc.Checklist(id='right-anim-participants', inline=True, inputStyle={'marginRight': '4px', 'marginLeft': '8px'}, style={'fontSize': '12px'}),
                        ],
                        id='right-anim-participants-container',
                        style={'display': 'none'}
                    ),
                ], id='right-panel', className='panel-card', style={
                    'flex': 'var(--right-panel-flex, 1)', 'margin': '10px 10px 10px 0px',
                }),

            ], id='split-container', style={
                'display': 'flex',
                'flex': '1',
                'overflow': 'hidden',
            }),

        ], style={
            'flex': '1',
            'display': 'flex',
            'flexDirection': 'column',
            'overflow': 'hidden',
        }),

    ], style={
        'display': 'flex',
        'height': 'calc(100vh - 56px)',
        'overflow': 'hidden',
    }),
])


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. Dataset → Image dropdown options ──
@app.callback(
    Output('image-dropdown', 'options'),
    Input('ddDB', 'value'),
    State('data-source-mode', 'data'),
)
def update_image_dd(value, mode):
    if mode == 'custom' or not value:
        return []
    try:
        img_list = FixaTons.info.stimuli(value)
        return [{'label': i, 'value': i} for i in img_list] if img_list else []
    except Exception:
        return []


# ── 2. Image → Participants dropdown options (both panels) ──
@app.callback(
    Output('ddParticipants-left', 'options', allow_duplicate=True),
    Output('ddParticipants-right', 'options', allow_duplicate=True),
    [Input('image-dropdown', 'value'), Input('ddDB', 'value')],
    State('data-source-mode', 'data'),
    prevent_initial_call=True
)
def update_participants_options(stimulus, db, mode):
    if mode == 'custom':
        return dash.no_update, dash.no_update
    if not db or not stimulus:
        return [], []
    try:
        participants_list = FixaTons.info.subjects(db, stimulus)
        opts = [{'label': p, 'value': p} for p in participants_list] if participants_list else []
        return opts, opts
    except Exception:
        return [], []


# ── 3. Left icon click → Left plot type dropdown ──
@app.callback(
    Output('left-plot-type', 'value'),
    Input({'type': 'left-icon', 'plot': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def set_left_plot_type(n_clicks_list):
    if not any(n for n in n_clicks_list if n):
        raise dash.exceptions.PreventUpdate
    triggered = ctx.triggered_id
    if isinstance(triggered, dict) and 'plot' in triggered:
        return triggered['plot']
    raise dash.exceptions.PreventUpdate


# ── 4. Right icon click → Right plot type dropdown ──
@app.callback(
    Output('right-plot-type', 'value'),
    Input({'type': 'right-icon', 'plot': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def set_right_plot_type(n_clicks_list):
    if not any(n for n in n_clicks_list if n):
        raise dash.exceptions.PreventUpdate
    triggered = ctx.triggered_id
    if isinstance(triggered, dict) and 'plot' in triggered:
        return triggered['plot']
    raise dash.exceptions.PreventUpdate


# ── 5. AOI handling (shape drawing, clear, stimulus change) ──
@app.callback(
    Output('aoi-store', 'data'),
    Output('aoi-count-badge', 'children'),
    Output('aoi-error-dialog', 'displayed'),
    Output('aoi-error-dialog', 'message'),
    [Input('left-graph', 'relayoutData'),
     Input('right-graph', 'relayoutData'),
     Input('btn-clear-aoi', 'n_clicks'),
     Input('image-dropdown', 'value')],
    [State('aoi-store', 'data')],
    prevent_initial_call=True
)
def handle_aoi(left_relayout, right_relayout, clear_clicks, stimulus, aoi_counter):
    global AOI, AOI_type
    trigger = ctx.triggered_id
    counter = (aoi_counter or 0)

    # Clear all AOIs
    if trigger == 'btn-clear-aoi':
        AOI = []
        return counter + 1, '0', False, ''

    # Reset AOIs when stimulus changes
    if trigger == 'image-dropdown':
        AOI = []
        return counter + 1, '0', False, ''

    # Handle shape drawing from either graph
    relayout = None
    if trigger == 'left-graph':
        relayout = left_relayout
    elif trigger == 'right-graph':
        relayout = right_relayout

    if relayout and isinstance(relayout, dict) and "shapes" in relayout:
        shapes = relayout["shapes"]
        # Only process if more shapes than we already have (i.e., a new shape was drawn)
        if len(shapes) > len(AOI):
            last_shape = shapes[-1]
            
            def check_overlap(new_box):
                nx0, ny0, nx1, ny1 = new_box
                for exist in AOI:
                    if isinstance(exist, list) and len(exist) == 4:
                        ex0, ey0, ex1, ey1 = exist
                        ex0, ex1 = min(ex0, ex1), max(ex0, ex1)
                        ey0, ey1 = min(ey0, ey1), max(ey0, ey1)
                        if not (nx1 <= ex0 or nx0 >= ex1 or ny1 <= ey0 or ny0 >= ey1):
                            return True
                    else:
                        pts = np.array(exist)
                        if len(pts) > 0:
                            ex0, ex1 = pts[:,0].min(), pts[:,0].max()
                            ey0, ey1 = pts[:,1].min(), pts[:,1].max()
                            if not (nx1 <= ex0 or nx0 >= ex1 or ny1 <= ey0 or ny0 >= ey1):
                                return True
                return False

            if last_shape.get("type") == "rect":
                x0 = int(last_shape["x0"])
                y0 = int(last_shape["y0"])
                x1 = int(last_shape["x1"])
                y1 = int(last_shape["y1"])
                
                nx0, nx1 = min(x0, x1), max(x0, x1)
                ny0, ny1 = min(y0, y1), max(y0, y1)
                if check_overlap((nx0, ny0, nx1, ny1)):
                    return counter + 1, str(len(AOI)), True, "Error: Overlapping AOIs are not allowed."
                
                AOI.append([x0, y0, x1, y1])
                AOI_type = "rect"
            elif "path" in last_shape:
                indices = path_to_indices(last_shape["path"])
                pts = np.array(indices)
                if len(pts) > 0:
                    nx0, nx1 = pts[:,0].min(), pts[:,0].max()
                    ny0, ny1 = pts[:,1].min(), pts[:,1].max()
                    if check_overlap((nx0, ny0, nx1, ny1)):
                        return counter + 1, str(len(AOI)), True, "Error: Overlapping AOIs are not allowed."
                
                AOI.append(indices)
                AOI_type = "free"
            return counter + 1, str(len(AOI)), False, ""

    raise dash.exceptions.PreventUpdate


# ── 5b. Key Frames dropdown: populate options ──
@app.callback(
    Output('keyframe-dropdown', 'options'),
    Output('keyframe-dropdown', 'value'),
    Output('keyframe-dropdown-container', 'style'),
    Input('custom-keyframes-store', 'data'),
    Input('data-source-mode', 'data'),
    prevent_initial_call=True
)
def populate_keyframe_dropdown(keyframes_json, mode):
    if mode != 'custom' or not keyframes_json:
        return [], None, {'display': 'none', 'flex': '1', 'minWidth': '160px'}

    try:
        key_frames = json.loads(keyframes_json)
    except Exception:
        return [], None, {'display': 'none', 'flex': '1', 'minWidth': '160px'}

    if not key_frames:
        return [], None, {'display': 'none', 'flex': '1', 'minWidth': '160px'}

    options = []
    for i, kf in enumerate(key_frames):
        ts = kf['timestamp_sec']
        label = f"Frame {i+1} — {ts:.1f}s"
        options.append({'label': label, 'value': i})

    # Auto-select the first frame
    return options, 0, {'display': 'block', 'flex': '1', 'minWidth': '160px'}


# ── 5c. Key Frame selection → update custom-image-store ──
@app.callback(
    Output('custom-image-store', 'data', allow_duplicate=True),
    Input('keyframe-dropdown', 'value'),
    State('custom-keyframes-store', 'data'),
    prevent_initial_call=True
)
def update_image_from_keyframe(selected_idx, keyframes_json):
    if selected_idx is None or not keyframes_json:
        raise dash.exceptions.PreventUpdate

    try:
        key_frames = json.loads(keyframes_json)
        kf = key_frames[selected_idx]
        if selected_idx > 0:
            t_start = key_frames[selected_idx - 1]['timestamp_sec']
            t_end = kf['timestamp_sec']
        else:
            t_start = 0.0
            if kf['timestamp_sec'] > 0.0:
                t_end = kf['timestamp_sec']
            elif len(key_frames) > 1:
                t_end = key_frames[1]['timestamp_sec']
            else:
                t_end = None
    except (json.JSONDecodeError, IndexError, TypeError):
        raise dash.exceptions.PreventUpdate

    return {
        'b64': kf['image_b64'],
        'width': kf['width'],
        'height': kf['height'],
        'filename': f"Key Frame {selected_idx + 1} — {kf['timestamp_sec']:.1f}s",
        'content_type': 'data:image/jpeg;base64',
        'is_video_frame': True,
        'keyframe_time_start': t_start,
        'keyframe_time_end': t_end,
    }

# ── 5d. K-Dataset Video selection → populate keyframes store and filter participants ──
@app.callback(
    Output('k-keyframes-store', 'data'),
    Output('ddParticipants-left', 'options', allow_duplicate=True),
    Output('ddParticipants-left', 'value', allow_duplicate=True),
    Output('ddParticipants-right', 'options', allow_duplicate=True),
    Output('ddParticipants-right', 'value', allow_duplicate=True),
    Input('k-video-dropdown', 'value'),
    Input('data-source-mode', 'data'),
    prevent_initial_call=True
)
def handle_k_video_selection(pid, mode):
    if mode != 'k_dataset' or not pid:
        raise dash.exceptions.PreventUpdate

    import k_dataset
    import os
    import json
    
    participant_options = [{'label': str(pid), 'value': str(pid)}]
    participant_values = [str(pid)]
    
    kf_path = os.path.join(k_dataset.K_DATA_ROOT, str(pid), f"{pid}_keyframes.json")
    if os.path.exists(kf_path):
        with open(kf_path, 'r') as f:
            key_frames = json.load(f)
        # Only store metadata to avoid sending huge payload (22MB+) to the browser
        metadata = [{'timestamp_sec': k['timestamp_sec'], 'width': k.get('width', 1920), 'height': k.get('height', 1080)} for k in key_frames]
        keyframes_data = json.dumps(metadata)
    else:
        keyframes_data = "[]"
        
    return keyframes_data, participant_options, participant_values, participant_options, participant_values

# ── 5e. K-Dataset Keyframes dropdown: populate options ──
@app.callback(
    Output('k-keyframe-dropdown', 'options'),
    Output('k-keyframe-dropdown', 'value'),
    Input('k-keyframes-store', 'data'),
    State('data-source-mode', 'data'),
    prevent_initial_call=True
)
def populate_k_keyframe_dropdown(keyframes_json, mode):
    if mode != 'k_dataset' or not keyframes_json:
        return [], None
    try:
        import json
        key_frames = json.loads(keyframes_json)
    except Exception:
        return [], None
    if not key_frames:
        return [], None
    options = []
    for i, kf in enumerate(key_frames):
        ts = kf['timestamp_sec']
        label = f"Frame {i+1} — {ts:.1f}s"
        options.append({'label': label, 'value': i})
    return options, 0

# ── 5f. K-Dataset Key Frame selection → update k-image-store ──
@app.callback(
    Output('k-image-store', 'data', allow_duplicate=True),
    Input('k-keyframe-dropdown', 'value'),
    State('k-keyframes-store', 'data'),
    State('k-video-dropdown', 'value'),
    prevent_initial_call=True
)
def update_k_image_from_keyframe(selected_idx, keyframes_json, pid):
    if selected_idx is None or not keyframes_json or not pid:
        raise dash.exceptions.PreventUpdate
    try:
        import json
        import os
        import k_dataset
        
        # We need the base64 image, so we must load the original JSON from disk again
        kf_path = os.path.join(k_dataset.K_DATA_ROOT, str(pid), f"{pid}_keyframes.json")
        with open(kf_path, 'r') as f:
            full_key_frames = json.load(f)
            
        kf_full = full_key_frames[selected_idx]
        
        # Load metadata to find time bounds
        key_frames = json.loads(keyframes_json)
        kf_meta = key_frames[selected_idx]
        if selected_idx > 0:
            t_start = key_frames[selected_idx - 1]['timestamp_sec']
            t_end = kf_meta['timestamp_sec']
        else:
            t_start = 0.0
            if kf_meta['timestamp_sec'] > 0.0:
                t_end = kf_meta['timestamp_sec']
            elif len(key_frames) > 1:
                t_end = key_frames[1]['timestamp_sec']
            else:
                t_end = None
    except (json.JSONDecodeError, IndexError, TypeError, FileNotFoundError, Exception) as e:
        raise dash.exceptions.PreventUpdate

    return {
        'b64': kf_full['image_b64'],
        'width': kf_meta.get('width', 1920),
        'height': kf_meta.get('height', 1080),
        'filename': f"Key Frame {selected_idx + 1} — {kf_meta['timestamp_sec']:.1f}s",
        'content_type': 'data:image/jpeg;base64',
        'is_video_frame': True,
        'keyframe_time_start': t_start,
        'keyframe_time_end': t_end,
    }



# ── 6. Update LEFT panel graph ──
@app.callback(
    Output('left-graph', 'figure'),
    [Input('left-plot-type', 'value'),
     Input('ddDB', 'value'),
     Input('image-dropdown', 'value'),
     Input('ddParticipants-left', 'value'),
     Input('aoi-store', 'data'),
     Input('left-anim-participants', 'value'),
     Input('custom-image-store', 'data'),
     Input('k-image-store', 'data')],
    [State('data-source-mode', 'data'),
     State('custom-scanpaths-store', 'data')],
    prevent_initial_call=True
)
def update_left_graph(plot_type, db_name, stimulus, participants, _aoi_trigger,
                      anim_participants, custom_image, k_image, mode, custom_scanpaths):
    try:
        import k_dataset
        import json
        # For scanpath animation, use the checklist's selected participants
        active_participants = anim_participants if plot_type == 'scanpath' and anim_participants else (participants or [])

        if plot_type.startswith('k_'):
            import k_visualizations
            
            if mode == 'custom':
                if not custom_image:
                    return empty_figure("Upload a stimulus image to begin")
                _, img_w, img_h, img_url = _decode_custom_image(custom_image)
                custom_dfs_list = _get_custom_scanpath_dfs(custom_scanpaths, active_participants, None)
                if not custom_dfs_list:
                    return empty_figure("No data for selected participants")
                custom_dfs = {str(p): df for p, df in zip(active_participants, custom_dfs_list)}
            elif mode == 'k_dataset':
                if k_image:
                    _, img_w, img_h, img_url = _decode_custom_image(k_image)
                else:
                    img_url = k_dataset.K_STIMULUS_URL
                    img_w = k_dataset.STIMULUS_WIDTH
                    img_h = k_dataset.STIMULUS_HEIGHT
                custom_dfs = k_dataset.K_DFS
            else:
                custom_dfs = None
                img_url = None
                img_w = None
                img_h = None
                
            if plot_type == 'k_video':
                return empty_figure("Video playing in panel above")
            elif plot_type == 'k_timeline':
                return k_visualizations.make_k_timeline_figure(active_participants, AOI, AOI_type, custom_dfs=custom_dfs)
            elif plot_type == 'k_heatmap':
                return k_visualizations.make_k_heatmap_figure(active_participants, k_mode='focal', custom_dfs=custom_dfs, custom_img_url=img_url, custom_w=img_w, custom_h=img_h)

        if mode == 'k_dataset':
            img_to_use = k_image if k_image else {'url': k_dataset.K_STIMULUS_URL, 'width': k_dataset.STIMULUS_WIDTH, 'height': k_dataset.STIMULUS_HEIGHT}
            return generate_figure_custom(plot_type, img_to_use, json.dumps({p: 'k' for p in active_participants}), active_participants, AOI, AOI_type, override_dfs=k_dataset.K_DFS)
            
        if mode == 'custom':
            return generate_figure_custom(plot_type, custom_image, custom_scanpaths,
                                          active_participants, AOI, AOI_type)
        return generate_figure(plot_type, db_name, stimulus, active_participants, AOI, AOI_type)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return empty_figure(f"Left Graph Error: {str(e)}")


# ── 7. Update RIGHT panel graph ──
@app.callback(
    Output('right-graph', 'figure'),
    [Input('right-plot-type', 'value'),
     Input('ddDB', 'value'),
     Input('image-dropdown', 'value'),
     Input('ddParticipants-right', 'value'),
     Input('aoi-store', 'data'),
     Input('right-anim-participants', 'value'),
     Input('custom-image-store', 'data'),
     Input('k-image-store', 'data')],
    [State('data-source-mode', 'data'),
     State('custom-scanpaths-store', 'data')],
    prevent_initial_call=True
)
def update_right_graph(plot_type, db_name, stimulus, participants, _aoi_trigger,
                       anim_participants, custom_image, k_image, mode, custom_scanpaths):
    try:
        import k_dataset
        import json
        active_participants = anim_participants if plot_type == 'scanpath' and anim_participants else (participants or [])

        if plot_type.startswith('k_'):
            import k_visualizations
            
            if mode == 'custom':
                if not custom_image:
                    return empty_figure("Upload a stimulus image to begin")
                _, img_w, img_h, img_url = _decode_custom_image(custom_image)
                custom_dfs_list = _get_custom_scanpath_dfs(custom_scanpaths, active_participants, None)
                if not custom_dfs_list:
                    return empty_figure("No data for selected participants")
                custom_dfs = {str(p): df for p, df in zip(active_participants, custom_dfs_list)}
            elif mode == 'k_dataset':
                if k_image:
                    _, img_w, img_h, img_url = _decode_custom_image(k_image)
                else:
                    img_url = k_dataset.K_STIMULUS_URL
                    img_w = k_dataset.STIMULUS_WIDTH
                    img_h = k_dataset.STIMULUS_HEIGHT
                custom_dfs = k_dataset.K_DFS
            else:
                custom_dfs = None
                img_url = None
                img_w = None
                img_h = None

            if plot_type == 'k_video':
                return empty_figure("Video playing in panel above")
            elif plot_type == 'k_timeline':
                return k_visualizations.make_k_timeline_figure(active_participants, AOI, AOI_type, custom_dfs=custom_dfs)
            elif plot_type == 'k_heatmap':
                return k_visualizations.make_k_heatmap_figure(active_participants, k_mode='ambient', custom_dfs=custom_dfs, custom_img_url=img_url, custom_w=img_w, custom_h=img_h)

        if mode == 'k_dataset':
            img_to_use = k_image if k_image else {'url': k_dataset.K_STIMULUS_URL, 'width': k_dataset.STIMULUS_WIDTH, 'height': k_dataset.STIMULUS_HEIGHT}
            return generate_figure_custom(plot_type, img_to_use, json.dumps({p: 'k' for p in active_participants}), active_participants, AOI, AOI_type, override_dfs=k_dataset.K_DFS)
        
        if mode == 'custom':
            return generate_figure_custom(plot_type, custom_image, custom_scanpaths,
                                          active_participants, AOI, AOI_type)
        return generate_figure(plot_type, db_name, stimulus, active_participants, AOI, AOI_type)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return empty_figure(f"Right Graph Error: {str(e)}")

# ── 8. Animation Checklists logic ──
@app.callback(
    Output('left-anim-participants-container', 'style'),
    Input('left-plot-type', 'value')
)
def toggle_left_anim_container(plot_type):
    if plot_type == 'scanpath':
        return {'display': 'block', 'padding': '10px', 'textAlign': 'center', 'borderTop': '1px solid #ddd', 'backgroundColor': '#f9f9f9'}
    return {'display': 'none'}

@app.callback(
    Output('right-anim-participants-container', 'style'),
    Input('right-plot-type', 'value')
)
def toggle_right_anim_container(plot_type):
    if plot_type == 'scanpath':
        return {'display': 'block', 'padding': '10px', 'textAlign': 'center', 'borderTop': '1px solid #ddd', 'backgroundColor': '#f9f9f9'}
    return {'display': 'none'}

@app.callback(
    Output('left-anim-participants', 'options'),
    Output('left-anim-participants', 'value'),
    Input('ddParticipants-left', 'value'),
    Input('left-anim-participants', 'value')
)
def update_left_anim_checklist(panel_participants, current_checked):
    trigger = ctx.triggered_id
    if not panel_participants:
        return [], []
    if trigger == 'ddParticipants-left' or current_checked is None:
        current_checked = panel_participants[:5]
    if len(current_checked) > 5:
        current_checked = current_checked[:5]
    options = []
    for p in panel_participants:
        options.append({
            'label': p, 'value': p,
            'disabled': len(current_checked) >= 5 and p not in current_checked
        })
    return options, current_checked

@app.callback(
    Output('right-anim-participants', 'options'),
    Output('right-anim-participants', 'value'),
    Input('ddParticipants-right', 'value'),
    Input('right-anim-participants', 'value')
)
def update_right_anim_checklist(panel_participants, current_checked):
    trigger = ctx.triggered_id
    if not panel_participants:
        return [], []
    if trigger == 'ddParticipants-right' or current_checked is None:
        current_checked = panel_participants[:5]
    if len(current_checked) > 5:
        current_checked = current_checked[:5]
    options = []
    for p in panel_participants:
        options.append({
            'label': p, 'value': p,
            'disabled': len(current_checked) >= 5 and p not in current_checked
        })
    return options, current_checked


# ── 9. Toggle video container vs graph container ──
@app.callback(
    Output('right-plot-type', 'value', allow_duplicate=True),
    Input('left-plot-type', 'value'),
    prevent_initial_call=True
)
def sync_right_timeline_with_video(left_val):
    if left_val == 'k_video':
        return 'k_timeline'
    raise dash.exceptions.PreventUpdate

@app.callback(
    Output('k-video-container', 'style'),
    Output('left-graph-container', 'style'),
    Input('left-plot-type', 'value'),
    prevent_initial_call=True
)
def toggle_video_vs_graph(plot_type):
    graph_style = {'flex': '1', 'overflow': 'auto', 'padding': '4px', 'display': 'flex', 'flexDirection': 'column'}
    video_style = {'display': 'none', 'flex': '1', 'position': 'relative', 'overflow': 'hidden', 'margin': '4px'}
    if plot_type == 'k_video':
        video_style['display'] = 'flex'
        graph_style['display'] = 'none'
    return video_style, graph_style

# ── 10. Update video source based on selected participant ──
@app.callback(
    Output('k-video-player', 'src'),
    Input('k-video-dropdown', 'value'),
    Input('ddParticipants-left', 'value'),
    State('data-source-mode', 'data'),
    State('custom-video-store', 'data'),
    prevent_initial_call=False
)
def update_k_video_src(k_vid_pid, participants, mode, custom_video):
    if mode == 'custom' and custom_video:
        return custom_video
    if mode == 'k_dataset':
        # Use selected video dropdown participant
        pid = k_vid_pid
        if not pid and participants:
            pid = participants[0] if isinstance(participants, list) else participants
        if pid:
            import k_dataset
            path = k_dataset.get_k_video_path(pid)
            if path:
                return f'/k_video/{pid}'
    return ''

# ── 11. Populate fixation data store for JS sync ──
@app.callback(
    Output('k-fixation-data', 'children'),
    Input('ddParticipants-left', 'value'),
    Input('left-plot-type', 'value'),
    State('data-source-mode', 'data'),
    State('custom-scanpaths-store', 'data'),
    State('custom-image-store', 'data'),
    prevent_initial_call=False
)
def populate_fixation_data(participants, plot_type, mode, custom_scanpaths, custom_image):
    import json as _json
    if plot_type != 'k_video' or not participants:
        return None
    
    try:
        import k_dataset
        
        if mode == 'k_dataset':
            source_dfs = k_dataset.K_DFS
        elif mode == 'custom' and custom_scanpaths:
            # Explicitly request scaling even though custom_image_store is None (to bypass keyframe filter)
            w = custom_image.get('width') if custom_image else None
            h = custom_image.get('height') if custom_image else None
            custom_dfs_list = _get_custom_scanpath_dfs(custom_scanpaths, participants, None, auto_scale_w_h=(w, h))
            source_dfs = {str(p): df for p, df in zip(participants, custom_dfs_list)} if custom_dfs_list else {}
        else:
            return None
        
        fixation_points = []
        for p in participants:
            if str(p) in source_dfs:
                df = source_dfs[str(p)].copy()
                if 'K_squashed' not in df.columns:
                    continue
                
                # Replace NaNs with 0 to prevent JSON.parse errors in JS
                df = df.fillna(0)
                
                for _, row in df.iterrows():
                    k_val = float(row['K_squashed'])
                    
                    x_val = float(row['X']) if mode == 'k_dataset' else float(row.get('X', 0))
                    y_val = float(row['Y']) if mode == 'k_dataset' else float(row.get('Y', 0))
                    
                    if mode == 'k_dataset':
                        x_pct = x_val / k_dataset.STIMULUS_WIDTH * 100.0
                        y_pct = y_val / k_dataset.STIMULUS_HEIGHT * 100.0
                    else:
                        img_w = custom_image.get('width') if custom_image else None
                        img_h = custom_image.get('height') if custom_image else None
                        x_pct = (x_val / img_w * 100.0) if img_w else x_val
                        y_pct = (y_val / img_h * 100.0) if img_h else y_val
                    
                    fixation_points.append({
                        'time_sec': float(row['TIME_FROM']) / 1000.0,
                        'time_end_sec': float(row['TIME_TO']) / 1000.0,
                        'x_pct': x_pct,
                        'y_pct': y_pct,
                        'k_squashed': k_val,
                        'subject': str(p),
                    })
        
        # Sort by time

        fixation_points.sort(key=lambda x: x['time_sec'])
        return _json.dumps(fixation_points)
    except Exception as e:
        print(f"[app] Error populating fixation data: {e}")
        return None


if __name__ == '__main__':
    from flask import send_file
    import k_dataset
    import os
    
    @app.server.route('/k_video/<pid>')
    def serve_k_video(pid):
        video_path = k_dataset.get_k_video_path(pid)
        if video_path and os.path.exists(video_path):
            return send_file(os.path.abspath(video_path))
        return "Not found", 404

    upload_panel.register_callbacks(app)
    app.run(debug=True, host='0.0.0.0', port=8050)