import os
import pandas as pd

# The columns we want to keep
COLUMNS_TO_KEEP = [
    "fixation_point_x",
    "fixation_point_y",
    "fixation_starts_at_ms",
    "fixation_ends_at_ms",
    "fixation_duration_ms",
    "saccade_length_px",
    "saccade_amplitude_percent",
    "K_i",
    "K_squashed"
]

def main():
    base_dir = "participant_fixations"
    
    # Find all participant folders (numeric names)
    if not os.path.exists(base_dir):
        print(f"Directory {base_dir} not found.")
        return
        
    participant_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f)) and f.isdigit()]
    
    if not participant_folders:
        print("No participant folders found.")
        return
        
    print(f"Found {len(participant_folders)} participant folder(s).")
    
    for folder in sorted(participant_folders, key=int):
        file_path = os.path.join(base_dir, folder, f"{folder}-fixations_with_K.csv")
        
        if not os.path.exists(file_path):
            print(f"  Skipping participant {folder}: file not found at {file_path}")
            continue
            
        print(f"  Processing participant {folder}...", end=" ")
        
        try:
            # Read the CSV
            df = pd.read_csv(file_path)
            
            # Check which columns are actually present to avoid errors
            cols_to_keep_present = [c for c in COLUMNS_TO_KEEP if c in df.columns]
            
            # Filter the dataframe
            filtered_df = df[cols_to_keep_present]
            
            # Save back to the same file (overwrite)
            # Or you can save to a new file, e.g., {folder}-fixations_filtered.csv
            filtered_df.to_csv(file_path, index=False)
            print("OK")
            
        except Exception as e:
            print(f"ERROR: {e}")

    print("\nAll files processed successfully.")

if __name__ == "__main__":
    main()
