"""
Visualization module for EMF compliance analysis.
Creates heat maps and compliance visualizations using matplotlib.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from typing import Dict, List, Optional, Tuple
import pandas as pd

from data_loader import pivot_to_grid


def create_field_heatmap(
    df: pd.DataFrame,
    title: str = "Electric Field Strength",
    antenna_positions: Optional[List[Dict]] = None,
    figsize: Tuple[int, int] = (10, 8),
    cmap: str = 'viridis'
) -> plt.Figure:
    """
    Create heat map of electric field strength.

    Args:
        df: Results DataFrame
        title: Plot title
        antenna_positions: List of antenna position dicts with 'x', 'y' keys
        figsize: Figure size tuple
        cmap: Colormap name

    Returns:
        matplotlib Figure object
    """
    X, Y, Z = pivot_to_grid(df, 'field_value_v_m')

    fig, ax = plt.subplots(figsize=figsize)

    # Create heat map
    im = ax.pcolormesh(X, Y, Z, cmap=cmap, shading='auto')
    cbar = fig.colorbar(im, ax=ax, label='Electric Field (V/m)')

    # Add antenna positions
    if antenna_positions:
        for ant in antenna_positions:
            ax.plot(ant['x'], ant['y'], 'r^', markersize=12, label=ant.get('id', 'Antenna'))

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(title)
    ax.set_aspect('equal')

    if antenna_positions:
        ax.legend(loc='upper right')

    plt.tight_layout()
    return fig


def create_percentage_heatmap(
    df: pd.DataFrame,
    title: str = "Percentage of Exposure Limit",
    antenna_positions: Optional[List[Dict]] = None,
    figsize: Tuple[int, int] = (10, 8)
) -> plt.Figure:
    """
    Create heat map with traffic light colors for percentage of limit.
    Green: < 50%, Yellow: 50-80%, Orange: 80-100%, Red: > 100%

    Args:
        df: Results DataFrame
        title: Plot title
        antenna_positions: List of antenna position dicts
        figsize: Figure size tuple

    Returns:
        matplotlib Figure object
    """
    X, Y, Z = pivot_to_grid(df, 'percentage_of_limit')

    fig, ax = plt.subplots(figsize=figsize)

    # Custom colormap: green -> yellow -> orange -> red
    colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#c0392b']
    nodes = [0.0, 0.5, 0.8, 1.0, 1.5]  # Normalize to 0-1 range for 0-150%

    # Normalize nodes to 0-1
    norm_nodes = [n / 1.5 for n in nodes]
    cmap = mcolors.LinearSegmentedColormap.from_list('compliance', list(zip(norm_nodes, colors)))

    # Normalize Z values (cap at 150% for visualization)
    Z_display = np.clip(Z, 0, 150)

    im = ax.pcolormesh(X, Y, Z_display, cmap=cmap, vmin=0, vmax=150, shading='auto')
    cbar = fig.colorbar(im, ax=ax, label='% of Limit')
    cbar.set_ticks([0, 25, 50, 75, 100, 125, 150])

    # Add 100% contour line
    try:
        contour = ax.contour(X, Y, Z, levels=[100], colors=['black'], linewidths=2, linestyles='--')
        ax.clabel(contour, fmt='100%%', fontsize=10)
    except ValueError:
        pass  # No contour if all values below or above threshold

    # Add antenna positions
    if antenna_positions:
        for ant in antenna_positions:
            ax.plot(ant['x'], ant['y'], 'k^', markersize=12)
            ax.annotate(ant.get('id', ''), (ant['x'], ant['y']),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(title)
    ax.set_aspect('equal')

    plt.tight_layout()
    return fig


def create_compliance_map(
    df: pd.DataFrame,
    title: str = "Compliance Status",
    antenna_positions: Optional[List[Dict]] = None,
    figsize: Tuple[int, int] = (10, 8)
) -> plt.Figure:
    """
    Create categorical compliance map (Compliant/Marginal/Non-compliant).

    Args:
        df: Results DataFrame
        title: Plot title
        antenna_positions: List of antenna position dicts
        figsize: Figure size tuple

    Returns:
        matplotlib Figure object
    """
    # Map status to numeric values
    status_map = {'COMPLIANT': 0, 'MARGINAL': 1, 'NON_COMPLIANT': 2}
    df_copy = df.copy()
    df_copy['status_num'] = df_copy['status'].map(status_map)

    X, Y, Z = pivot_to_grid(df_copy, 'status_num')

    fig, ax = plt.subplots(figsize=figsize)

    # Custom colormap for status
    colors = ['#2ecc71', '#f39c12', '#e74c3c']  # Green, Orange, Red
    cmap = mcolors.ListedColormap(colors)
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    im = ax.pcolormesh(X, Y, Z, cmap=cmap, norm=norm, shading='auto')

    # Create custom colorbar
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2])
    cbar.ax.set_yticklabels(['Compliant', 'Marginal', 'Non-Compliant'])

    # Add antenna positions
    if antenna_positions:
        for ant in antenna_positions:
            ax.plot(ant['x'], ant['y'], 'w^', markersize=12, markeredgecolor='black')
            ax.annotate(ant.get('id', ''), (ant['x'], ant['y']),
                       xytext=(5, 5), textcoords='offset points', fontsize=8, color='white')

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(title)
    ax.set_aspect('equal')

    plt.tight_layout()
    return fig


def create_compliance_boundary_plot(
    df: pd.DataFrame,
    boundaries: Dict[str, float],
    antenna_positions: List[Dict],
    title: str = "Compliance Boundaries",
    figsize: Tuple[int, int] = (10, 8)
) -> plt.Figure:
    """
    Create plot showing compliance boundaries around antennas.

    Args:
        df: Results DataFrame
        boundaries: Dict mapping antenna_id to boundary distance
        antenna_positions: List of antenna position dicts
        title: Plot title
        figsize: Figure size tuple

    Returns:
        matplotlib Figure object
    """
    X, Y, Z = pivot_to_grid(df, 'percentage_of_limit')

    fig, ax = plt.subplots(figsize=figsize)

    # Background heat map
    im = ax.pcolormesh(X, Y, Z, cmap='YlOrRd', alpha=0.5, shading='auto')
    fig.colorbar(im, ax=ax, label='% of Limit')

    # Add 100% contour
    try:
        contour = ax.contour(X, Y, Z, levels=[100], colors=['red'], linewidths=2)
        ax.clabel(contour, fmt='100%%', fontsize=10)
    except ValueError:
        pass

    # Add compliance boundary circles
    for ant in antenna_positions:
        ant_id = ant.get('id', 'unknown')
        if ant_id in boundaries:
            boundary_dist = boundaries[ant_id]
            circle = Circle((ant['x'], ant['y']), boundary_dist,
                           fill=False, color='blue', linewidth=2, linestyle='--',
                           label=f'{ant_id}: {boundary_dist:.1f}m')
            ax.add_patch(circle)

        # Mark antenna position
        ax.plot(ant['x'], ant['y'], 'k^', markersize=12)
        ax.annotate(ant_id, (ant['x'], ant['y']),
                   xytext=(5, 5), textcoords='offset points', fontsize=9)

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(title)
    ax.set_aspect('equal')
    ax.legend(loc='upper right')

    plt.tight_layout()
    return fig


def create_summary_figure(
    df: pd.DataFrame,
    report: Dict,
    figsize: Tuple[int, int] = (14, 10)
) -> plt.Figure:
    """
    Create comprehensive summary figure with multiple views.

    Args:
        df: Results DataFrame
        report: Report dictionary
        figsize: Figure size tuple

    Returns:
        matplotlib Figure object
    """
    fig = plt.figure(figsize=figsize)

    # Get antenna positions from report
    antenna_positions = []
    if 'antennas' in report:
        for ant in report['antennas']:
            antenna_positions.append({
                'id': ant['id'],
                'x': ant['position']['x'],
                'y': ant['position']['y']
            })

    # 2x2 grid of plots
    ax1 = fig.add_subplot(221)
    ax2 = fig.add_subplot(222)
    ax3 = fig.add_subplot(223)
    ax4 = fig.add_subplot(224)

    # Plot 1: Field strength
    X, Y, Z_field = pivot_to_grid(df, 'field_value_v_m')
    im1 = ax1.pcolormesh(X, Y, Z_field, cmap='viridis', shading='auto')
    fig.colorbar(im1, ax=ax1, label='V/m')
    ax1.set_title('Electric Field Strength')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_aspect('equal')

    # Plot 2: Percentage of limit
    X, Y, Z_pct = pivot_to_grid(df, 'percentage_of_limit')
    colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
    nodes = [0.0, 0.5, 0.8, 1.0]
    cmap = mcolors.LinearSegmentedColormap.from_list('compliance', list(zip(nodes, colors)))
    Z_pct_clip = np.clip(Z_pct, 0, 100)
    im2 = ax2.pcolormesh(X, Y, Z_pct_clip, cmap=cmap, vmin=0, vmax=100, shading='auto')
    fig.colorbar(im2, ax=ax2, label='% of Limit')
    try:
        ax2.contour(X, Y, Z_pct, levels=[100], colors=['black'], linewidths=2, linestyles='--')
    except ValueError:
        pass
    ax2.set_title('Percentage of Exposure Limit')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_aspect('equal')

    # Plot 3: Compliance status
    status_map = {'COMPLIANT': 0, 'MARGINAL': 1, 'NON_COMPLIANT': 2}
    df_copy = df.copy()
    df_copy['status_num'] = df_copy['status'].map(status_map)
    X, Y, Z_status = pivot_to_grid(df_copy, 'status_num')
    colors_status = ['#2ecc71', '#f39c12', '#e74c3c']
    cmap_status = mcolors.ListedColormap(colors_status)
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = mcolors.BoundaryNorm(bounds, cmap_status.N)
    im3 = ax3.pcolormesh(X, Y, Z_status, cmap=cmap_status, norm=norm, shading='auto')
    cbar3 = fig.colorbar(im3, ax=ax3, ticks=[0, 1, 2])
    cbar3.ax.set_yticklabels(['OK', 'Marginal', 'Exceeds'])
    ax3.set_title('Compliance Status')
    ax3.set_xlabel('X (m)')
    ax3.set_ylabel('Y (m)')
    ax3.set_aspect('equal')

    # Plot 4: Summary text
    ax4.axis('off')
    summary = report.get('summary', {})
    metadata = report.get('metadata', {})

    summary_text = f"""
    EMF Compliance Analysis Summary
    ================================
    Standard: {metadata.get('standard', 'N/A')}
    Category: {metadata.get('category', 'N/A')}

    Total Points: {summary.get('total_points', 'N/A'):,}
    Compliant: {summary.get('compliant_points', 0):,}
    Marginal (80-100%): {summary.get('marginal_points', 0):,}
    Non-Compliant: {summary.get('non_compliant_points', 0):,}

    Max Field: {summary.get('max_field_value_v_m', 0):.3f} V/m
    Max % of Limit: {summary.get('max_percentage_of_limit', 0):.1f}%

    Overall: {'COMPLIANT' if summary.get('overall_compliant', False) else 'NON-COMPLIANT'}
    """

    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Add antenna markers to field plots
    for ax in [ax1, ax2, ax3]:
        for ant in antenna_positions:
            ax.plot(ant['x'], ant['y'], 'r^', markersize=8)

    plt.suptitle(metadata.get('simulation_name', 'EMF Analysis'), fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    return fig
