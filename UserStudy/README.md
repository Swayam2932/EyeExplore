# EyeExplore participant study portal

The portal is served by the main EyeExplore process at `/user-study/`. It
provides participant login, parity-based set assignment, pre-study
instructions, four task questions, separate visualization ease ratings, task
timing, an optional final review, SQLite persistence, and cumulative CSV email.

## Assignment rules

- The novice access code is `nuserstudy`; the expert access code is
  `euserstudy`. The access code alone identifies the participant cohort.
- Participant IDs are positive integers and unique across both cohorts.
- Odd IDs receive Set 1; even IDs receive Set 2 for their cohort.
- The recruiter assigns globally unique participant IDs incrementally from 1.
  The ID labels and assigns the study set; it is not a credential.
- An unfinished participant can log in again to resume. A completed ID cannot
  be reused.

## Prepare the questionnaire

`questions.json` contains four tasks for each of the four sets, transcribed from
`EyeExplore_Final_Hypothesis_Testing_Questionnaire.pdf`. Each task includes the
participant-facing steps, exactly four single-choice options, and the names of
the visualization(s) that must be rated after the answer is submitted.

Before a study session, replace the same-name placeholder values in
`study_setup.json` with the final frozen values. The question text displays
these setup fields where relevant:

```text
TARGET_AOI_LABEL
TARGET_AOI_BOUNDARY
COMPARISON_AOI_LABELS_AND_BOUNDARIES
VIDEO_DATASET_NAME
VIDEO_DATASET_VERSION
EPISODE_A_VIDEO_FILENAME
EPISODE_A_START_TIME
EPISODE_A_END_TIME
EPISODE_A_PLAYBACK_SPEED
K_COEFFICIENT_FIELD_SOURCE
DASHBOARD_APP_VERSION
FIXATION_AOI_PREPROCESSING_VERSION
```

Set each `NOVICE_SET1_Q1_CORRECT_OPTION` through
`EXPERT_SET2_Q4_CORRECT_OPTION` to the correct option letter (`A`, `B`, `C`, or
`D`) calculated from the frozen study records and AOI definitions. The answer
keys are kept out of participant-facing question data. Until a key is filled,
the corresponding task is recorded as `not_scored`; no answer is guessed.
Option D indicates a technical unavailability issue and should be reviewed
separately from ordinary incorrect answers.

The overall 25-minute countdown starts when the participant clicks **Start**
and stays visible during tasks, visualization ratings, and optional review.
At zero it alerts the participant and recruiter without submitting or
discarding an unfinished answer. Each task is separately timed from question
display until answer submission; ease ratings are excluded from task time. The
optional written review is a separate final step outside the questionnaire.
After responses are saved, the participant session is cleared and the portal
returns to the login page for the next participant.

## Configure the server

Set these variables in the server's secret/configuration manager. Do not put
real access codes or SMTP credentials in source control.

```text
STUDY_SECRET_KEY=<long random secret that stays stable across restarts>
USER_STUDY_DATA_DIR=<persistent writable directory for the SQLite database>
STUDY_COOKIE_SECURE=1

STUDY_RESULTS_EMAIL=<results recipient>
STUDY_SMTP_HOST=<SMTP server>
STUDY_SMTP_PORT=587
STUDY_SMTP_USER=<SMTP account>
STUDY_SMTP_PASSWORD=<SMTP password or app password>
STUDY_SMTP_FROM=<verified sender address>
STUDY_SMTP_SSL=0
```

Use HTTPS in production and set `STUDY_COOKIE_SECURE=1`; for local HTTP, use
`0`. The default database is `UserStudy/data/responses.sqlite3`. On hosts with
ephemeral disks, use a persistent mounted volume for `USER_STUDY_DATA_DIR`.
Keep the secret key stable across restarts so participants can resume.

After each completion, the server refreshes a cumulative CSV of all completed
sessions at `UserStudy/data/eyeexplore_user_study_results.csv` by default. The
CSV is saved beside the SQLite database, so changing `USER_STUDY_DATA_DIR` or
`USER_STUDY_DB` changes its location too. The file contains participant,
cohort, and set identifiers; task responses, scoring status,
per-visualization ratings, question start/end times and durations; and any
optional review. When SMTP is configured, the same CSV is also emailed after
each completion. SQLite remains the durable source. Missing or failed email
configuration does not prevent the local CSV save.

## Start

From the repository root:

```bash
source eye/bin/activate
python main.py
```

The landing page's **Take User Study** button opens the portal in a new tab.
