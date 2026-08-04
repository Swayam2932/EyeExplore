# Feature Spec: Custom Data Upload for EyeExplore

## 0. Goal

Let a user, in addition to browsing the built-in FixaTons datasets, upload:
1. **One stimulus image** (their own picture) — limited extensions, size-capped.
2. **One or more scanpath files** (one file = one participant) — `.csv`/`.tsv`/`.txt`, count-capped.

Their scanpath files may not be in the app's internal column order, and may use either of two time formats. So before anything is plotted, the user must be walked through **instructions → format selection → column mapping → preview/confirm**, and the result must be silently converted into the same `X, Y, TIME_FROM, TIME_TO` shape the rest of `app.py` already consumes (confirmed against your reference file: `516 373 0.004 0.267`, no header).

Three deliverables, as you asked:

| # | File | Responsibility |
|---|------|-----------------|
| 1 | `upload_panel.py` | All UI: upload widgets, instructions copy, format selector, column-mapping form, preview, validation messages |
| 2 | `scanpath_converter.py` | Pure data logic: delimiter sniffing, column reordering, the two time-format conversions, AOI tagging for custom data |
| 3 | `app.py` (modified) | Mode toggle (built-in vs. custom), new stores/callbacks, wiring custom data into `generate_figure` |

---

## 1. User Flow

1. Next to the existing **Dataset** dropdown, add a 2-way toggle: **"Built-in Datasets" / "My Own Data"**.
2. Selecting **"My Own Data"** swaps the controls bar:
   - Dataset/Stimulus dropdowns are replaced by an **Upload Image** button + thumbnail/dimensions preview.
   - Participants dropdown is replaced by an **Upload Scanpath File(s)** button. Each accepted file appears as a chip/row named after its filename (minus extension) — this filename becomes that participant's `SUBJECT` id.
3. The first time scanpath files are uploaded in a session, an **instructions + mapping panel** expands (described in §3). It's shown once per upload batch, not once per file — the user is assumed to export all participants from the same tool, so one mapping applies to all files in that batch, with an "Advanced: remap this file individually" escape hatch per file.
4. User picks the **time format** (4-column explicit vs. 3-column cumulative — see §4), maps column indices to meanings, and sees a 5-row preview of the converted result for one file before confirming.
5. On confirm, every uploaded scanpath file is parsed → mapped → converted → validated, and stored in memory as standardized DataFrames.
6. Participants dropdown now lists the uploaded filenames; AOI drawing, plot-type selection, and both panels behave exactly as in built-in mode.

---

## 2. File 1 — `upload_panel.py` (UI layer)

### Constants (tune as needed — see §6 for defaults)
```python
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
MAX_IMAGE_SIZE_MB = 10

ALLOWED_SCANPATH_EXTENSIONS = {'.csv', '.tsv', '.txt'}
MAX_SCANPATH_FILES = 10          # max participants per custom session
MAX_SCANPATH_SIZE_MB = 5         # per file
```

### Components to build
- `make_mode_toggle()` — segmented control, drives `dcc.Store(id='data-source-mode')` (`'builtin'` | `'custom'`).
- `make_image_upload()` — `dcc.Upload` (single file, `multiple=False`), extension/size check on upload, thumbnail + `width × height` readout once decoded via PIL.
- `make_scanpath_upload()` — `dcc.Upload` (`multiple=True`), enforces `MAX_SCANPATH_FILES`, lists accepted/rejected files with reasons (bad extension, too large, duplicate filename).
- `make_instructions_block()` — static copy explaining:
  - No header row expected.
  - Delimiter can be comma, tab, or whitespace — auto-detected, but tell the user this so a malformed file makes sense to them.
  - The two supported time formats (plain language + the worked example from §4).
  - A "Download example file" link (nice-to-have — generate the two sample formats as static files).
- `make_format_selector()` — radio: **"My file has Start & End time (4 columns)"** vs. **"My file has one cumulative time value (3 columns)"**.
- `make_column_mapper(preview_df, format_type)` — dynamically renders one dropdown per detected column (`Col 1`, `Col 2`, …), options depend on `format_type`:
  - 4-col mode: `{X coordinate, Y coordinate, Start time, End time, Ignore this column}`
  - 3-col mode: `{X coordinate, Y coordinate, Cumulative time, Ignore this column}`
  - Validation: block "Apply" until every required meaning is assigned exactly once (no duplicates, none skipped).
- `make_preview_table(converted_df_head)` — shows the first 5 rows *after* conversion, with the final column names, so the user can sanity-check before committing.
- Error banner component for: unreadable file, non-numeric cells, row length mismatch mid-file, all-rows-rejected.

### Callbacks owned by this file
- Image upload → validate → decode → store thumbnail + raw bytes + dimensions.
- Scanpath upload(s) → for the *first* file in the batch, sniff delimiter + column count → render mapping form.
- Format radio change → re-render mapping dropdown options.
- "Apply Mapping" click → call `scanpath_converter.standardize_scanpath()` (File 2) per file → on success, populate preview + enable "Confirm & Load"; on failure, show which file/row failed.
- "Confirm & Load" → push final `{subject_name: standardized_df}` dict into a `dcc.Store`, collapse the mapping panel, populate the Participants dropdown.

---

## 3. File 2 — `scanpath_converter.py` (pure logic, no Dash)

Keep this framework-agnostic so it's independently testable.

```python
def sniff_delimiter(raw_text: str) -> str:
    """Try ',', '\t', then fall back to splitting on runs of whitespace."""

def parse_raw_table(raw_text: str, delimiter: str) -> pd.DataFrame:
    """No header. All-numeric coercion; raise/report row index on failure."""

def reorder_columns(df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """column_mapping example: {'X': 0, 'Y': 1, 'START': 2, 'END': 3}
    or {'X': 0, 'Y': 1, 'T': 2}. Drops columns mapped to 'IGNORE'."""

def convert_explicit_times(df_reordered: pd.DataFrame) -> pd.DataFrame:
    """4-column case — straight rename to TIME_FROM / TIME_TO, no math."""

def convert_cumulative_time(df_reordered: pd.DataFrame) -> pd.DataFrame:
    """3-column case — see worked example in §4.
    TIME_TO[i]   = T[i]
    TIME_FROM[0] = 0
    TIME_FROM[i] = TIME_TO[i-1]   for i > 0
    """

def standardize_scanpath(raw_text, column_mapping, format_type, subject_name) -> pd.DataFrame:
    """Top-level entry point: sniff -> parse -> reorder -> convert ->
    validate (END >= START, no NaNs, monotonic non-decreasing time) ->
    return DataFrame with columns exactly: SUBJECT, X, Y, TIME_FROM, TIME_TO
    (same shape FixaTons.get.scanpath_aoi already returns for built-in data)."""

def assign_aoi(df_scanpath: pd.DataFrame, aoi_list: list, aoi_type: str) -> pd.DataFrame:
    """Adds an 'AOI' column by point-in-rect / point-in-polygon testing each
    (X, Y) against aoi_list. This replaces what FixaTons.get.scanpath_aoi does
    internally for built-in datasets — needed because custom data never goes
    through FixaTons, but make_scarf_figure / make_timeline_figure color by
    this column, so it must exist for custom data too."""
```

### Why `assign_aoi` matters
For built-in datasets, `FixaTons.get.scanpath_aoi(db_name, stimulus, participants, aoi_list, aoi_type_val)` returns fixations **already tagged** with which AOI (if any) they fall inside — that's how the Scarf Plot and AOI Timeline color their bars/lines. Custom uploads have no such library to call, so this function has to replicate that tagging logic locally (reuse the existing `path_to_indices` / `draw.polygon` machinery already in `app.py` for the "free" AOI type, plus simple rectangle containment for the "rect" type).

### Worked example (exactly your numbers)
3-column input (no header):
```
153  152  155
184  189  300
```
Converts to:
```
X=153  Y=152  TIME_FROM=0    TIME_TO=155
X=184  Y=189  TIME_FROM=155  TIME_TO=300
```
i.e. each row's cumulative time becomes its `TIME_TO`, and its `TIME_FROM` is simply the previous row's `TIME_TO` (or `0` for the first row).

---

## 4. The Two Supported Scanpath Formats

| Format | Columns (after mapping) | Conversion |
|---|---|---|
| **A — Explicit** | `X, Y, START, END` | Passthrough rename only |
| **B — Cumulative** | `X, Y, T` (T = elapsed time when fixation *ends*, measured from recording start = 0) | Chain: `START[i] = END[i-1]` (or 0), `END[i] = T[i]` |

Both end up as the same internal schema: `SUBJECT, X, Y, TIME_FROM, TIME_TO`.

---

## 5. File 3 — Changes to `app.py`

1. **New stores**
   ```python
   dcc.Store(id='data-source-mode', data='builtin'),
   dcc.Store(id='custom-image-store'),       # {b64, width, height}
   dcc.Store(id='custom-scanpaths-store'),    # {subject: df.to_json()}
   ```
2. **New layout branch** — controls bar renders built-in dropdowns or the upload widgets from `upload_panel.py` depending on `data-source-mode`.
3. **Participants dropdown population** — in custom mode, options come from `custom-scanpaths-store.keys()` instead of `FixaTons.info.subjects(...)`.
4. **`generate_figure` dispatch** — cleanest approach: refactor the existing `make_*_figure` functions to take **raw inputs** (`image_array, image_width, image_height, df_scanpath_aoi`) instead of `db_name, stimulus`, with two thin wrapper paths above them:
   - *Built-in path*: fetches via `FixaTons.get.*` (as today) then calls the shared figure function.
   - *Custom path*: reads from the two new stores, concatenates the selected participants' DataFrames, calls `scanpath_converter.assign_aoi(...)`, then calls the **same** shared figure function.

   This avoids duplicating all nine chart functions for a second data source.
5. **Per-chart-type impact in custom mode**:
   - `stimulus`, `scanpath`, `scanpath_overlay`, `scarf`, `aoi_timeline`, `3d_scanpath`, `3d_scatter`, `transition`, `detection` — all work once the wrapper above supplies a raw image array + a tagged scanpath DataFrame. `detection` (YOLO) and segmentation already operate on raw arrays, so literally zero change needed there.
   - `attention` — currently calls `FixaTons.show.attention_map(...)`. Needs a local replacement (a Gaussian-blurred fixation-density heatmap — `scipy.ndimage.gaussian_filter` is already imported, so this is a small new function, not a new dependency).
   - `coassociation` — calls `compute_coa.compute_coasso(db_name, ...)`, which is keyed off on-disk dataset structure. **Flag as a known gap**: either disable this option in the plot-type dropdown when in custom mode, or scope a follow-up to make it accept in-memory DataFrames directly. Recommend disabling for v1.
6. **AOI drawing/clearing logic** (`handle_aoi` callback) — already operates purely on `relayoutData` from whichever graph is showing, so it needs no changes; it just needs to also fire when the custom stimulus image is the one being drawn on.

---

## 6. Validation & Limits (defaults — confirm or adjust)

| Rule | Default |
|---|---|
| Image extensions | `.png .jpg .jpeg .bmp .webp` |
| Max image size | 10 MB |
| Scanpath extensions | `.csv .tsv .txt` |
| Max scanpath files per session | 10 |
| Max size per scanpath file | 5 MB |
| Row with non-numeric cell | Drop row, report count to user, don't hard-fail the whole file |
| `END < START` after conversion | Reject that row, surface a warning |
| Empty file / all rows rejected | Hard error, file not added |
| Persistence | In-memory only for the session (no server-side disk storage) — simplest, and avoids needing cleanup/retention logic |

---

## 7. Open Decisions Before You Start Building

1. **Co-association Matrix in custom mode** — disable it for now, or is it worth scoping the rewrite immediately?
2. **Per-batch vs. per-file mapping** — confirm one shared mapping for all scanpath files in a session is fine (recommended), vs. needing per-file remapping as a first-class (not just "advanced") option.
3. **Sample/template download** — worth adding example files for both formats in the instructions panel, or skip for v1?
4. **Limits in §6** — any of these need to be different for your actual data (e.g., do you expect files larger than 5 MB, or more than 10 participants at once)?

---

## 8. Suggested Build Order

1. `scanpath_converter.py` — pure functions, easiest to unit-test in isolation with your sample file and the 3-column example.
2. `upload_panel.py` — UI layer, depends on #1 for the "Apply Mapping" preview.
3. `app.py` — mode toggle, stores, and the built-in/custom wrapper split around `generate_figure`.