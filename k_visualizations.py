import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import cv2
import urllib.request
import k_dataset
import scanpath_converter as sc
import FixaTons

def empty_figure(message="Select options to visualize"):
    fig = go.Figure()
    fig.update_layout(
        xaxis={"visible": False}, yaxis={"visible": False},
        annotations=[{
            "text": message, "xref": "paper", "yref": "paper",
            "showarrow": False, "font": {"size": 16}
        }],
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def _get_combined_df(participants, custom_dfs=None):
    dfs = []
    source_dfs = custom_dfs if custom_dfs is not None else k_dataset.K_DFS
    for p in participants:
        if p in source_dfs:
            df = source_dfs[p].copy()
            df['SUBJECT'] = str(p)
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def make_k_timeline_figure(participants, aoi_list, aoi_type_val, custom_dfs=None):
    if not participants:
        return empty_figure("Select at least one participant")
    
    df = _get_combined_df(participants, custom_dfs=custom_dfs)
    if df.empty or 'K_squashed' not in df.columns:
        return empty_figure("No K-coefficient data found for selected participants")
        
    # Convert time to seconds
    df['TIME_SEC'] = df['TIME_FROM'] / 1000.0

    # Sort and smooth K_squashed with rolling mean for each participant
    smoothed_dfs = []
    for pid in df['SUBJECT'].unique():
        p_df = df[df['SUBJECT'] == pid].copy()
        p_df = p_df.sort_values('TIME_SEC')
        # Window size 15 for smoothing
        p_df['K_squashed_smooth'] = p_df['K_squashed'].rolling(window=15, min_periods=1).mean()
        smoothed_dfs.append(p_df)
    
    if smoothed_dfs:
        df = pd.concat(smoothed_dfs, ignore_index=True)

    fig = px.line(
        df, 
        x='TIME_SEC', 
        y='K_squashed_smooth', 
        color='SUBJECT',
        title="K-Coefficient Timeline",
        labels={'TIME_SEC': 'Time (s)', 'K_squashed_smooth': 'Squashed K Coefficient', 'SUBJECT': 'Participant'},
        markers=False,
        line_shape='spline'
    )
    
    # Calculate dynamic Y-axis range from actual data
    y_min = df['K_squashed_smooth'].min()
    y_max = df['K_squashed_smooth'].max()
    # Add 15% padding
    y_padding = max(0.05, (y_max - y_min) * 0.15)
    y_range_min = min(y_min - y_padding, -0.05)  # Always include 0
    y_range_max = max(y_max + y_padding, 0.05)   # Always include 0
    
    # Get time range for scrubber line
    t_min = df['TIME_SEC'].min()
    
    # Add scrubber line FIRST so it's always shapes[0] for JS sync
    fig.add_shape(
        type='line',
        x0=t_min, x1=t_min,
        y0=y_range_min, y1=y_range_max,
        line=dict(color='red', width=2, dash='solid'),
        name='scrubber'
    )
    
    # Add colored zones for Focal (positive) and Ambient (negative)
    fig.add_hrect(y0=0, y1=y_range_max, line_width=0, fillcolor="rgba(144, 238, 144, 0.3)", annotation_text="Focal Inspection Phase (K > 0)", annotation_position="top left")
    fig.add_hrect(y0=y_range_min, y1=0, line_width=0, fillcolor="rgba(255, 160, 122, 0.3)", annotation_text="Ambient Search Phase (K < 0)", annotation_position="bottom left")
    
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis_range=[y_range_min, y_range_max],
        margin=dict(l=40, r=40, t=40, b=40),
    )
    # Add grid lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig

def make_k_colored_scanpath(participants, aoi_list, aoi_type_val, custom_dfs=None, custom_img_url=None, custom_w=None, custom_h=None):
    if not participants:
        return empty_figure("Select at least one participant")
        
    df = _get_combined_df(participants, custom_dfs=custom_dfs)
    if df.empty or 'K_squashed' not in df.columns:
        return empty_figure("No K-coefficient data found")
        
    # Standardize time for animation
    df['FRAME_TIME'] = (df['TIME_FROM'] / 100).astype(int) * 100
    
    # Get stimulus image
    img_url = custom_img_url if custom_img_url is not None else k_dataset.K_STIMULUS_URL
    w = custom_w if custom_w is not None else k_dataset.STIMULUS_WIDTH
    h = custom_h if custom_h is not None else k_dataset.STIMULUS_HEIGHT
    
    fig = px.scatter(
        df,
        x='X',
        y='Y',
        animation_frame='FRAME_TIME',
        animation_group='SUBJECT',
        color='K_squashed',
        size='ELAPSED_TIME',
        hover_name='SUBJECT',
        color_continuous_scale=px.colors.diverging.RdBu,
        range_color=[-0.5, 0.5],
        title="K-Colored Scanpath Animation"
    )
    
    if img_url:
        fig.add_layout_image(
            dict(
                source=img_url,
                xref="x",
                yref="y",
                x=0,
                y=0,
                sizex=w,
                sizey=h,
                sizing="stretch",
                opacity=0.8,
                layer="below"
            )
        )
        
    fig.update_xaxes(showgrid=False, range=[0, w], constrain="domain")
    fig.update_yaxes(showgrid=False, range=[h, 0], scaleanchor="x", scaleratio=1)
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title="K-Value (Red=Ambient, Blue=Focal)")
    )
    
    # Fix play button animation speed
    if 'updatemenus' in fig.layout:
        fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 100
        fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 0
        
    return fig

def make_k_heatmap_figure(participants, k_mode='focal', custom_dfs=None, custom_img_url=None, custom_w=None, custom_h=None):
    if not participants:
        return empty_figure("Select at least one participant")
        
    df = _get_combined_df(participants, custom_dfs=custom_dfs)
    if df.empty or 'K_squashed' not in df.columns:
        return empty_figure("No K-coefficient data found")
        
    # Filter based on mode
    if k_mode == 'focal':
        filtered_df = df[df['K_squashed'] > 0].copy()
        title = "Focal Fixations Heatmap (K > 0)"
        color_scale = 'Blues'
    else:
        filtered_df = df[df['K_squashed'] < 0].copy()
        title = "Ambient Fixations Heatmap (K < 0)"
        color_scale = 'Reds'
        
    if filtered_df.empty:
        return empty_figure(f"No {k_mode} fixations found for selected participants")
        
    # We will generate a density contour plot
    img_url = custom_img_url if custom_img_url is not None else k_dataset.K_STIMULUS_URL
    w = custom_w if custom_w is not None else k_dataset.STIMULUS_WIDTH
    h = custom_h if custom_h is not None else k_dataset.STIMULUS_HEIGHT
    
    fig = px.density_contour(
        filtered_df,
        x='X',
        y='Y',
        title=title,
        color_discrete_sequence=[px.colors.qualitative.Plotly[0] if k_mode == 'focal' else px.colors.qualitative.Plotly[1]]
    )
    
    fig.update_traces(contours_coloring="fill", contours_showlines=False, opacity=0.6)
    
    if img_url:
        fig.add_layout_image(
            dict(
                source=img_url,
                xref="x",
                yref="y",
                x=0,
                y=0,
                sizex=w,
                sizey=h,
                sizing="stretch",
                opacity=0.8,
                layer="below"
            )
        )
        
    fig.update_xaxes(showgrid=False, range=[0, w], constrain="domain")
    fig.update_yaxes(showgrid=False, range=[h, 0], scaleanchor="x", scaleratio=1)
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig
