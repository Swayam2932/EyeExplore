# EyeExplore — Visual Eyetracking Dashboard

A web-based interactive dashboard for visualizing and analyzing eye-tracking data. Built for researchers, UX designers, and cognitive psychologists to explore gaze patterns, fixation behaviors, and scanpath dynamics through an intuitive dual-panel interface.

> **IIIT Bangalore — SRIP Research Project | Version 2.0**

---

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Dashboard Modes](#dashboard-modes)
  - [Built-in Datasets](#1-built-in-datasets)
  - [My Own Data](#2-my-own-data)
  - [K-Coefficient Dataset](#3-k-coefficient-dataset)
- [Visualization Types](#visualization-types)
- [Areas of Interest (AOIs)](#areas-of-interest-aois)
- [Dual-Panel Comparison](#dual-panel-comparison)
- [Data Format Reference](#data-format-reference)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Dual-panel layout** — side-by-side visualization comparison with independent controls per panel
- **13 visualization types** — from basic stimulus display to 3D scanpaths and K-Coefficient timelines
- **Three data modes** — built-in research datasets, custom data uploads, and K-Coefficient video analysis
- **Interactive AOI tools** — draw rectangle regions directly on stimuli with overlap detection
- **Real-time video sync** — synced video playback with fixation dot overlay and K-Coefficient timeline scrubber
- **Object detection** — YOLO-powered object detection overlay on stimulus images
- **In-memory processing** — no files are persisted on the server; all data is cleared on refresh
- **Auto-scaling** — automatically detects percentage-based coordinates and scales to pixel dimensions
- **Export** — download any visualization as PNG via the Plotly toolbar

---

## Getting Started

### Prerequisites

- Python 3.10+
- Modern web browser (Chrome, Firefox, Safari, or Edge)
- Minimum 4 GB RAM for large dataset visualizations

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd EyeExplore

# Install dependencies
pip install -r requirements.txt

# Launch the dashboard
python app.py
```

Open your browser and navigate to **http://localhost:8050**

The dashboard loads with the **Built-in Datasets** tab active by default.

---

## Dashboard Modes

### 1. Built-in Datasets

Pre-loaded eye-tracking research datasets ready to explore.

| Dataset | Stimuli | Participants per Stimulus | Description |
|---------|---------|--------------------------|-------------|
| **MIT1003** | 1,003 images | ~15 | Natural scene viewing |
| **SIENA12** | 12 images | ~23 | Controlled scene viewing |
| **VisRecall++** | 171 images | ~14 | Chart and visualization recall |

**Controls:**
- **Dataset dropdown** — select from available built-in datasets
- **Stimulus dropdown** — select which stimulus image to analyze
- **Participant dropdowns** — independently select participants for left and right panels

---

### 2. My Own Data

Upload your own stimulus images/videos and scanpath data files for analysis.

**Supported Stimulus Formats:**

| Type | Extensions |
|------|-----------|
| Images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp` |
| Videos | `.mp4`, `.avi`, `.mov`, `.webm`, `.mkv` |

- Maximum file size: **10 MB**
- Videos are automatically processed for key frame extraction

**Supported Scanpath Formats:**

| Extension | Description |
|-----------|-------------|
| `.csv` | Comma-separated values |
| `.tsv` | Tab-separated values |
| `.txt` | Plain text (auto-detected delimiter) |

- Maximum **10** scanpath files per session
- Two time formats supported:
  - **Explicit (4-column):** X, Y, Start Time, End Time
  - **Cumulative (3-column):** X, Y, Timestamp

**Column Mapping:**

After uploading scanpath files, a column mapper appears where you assign semantic meaning (X, Y, START, END, or T) to each column in your data. A preview table shows the first 5 rows after mapping. Click **Confirm & Load** to finalize.

**Key Frames (Video Mode):**

When a video is uploaded, key frames are extracted automatically. The Key Frames dropdown lets you select specific moments in the video for analysis (e.g., "Frame 1 — 0.0s", "Frame 23 — 31.2s"). Static visualizations (Scanpath Overlay, Attention Map, etc.) filter to the selected frame's time window.

**Auto-Scaling:**

If your scanpath file uses percentage coordinates (0–100 range) instead of pixel coordinates, the dashboard automatically detects this and scales them to the stimulus dimensions. This ensures fixation points are correctly distributed across the image rather than being clustered in one corner.

---

### 3. K-Coefficient Dataset

Specialized mode for ambient/focal attention analysis using video stimuli with K-Coefficient-based gaze classification.

- **27 video stimuli** (participant IDs: 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 27, 31, 35, 39, 41, 42, 45)
- **26 participant fixation files** with computed K-values
- Video resolution: **1920 × 1080**

**Unique Features:**
- **Synced Video + K-Timeline** — video playback with a fixation dot overlay tracking gaze position in real-time. A red scrubber line on the K-Coefficient Timeline moves in sync with the video.
- **K-Coefficient Timeline** — line chart showing the K_squashed value over time. Values above 0 (green zone) indicate **focal inspection**; values below 0 (pink zone) indicate **ambient search**.
- **Fixation dot overlay** — a black dot with trailing history dots follows the participant's gaze on the video in real-time.

**K-Coefficient Data Schema:**

Each participant's CSV (`{id}-fixations_with_K.csv`) contains:

| Column | Description |
|--------|-------------|
| `fixation_point_x` | X coordinate (% of stimulus width, 0–100) |
| `fixation_point_y` | Y coordinate (% of stimulus height, 0–100) |
| `fixation_starts_at_ms` | Fixation start time (milliseconds) |
| `fixation_ends_at_ms` | Fixation end time (milliseconds) |
| `fixation_duration_ms` | Fixation duration (milliseconds) |
| `saccade_length_px` | Saccade length in pixels |
| `saccade_amplitude_percent` | Saccade amplitude as percentage |
| `K_i` | Raw K-Coefficient value |
| `K_squashed` | Squashed (normalized) K-Coefficient value |

---

## Visualization Types

| # | Visualization | Description | Requirements |
|---|--------------|-------------|-------------|
| 1 | **Stimulus Image** | Raw stimulus display with AOI drawing support | None |
| 2 | **Scanpath Animation** | Animated playback of gaze paths over the stimulus | 1+ participants |
| 3 | **Scanpath Overlay** | Static overlay of complete scanpaths with numbered fixation circles and saccade lines | 1 participant |
| 4 | **Attention Map** | Heat map showing aggregate fixation density (red = high, blue = low) | 1+ participants |
| 5 | **Scarf Plot** | Horizontal bar chart showing temporal sequence of AOI visits per participant | 1+ participants, AOIs |
| 6 | **AOI Timeline** | Time-series chart showing when each AOI was visited and for how long | 1+ participants, AOIs |
| 7 | **3D Scanpath** | 3D trajectory where X, Y = gaze coordinates and Z = time | 1+ participants |
| 8 | **3D Scatter** | 3D scatter plot of fixation points at (X, Y, Time) with size encoding duration | 1+ participants |
| 9 | **Co-association Matrix** | Heatmap of gaze pattern similarity between participant pairs | 2+ participants |
| 10 | **Object Detection** | YOLO object detection overlay with bounding boxes and confidence scores | None |
| 11 | **Transition Matrix** | Frequency matrix of gaze transitions between AOI regions | AOIs |
| 12 | **Synced Video + K-Timeline** | Video with real-time fixation dot overlay synced to K-Coefficient chart | 1+ participants (K-data) |
| 13 | **K-Coefficient Timeline** | Line chart of K-Coefficient values over time with focal/ambient phase shading | 1+ participants (K-data) |

---

## Areas of Interest (AOIs)

AOIs are user-defined regions on the stimulus image used for targeted analysis.

**Drawing AOIs:**
1. Select **Stimulus Image** in either panel
2. The **rectangle** draw tool is selected by default
3. Click and drag to draw rectangular AOI regions
4. The AOI count badge updates automatically

**Rules:**
- AOIs **cannot overlap** — if a drawn AOI overlaps with an existing one, it is rejected with an error message
- AOIs are **shared between both panels** — drawing in one applies to both
- AOIs **persist** across visualization type switches until explicitly cleared
- Click **Clear AOIs** (red button) to remove all regions

**AOI-dependent visualizations:** Scarf Plot, AOI Timeline, Transition Matrix

---

## Dual-Panel Comparison

The signature feature of EyeExplore is its dual-panel layout for side-by-side comparison.

Each panel has its own:
- **Visualization type dropdown** — choose different plot types per panel
- **Participant selector** — compare different participant groups
- **Info button** — contextual help for the selected visualization

**Example workflows:**
- Left: Stimulus Image → Right: Attention Map (see where people looked)
- Left: Scanpath Overlay → Right: Scarf Plot (temporal viewing patterns)
- Left: Synced Video → Right: K-Coefficient Timeline (attention mode analysis)

A **draggable divider** separates the panels. Click and drag to resize.

---

## Data Format Reference

### Standard Scanpath Format (Internal)

After column mapping, all scanpath data is standardized to:

| Column | Type | Description |
|--------|------|-------------|
| `SUBJECT` | string | Participant identifier (derived from filename) |
| `X` | float | Horizontal gaze coordinate (pixels) |
| `Y` | float | Vertical gaze coordinate (pixels) |
| `TIME_FROM` | float | Fixation start time (milliseconds) |
| `TIME_TO` | float | Fixation end time (milliseconds) |

### Explicit Format (4-column input)

Your CSV/TSV must contain columns that can be mapped to: **X**, **Y**, **Start Time**, **End Time**

### Cumulative Format (3-column input)

Your CSV/TSV must contain columns that can be mapped to: **X**, **Y**, **Timestamp**

The dashboard automatically converts cumulative timestamps to start/end intervals.

---

## Project Structure

```
EyeExplore/
├── app.py                    # Main Dash application and callbacks
├── upload_panel.py           # Custom data upload UI and logic
├── scanpath_converter.py     # Scanpath parsing and standardization
├── k_dataset.py              # K-Coefficient dataset loader
├── k_visualizations.py       # K-Coefficient-specific visualizations
├── FixaTons.py               # Built-in dataset interface
├── FixaTons_methods/         # Dataset utility functions
├── assets/
│   ├── k_sync.js             # Video-timeline sync (fixation dot + scrubber)
│   └── styles.css            # Dashboard styles
├── data/
│   └── FixaTons/             # Built-in datasets
│       ├── MIT1003/
│       ├── SIENA12/
│       └── VisRecall++/
├── fixationsexport/          # K-Coefficient dataset
│   ├── participant_fixations/ # Per-participant CSVs with K-values
│   └── {id}/                 # Video files per participant
├── EyeExplore_User_Guide.pdf
├── EyeExplore_Testing_Manual.pdf
├── EyeExplore_Test_Runner.html
└── requirements.txt
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Blank visualization | Ensure participants are selected from the dropdown |
| AOI-dependent plots show nothing | Draw at least one AOI on the Stimulus Image first |
| Scanpath Overlay points in corner | Your data likely uses percentage coordinates — the dashboard auto-scales, but verify column mapping is correct |
| Server unresponsive | Refresh the page or restart with `python app.py` |
| Port 8050 in use | Stop other processes on port 8050, or modify the port in `app.py` |
| Video sync dot not moving | Hard refresh (`Cmd+Shift+R`) to reload `k_sync.js` |
| K-Timeline shows tiny range | Ensure you're using Synced Video + K-Timeline (not a keyframe-filtered view) |
| Upload fails | Check file size (max 10 MB) and format (see supported formats above) |

---

## Security

- **In-memory only** — all uploaded data is processed in memory and never written to disk
- **Data cleared on refresh** — closing or refreshing the browser removes all uploaded data
- **Filename sanitization** — all uploaded filenames are sanitized to prevent path traversal and injection attacks
- **No database** — the application has no persistent storage backend

---

## Browser Support

| Browser | Status |
|---------|--------|
| Chrome | ✅ Recommended |
| Firefox | ✅ Supported |
| Safari | ✅ Supported |
| Edge | ✅ Supported |

Minimum screen resolution: **1280 × 720**

---

## License

IIIT Bangalore — SRIP Research Project

---
