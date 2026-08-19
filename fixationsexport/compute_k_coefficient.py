#!/usr/bin/env python3
"""
Compute K Coefficient (Ambient/Focal Attention Metric) from Fixation Data.

Based on the K coefficient paper:
    K_i = (d_i - μ_d) / σ_d  -  (a_{i-1} - μ_a) / σ_a

Where:
    d_i     = fixation duration (fixation_duration_ms)
    a_{i-1} = preceding saccade amplitude (saccade_amplitude_percent)
    μ_d, σ_d = mean and std of fixation durations within the trial
    μ_a, σ_a = mean and std of saccade amplitudes within the trial

K is then squashed to [-1, 1] via logistic function:
    K_squashed = L / (1 + exp(-k * K_i)) - 1
    with L = 2, k = 0.125

    K > 0 → focal processing (long fixations, short saccades)
    K < 0 → ambient processing (short fixations, long saccades)

Usage:
    python compute_k_coefficient.py
"""

import os
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "participant_fixations")
LOGISTIC_L = 2.0     # Supremum of the logistic function (range → [-1, 1])
LOGISTIC_K = 0.125   # Steepness of the logistic curve

# CSV column names
COL_PARTICIPANT = "participant_id"
COL_ITEM        = "item_id"
COL_DURATION    = "fixation_duration_ms"
COL_AMPLITUDE   = "saccade_amplitude_percent"


def logistic_squash(K_raw: np.ndarray, L: float = LOGISTIC_L, k: float = LOGISTIC_K) -> np.ndarray:
    """
    Squash K to [-1, 1] using a logistic function:
        f(x) = L / (1 + exp(-k * x)) - 1

    With L=2, k=0.125 this maps:
        x → -∞  =>  f(x) → -1
        x = 0   =>  f(x) =  0
        x → +∞  =>  f(x) → +1
    """
    return L / (1.0 + np.exp(-k * K_raw)) - 1.0


def compute_k_for_trial(trial_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute K_i and K_squashed for all fixations in a single trial.

    Parameters
    ----------
    trial_df : pd.DataFrame
        Subset of rows belonging to one trial (one participant × one item).

    Returns
    -------
    pd.DataFrame
        The input DataFrame with two new columns: 'K_i' and 'K_squashed'.
    """
    trial_df = trial_df.copy()

    durations  = trial_df[COL_DURATION].astype(float)
    amplitudes = trial_df[COL_AMPLITUDE].astype(float)

    # Trial-level statistics
    mu_d    = durations.mean()
    sigma_d = durations.std(ddof=1)   # sample std (ddof=1)
    mu_a    = amplitudes.mean()
    sigma_a = amplitudes.std(ddof=1)

    # Edge cases: if std is 0 or NaN (constant values / single fixation), K is undefined
    if pd.isna(sigma_d) or sigma_d == 0 or pd.isna(sigma_a) or sigma_a == 0:
        trial_df["K_i"] = np.nan
        trial_df["K_squashed"] = np.nan
        return trial_df

    # Compute K_i = z_duration - z_amplitude  (Eq. 3)
    z_duration  = (durations - mu_d) / sigma_d
    z_amplitude = (amplitudes - mu_a) / sigma_a

    K_raw = z_duration - z_amplitude

    # Squash to [-1, 1]
    K_squashed = logistic_squash(K_raw)

    trial_df["K_i"] = K_raw
    trial_df["K_squashed"] = K_squashed

    return trial_df


def process_participant(participant_folder: str) -> dict:
    """
    Process a single participant's fixation CSV.

    Parameters
    ----------
    participant_folder : str
        Path to the participant folder (e.g., .../participant_fixations/2/).

    Returns
    -------
    dict
        Summary statistics for this participant.
    """
    folder_name = os.path.basename(participant_folder)
    csv_path = os.path.join(participant_folder, f"{folder_name}-fixations.csv")

    if not os.path.isfile(csv_path):
        return {"participant": folder_name, "status": "SKIPPED - file not found", "rows": 0}

    # Read CSV
    df = pd.read_csv(csv_path)

    # Validate required columns exist
    for col in [COL_PARTICIPANT, COL_ITEM, COL_DURATION, COL_AMPLITUDE]:
        if col not in df.columns:
            return {"participant": folder_name, "status": f"SKIPPED - missing column: {col}", "rows": len(df)}

    # Convert to numeric (coerce errors → NaN)
    df[COL_DURATION]  = pd.to_numeric(df[COL_DURATION], errors="coerce")
    df[COL_AMPLITUDE] = pd.to_numeric(df[COL_AMPLITUDE], errors="coerce")

    # Group by trial = (participant_id, item_id)
    grouped = df.groupby([COL_PARTICIPANT, COL_ITEM], sort=False)

    # Compute K for each trial, then reassemble
    results = []
    n_trials = 0
    for _group_key, trial_df in grouped:
        trial_result = compute_k_for_trial(trial_df)
        results.append(trial_result)
        n_trials += 1

    df_out = pd.concat(results, ignore_index=False).sort_index()

    # Save output
    output_path = os.path.join(participant_folder, f"{folder_name}-fixations_with_K.csv")
    df_out.to_csv(output_path, index=False)

    # Summary stats
    valid_K = df_out["K_squashed"].dropna()
    summary = {
        "participant": folder_name,
        "status": "OK",
        "rows": len(df_out),
        "trials": n_trials,
        "K_valid": len(valid_K),
        "K_nan": int(df_out["K_squashed"].isna().sum()),
        "K_squashed_mean": round(valid_K.mean(), 4) if len(valid_K) > 0 else np.nan,
        "K_squashed_std": round(valid_K.std(), 4) if len(valid_K) > 0 else np.nan,
        "output_file": output_path,
    }
    return summary


def main():
    """Main entry point: discover all participant folders and process them."""
    print("=" * 70)
    print("  K Coefficient Computation - Ambient/Focal Attention Metric")
    print("=" * 70)
    print(f"\nBase directory: {BASE_DIR}")
    print(f"Logistic parameters: L={LOGISTIC_L}, k={LOGISTIC_K}")
    print()

    # Discover participant folders (numeric folder names)
    all_entries = sorted(os.listdir(BASE_DIR), key=lambda x: int(x) if x.isdigit() else 999)
    participant_folders = [
        os.path.join(BASE_DIR, entry)
        for entry in all_entries
        if os.path.isdir(os.path.join(BASE_DIR, entry)) and entry.isdigit()
    ]

    if not participant_folders:
        print("ERROR: No participant folders found!")
        return

    print(f"Found {len(participant_folders)} participant folder(s).\n")

    # Process each participant
    summaries = []
    for folder in participant_folders:
        folder_name = os.path.basename(folder)
        print(f"  Processing participant {folder_name}...", end=" ")
        summary = process_participant(folder)
        summaries.append(summary)
        print(summary["status"])

    # ──────────────────────────────────────────
    # Print summary report
    # ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  Summary Report")
    print("=" * 70)

    summary_df = pd.DataFrame(summaries)
    ok_mask = summary_df["status"] == "OK"

    print(f"\n  Total participants processed:  {len(summaries)}")
    print(f"  Successful:                    {ok_mask.sum()}")
    print(f"  Skipped/Errors:                {(~ok_mask).sum()}")

    if ok_mask.any():
        ok_df = summary_df[ok_mask]
        total_rows = int(ok_df["rows"].sum())
        total_valid = int(ok_df["K_valid"].sum())
        total_nan = int(ok_df["K_nan"].sum())

        print(f"\n  Total fixation rows:           {total_rows}")
        print(f"  K values computed:             {total_valid}")
        print(f"  K values NaN:                  {total_nan}")
        print(f"\n  Overall K_squashed mean:       {ok_df['K_squashed_mean'].mean():.4f}")
        print(f"  Overall K_squashed std:        {ok_df['K_squashed_std'].mean():.4f}")

    if (~ok_mask).any():
        print("\n  Skipped participants:")
        for _, row in summary_df[~ok_mask].iterrows():
            print(f"    Participant {row['participant']}: {row['status']}")

    print("\n" + "=" * 70)
    print("  Output files saved as: {i}-fixations_with_K.csv")
    print("  New columns: K_i (raw), K_squashed (logistic, bounded [-1, 1])")
    print("=" * 70)


if __name__ == "__main__":
    main()
