"""
scanpath_converter.py — Pure data logic for custom scanpath uploads.
Framework-agnostic (no Dash imports), independently testable.
"""

import base64
import tempfile
import os
import numpy as np
import pandas as pd
import cv2
from scipy.ndimage import gaussian_filter
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.webm', '.mkv'}
ALLOWED_STIMULUS_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
MAX_IMAGE_SIZE_MB = 10
MAX_VIDEO_SIZE_MB = 50

ALLOWED_SCANPATH_EXTENSIONS = {'.csv', '.tsv', '.txt'}
MAX_SCANPATH_FILES = 10
MAX_SCANPATH_SIZE_MB = 5


# ═══════════════════════════════════════════════════════════════════════════════
# DELIMITER & PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def sniff_delimiter(raw_text: str) -> str:
    """Try ',', '\\t', then fall back to splitting on runs of whitespace.
    Returns the detected delimiter string, or None for whitespace splitting."""
    # Take first non-empty line
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Check comma
        if ',' in line:
            return ','
        # Check tab
        if '\t' in line:
            return '\t'
        # Fall back to whitespace
        return None
    return None


def parse_raw_table(raw_text: str, delimiter: str) -> pd.DataFrame:
    lines = raw_text.strip().splitlines()
    good_rows = []
    bad_rows = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            if delimiter:
                parts = line.split(delimiter)
            else:
                parts = line.split()  # whitespace splitting
            values = [float(v.strip()) for v in parts if v.strip()]
            good_rows.append(values)
        except (ValueError, TypeError):
            bad_rows.append((i + 1, line))

    if not good_rows:
        raise ValueError("No valid numeric rows found in file")

    # Verify consistent column count
    col_count = len(good_rows[0])
    filtered_rows = []
    for row in good_rows:
        if len(row) == col_count:
            filtered_rows.append(row)
        else:
            bad_rows.append((-1, str(row)))  # inconsistent column count

    if not filtered_rows:
        raise ValueError("No rows with consistent column count")

    df = pd.DataFrame(filtered_rows, columns=[f'Col_{j+1}' for j in range(col_count)])
    return df, bad_rows


# ═══════════════════════════════════════════════════════════════════════════════
# COLUMN MAPPING & TIME CONVERSION
# ═══════════════════════════════════════════════════════════════════════════════

def reorder_columns(df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    col_names = df.columns.tolist()
    result = pd.DataFrame()

    for meaning, col_idx in column_mapping.items():
        if meaning == 'IGNORE':
            continue
        if isinstance(col_idx, (list, tuple)):
            # Multiple columns mapped to IGNORE
            continue
        result[meaning] = df.iloc[:, col_idx]

    return result


def convert_explicit_times(df_reordered: pd.DataFrame) -> pd.DataFrame:
    """4-column case — straight rename to X, Y, TIME_FROM, TIME_TO. No math needed."""
    df = df_reordered.copy()
    rename_map = {}
    if 'START' in df.columns:
        rename_map['START'] = 'TIME_FROM'
    if 'END' in df.columns:
        rename_map['END'] = 'TIME_TO'
    df.rename(columns=rename_map, inplace=True)
    return df


def convert_cumulative_time(df_reordered: pd.DataFrame) -> pd.DataFrame:
    """3-column case — convert cumulative time to TIME_FROM/TIME_TO.

    TIME_TO[i]   = T[i]
    TIME_FROM[0] = 0
    TIME_FROM[i] = TIME_TO[i-1]   for i > 0

    Worked example:
        Input:  X=153 Y=152 T=155
                X=184 Y=189 T=300
        Output: X=153 Y=152 TIME_FROM=0   TIME_TO=155
                X=184 Y=189 TIME_FROM=155 TIME_TO=300
    """
    df = df_reordered.copy()
    df['TIME_TO'] = df['T']
    df['TIME_FROM'] = df['TIME_TO'].shift(1, fill_value=0)
    df.drop(columns=['T'], inplace=True)
    return df


def validate_scanpath(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean a standardized scanpath DataFrame.
    Checks: no NaNs, END >= START, monotonic non-decreasing time.
    Returns cleaned DataFrame (bad rows dropped).
    Raises ValueError if all rows are rejected."""
    # Drop NaN rows
    initial_len = len(df)
    df = df.dropna()

    # Filter: TIME_TO >= TIME_FROM
    df = df[df['TIME_TO'] >= df['TIME_FROM']]

    if len(df) == 0:
        raise ValueError("All rows rejected during validation")

    # Reset index
    df = df.reset_index(drop=True)
    return df


def standardize_scanpath(raw_text: str, column_mapping: dict, format_type: str,
                         subject_name: str) -> dict:
    """Top-level entry point: sniff → parse → reorder → convert → validate.

    Args:
        raw_text: Raw file content as string
        column_mapping: Dict mapping semantic names to 0-indexed column indices
        format_type: 'explicit' (4-col) or 'cumulative' (3-col)
        subject_name: Name for the SUBJECT column (typically filename without extension)

    Returns:
        dict with keys:
            'df': DataFrame with columns [SUBJECT, X, Y, TIME_FROM, TIME_TO]
            'bad_rows': list of (line_number, line_text) tuples
            'dropped_count': number of rows dropped during validation
    """
    delimiter = sniff_delimiter(raw_text)
    df, bad_rows = parse_raw_table(raw_text, delimiter)

    df = reorder_columns(df, column_mapping)

    if format_type == 'explicit':
        df = convert_explicit_times(df)
    elif format_type == 'cumulative':
        df = convert_cumulative_time(df)
    else:
        raise ValueError(f"Unknown format_type: {format_type}")

    pre_validate_len = len(df)
    df = validate_scanpath(df)
    dropped_count = pre_validate_len - len(df)

    df['SUBJECT'] = subject_name

    # Ensure correct column order
    df = df[['SUBJECT', 'X', 'Y', 'TIME_FROM', 'TIME_TO']]

    return {
        'df': df,
        'bad_rows': bad_rows,
        'dropped_count': dropped_count
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AOI TAGGING
# ═══════════════════════════════════════════════════════════════════════════════

def assign_aoi(df_scanpath: pd.DataFrame, aoi_list: list, aoi_type: str) -> pd.DataFrame:
    """Add an 'AOI' column by point-in-rect/polygon testing each (X, Y).

    Replicates what FixaTons.get.scanpath_aoi does internally for built-in
    datasets. Custom data never goes through FixaTons, but scarf/timeline
    figures color by AOI, so this column must exist.

    Args:
        df_scanpath: DataFrame with X, Y columns
        aoi_list: List of AOI definitions
            - rect type: [[x0, y0, x1, y1], ...]
            - free type: [np.array([[x,y], ...]), ...]
        aoi_type: 'rect' or 'free'

    Returns:
        DataFrame with AOI column added (0 = no AOI, 1+ = AOI index)
    """
    df = df_scanpath.copy()
    df['AOI'] = 0

    if not aoi_list:
        return df

    # Build shapely polygons
    polygons = []
    if aoi_type == 'rect':
        for [x0, y0, x1, y1] in aoi_list:
            polygons.append(Polygon([(x0, y0), (x0 + x1, y0), (x1, y0 + y1), (x1, y1)]))
    else:
        for point_array in aoi_list:
            points = []
            arr = np.array(point_array)
            for i in range(len(arr)):
                points.append((arr[i][0], arr[i][1]))
            points.append((arr[0][0], arr[0][1]))  # Close the shape
            polygons.append(Polygon(points))

    # Tag each fixation
    for idx in df.index:
        pt = Point(df.loc[idx, 'X'], df.loc[idx, 'Y'])
        for j, poly in enumerate(polygons):
            if poly.contains(pt):
                df.loc[idx, 'AOI'] = j + 1
                break

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM ATTENTION MAP
# ═══════════════════════════════════════════════════════════════════════════════

def compute_custom_attention_map(image_array: np.ndarray, scanpath_dfs: list) -> np.ndarray:
    """Generate a Gaussian-blurred fixation density heatmap overlaid on the stimulus.

    Replaces FixaTons.show.attention_map() for custom data.

    Args:
        image_array: RGB numpy array of the stimulus image
        scanpath_dfs: List of DataFrames with X, Y columns

    Returns:
        RGB numpy array of the attention-map overlay
    """
    h, w = image_array.shape[:2]

    # Build fixation density map
    density = np.zeros((h, w), dtype=np.float64)
    for df in scanpath_dfs:
        for _, row in df.iterrows():
            x, y = int(round(row['X'])), int(round(row['Y']))
            if 0 <= x < w and 0 <= y < h:
                density[y, x] += 1

    # Apply Gaussian blur (sigma ~30px for typical 1-degree visual angle)
    if density.max() > 0:
        density = gaussian_filter(density, sigma=30)
        density = (density / density.max() * 255).astype(np.uint8)
    else:
        density = density.astype(np.uint8)

    # Apply colormap and blend with image
    heatmap_img = cv2.applyColorMap(density, cv2.COLORMAP_HOT)
    stimulus_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    result = cv2.addWeighted(heatmap_img, 0.5, stimulus_bgr, 0.5, 0)
    return cv2.cvtColor(result, cv2.COLOR_BGR2RGB)


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM TRANSITION MATRIX
# ═══════════════════════════════════════════════════════════════════════════════

def compute_custom_transition_matrix(scanpath_dfs: list, aoi_list: list,
                                     aoi_type: str) -> pd.DataFrame:
    """Compute AOI transition probability matrix from custom scanpath data.

    Replaces FixaTons.stats.AOI_transition_matrix() for custom data.

    Args:
        scanpath_dfs: List of DataFrames with SUBJECT, X, Y, TIME_FROM, TIME_TO columns
        aoi_list: List of AOI definitions
        aoi_type: 'rect' or 'free'

    Returns:
        Normalized transition matrix as DataFrame
    """
    # Concatenate and tag with AOI
    all_df = pd.concat(scanpath_dfs, ignore_index=True)
    all_df = assign_aoi(all_df, aoi_list, aoi_type)
    all_df = all_df.sort_values(by=['SUBJECT', 'TIME_FROM'])

    # Compute transitions per subject
    all_df['TRANSITION'] = all_df.groupby('SUBJECT')['AOI'].shift(1)
    all_df['TRANS_COUNTS'] = 1

    trans_matrix = all_df.groupby(['AOI', 'TRANSITION']).count().unstack()
    if trans_matrix.empty:
        return pd.DataFrame()

    trans_matrix.columns = trans_matrix.columns.droplevel()
    trans_matrix = trans_matrix.loc[:, ~trans_matrix.T.duplicated(keep='first')]
    arr = np.nan_to_num(np.array(trans_matrix))
    total = np.sum(arr)
    if total > 0:
        normalized = arr / total
    else:
        normalized = arr

    return pd.DataFrame(normalized)


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO KEY FRAME EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_key_frames(video_bytes: bytes) -> list:
    """Extract key frames from a video using adaptive multi-modal scene change detection.

    Algorithm:
        1. Compute HSV color histogram and downsampled grayscale frame for each position.
        2. Compute combined dissimilarity score (50% color histogram difference + 50% pixel motion diff).
        3. Use adaptive thresholding (mean + relative std deviation) so keyframes are detected
           properly regardless of video speed or contrast.
        4. Always include first and last frames.
        5. Max frames is dynamically capped at (video length in seconds * 5).

    Args:
        video_bytes: Raw video file bytes.

    Returns:
        List of dicts: [{frame_index, timestamp_sec, image_b64, width, height}, ...]
    """
    # Write video bytes to a temp file for OpenCV
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.mp4')
    try:
        with os.fdopen(tmp_fd, 'wb') as f:
            f.write(video_bytes)

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            raise ValueError("Video has no frames")

        video_length_sec = total_frames / fps if fps > 0 else 0
        max_frames = int(video_length_sec * 5)
        # Ensure at least 2 frames (first and last)
        max_frames = max(2, max_frames)

        # Sample every Nth frame to avoid processing every single frame
        sample_step = max(1, int(fps / 10))  # ~10 samples per second

        # Pass 1: Collect histograms and downsampled grayscale frames
        frame_data = []  # (frame_index, histogram, gray_small, frame_bgr)
        idx = 0
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                break

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_small = cv2.resize(gray, (160, 120))

            frame_data.append((idx, hist, gray_small, frame.copy()))
            idx += sample_step
            if idx >= total_frames:
                # Make sure we include the very last frame
                if frame_data[-1][0] != total_frames - 1:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
                    ret, frame = cap.read()
                    if ret:
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60],
                                            [0, 180, 0, 256])
                        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        gray_small = cv2.resize(gray, (160, 120))
                        frame_data.append((total_frames - 1, hist, gray_small, frame.copy()))
                break

        cap.release()

        if len(frame_data) <= 1:
            return _frames_to_result([(fd[0], fd[3]) for fd in frame_data], fps)

        # Pass 2: Compute combined dissimilarity score between consecutive sampled frames
        diff_scores = []  # (sample_index, dissimilarity_score)
        for i in range(1, len(frame_data)):
            # 1. Color histogram dissimilarity (0 = identical, 1 = completely different)
            corr = cv2.compareHist(frame_data[i - 1][1], frame_data[i][1], cv2.HISTCMP_CORREL)
            hist_diff = max(0.0, 1.0 - corr)

            # 2. Structural pixel motion difference (0 = identical, 1 = max diff)
            pix_diff = float(np.mean(cv2.absdiff(frame_data[i - 1][2], frame_data[i][2]))) / 255.0

            # Combined dissimilarity score
            score = 0.5 * hist_diff + 0.5 * pix_diff
            diff_scores.append((i, score))

        # Always include first and last frame
        selected_indices = {0, len(frame_data) - 1}

        # Adaptive Thresholding based on video's dynamic change distribution
        scores_arr = np.array([s for _, s in diff_scores])
        mean_score = float(np.mean(scores_arr))
        std_score = float(np.std(scores_arr))

        # Adaptive threshold: frames that show significant relative change
        adaptive_thresh = max(0.015, mean_score + 0.15 * std_score)

        candidates = [idx for idx, s in diff_scores if s >= adaptive_thresh]

        # If adaptive threshold yields too few frames, pick top 30% highest change frames
        if len(candidates) < 3 and len(diff_scores) > 2:
            sorted_by_score = sorted(diff_scores, key=lambda x: x[1], reverse=True)
            candidates = [idx for idx, s in sorted_by_score[:max(3, int(len(diff_scores) * 0.3))]]

        # Sort candidate frames by change score descending (most prominent changes first)
        candidates_with_score = [(idx, s) for idx, s in diff_scores if idx in candidates]
        candidates_with_score.sort(key=lambda x: x[1], reverse=True)

        for idx, _s in candidates_with_score:
            if len(selected_indices) >= max_frames:
                break
            selected_indices.add(idx)

        # Sort selected frame indices chronologically
        selected = sorted(selected_indices)[:max_frames]
        selected_frames = [(frame_data[i][0], frame_data[i][3]) for i in selected]

        return _frames_to_result(selected_frames, fps)

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _frames_to_result(frame_tuples: list, fps: float) -> list:
    """Convert raw frame data tuples to the standard result format."""
    result = []
    for frame_idx, frame_bgr in frame_tuples:
        # Convert BGR to RGB for display
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]

        # Encode as JPEG base64
        _, buf = cv2.imencode('.jpg', frame_bgr,
                              [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64 = base64.b64encode(buf).decode('utf-8')

        timestamp = frame_idx / fps if fps > 0 else 0.0

        result.append({
            'frame_index': int(frame_idx),
            'timestamp_sec': round(timestamp, 2),
            'image_b64': b64,
            'width': int(w),
            'height': int(h),
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATION SYNCHRONIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def resample_scanpaths(df: pd.DataFrame, fps: int = 10,
                       time_start: float = None, time_end: float = None) -> pd.DataFrame:
    """Resample multiple subjects' scanpaths into discrete time frames.
    
    Creates a common 'FRAME_TIME' for Plotly animations so all subjects
    animate together smoothly. Interpolates position during saccades.

    Args:
        time_start: If provided, override the animation start time (seconds).
        time_end:   If provided, override the animation end time (seconds).
    """
    if df.empty:
        return df

    min_time = time_start if time_start is not None else df['TIME_FROM'].min()
    max_time = time_end if time_end is not None else df['TIME_TO'].max()
    frames = np.arange(min_time, max_time + 1.0/fps, 1.0/fps)
    
    resampled_data = []
    
    for subject in df['SUBJECT'].unique():
        sub_df = df[df['SUBJECT'] == subject].copy()
        sub_df = sub_df.sort_values('TIME_FROM').reset_index(drop=True)
        
        for t in frames:
            row = {'SUBJECT': subject, 'FRAME_TIME': round(t, 2)}
            
            # 1. Before first fixation
            if t <= sub_df.iloc[0]['TIME_FROM']:
                row['X'] = sub_df.iloc[0]['X']
                row['Y'] = sub_df.iloc[0]['Y']
            
            # 2. After last fixation
            elif t >= sub_df.iloc[-1]['TIME_TO']:
                row['X'] = sub_df.iloc[-1]['X']
                row['Y'] = sub_df.iloc[-1]['Y']
                
            else:
                # 3. During a fixation or saccade
                active_idx = sub_df[(sub_df['TIME_FROM'] <= t) & (sub_df['TIME_TO'] > t)].index
                if not active_idx.empty:
                    # During fixation
                    idx = active_idx[0]
                    row['X'] = sub_df.iloc[idx]['X']
                    row['Y'] = sub_df.iloc[idx]['Y']
                else:
                    # During saccade (between fixations)
                    past = sub_df[sub_df['TIME_TO'] <= t]
                    future = sub_df[sub_df['TIME_FROM'] > t]
                    
                    if not past.empty and not future.empty:
                        idx_prev = past.index[-1]
                        idx_next = future.index[0]
                        
                        t0 = sub_df.iloc[idx_prev]['TIME_TO']
                        t1 = sub_df.iloc[idx_next]['TIME_FROM']
                        x0 = sub_df.iloc[idx_prev]['X']
                        y0 = sub_df.iloc[idx_prev]['Y']
                        x1 = sub_df.iloc[idx_next]['X']
                        y1 = sub_df.iloc[idx_next]['Y']
                        
                        # Linear interpolation
                        if t1 > t0:
                            ratio = (t - t0) / (t1 - t0)
                            row['X'] = x0 + (x1 - x0) * ratio
                            row['Y'] = y0 + (y1 - y0) * ratio
                        else:
                            row['X'] = x0
                            row['Y'] = y0
                            
            row['BUBBLE_SIZE'] = 15
            resampled_data.append(row)
                
    return pd.DataFrame(resampled_data)
