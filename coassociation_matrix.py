import FixaTons
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.ndimage import gaussian_filter
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering


def compute_coasso(DATASET_NAME='MIT1003', STIMULUS_SET=None, subjects=None, show_fig=False):
    """Compute a co-association matrix using the Heatmap-based (Vectorized) approach.

    Returns: (coassociation_matrix (ndarray), subjects (list), subjects (list))
    """
    if STIMULUS_SET is None:
        STIMULUS_SET = ['i2289665173.jpeg']

    if subjects is None:
        if len(STIMULUS_SET) > 0:
            try:
                subjects = FixaTons.info.subjects(DATASET_NAME, STIMULUS_SET[0])
            except Exception:
                subjects = []
        else:
            subjects = []
    else:
        subjects = list(subjects)

    n_subjects = len(subjects)
    if n_subjects == 0:
        return np.zeros([0, 0]), [], []

    coassociation_matrix = np.zeros([n_subjects, n_subjects])

    for stimulus in STIMULUS_SET:
        try:
            image_width, image_height = FixaTons.get.stimulus_size(DATASET_NAME, stimulus)
            all_stim_subjects = FixaTons.info.subjects(DATASET_NAME, stimulus)
        except Exception:
            continue
            
        current_subjects = [s for s in subjects if s in all_stim_subjects]
        n_curr = len(current_subjects)
        if n_curr == 0:
            continue

        # We build a downsampled fixation heatmap for each participant
        H, W = 64, 64  # Downsampled dimensions for performance
        H_flat = np.zeros((n_curr, H * W))

        for idx, sub in enumerate(current_subjects):
            try:
                scanpath_data = FixaTons.get.scanpath(DATASET_NAME, stimulus, sub)
            except Exception:
                continue
            
            grid = np.zeros((H, W))
            for fixation in scanpath_data:
                # each row: [x, y, time_from, time_to]
                x, y, t_start, t_end = fixation[0], fixation[1], fixation[2], fixation[3]
                duration = max(0.0, t_end - t_start)
                col = int(x * (W - 1) / image_width)
                row = int(y * (H - 1) / image_height)
                if 0 <= col < W and 0 <= row < H:
                    grid[row, col] += duration
            
            # Smooth the individual's attention map using gaussian filter
            smoothed = gaussian_filter(grid, sigma=2.0)
            H_flat[idx] = smoothed.flatten()

        # Compute pairwise Euclidean distances between subject heatmaps (fully vectorized)
        distance_matrix = cdist(H_flat, H_flat, metric='euclidean')

        # Feature scaling
        distance_matrix = np.nan_to_num(distance_matrix)
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(distance_matrix)

        k = min(4, n_curr)

        if k >= 2:
            # K-means
            try:
                kmeans = KMeans(init="random", n_clusters=k, n_init=10, max_iter=300)
                kmeans.fit(scaled_features)
                labels_kmeans = kmeans.labels_
                has_kmeans = True
            except Exception:
                has_kmeans = False

            # Hierarchical clustering
            try:
                hierarchical_cluster = AgglomerativeClustering(n_clusters=k, linkage='ward', metric="euclidean")
                labels_hierarchical = hierarchical_cluster.fit_predict(scaled_features)
                has_hierarchical = True
            except Exception:
                has_hierarchical = False

            # Spectral clustering
            has_spectral = False
            if k < n_curr:
                try:
                    spectral_model_nn = SpectralClustering(n_clusters=k, affinity='nearest_neighbors', n_neighbors=min(10, n_curr - 1))
                    labels_spectral = spectral_model_nn.fit_predict(scaled_features)
                    has_spectral = True
                except Exception:
                    pass

            for subject_1 in range(n_curr):
                for subject_2 in range(n_curr):
                    try:
                        g_idx1 = subjects.index(current_subjects[subject_1])
                        g_idx2 = subjects.index(current_subjects[subject_2])
                        if has_kmeans and labels_kmeans[subject_1] == labels_kmeans[subject_2]:
                            coassociation_matrix[g_idx1][g_idx2] += 1
                        if has_hierarchical and labels_hierarchical[subject_1] == labels_hierarchical[subject_2]:
                            coassociation_matrix[g_idx1][g_idx2] += 1
                        if has_spectral and labels_spectral[subject_1] == labels_spectral[subject_2]:
                            coassociation_matrix[g_idx1][g_idx2] += 1
                    except (ValueError, IndexError):
                        pass

    # Probabilistic normalization: make each row sum to 1
    row_sums = coassociation_matrix.sum(axis=1, keepdims=True)
    coassociation_matrix = np.divide(
        coassociation_matrix,
        row_sums,
        out=np.zeros_like(coassociation_matrix),
        where=row_sums != 0
    )

    if show_fig and subjects is not None:
        fig1 = px.imshow(coassociation_matrix, x=subjects, y=subjects, color_continuous_scale='balance', range_color=[0, 1])
        fig1.show()

    return coassociation_matrix, subjects, subjects
