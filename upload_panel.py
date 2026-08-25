"""
upload_panel.py — All UI components and callbacks for custom data upload.
Provides layout builders and a register_callbacks(app) function.
"""

import base64
import io
import os
import json

import numpy as np
import pandas as pd
from PIL import Image
from dash import dcc, html, Input, Output, State, ctx, no_update, dash_table
import dash_bootstrap_components as dbc
import dash

import scanpath_converter as sc
import re

def secure_filename(filename):
    """Sanitize filename to prevent path traversal and basic injection, preserving spaces."""
    # Remove path separators and risky shell/html characters
    return re.sub(r'[<>\/\\|&:;$]', '_', filename)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

ALLOWED_IMAGE_EXTENSIONS = sc.ALLOWED_IMAGE_EXTENSIONS
ALLOWED_VIDEO_EXTENSIONS = sc.ALLOWED_VIDEO_EXTENSIONS
ALLOWED_STIMULUS_EXTENSIONS = sc.ALLOWED_STIMULUS_EXTENSIONS
MAX_IMAGE_SIZE_MB = sc.MAX_IMAGE_SIZE_MB
MAX_VIDEO_SIZE_MB = sc.MAX_VIDEO_SIZE_MB
ALLOWED_SCANPATH_EXTENSIONS = {'.csv', '.tsv', '.txt'}
MAX_SCANPATH_FILES = 10
MAX_SCANPATH_SIZE_MB = 5


# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def make_mode_toggle():
    """Segmented control: Built-in Datasets / My Own Data / K-Coefficient Data."""
    return html.Div([
        html.Div([
            html.Button(
                '📊 Built-in Datasets',
                id='btn-mode-builtin',
                n_clicks=0,
                className='mode-toggle-btn mode-toggle-active',
            ),
            html.Button(
                '📁 My Own Data',
                id='btn-mode-custom',
                n_clicks=0,
                className='mode-toggle-btn',
            ),
            html.Button(
                '🧠 K-Coefficient Dataset',
                id='btn-mode-kdataset',
                n_clicks=0,
                className='mode-toggle-btn',
            ),
        ], className='mode-toggle-group'),
    ], style={'display': 'flex', 'alignItems': 'center'})


def make_image_upload():
    """Stimulus upload widget (image or video) with thumbnail preview."""
    # Build accept string for both images and videos
    accept_types = list(ALLOWED_IMAGE_EXTENSIONS) + [
        'video/mp4', 'video/avi', 'video/quicktime', 'video/webm',
        'video/x-matroska',
    ] + list(ALLOWED_VIDEO_EXTENSIONS)
    return html.Div([
        html.Label('Stimulus (Image or Video)', className='control-label'),
        dcc.Upload(
            id='custom-image-upload',
            children=html.Div([
                html.I(className='bi bi-cloud-arrow-up', style={'fontSize': '20px', 'marginRight': '8px'}),
                html.Span('Drop image/video or click to browse'),
            ], className='upload-zone-content'),
            className='upload-zone',
            multiple=False,
        ),
        # Thumbnail preview and loading state
        dcc.Loading(
            id="loading-image-upload",
            type="circle",
            color="#3f51b5",
            children=[
                html.Div(id='image-preview-container', children=[], style={'marginTop': '6px'}),
                html.Div(id='image-upload-error', className='upload-error')
            ]
        ),
    ], style={'flex': '1', 'minWidth': '180px'})


def make_scanpath_upload():
    """Scanpath file(s) upload widget with file list."""
    return html.Div([
        html.Label('Scanpath Files', className='control-label'),
        dcc.Upload(
            id='custom-scanpath-upload',
            children=html.Div([
                html.I(className='bi bi-file-earmark-arrow-up', style={'fontSize': '20px', 'marginRight': '8px'}),
                html.Span('Drop scanpath file(s) or click'),
            ], className='upload-zone-content'),
            className='upload-zone',
            multiple=True,
            accept=','.join(ALLOWED_SCANPATH_EXTENSIONS),
        ),
        # File chips and loading state
        dcc.Loading(
            id="loading-scanpath-upload",
            type="circle",
            color="#3f51b5",
            children=[
                html.Div(id='scanpath-file-chips', children=[], style={'marginTop': '6px', 'display': 'flex', 'flexWrap': 'wrap', 'gap': '4px'}),
                html.Div(id='scanpath-upload-error', className='upload-error')
            ]
        ),
    ], style={'flex': '1.5', 'minWidth': '200px'})


def make_instructions_block():
    """Static instructions explaining file format requirements."""
    return html.Div([
        html.Div([
            html.Div([
                html.I(className='bi bi-info-circle-fill', style={'marginRight': '8px', 'color': '#3f51b5'}),
                html.Span('File Format Guide', style={'fontWeight': '700', 'fontSize': '14px'}),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '12px'}),
            
            html.Div([
                html.P([
                    html.Strong('No header row'), ' — Your file should contain only numeric data, one fixation per line.'
                ], style={'margin': '0 0 8px', 'fontSize': '13px'}),
                
                html.P([
                    html.Strong('Delimiter: '), 'Auto-detected (comma, tab, or whitespace).'
                ], style={'margin': '0 0 8px', 'fontSize': '13px'}),
                
                html.P([
                    html.Strong('Supported time formats:'),
                ], style={'margin': '0 0 4px', 'fontSize': '13px'}),
                
                html.Div([
                    html.Div([
                        html.Div('Format A — Explicit Start & End', style={
                            'fontWeight': '600', 'fontSize': '12px', 'color': '#3f51b5', 'marginBottom': '4px'
                        }),
                        html.Code('516 373 0.004 0.267', style={'fontSize': '12px', 'display': 'block'}),
                        html.Code('502 449 0.400 0.496', style={'fontSize': '12px', 'display': 'block'}),
                        html.Div('→ X=516 Y=373 START=0.004 END=0.267', style={'fontSize': '11px', 'color': '#666', 'marginTop': '4px'}),
                    ], className='format-example-card'),
                    
                    html.Div([
                        html.Div('Format B — Cumulative Time', style={
                            'fontWeight': '600', 'fontSize': '12px', 'color': '#e53935', 'marginBottom': '4px'
                        }),
                        html.Code('153 152 155', style={'fontSize': '12px', 'display': 'block'}),
                        html.Code('184 189 300', style={'fontSize': '12px', 'display': 'block'}),
                        html.Div('→ X=153 Y=152 FROM=0 TO=155', style={'fontSize': '11px', 'color': '#666', 'marginTop': '4px'}),
                    ], className='format-example-card'),
                ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'}),
            ]),
        ], className='instructions-panel'),
    ], id='instructions-container')


def make_format_selector():
    """Radio: 4-column explicit vs 3-column cumulative."""
    return html.Div([
        html.Label('Time Format', className='control-label'),
        dcc.RadioItems(
            id='format-type-radio',
            options=[
                {'label': ' My file has Start & End time (4 columns)', 'value': 'explicit'},
                {'label': ' My file has one cumulative time value (3 columns)', 'value': 'cumulative'},
            ],
            value='explicit',
            className='format-radio-group',
            labelStyle={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '6px', 'fontSize': '13px'},
        ),
    ], style={'marginBottom': '12px'})


def make_mapping_panel():
    """The full mapping panel: format selector + column mapper + preview + actions."""
    return html.Div([
        html.Div([
            # Header
            html.Div([
                html.Div([
                    html.I(className='bi bi-table', style={'marginRight': '8px', 'fontSize': '18px'}),
                    html.Span('Column Mapping', style={'fontWeight': '700', 'fontSize': '15px'}),
                ], style={'display': 'flex', 'alignItems': 'center'}),
                html.Button(
                    html.I(className='bi bi-x-lg'),
                    id='btn-close-mapping',
                    n_clicks=0,
                    className='mapping-close-btn',
                ),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '12px'}),
            
            # Compact instructions (one-liner + collapsible detail)
            html.Details([
                html.Summary('ℹ️ File Format Guide (click to expand)', style={'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': '600', 'color': '#3f51b5', 'marginBottom': '8px'}),
                make_instructions_block(),
            ], open=False, style={'marginBottom': '12px'}),
            
            # Format selector
            make_format_selector(),
            
            # Column mapper (dynamic)
            html.Div(id='column-mapper-container', children=[]),
            
            # Validation error
            html.Div(id='mapping-validation-error', className='upload-error'),
            
            # Action buttons row (Apply + Confirm side by side)
            html.Div([
                html.Button('Apply Mapping & Preview', id='btn-apply-mapping', n_clicks=0,
                            className='btn-apply-mapping', disabled=True),
                # Confirm button container (inline, shown after preview)
                html.Div(id='confirm-container', children=[], style={'display': 'inline-flex'}),
            ], style={'marginTop': '12px', 'display': 'flex', 'gap': '12px', 'alignItems': 'center', 'flexWrap': 'wrap'}),

            # Preview table
            html.Div(id='preview-table-container', children=[], style={'marginTop': '12px'}),
            
        ], className='mapping-panel'),
    ], id='mapping-panel-container', style={'display': 'none'})



def make_replace_confirm_modal():
    """Confirmation modal shown when user uploads a new stimulus image
    while existing data is loaded."""
    return dbc.Modal([
        dbc.ModalHeader(
            dbc.ModalTitle(
                html.Div([
                    html.I(className='bi bi-exclamation-triangle-fill',
                           style={'color': '#e53935', 'marginRight': '10px',
                                  'fontSize': '20px'}),
                    html.Span('Replace Stimulus?'),
                ], style={'display': 'flex', 'alignItems': 'center'}),
            ),
            close_button=False,
        ),
        dbc.ModalBody(
            html.Div([
                html.P('Uploading a new stimulus image will:',
                       style={'fontWeight': '600', 'marginBottom': '8px'}),
                html.Ul([
                    html.Li('Replace the current stimulus image'),
                    html.Li('Remove all uploaded scanpath files'),
                    html.Li('Clear participant selections'),
                ], style={'color': '#555', 'marginBottom': '12px'}),
                html.P('Do you want to continue?',
                       style={'fontWeight': '500'}),
            ])
        ),
        dbc.ModalFooter([
            html.Button('Cancel', id='btn-replace-cancel', n_clicks=0,
                        style={'padding': '6px 18px', 'border': '1px solid #ccc',
                               'borderRadius': '6px', 'background': 'white',
                               'cursor': 'pointer', 'fontWeight': '600',
                               'fontSize': '13px'}),
            html.Button('Yes, Replace', id='btn-replace-confirm', n_clicks=0,
                        style={'padding': '6px 18px', 'border': 'none',
                               'borderRadius': '6px', 'cursor': 'pointer',
                               'fontWeight': '600', 'fontSize': '13px',
                               'background': '#e53935', 'color': 'white'}),
        ]),
    ], id='replace-confirm-modal', is_open=False, centered=True, backdrop='static')


def make_custom_controls():
    """Full custom-mode controls container."""
    return html.Div([
        make_image_upload(),
        make_scanpath_upload(),
        make_replace_confirm_modal(),
        dcc.Store(id='pending-image-store'),
        dcc.Store(id='pending-image-preview-data'),
        dcc.Store(id='custom-keyframes-store'),  # Stores extracted key frames from video
    ], id='custom-controls-container', style={
        'display': 'none',
        'gap': '16px',
        'alignItems': 'flex-start',
        'flex': '2',
    })


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════

def register_callbacks(app):
    """Register all upload-panel callbacks on the Dash app."""
    
    # ── Mode toggle ──
    @app.callback(
        Output('data-source-mode', 'data'),
        Output('btn-mode-builtin', 'className'),
        Output('btn-mode-custom', 'className'),
        Output('btn-mode-kdataset', 'className'),
        Output('builtin-controls-container', 'style'),
        Output('custom-controls-container', 'style'),
        Output('k-controls-container', 'style'),
        Output('ddParticipants-left', 'options', allow_duplicate=True),
        Output('ddParticipants-left', 'value', allow_duplicate=True),
        Output('ddParticipants-right', 'options', allow_duplicate=True),
        Output('ddParticipants-right', 'value', allow_duplicate=True),
        Output('left-plot-type', 'value', allow_duplicate=True),
        Output('right-plot-type', 'value', allow_duplicate=True),
        [Input('btn-mode-builtin', 'n_clicks'),
         Input('btn-mode-custom', 'n_clicks'),
         Input('btn-mode-kdataset', 'n_clicks')],
        [State('custom-scanpaths-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_mode(builtin_clicks, custom_clicks, kdataset_clicks, custom_scanpaths):
        trigger = ctx.triggered_id

        if trigger == 'btn-mode-custom':
            # Switching TO custom mode — restore participants from stored data
            participant_options = []
            participant_values = []
            if custom_scanpaths:
                try:
                    store = json.loads(custom_scanpaths)
                    participant_options = [{'label': s, 'value': s}
                                           for s in store.keys()]
                    participant_values = list(store.keys())
                except Exception:
                    pass
            return (
                'custom',
                'mode-toggle-btn',
                'mode-toggle-btn mode-toggle-active',
                'mode-toggle-btn',
                {'display': 'none'},
                {'display': 'flex', 'gap': '16px',
                 'alignItems': 'flex-start', 'flex': '2'},
                {'display': 'none'},
                participant_options,
                participant_values,
                participant_options,
                participant_values,
                'stimulus',
                'attention',
            )
        elif trigger == 'btn-mode-kdataset':
            # Switching TO K-Coefficient Dataset mode
            import k_dataset
            participant_options = [{'label': str(p), 'value': str(p)} for p in k_dataset.K_PARTICIPANTS]
            participant_values = [str(k_dataset.K_PARTICIPANTS[0])] if k_dataset.K_PARTICIPANTS else []
            return (
                'k_dataset',
                'mode-toggle-btn',
                'mode-toggle-btn',
                'mode-toggle-btn mode-toggle-active',
                {'display': 'none'},
                {'display': 'none'},
                {'display': 'flex', 'gap': '16px', 'alignItems': 'flex-start', 'flex': '2'},
                participant_options,
                participant_values,
                participant_options,
                participant_values,
                'stimulus',
                'attention',
            )
        else:
            # Switching TO builtin mode — clear participants (will be repopulated
            # by the dataset/stimulus callbacks)
            return (
                'builtin',
                'mode-toggle-btn mode-toggle-active',
                'mode-toggle-btn',
                'mode-toggle-btn',
                {'display': 'contents'},
                {'display': 'none', 'gap': '16px',
                 'alignItems': 'flex-start', 'flex': '2'},
                {'display': 'none'},
                [],
                [],
                [],
                [],
                'stimulus',
                'attention',
            )
    
    # ── Image/Video upload ──
    @app.callback(
        Output('custom-image-store', 'data', allow_duplicate=True),
        Output('image-preview-container', 'children'),
        Output('image-upload-error', 'children'),
        Output('replace-confirm-modal', 'is_open'),
        Output('pending-image-store', 'data'),
        Output('pending-image-preview-data', 'data'),
        Output('custom-keyframes-store', 'data'),
        Input('custom-image-upload', 'contents'),
        State('custom-image-upload', 'filename'),
        State('custom-image-store', 'data'),
        State('custom-scanpaths-store', 'data'),
        prevent_initial_call=True
    )
    def handle_image_upload(contents, filename, existing_image,
                            existing_scanpaths):
        if contents is None:
            return (no_update,) * 7

        filename = secure_filename(filename)
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_STIMULUS_EXTENSIONS:
            return (no_update, no_update,
                    f'❌ Invalid type: {ext}. '
                    f'Allowed: {", ".join(sorted(ALLOWED_STIMULUS_EXTENSIONS))}',
                    False, None, None, no_update)

        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            size_mb = len(decoded) / (1024 * 1024)

            # ── VIDEO UPLOAD ──
            if ext in ALLOWED_VIDEO_EXTENSIONS:
                if size_mb > MAX_VIDEO_SIZE_MB:
                    return (no_update, no_update,
                            f'❌ Video too large: {size_mb:.1f} MB '
                            f'(max {MAX_VIDEO_SIZE_MB} MB)',
                            False, None, None, no_update)

                # Extract key frames
                try:
                    key_frames = sc.extract_key_frames(decoded)
                except Exception as e:
                    return (no_update, no_update,
                            f'❌ Error extracting key frames: {str(e)}',
                            False, None, None, no_update)

                if not key_frames:
                    return (no_update, no_update,
                            '❌ Could not extract any frames from video',
                            False, None, None, no_update)

                # Build video preview (show filename + frame count)
                preview = html.Div([
                    html.I(className='bi bi-film',
                           style={'fontSize': '32px', 'color': '#3f51b5',
                                  'marginRight': '10px'}),
                    html.Div([
                        html.Span(filename,
                                  style={'fontWeight': '600', 'fontSize': '12px'}),
                        html.Span(
                            f'{len(key_frames)} key frames extracted • '
                            f'{size_mb:.1f} MB',
                            className='image-dimensions-badge'),
                    ], style={'display': 'flex', 'flexDirection': 'column',
                              'gap': '2px'}),
                ], className='image-preview-row')

                # Store the first key frame as the default stimulus
                first = key_frames[0]
                t_end_first = first['timestamp_sec'] if first['timestamp_sec'] > 0.0 else (key_frames[1]['timestamp_sec'] if len(key_frames) > 1 else None)
                store_data = {
                    'b64': first['image_b64'],
                    'width': first['width'],
                    'height': first['height'],
                    'filename': f"{filename} — Frame {first['frame_index']}",
                    'content_type': 'data:image/jpeg;base64',
                    'is_video_frame': True,
                    'keyframe_time_start': 0.0,
                    'keyframe_time_end': t_end_first,
                }

                keyframes_json = json.dumps(key_frames)

                # Check if existing data would be lost
                has_existing = (existing_image is not None
                                and existing_scanpaths is not None)
                if has_existing:
                    preview_info = {
                        'src': f'data:image/jpeg;base64,{first["image_b64"]}',
                        'filename': filename,
                        'width': first['width'],
                        'height': first['height'],
                        'is_video': True,
                        'keyframes_json': keyframes_json,
                    }
                    return (no_update, no_update, '',
                            True, store_data,
                            json.dumps(preview_info), no_update)
                else:
                    return (store_data, preview, '',
                            False, None, None, keyframes_json)

            # ── IMAGE UPLOAD ──
            else:
                if size_mb > MAX_IMAGE_SIZE_MB:
                    return (no_update, no_update,
                            f'❌ Too large: {size_mb:.1f} MB '
                            f'(max {MAX_IMAGE_SIZE_MB} MB)',
                            False, None, None, no_update)

                img = Image.open(io.BytesIO(decoded))
                width, height = img.size

                store_data = {
                    'b64': content_string,
                    'width': width,
                    'height': height,
                    'filename': filename,
                    'content_type': content_type,
                }

                preview = html.Div([
                    html.Img(src=contents, className='image-thumbnail'),
                    html.Div([
                        html.Span(filename,
                                  style={'fontWeight': '600', 'fontSize': '12px'}),
                        html.Span(f'{width} × {height}px',
                                  className='image-dimensions-badge'),
                    ], style={'display': 'flex', 'flexDirection': 'column',
                              'gap': '2px'}),
                ], className='image-preview-row')

                # Check if there's existing data that would be lost
                has_existing = (existing_image is not None
                                and existing_scanpaths is not None)
                if has_existing:
                    preview_info = {
                        'src': contents,
                        'filename': filename,
                        'width': width,
                        'height': height,
                    }
                    return (no_update, no_update, '',
                            True, store_data,
                            json.dumps(preview_info), no_update)
                else:
                    # No existing data — apply directly, clear keyframes
                    return (store_data, preview, '',
                            False, None, None, None)

        except Exception as e:
            return (no_update, no_update,
                    f'❌ Error reading file: {str(e)}',
                    False, None, None, no_update)

    # ── Modal: Confirm Replace ──
    @app.callback(
        Output('custom-image-store', 'data', allow_duplicate=True),
        Output('image-preview-container', 'children', allow_duplicate=True),
        Output('replace-confirm-modal', 'is_open', allow_duplicate=True),
        Output('custom-scanpaths-store', 'data', allow_duplicate=True),
        Output('custom-raw-scanpaths-store', 'data', allow_duplicate=True),
        Output('scanpath-file-chips', 'children', allow_duplicate=True),
        Output('ddParticipants-left', 'options', allow_duplicate=True),
        Output('ddParticipants-left', 'value', allow_duplicate=True),
        Output('ddParticipants-right', 'options', allow_duplicate=True),
        Output('ddParticipants-right', 'value', allow_duplicate=True),
        Output('mapping-panel-container', 'style', allow_duplicate=True),
        Output('custom-keyframes-store', 'data', allow_duplicate=True),
        Input('btn-replace-confirm', 'n_clicks'),
        State('pending-image-store', 'data'),
        State('pending-image-preview-data', 'data'),
        prevent_initial_call=True
    )
    def confirm_replace_image(n_clicks, pending_image, pending_preview_json):
        if not n_clicks or not pending_image:
            return (no_update,) * 12

        # Build preview from pending data
        preview_info = json.loads(pending_preview_json)
        is_video = preview_info.get('is_video', False)

        if is_video:
            preview = html.Div([
                html.I(className='bi bi-film',
                       style={'fontSize': '32px', 'color': '#3f51b5',
                              'marginRight': '10px'}),
                html.Div([
                    html.Span(preview_info['filename'],
                              style={'fontWeight': '600', 'fontSize': '12px'}),
                    html.Span(
                        f'{preview_info["width"]} × {preview_info["height"]}px',
                        className='image-dimensions-badge'),
                ], style={'display': 'flex', 'flexDirection': 'column',
                          'gap': '2px'}),
            ], className='image-preview-row')
            keyframes_json = preview_info.get('keyframes_json', None)
        else:
            preview = html.Div([
                html.Img(src=preview_info['src'],
                         className='image-thumbnail'),
                html.Div([
                    html.Span(preview_info['filename'],
                              style={'fontWeight': '600', 'fontSize': '12px'}),
                    html.Span(
                        f'{preview_info["width"]} × {preview_info["height"]}px',
                        className='image-dimensions-badge'),
                ], style={'display': 'flex', 'flexDirection': 'column',
                          'gap': '2px'}),
            ], className='image-preview-row')
            keyframes_json = None  # clear keyframes for image upload

        # Apply new image + clear all scanpath data
        return (
            pending_image,        # custom-image-store
            preview,              # image-preview-container
            False,                # close modal
            None,                 # clear custom-scanpaths-store
            None,                 # clear custom-raw-scanpaths-store
            [],                   # clear file chips
            [],                   # clear left participants options
            [],                   # clear left participants value
            [],                   # clear right participants options
            [],                   # clear right participants value
            {'display': 'none'},  # hide mapping panel
            keyframes_json,       # update keyframes store
        )

    # ── Modal: Cancel Replace ──
    @app.callback(
        Output('replace-confirm-modal', 'is_open', allow_duplicate=True),
        Output('pending-image-store', 'data', allow_duplicate=True),
        Input('btn-replace-cancel', 'n_clicks'),
        prevent_initial_call=True
    )
    def cancel_replace_image(n_clicks):
        if not n_clicks:
            return no_update, no_update
        return False, None
    
    # ── Scanpath upload (merges with existing files) ──
    @app.callback(
        Output('custom-raw-scanpaths-store', 'data'),
        Output('scanpath-file-chips', 'children'),
        Output('scanpath-upload-error', 'children'),
        Output('mapping-panel-container', 'style'),
        Output('column-mapper-container', 'children'),
        Output('btn-apply-mapping', 'disabled'),
        Input('custom-scanpath-upload', 'contents'),
        State('custom-scanpath-upload', 'filename'),
        State('format-type-radio', 'value'),
        State('custom-raw-scanpaths-store', 'data'),
        prevent_initial_call=True
    )
    def handle_scanpath_upload(contents_list, filenames, format_type,
                               existing_raw_data):
        if contents_list is None:
            return (no_update,) * 6

        if not isinstance(contents_list, list):
            contents_list = [contents_list]
            filenames = [filenames]

        filenames = [secure_filename(f) for f in filenames]

        # Load existing raw texts if any
        raw_texts = {}
        existing_chips = []
        if existing_raw_data:
            try:
                raw_texts = json.loads(existing_raw_data)
                # Build chips for already-loaded files
                for subj in raw_texts:
                    existing_chips.append(
                        html.Span(f'✓ {subj}',
                                  className='file-chip file-chip-accepted'))
            except Exception:
                pass

        # Validate total count
        if len(contents_list) + len(raw_texts) > MAX_SCANPATH_FILES:
            return (no_update, existing_chips,
                    f'❌ Too many files total: '
                    f'{len(contents_list) + len(raw_texts)} '
                    f'(max {MAX_SCANPATH_FILES})',
                    no_update, no_update, no_update)

        new_accepted = []
        rejected_chips = []

        for content, fname in zip(contents_list, filenames):
            _, ext = os.path.splitext(fname.lower())

            if ext not in ALLOWED_SCANPATH_EXTENSIONS:
                rejected_chips.append(
                    html.Span(f'❌ {fname} (bad type)',
                              className='file-chip file-chip-rejected'))
                continue

            try:
                _, content_string = content.split(',')
                decoded = base64.b64decode(content_string)

                size_mb = len(decoded) / (1024 * 1024)
                if size_mb > MAX_SCANPATH_SIZE_MB:
                    rejected_chips.append(
                        html.Span(f'❌ {fname} ({size_mb:.1f}MB)',
                                  className='file-chip file-chip-rejected'))
                    continue

                raw_text = decoded.decode('utf-8', errors='replace')
                subject_name = os.path.splitext(fname)[0]

                if subject_name in raw_texts:
                    rejected_chips.append(
                        html.Span(f'❌ {fname} (duplicate)',
                                  className='file-chip file-chip-rejected'))
                    continue

                raw_texts[subject_name] = raw_text
                new_accepted.append(
                    html.Span(f'✓ {fname}',
                              className='file-chip file-chip-accepted'))
            except Exception as e:
                rejected_chips.append(
                    html.Span(f'❌ {fname} ({str(e)})',
                              className='file-chip file-chip-rejected'))

        if not raw_texts:
            return (None, rejected_chips,
                    '❌ No valid scanpath files accepted',
                    {'display': 'none'}, [], True)

        all_chips = existing_chips + new_accepted + rejected_chips

        # Sniff format from the newest file to build column mapper
        newest_subject = list(raw_texts.keys())[-1]
        newest_text = raw_texts[newest_subject]

        try:
            delimiter = sc.sniff_delimiter(newest_text)
            df_preview, _ = sc.parse_raw_table(newest_text, delimiter)
            columns = df_preview.columns.tolist()
            mapper = _build_column_mapper(columns, format_type)

            return (json.dumps(raw_texts), all_chips, '',
                    {'display': 'block'}, mapper, False)
        except Exception as e:
            return (json.dumps(raw_texts), all_chips,
                    f'❌ Error parsing newest file: {str(e)}',
                    {'display': 'none'}, [], True)
    
    # ── Format radio change → update mapper ──
    @app.callback(
        Output('column-mapper-container', 'children', allow_duplicate=True),
        Input('format-type-radio', 'value'),
        State('custom-raw-scanpaths-store', 'data'),
        prevent_initial_call=True
    )
    def update_mapper_on_format_change(format_type, raw_data):
        if not raw_data:
            return no_update
        
        raw_texts = json.loads(raw_data)
        first_text = list(raw_texts.values())[0]
        
        try:
            delimiter = sc.sniff_delimiter(first_text)
            df_preview, _ = sc.parse_raw_table(first_text, delimiter)
            columns = df_preview.columns.tolist()
            return _build_column_mapper(columns, format_type)
        except Exception:
            return no_update
    
    # ── Apply Mapping → Convert & Preview ──
    @app.callback(
        Output('preview-table-container', 'children'),
        Output('confirm-container', 'children'),
        Output('mapping-validation-error', 'children'),
        Input('btn-apply-mapping', 'n_clicks'),
        State('custom-raw-scanpaths-store', 'data'),
        State('format-type-radio', 'value'),
        [State({'type': 'col-mapping-dd', 'index': dash.ALL}, 'value')],
        prevent_initial_call=True
    )
    def apply_mapping(n_clicks, raw_data, format_type, col_values):
        if not n_clicks or not raw_data:
            return no_update, no_update, no_update
        
        # Build column_mapping from dropdown values
        if format_type == 'explicit':
            required = {'X', 'Y', 'START', 'END'}
        else:
            required = {'X', 'Y', 'T'}
        
        # Validate: all required meanings assigned, no duplicates
        assigned = {}
        for i, val in enumerate(col_values):
            if val and val != 'IGNORE':
                if val in assigned:
                    return [], [], f'❌ "{val}" is assigned to multiple columns'
                assigned[val] = i
        
        missing = required - set(assigned.keys())
        if missing:
            return [], [], f'❌ Missing required mappings: {", ".join(missing)}'
        
        column_mapping = assigned
        
        # Try converting the first file for preview
        raw_texts = json.loads(raw_data)
        first_subject = list(raw_texts.keys())[0]
        first_text = raw_texts[first_subject]
        
        try:
            result = sc.standardize_scanpath(first_text, column_mapping, format_type, first_subject)
            df = result['df']
            
            # Build preview table (first 5 rows)
            preview_df = df.head(5)
            preview_table = html.Div([
                html.Div('Preview (first 5 rows of "' + first_subject + '")', style={
                    'fontWeight': '600', 'fontSize': '13px', 'marginBottom': '8px', 'color': '#3f51b5'
                }),
                dash_table.DataTable(
                    data=preview_df.to_dict('records'),
                    columns=[{'name': c, 'id': c} for c in preview_df.columns],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'center', 'padding': '8px', 'fontSize': '12px',
                                'fontFamily': 'monospace'},
                    style_header={'backgroundColor': '#e8eaf6', 'fontWeight': '700',
                                  'color': '#283593', 'fontSize': '12px'},
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#fafafa'}
                    ],
                ),
                html.Div(f'{len(result["bad_rows"])} unparseable rows skipped, {result["dropped_count"]} rows dropped during validation',
                         style={'fontSize': '11px', 'color': '#888', 'marginTop': '6px'})
                if result['bad_rows'] or result['dropped_count'] > 0 else None,
            ])
            
            # Store the mapping for confirm step
            confirm = html.Div([
                dcc.Store(id='confirmed-mapping-store', data=json.dumps({
                    'column_mapping': column_mapping,
                    'format_type': format_type,
                })),
                html.Button('✓ Confirm & Load All Files', id='btn-confirm-load', n_clicks=0,
                            className='btn-confirm-load'),
            ])
            
            return preview_table, confirm, ''
            
        except Exception as e:
            return [], [], f'❌ Conversion error: {str(e)}'
    
    # ── Confirm & Load ──
    @app.callback(
        Output('custom-scanpaths-store', 'data'),
        Output('ddParticipants-left', 'options', allow_duplicate=True),
        Output('ddParticipants-left', 'value', allow_duplicate=True),
        Output('ddParticipants-right', 'options', allow_duplicate=True),
        Output('ddParticipants-right', 'value', allow_duplicate=True),
        Output('mapping-panel-container', 'style', allow_duplicate=True),
        Output('scanpath-upload-error', 'children', allow_duplicate=True),
        Input('btn-confirm-load', 'n_clicks'),
        State('custom-raw-scanpaths-store', 'data'),
        State('confirmed-mapping-store', 'data'),
        prevent_initial_call=True
    )
    def confirm_and_load(n_clicks, raw_data, mapping_data):
        if not n_clicks or not raw_data or not mapping_data:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        raw_texts = json.loads(raw_data)
        mapping_info = json.loads(mapping_data)
        column_mapping = mapping_info['column_mapping']
        # Convert string keys back to ints for column indices
        column_mapping = {k: int(v) for k, v in column_mapping.items()}
        format_type = mapping_info['format_type']
        
        standardized = {}
        errors = []
        
        for subject_name, raw_text in raw_texts.items():
            try:
                result = sc.standardize_scanpath(raw_text, column_mapping, format_type, subject_name)
                standardized[subject_name] = result['df'].to_json(orient='split')
            except Exception as e:
                errors.append(f'{subject_name}: {str(e)}')
        
        if not standardized:
            return no_update, no_update, no_update, no_update, no_update, no_update, f'❌ All files failed: {"; ".join(errors)}'
        
        # Populate participants dropdown
        participant_options = [{'label': s, 'value': s} for s in standardized.keys()]
        participant_values = list(standardized.keys())
        
        error_msg = ''
        if errors:
            error_msg = f'⚠️ {len(errors)} file(s) failed: {"; ".join(errors)}'
        
        return (
            json.dumps(standardized),
            participant_options,
            participant_values,
            participant_options,
            participant_values,
            {'display': 'none'},
            error_msg,
        )
    
    # ── Close mapping panel ──
    @app.callback(
        Output('mapping-panel-container', 'style', allow_duplicate=True),
        Input('btn-close-mapping', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_mapping_panel(n_clicks):
        if n_clicks:
            return {'display': 'none'}
        return no_update

    # ── Store custom video URL for video player ──
    @app.callback(
        Output('custom-video-store', 'data'),
        Input('custom-image-upload', 'contents'),
        State('custom-image-upload', 'filename'),
        prevent_initial_call=True
    )
    def store_custom_video(contents, filename):
        if not contents or not filename:
            raise dash.exceptions.PreventUpdate
        
        filename = secure_filename(filename)
        _, ext = os.path.splitext(filename.lower())
        if ext in ALLOWED_VIDEO_EXTENSIONS:
            # Return the full data URL so the video player can use it as src
            return contents
        return no_update


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_column_mapper(columns, format_type):
    """Build column mapping dropdowns based on detected column count and format type."""
    num_cols = len(columns)
    if format_type == 'explicit':
        options = [
            {'label': 'X coordinate', 'value': 'X'},
            {'label': 'Y coordinate', 'value': 'Y'},
            {'label': 'Start time', 'value': 'START'},
            {'label': 'End time', 'value': 'END'},
            {'label': 'Saccade Amplitude', 'value': 'SACCADE_AMPLITUDE'},
            {'label': 'Raw K-Coefficient', 'value': 'K_i'},
            {'label': 'Squashed K-Coefficient', 'value': 'K_squashed'},
            {'label': 'Ignore this column', 'value': 'IGNORE'},
        ]
        fallback_defaults = {0: 'X', 1: 'Y', 2: 'START', 3: 'END'}
    else:
        options = [
            {'label': 'X coordinate', 'value': 'X'},
            {'label': 'Y coordinate', 'value': 'Y'},
            {'label': 'Cumulative time', 'value': 'T'},
            {'label': 'Saccade Amplitude', 'value': 'SACCADE_AMPLITUDE'},
            {'label': 'Raw K-Coefficient', 'value': 'K_i'},
            {'label': 'Squashed K-Coefficient', 'value': 'K_squashed'},
            {'label': 'Ignore this column', 'value': 'IGNORE'},
        ]
        fallback_defaults = {0: 'X', 1: 'Y', 2: 'T'}
    
    mapper_rows = []
    assigned_defaults = set()
    for i in range(num_cols):
        col_name = str(columns[i])
        
        # Smart mapping based on common K-Dataset column names
        default_val = 'IGNORE'
        col_lower = col_name.lower()
        
        if format_type == 'explicit':
            if col_lower in ['fixation_point_x', 'x'] or col_name == 'Col_1': default_val = 'X'
            elif col_lower in ['fixation_point_y', 'y'] or col_name == 'Col_2': default_val = 'Y'
            elif col_lower in ['fixation_starts_at_ms', 'start_time'] or col_name == 'Col_3': default_val = 'START'
            elif col_lower in ['fixation_ends_at_ms', 'end_time'] or col_name == 'Col_4': default_val = 'END'
            elif col_lower in ['saccade_length_px', 'saccade_amplitude_percent', 'saccade_amplitude']: default_val = 'SACCADE_AMPLITUDE'
            elif col_name == 'K_i': default_val = 'K_i'
            elif col_name == 'K_squashed': default_val = 'K_squashed'
            elif default_val == 'IGNORE':
                default_val = fallback_defaults.get(i, 'IGNORE') if col_name.startswith('Col_') else 'IGNORE'
        else:
            if col_lower in ['fixation_point_x', 'x'] or col_name == 'Col_1': default_val = 'X'
            elif col_lower in ['fixation_point_y', 'y'] or col_name == 'Col_2': default_val = 'Y'
            elif col_lower in ['fixation_ends_at_ms', 'time', 't'] or col_name == 'Col_3': default_val = 'T'
            elif col_lower in ['saccade_length_px', 'saccade_amplitude_percent', 'saccade_amplitude']: default_val = 'SACCADE_AMPLITUDE'
            elif col_name == 'K_i': default_val = 'K_i'
            elif col_name == 'K_squashed': default_val = 'K_squashed'
            elif default_val == 'IGNORE':
                default_val = fallback_defaults.get(i, 'IGNORE') if col_name.startswith('Col_') else 'IGNORE'
                
        # Prevent assigning the same meaning to multiple columns (except IGNORE)
        if default_val != 'IGNORE':
            if default_val in assigned_defaults:
                default_val = 'IGNORE'
            else:
                assigned_defaults.add(default_val)
                
        # truncate long column names for display
        display_name = col_name if len(col_name) <= 25 else col_name[:22] + "..."
                
        mapper_rows.append(
            html.Div([
                html.Span(f'Col {i + 1}: {display_name}', style={
                    'fontWeight': '600', 'fontSize': '12px', 'minWidth': '180px', 'maxWidth': '180px',
                    'color': '#555', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap'
                }, title=col_name),
                dcc.Dropdown(
                    id={'type': 'col-mapping-dd', 'index': i},
                    options=options,
                    value=default_val,
                    clearable=False,
                    style={'flex': '1', 'fontSize': '12px'},
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '6px'})
        )
    
    return html.Div([
        html.Div('Map each column to its meaning:', style={
            'fontWeight': '600', 'fontSize': '13px', 'marginBottom': '8px', 'color': '#333'
        }),
        *mapper_rows,
    ])
