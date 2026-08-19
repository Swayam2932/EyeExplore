import pandas as pd
import os

# Constants based on the implementation plan
K_VIDEO_ROOT = "/Users/test/Desktop/EyeExplore/fixationsexport"
K_DATA_ROOT = os.path.join(K_VIDEO_ROOT, "participant_fixations")
STIMULUS_WIDTH = 1920
STIMULUS_HEIGHT = 1080

def get_k_participants():
    if not os.path.exists(K_DATA_ROOT):
        return []
    
    participants = []
    for pid in os.listdir(K_DATA_ROOT):
        pid_path = os.path.join(K_DATA_ROOT, pid)
        if os.path.isdir(pid_path) and pid.isdigit():
            participants.append(pid)
    return sorted(participants, key=int)

def load_k_dataset(participants_to_load=None):
    if participants_to_load is None:
        participants_to_load = get_k_participants()
        
    all_dfs = {}
    
    for pid in participants_to_load:
        csv_path = os.path.join(K_DATA_ROOT, pid, f"{pid}-fixations_with_K.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                mapped_df = pd.DataFrame()
                
                # Scale % coordinates to pixels
                mapped_df['X'] = df['fixation_point_x'] / 100.0 * STIMULUS_WIDTH
                mapped_df['Y'] = df['fixation_point_y'] / 100.0 * STIMULUS_HEIGHT
                
                mapped_df['TIME_FROM'] = df['fixation_starts_at_ms']
                mapped_df['TIME_TO'] = df['fixation_ends_at_ms']
                mapped_df['ELAPSED_TIME'] = df['fixation_duration_ms']
                
                # Keep K-metrics
                mapped_df['K_i'] = df['K_i']
                mapped_df['K_squashed'] = df['K_squashed']
                
                # Copy subject/participant id
                mapped_df['SUBJECT'] = pid
                
                all_dfs[pid] = mapped_df
            except Exception as e:
                print(f"Error loading {csv_path}: {e}")
                
    return all_dfs

def get_k_stimulus_image_url():
    participants = get_k_participants()
    if not participants:
        return None
        
    csv_path = os.path.join(K_DATA_ROOT, participants[0], f"{participants[0]}-fixations_with_K.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, nrows=1)
            return df['item_cdn_url'].iloc[0]
        except Exception:
            pass
    return None

def get_k_video_path(participant_id):
    video_path = os.path.join(K_VIDEO_ROOT, str(participant_id), f"{participant_id}-screenclip_final.webm")
    if os.path.exists(video_path):
        return video_path
    return None

# Load the dataset at module initialization
print("Loading K-Coefficient Dataset...")
K_PARTICIPANTS = get_k_participants()
K_DFS = load_k_dataset(K_PARTICIPANTS)
K_STIMULUS_URL = get_k_stimulus_image_url()
print(f"Loaded {len(K_DFS)} participants for K-Dataset.")
