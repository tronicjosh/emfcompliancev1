"""
EMF Compliance Analysis Dashboard - Interactive Configuration Builder

A web interface for RF/telecom engineers to configure base stations,
place antennas, and assess EMF regulatory compliance.

The frontend builds configuration; the backend (C++) performs all calculations.
"""

import streamlit as st
import subprocess
import os
import sys
import json
import yaml
import tempfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrow, Circle, Wedge
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from copy import deepcopy

# Page configuration
st.set_page_config(
    page_title="EMF Compliance Analysis Tool",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
EXECUTABLE = PROJECT_ROOT / "build" / "emfcompliance"
PATTERNS_DIR = PROJECT_ROOT / "data" / "patterns"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AntennaDefinition:
    """Definition of an antenna on a base station.

    Each antenna is independently configured with its own radiation pattern,
    frequency, power, position offset, and orientation (azimuth/tilt).
    Azimuth and tilt are runtime orientation transforms applied to the pattern.
    """
    id: str
    antenna_type: str  # From library
    pattern_file: str
    frequency_mhz: float
    power_eirp_watts: float
    azimuth_deg: float
    tilt_deg: float
    height_offset: float  # Relative to base station tower height
    enabled: bool = True


@dataclass
class BaseStation:
    """A base station is a container of antennas at a specific location."""
    id: str
    name: str
    x: float
    y: float
    tower_height: float
    antennas: List[AntennaDefinition] = field(default_factory=list)


@dataclass
class SimulationConfig:
    """Full simulation configuration."""
    name: str = "EMF Analysis"
    # Grid settings
    x_min: float = -100.0
    x_max: float = 100.0
    y_min: float = -100.0
    y_max: float = 100.0
    z_level: float = 1.5
    resolution: float = 1.0
    # Compliance settings
    standard: str = "ICNIRP_2020"
    category: str = "general_public"


# ============================================================================
# ANTENNA LIBRARY
# ============================================================================

ANTENNA_LIBRARY = {
    "Isotropic": {
        "description": "Ideal isotropic radiator (0 dBi)",
        "pattern_file": "isotropic",
        "default_frequency": 1800.0,
        "bands": ["All"]
    },
    "700 MHz Panel": {
        "description": "Typical 700 MHz LTE panel antenna",
        "pattern_file": "isotropic",  # Replace with actual MSI file
        "default_frequency": 700.0,
        "bands": ["700 MHz"]
    },
    "900 MHz Panel": {
        "description": "Typical 900 MHz GSM/LTE panel antenna",
        "pattern_file": "isotropic",
        "default_frequency": 900.0,
        "bands": ["900 MHz"]
    },
    "1800 MHz Panel": {
        "description": "Typical 1800 MHz LTE panel antenna",
        "pattern_file": "isotropic",
        "default_frequency": 1800.0,
        "bands": ["1800 MHz"]
    },
    "2100 MHz Panel": {
        "description": "Typical 2100 MHz UMTS/LTE panel antenna",
        "pattern_file": "isotropic",
        "default_frequency": 2100.0,
        "bands": ["2100 MHz"]
    },
    "2600 MHz Panel": {
        "description": "Typical 2600 MHz LTE panel antenna",
        "pattern_file": "isotropic",
        "default_frequency": 2600.0,
        "bands": ["2600 MHz"]
    },
    "3500 MHz Panel (5G)": {
        "description": "Typical 3.5 GHz 5G NR panel antenna",
        "pattern_file": "isotropic",
        "default_frequency": 3500.0,
        "bands": ["3500 MHz"]
    },
}

COMPLIANCE_STANDARDS = {
    "ICNIRP_2020": "ICNIRP 2020 Guidelines",
    "FCC": "FCC OET-65",
    "ICASA": "ICASA (South Africa)"
}

EXPOSURE_CATEGORIES = {
    "general_public": "General Public",
    "occupational": "Occupational"
}

# Preset configurations for common deployments
PRESETS = {
    "3-Sector Macro (1800 MHz)": {
        "description": "Standard 3-sector macro site with 120° separation",
        "antennas": [
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 0.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 120.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 240.0, "tilt_deg": -3.0, "height_offset": 0.0},
        ]
    },
    "3-Sector Macro (Multi-band)": {
        "description": "3-sector with 900 MHz and 1800 MHz per sector",
        "antennas": [
            {"antenna_type": "900 MHz Panel", "frequency_mhz": 900.0, "power_eirp_watts": 80.0, "azimuth_deg": 0.0, "tilt_deg": -2.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 0.0, "tilt_deg": -4.0, "height_offset": -0.5},
            {"antenna_type": "900 MHz Panel", "frequency_mhz": 900.0, "power_eirp_watts": 80.0, "azimuth_deg": 120.0, "tilt_deg": -2.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 120.0, "tilt_deg": -4.0, "height_offset": -0.5},
            {"antenna_type": "900 MHz Panel", "frequency_mhz": 900.0, "power_eirp_watts": 80.0, "azimuth_deg": 240.0, "tilt_deg": -2.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 240.0, "tilt_deg": -4.0, "height_offset": -0.5},
        ]
    },
    "6-Sector Site": {
        "description": "6-sector site with 60° separation",
        "antennas": [
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 0.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 60.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 120.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 180.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 240.0, "tilt_deg": -3.0, "height_offset": 0.0},
            {"antenna_type": "1800 MHz Panel", "frequency_mhz": 1800.0, "power_eirp_watts": 100.0, "azimuth_deg": 300.0, "tilt_deg": -3.0, "height_offset": 0.0},
        ]
    },
    "Single Omni": {
        "description": "Single omnidirectional antenna",
        "antennas": [
            {"antenna_type": "Isotropic", "frequency_mhz": 1800.0, "power_eirp_watts": 50.0, "azimuth_deg": 0.0, "tilt_deg": 0.0, "height_offset": 0.0},
        ]
    },
}

# Color palette for antennas (based on index)
ANTENNA_COLORS = [
    '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c',
    '#e67e22', '#34495e', '#16a085', '#c0392b', '#2980b9', '#27ae60'
]

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if 'base_stations' not in st.session_state:
        st.session_state.base_stations = []
    if 'sim_config' not in st.session_state:
        st.session_state.sim_config = SimulationConfig()
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    if 'report' not in st.session_state:
        st.session_state.report = None
    if 'selected_point' not in st.session_state:
        st.session_state.selected_point = None
    if 'next_bs_id' not in st.session_state:
        st.session_state.next_bs_id = 1
    if 'next_ant_id' not in st.session_state:
        st.session_state.next_ant_id = 1


# ============================================================================
# CONFIGURATION GENERATION
# ============================================================================

def generate_yaml_config() -> str:
    """Generate YAML configuration from current session state.

    All enabled antennas from all base stations are written explicitly
    to the YAML with their full configuration.
    """
    config = st.session_state.sim_config
    base_stations = st.session_state.base_stations

    yaml_dict = {
        'name': config.name,
        'grid': {
            'x_min': config.x_min,
            'x_max': config.x_max,
            'y_min': config.y_min,
            'y_max': config.y_max,
            'z_level': config.z_level,
            'resolution': config.resolution
        },
        'compliance': {
            'standard': config.standard,
            'category': config.category
        },
        'antennas': []
    }

    # Flatten all antennas from all base stations
    for bs in base_stations:
        for ant in bs.antennas:
            if not ant.enabled:
                continue
            yaml_dict['antennas'].append({
                'id': f"{bs.id}_{ant.id}",
                'pattern_file': ant.pattern_file,
                'frequency_mhz': ant.frequency_mhz,
                'power_eirp_watts': ant.power_eirp_watts,
                'position': {
                    'x': bs.x,
                    'y': bs.y,
                    'z': bs.tower_height + ant.height_offset
                },
                'orientation': {
                    'azimuth_deg': ant.azimuth_deg,
                    'tilt_deg': ant.tilt_deg
                }
            })

    return yaml.dump(yaml_dict, default_flow_style=False, sort_keys=False)


def run_analysis(config_yaml: str) -> Tuple[bool, str]:
    """Run the C++ analysis with the given configuration."""
    if not EXECUTABLE.exists():
        return False, f"Executable not found at {EXECUTABLE}. Please build the project first:\ncd build && cmake .. && make"

    # Write config to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [str(EXECUTABLE), "-v", "-o", str(OUTPUT_DIR), config_path],
            capture_output=True,
            text=True,
            timeout=300
        )

        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr

        if result.returncode == 2:
            return False, f"Configuration error:\n{output}"

        # Load results
        results_csv = OUTPUT_DIR / "results.csv"
        report_json = OUTPUT_DIR / "report.json"

        if results_csv.exists():
            st.session_state.results_df = pd.read_csv(results_csv)
        if report_json.exists():
            with open(report_json) as f:
                st.session_state.report = json.load(f)

        return True, output

    except subprocess.TimeoutExpired:
        return False, "Analysis timed out (exceeded 5 minutes)"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        os.unlink(config_path)


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_map_view(show_results: bool = False) -> plt.Figure:
    """Create map view with base stations and optional results overlay."""
    config = st.session_state.sim_config
    base_stations = st.session_state.base_stations

    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot results heatmap if available
    if show_results and st.session_state.results_df is not None:
        df = st.session_state.results_df
        x_unique = np.sort(df['x'].unique())
        y_unique = np.sort(df['y'].unique())

        pivot = df.pivot_table(
            values='percentage_of_limit',
            index='y',
            columns='x',
            aggfunc='mean'
        ).reindex(index=y_unique, columns=x_unique)

        X, Y = np.meshgrid(x_unique, y_unique)
        Z = np.clip(pivot.values, 0, 150)

        # Traffic light colormap
        from matplotlib.colors import LinearSegmentedColormap
        colors = ['#27ae60', '#f1c40f', '#e67e22', '#e74c3c', '#8e44ad']
        nodes = [0.0, 0.5, 0.8, 1.0, 1.5]
        norm_nodes = [n / 1.5 for n in nodes]
        cmap = LinearSegmentedColormap.from_list('compliance', list(zip(norm_nodes, colors)))

        im = ax.pcolormesh(X, Y, Z, cmap=cmap, vmin=0, vmax=150, shading='auto', alpha=0.8)
        cbar = fig.colorbar(im, ax=ax, label='% of Exposure Limit', shrink=0.8)
        cbar.set_ticks([0, 25, 50, 75, 100, 125, 150])

        # Add 100% contour
        try:
            contour = ax.contour(X, Y, pivot.values, levels=[100], colors=['red'], linewidths=2, linestyles='--')
            ax.clabel(contour, fmt='100%%', fontsize=9)
        except:
            pass

    # Plot grid boundary
    ax.add_patch(plt.Rectangle(
        (config.x_min, config.y_min),
        config.x_max - config.x_min,
        config.y_max - config.y_min,
        fill=False, edgecolor='gray', linestyle='--', linewidth=1
    ))

    # Plot base stations and antennas
    for bs in base_stations:
        # Base station marker
        ax.plot(bs.x, bs.y, 'ko', markersize=12, zorder=10)
        ax.annotate(bs.name, (bs.x, bs.y), xytext=(5, 5),
                   textcoords='offset points', fontsize=9, fontweight='bold')

        # Draw each antenna as a direction arrow and wedge
        for ant_idx, ant in enumerate(bs.antennas):
            if not ant.enabled:
                continue

            # Color based on antenna index
            color = ANTENNA_COLORS[ant_idx % len(ANTENNA_COLORS)]

            # Draw direction arrow
            arrow_length = 15
            dx = arrow_length * np.cos(np.radians(ant.azimuth_deg))
            dy = arrow_length * np.sin(np.radians(ant.azimuth_deg))

            ax.annotate('', xy=(bs.x + dx, bs.y + dy), xytext=(bs.x, bs.y),
                       arrowprops=dict(arrowstyle='->', color=color, lw=2))

            # Draw sector wedge (65 degree beamwidth typical)
            wedge = Wedge((bs.x, bs.y), 20, ant.azimuth_deg - 32.5, ant.azimuth_deg + 32.5,
                         alpha=0.2, color=color)
            ax.add_patch(wedge)

    # Set axis properties
    ax.set_xlim(config.x_min - 10, config.x_max + 10)
    ax.set_ylim(config.y_min - 10, config.y_max + 10)
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.set_title('Site Map - Base Station Layout')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def create_results_figure() -> plt.Figure:
    """Create comprehensive results visualization."""
    if st.session_state.results_df is None:
        return None

    df = st.session_state.results_df
    report = st.session_state.report or {}

    fig = plt.figure(figsize=(14, 10))

    # Get data for plots
    x_unique = np.sort(df['x'].unique())
    y_unique = np.sort(df['y'].unique())

    # Field strength plot
    ax1 = fig.add_subplot(221)
    pivot_field = df.pivot_table(values='field_value_v_m', index='y', columns='x').reindex(index=y_unique, columns=x_unique)
    X, Y = np.meshgrid(x_unique, y_unique)
    im1 = ax1.pcolormesh(X, Y, pivot_field.values, cmap='viridis', shading='auto')
    fig.colorbar(im1, ax=ax1, label='E-field (V/m)')
    ax1.set_title('Electric Field Strength')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_aspect('equal')

    # Percentage plot
    ax2 = fig.add_subplot(222)
    pivot_pct = df.pivot_table(values='percentage_of_limit', index='y', columns='x').reindex(index=y_unique, columns=x_unique)
    from matplotlib.colors import LinearSegmentedColormap
    colors = ['#27ae60', '#f1c40f', '#e67e22', '#e74c3c']
    cmap = LinearSegmentedColormap.from_list('compliance', colors)
    Z_clip = np.clip(pivot_pct.values, 0, 100)
    im2 = ax2.pcolormesh(X, Y, Z_clip, cmap=cmap, vmin=0, vmax=100, shading='auto')
    fig.colorbar(im2, ax=ax2, label='% of Limit')
    try:
        ax2.contour(X, Y, pivot_pct.values, levels=[100], colors=['black'], linewidths=2, linestyles='--')
    except:
        pass
    ax2.set_title('Percentage of Exposure Limit')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_aspect('equal')

    # Compliance status plot
    ax3 = fig.add_subplot(223)
    status_map = {'COMPLIANT': 0, 'MARGINAL': 1, 'NON_COMPLIANT': 2}
    df_copy = df.copy()
    df_copy['status_num'] = df_copy['status'].map(status_map)
    pivot_status = df_copy.pivot_table(values='status_num', index='y', columns='x').reindex(index=y_unique, columns=x_unique)
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap_status = ListedColormap(['#27ae60', '#f39c12', '#e74c3c'])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap_status.N)
    im3 = ax3.pcolormesh(X, Y, pivot_status.values, cmap=cmap_status, norm=norm, shading='auto')
    cbar3 = fig.colorbar(im3, ax=ax3, ticks=[0, 1, 2])
    cbar3.ax.set_yticklabels(['Compliant', 'Marginal', 'Exceeds'])
    ax3.set_title('Compliance Status')
    ax3.set_xlabel('X (m)')
    ax3.set_ylabel('Y (m)')
    ax3.set_aspect('equal')

    # Summary text
    ax4 = fig.add_subplot(224)
    ax4.axis('off')

    summary = report.get('summary', {})
    metadata = report.get('metadata', {})

    summary_text = f"""
EMF Compliance Analysis Summary
{'='*35}

Standard: {metadata.get('standard', 'N/A')}
Category: {metadata.get('category', 'N/A').replace('_', ' ').title()}

Total Points: {summary.get('total_points', 0):,}
Compliant: {summary.get('compliant_points', 0):,}
Marginal: {summary.get('marginal_points', 0):,}
Non-Compliant: {summary.get('non_compliant_points', 0):,}

Max Field: {summary.get('max_field_value_v_m', 0):.3f} V/m
Max % of Limit: {summary.get('max_percentage_of_limit', 0):.1f}%

Overall: {'COMPLIANT' if summary.get('overall_compliant', False) else 'NON-COMPLIANT'}
"""

    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Add base station markers to plots
    for bs in st.session_state.base_stations:
        for ax in [ax1, ax2, ax3]:
            ax.plot(bs.x, bs.y, 'r^', markersize=8)

    plt.suptitle(metadata.get('simulation_name', 'EMF Analysis'), fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    return fig


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_antenna_library():
    """Render the antenna library panel in sidebar."""
    st.sidebar.header("📚 Antenna Library")

    selected_type = st.sidebar.selectbox(
        "Select Antenna Type",
        options=list(ANTENNA_LIBRARY.keys()),
        help="Choose an antenna type to add to a base station"
    )

    if selected_type:
        ant_info = ANTENNA_LIBRARY[selected_type]
        st.sidebar.caption(ant_info['description'])
        st.sidebar.caption(f"Bands: {', '.join(ant_info['bands'])}")
        st.sidebar.caption(f"Default freq: {ant_info['default_frequency']} MHz")

    return selected_type


def render_simulation_controls():
    """Render simulation control panel in sidebar."""
    st.sidebar.header("⚙️ Simulation Settings")

    config = st.session_state.sim_config

    # Compliance standard
    config.standard = st.sidebar.selectbox(
        "Compliance Standard",
        options=list(COMPLIANCE_STANDARDS.keys()),
        format_func=lambda x: COMPLIANCE_STANDARDS[x],
        index=list(COMPLIANCE_STANDARDS.keys()).index(config.standard)
    )

    config.category = st.sidebar.selectbox(
        "Exposure Category",
        options=list(EXPOSURE_CATEGORIES.keys()),
        format_func=lambda x: EXPOSURE_CATEGORIES[x],
        index=list(EXPOSURE_CATEGORIES.keys()).index(config.category)
    )

    st.sidebar.subheader("Grid Settings")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        config.x_min = st.number_input("X Min (m)", value=config.x_min, step=10.0)
        config.y_min = st.number_input("Y Min (m)", value=config.y_min, step=10.0)
    with col2:
        config.x_max = st.number_input("X Max (m)", value=config.x_max, step=10.0)
        config.y_max = st.number_input("Y Max (m)", value=config.y_max, step=10.0)

    config.z_level = st.sidebar.number_input(
        "Evaluation Height (m)",
        value=config.z_level,
        min_value=0.0,
        max_value=50.0,
        step=0.5,
        help="Height above ground for field evaluation (1.5m = typical human height)"
    )

    config.resolution = st.sidebar.number_input(
        "Grid Resolution (m)",
        value=config.resolution,
        min_value=0.5,
        max_value=10.0,
        step=0.5,
        help="Spacing between calculation points"
    )

    # Calculate grid info
    nx = int((config.x_max - config.x_min) / config.resolution) + 1
    ny = int((config.y_max - config.y_min) / config.resolution) + 1
    st.sidebar.caption(f"Grid: {nx} x {ny} = {nx*ny:,} points")


def render_base_station_panel(selected_antenna_type: str):
    """Render base station configuration panel."""
    st.header("🗼 Base Station Configuration")

    # Add new base station
    st.subheader("Add New Base Station")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        new_bs_name = st.text_input("Name", value=f"Site_{st.session_state.next_bs_id}", key="new_bs_name")
    with col2:
        new_bs_x = st.number_input("X (m)", value=0.0, step=10.0, key="new_bs_x")
    with col3:
        new_bs_y = st.number_input("Y (m)", value=0.0, step=10.0, key="new_bs_y")
    with col4:
        new_bs_height = st.number_input("Tower Height (m)", value=30.0, min_value=1.0, step=5.0, key="new_bs_h")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("➕ Add Empty Base Station", type="primary"):
            new_bs = BaseStation(
                id=f"BS{st.session_state.next_bs_id}",
                name=new_bs_name,
                x=new_bs_x,
                y=new_bs_y,
                tower_height=new_bs_height,
                antennas=[]
            )
            st.session_state.base_stations.append(new_bs)
            st.session_state.next_bs_id += 1
            st.rerun()

    with col2:
        # Preset dropdown
        preset_name = st.selectbox(
            "Or add from preset:",
            options=["Select a preset..."] + list(PRESETS.keys()),
            key="preset_select"
        )
        if preset_name != "Select a preset..." and st.button("➕ Add Preset"):
            preset = PRESETS[preset_name]
            new_bs = BaseStation(
                id=f"BS{st.session_state.next_bs_id}",
                name=new_bs_name,
                x=new_bs_x,
                y=new_bs_y,
                tower_height=new_bs_height,
                antennas=[]
            )
            # Add antennas from preset (fully editable)
            for ant_def in preset['antennas']:
                ant_info = ANTENNA_LIBRARY[ant_def['antenna_type']]
                new_ant = AntennaDefinition(
                    id=f"ANT{st.session_state.next_ant_id}",
                    antenna_type=ant_def['antenna_type'],
                    pattern_file=ant_info['pattern_file'],
                    frequency_mhz=ant_def['frequency_mhz'],
                    power_eirp_watts=ant_def['power_eirp_watts'],
                    azimuth_deg=ant_def['azimuth_deg'],
                    tilt_deg=ant_def['tilt_deg'],
                    height_offset=ant_def['height_offset'],
                    enabled=True
                )
                new_bs.antennas.append(new_ant)
                st.session_state.next_ant_id += 1
            st.session_state.base_stations.append(new_bs)
            st.session_state.next_bs_id += 1
            st.rerun()

    st.divider()

    # Display and edit existing base stations
    for bs_idx, bs in enumerate(st.session_state.base_stations):
        with st.expander(f"📍 {bs.name} ({len(bs.antennas)} antennas)", expanded=True):
            # Base station properties
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            with col1:
                bs.name = st.text_input("Name", value=bs.name, key=f"bs_name_{bs_idx}")
            with col2:
                bs.x = st.number_input("X (m)", value=bs.x, step=10.0, key=f"bs_x_{bs_idx}")
            with col3:
                bs.y = st.number_input("Y (m)", value=bs.y, step=10.0, key=f"bs_y_{bs_idx}")
            with col4:
                bs.tower_height = st.number_input("Tower (m)", value=bs.tower_height, min_value=1.0, key=f"bs_h_{bs_idx}")
            with col5:
                if st.button("🗑️ Delete Site", key=f"del_bs_{bs_idx}"):
                    st.session_state.base_stations.pop(bs_idx)
                    st.rerun()

            st.markdown("---")

            # Add antenna section
            st.markdown("**Add Antenna:**")
            col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1, 1, 1, 1, 1])
            with col1:
                add_ant_type = st.selectbox(
                    "Type",
                    options=list(ANTENNA_LIBRARY.keys()),
                    index=list(ANTENNA_LIBRARY.keys()).index(selected_antenna_type),
                    key=f"add_ant_type_{bs_idx}",
                    label_visibility="collapsed"
                )
                ant_info = ANTENNA_LIBRARY[add_ant_type]
            with col2:
                # Frequency is only editable for isotropic (frequency-agnostic) patterns
                is_isotropic = "All" in ant_info['bands']
                if is_isotropic:
                    ant_freq = st.number_input("Freq (MHz)", value=ant_info['default_frequency'], key=f"ant_freq_{bs_idx}")
                else:
                    ant_freq = ant_info['default_frequency']
                    st.text_input("Freq (MHz)", value=f"{ant_freq}", disabled=True, key=f"ant_freq_{bs_idx}")
            with col3:
                ant_power = st.number_input("EIRP (W)", value=100.0, min_value=0.1, key=f"ant_power_{bs_idx}")
            with col4:
                ant_azimuth = st.number_input("Azimuth (°)", value=0.0, min_value=0.0, max_value=359.0, key=f"ant_az_{bs_idx}")
            with col5:
                ant_tilt = st.number_input("Tilt (°)", value=-3.0, min_value=-45.0, max_value=45.0, key=f"ant_tilt_{bs_idx}")
            with col6:
                ant_height_offset = st.number_input("H offset (m)", value=0.0, min_value=-10.0, max_value=10.0, key=f"ant_ho_{bs_idx}")

            if st.button(f"➕ Add Antenna", key=f"add_ant_{bs_idx}"):
                new_ant = AntennaDefinition(
                    id=f"ANT{st.session_state.next_ant_id}",
                    antenna_type=add_ant_type,
                    pattern_file=ant_info['pattern_file'],
                    frequency_mhz=ant_freq,
                    power_eirp_watts=ant_power,
                    azimuth_deg=ant_azimuth,
                    tilt_deg=ant_tilt,
                    height_offset=ant_height_offset,
                    enabled=True
                )
                bs.antennas.append(new_ant)
                st.session_state.next_ant_id += 1
                st.rerun()

            # List existing antennas
            if bs.antennas:
                st.markdown("**Antennas:**")

                # Header row
                cols = st.columns([0.4, 1.5, 1, 1, 1, 1, 0.8, 0.4])
                cols[0].markdown("**On**")
                cols[1].markdown("**Type**")
                cols[2].markdown("**Freq (MHz)**")
                cols[3].markdown("**EIRP (W)**")
                cols[4].markdown("**Azimuth (°)**")
                cols[5].markdown("**Tilt (°)**")
                cols[6].markdown("**H offset (m)**")
                cols[7].markdown("**Del**")

                for ant_idx, ant in enumerate(bs.antennas):
                    cols = st.columns([0.4, 1.5, 1, 1, 1, 1, 0.8, 0.4])
                    with cols[0]:
                        ant.enabled = st.checkbox("", value=ant.enabled, key=f"ant_en_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                    with cols[1]:
                        # Show color indicator and type
                        color = ANTENNA_COLORS[ant_idx % len(ANTENNA_COLORS)]
                        st.markdown(f'<span style="color:{color}">●</span> {ant.antenna_type}', unsafe_allow_html=True)
                    with cols[2]:
                        # Frequency is only editable for isotropic patterns
                        ant_lib_info = ANTENNA_LIBRARY.get(ant.antenna_type, {})
                        is_isotropic = "All" in ant_lib_info.get('bands', [])
                        if is_isotropic:
                            ant.frequency_mhz = st.number_input("f", value=ant.frequency_mhz, key=f"ant_f_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                        else:
                            st.text_input("f", value=f"{ant.frequency_mhz}", disabled=True, key=f"ant_f_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                    with cols[3]:
                        ant.power_eirp_watts = st.number_input("p", value=ant.power_eirp_watts, key=f"ant_p_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                    with cols[4]:
                        ant.azimuth_deg = st.number_input("a", value=ant.azimuth_deg, min_value=0.0, max_value=359.0, key=f"ant_a_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                    with cols[5]:
                        ant.tilt_deg = st.number_input("t", value=ant.tilt_deg, min_value=-45.0, max_value=45.0, key=f"ant_t_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                    with cols[6]:
                        ant.height_offset = st.number_input("h", value=ant.height_offset, min_value=-10.0, max_value=10.0, key=f"ant_h_{bs_idx}_{ant_idx}", label_visibility="collapsed")
                    with cols[7]:
                        if st.button("🗑️", key=f"del_ant_{bs_idx}_{ant_idx}"):
                            bs.antennas.pop(ant_idx)
                            st.rerun()


def render_point_inspector():
    """Render numerical point inspection tool."""
    if st.session_state.results_df is None:
        return

    st.subheader("🔍 Point Inspector")

    df = st.session_state.results_df
    config = st.session_state.sim_config

    col1, col2 = st.columns(2)
    with col1:
        inspect_x = st.number_input(
            "X coordinate (m)",
            min_value=float(df['x'].min()),
            max_value=float(df['x'].max()),
            value=0.0,
            step=config.resolution
        )
    with col2:
        inspect_y = st.number_input(
            "Y coordinate (m)",
            min_value=float(df['y'].min()),
            max_value=float(df['y'].max()),
            value=0.0,
            step=config.resolution
        )

    # Find nearest point
    distances = np.sqrt((df['x'] - inspect_x)**2 + (df['y'] - inspect_y)**2)
    nearest_idx = distances.idxmin()
    point = df.loc[nearest_idx]

    st.markdown(f"""
    **Location:** ({point['x']:.1f}, {point['y']:.1f}, {point['z']:.1f}) m

    | Quantity | Value |
    |----------|-------|
    | Electric Field | {point['field_value_v_m']:.4f} V/m |
    | Exposure Limit | {point['limit_v_m']:.2f} V/m |
    | % of Limit | {point['percentage_of_limit']:.2f}% |
    | Status | **{point['status']}** |
    """)

    # Show distance to each base station
    st.markdown("**Distance to Base Stations:**")
    for bs in st.session_state.base_stations:
        dist = np.sqrt((point['x'] - bs.x)**2 + (point['y'] - bs.y)**2 + (point['z'] - bs.tower_height)**2)
        st.write(f"- {bs.name}: {dist:.1f} m")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    init_session_state()

    st.title("📡 EMF Compliance Analysis Tool")
    st.caption("Interactive configuration builder for RF/telecom engineers")

    # Sidebar
    selected_antenna_type = render_antenna_library()
    render_simulation_controls()

    # Run analysis button in sidebar
    st.sidebar.divider()

    # Count enabled antennas
    total_antennas = sum(
        1 for bs in st.session_state.base_stations
        for ant in bs.antennas if ant.enabled
    )

    st.sidebar.metric("Total Antennas", total_antennas)

    can_run = total_antennas > 0

    if st.sidebar.button("🚀 Run EMF Analysis", type="primary", disabled=not can_run):
        config_yaml = generate_yaml_config()

        with st.spinner("Running EMF analysis..."):
            success, output = run_analysis(config_yaml)

        if success:
            st.sidebar.success("Analysis complete!")
        else:
            st.sidebar.error("Analysis failed")
            st.error(output)

    if not can_run:
        st.sidebar.warning("Add at least one antenna to run analysis")

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗼 Base Stations",
        "🗺️ Map View",
        "📊 Results",
        "🔍 Inspector",
        "📄 Configuration"
    ])

    with tab1:
        render_base_station_panel(selected_antenna_type)

    with tab2:
        st.header("Site Map")
        show_results = st.checkbox("Show EMF Results Overlay", value=st.session_state.results_df is not None)
        fig = create_map_view(show_results=show_results and st.session_state.results_df is not None)
        st.pyplot(fig)
        plt.close(fig)

    with tab3:
        st.header("Analysis Results")
        if st.session_state.results_df is not None:
            # Summary metrics
            report = st.session_state.report or {}
            summary = report.get('summary', {})

            is_compliant = summary.get('overall_compliant', False)
            if is_compliant:
                st.success("✅ COMPLIANT - All points within exposure limits")
            else:
                st.error("❌ NON-COMPLIANT - Some points exceed exposure limits")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Max Field", f"{summary.get('max_field_value_v_m', 0):.3f} V/m")
            with col2:
                st.metric("Max % of Limit", f"{summary.get('max_percentage_of_limit', 0):.1f}%")
            with col3:
                st.metric("Compliant Points", f"{summary.get('compliant_points', 0):,}")
            with col4:
                st.metric("Non-Compliant", f"{summary.get('non_compliant_points', 0):,}")

            # Results visualization
            fig = create_results_figure()
            if fig:
                st.pyplot(fig)
                plt.close(fig)

            # Compliance boundaries
            boundaries = report.get('compliance_boundaries', {})
            if boundaries:
                st.subheader("Compliance Boundary Distances")
                for ant_id, dist in boundaries.items():
                    st.write(f"**{ant_id}**: {dist:.1f} m")
        else:
            st.info("Run an analysis to see results")

    with tab4:
        st.header("Numerical Point Inspection")
        if st.session_state.results_df is not None:
            render_point_inspector()

            # Worst-case point
            st.subheader("Worst-Case Exposure")
            df = st.session_state.results_df
            max_idx = df['percentage_of_limit'].idxmax()
            worst = df.loc[max_idx]
            st.markdown(f"""
            **Location:** ({worst['x']:.1f}, {worst['y']:.1f}, {worst['z']:.1f}) m

            - Electric Field: **{worst['field_value_v_m']:.4f} V/m**
            - % of Limit: **{worst['percentage_of_limit']:.2f}%**
            - Status: **{worst['status']}**
            """)
        else:
            st.info("Run an analysis to inspect points")

    with tab5:
        st.header("Generated Configuration")

        if st.session_state.base_stations:
            config_yaml = generate_yaml_config()
            st.code(config_yaml, language='yaml')

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Config (YAML)",
                    config_yaml,
                    file_name="emf_config.yaml",
                    mime="text/yaml"
                )

            if st.session_state.results_df is not None:
                with col2:
                    csv_data = st.session_state.results_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Results (CSV)",
                        csv_data,
                        file_name="emf_results.csv",
                        mime="text/csv"
                    )
        else:
            st.info("Add base stations to generate configuration")


if __name__ == "__main__":
    main()
