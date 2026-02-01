"""
Streamlit dashboard for EMF Compliance Analysis.
Provides interactive visualization of C++ calculation results.
"""

import streamlit as st
import subprocess
import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import load_analysis_results, get_max_exposure_point, get_statistics
from visualizer import (
    create_field_heatmap,
    create_percentage_heatmap,
    create_compliance_map,
    create_compliance_boundary_plot,
    create_summary_figure
)

# Page configuration
st.set_page_config(
    page_title="EMF Compliance Analysis",
    page_icon="📡",
    layout="wide"
)

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "output"
EXECUTABLE = PROJECT_ROOT / "build" / "emfcompliance"


def run_analysis(config_path: str, output_dir: str) -> tuple[bool, str]:
    """Run the C++ analysis executable."""
    if not EXECUTABLE.exists():
        return False, f"Executable not found at {EXECUTABLE}. Please build the project first."

    try:
        result = subprocess.run(
            [str(EXECUTABLE), "-v", "-o", output_dir, config_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        output = result.stdout + "\n" + result.stderr

        if result.returncode == 2:
            return False, f"Configuration error:\n{output}"

        return True, output

    except subprocess.TimeoutExpired:
        return False, "Analysis timed out (exceeded 5 minutes)"
    except Exception as e:
        return False, f"Error running analysis: {str(e)}"


def main():
    st.title("📡 EMF Compliance Analysis Dashboard")

    # Sidebar for configuration
    st.sidebar.header("Configuration")

    # Config file selection
    config_source = st.sidebar.radio(
        "Configuration Source",
        ["Default Config", "Upload Config"]
    )

    config_path = None
    temp_config = None

    if config_source == "Default Config":
        if DEFAULT_CONFIG.exists():
            config_path = str(DEFAULT_CONFIG)
            st.sidebar.success(f"Using: {DEFAULT_CONFIG.name}")
        else:
            st.sidebar.error("Default config not found")
    else:
        uploaded_file = st.sidebar.file_uploader("Upload config.yaml", type=['yaml', 'yml'])
        if uploaded_file:
            # Save to temp file
            temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
            temp_config.write(uploaded_file.getvalue().decode())
            temp_config.close()
            config_path = temp_config.name
            st.sidebar.success("Config uploaded")

    # Output directory
    output_dir = st.sidebar.text_input("Output Directory", str(DEFAULT_OUTPUT))

    # Run analysis button
    run_button = st.sidebar.button("🚀 Run Analysis", type="primary", disabled=config_path is None)

    if run_button and config_path:
        with st.spinner("Running EMF analysis..."):
            success, output = run_analysis(config_path, output_dir)

            if success:
                st.sidebar.success("Analysis completed!")
                st.session_state['analysis_output'] = output
                st.session_state['output_dir'] = output_dir
            else:
                st.sidebar.error("Analysis failed")
                st.error(output)

    # Clean up temp file
    if temp_config:
        try:
            os.unlink(temp_config.name)
        except:
            pass

    # Main content area
    st.markdown("---")

    # Check if results exist
    output_path = Path(output_dir)
    results_csv = output_path / "results.csv"
    report_json = output_path / "report.json"

    if not results_csv.exists() or not report_json.exists():
        st.info("No analysis results found. Run an analysis or check the output directory.")

        # Show raw output if available
        if 'analysis_output' in st.session_state:
            with st.expander("Analysis Output"):
                st.code(st.session_state['analysis_output'])
        return

    # Load results
    try:
        df, report = load_analysis_results(output_dir)
    except Exception as e:
        st.error(f"Error loading results: {e}")
        return

    # Summary section
    st.header("📊 Compliance Summary")

    summary = report.get('summary', {})
    metadata = report.get('metadata', {})

    # Compliance status indicator
    is_compliant = summary.get('overall_compliant', False)
    if is_compliant:
        st.success("✅ COMPLIANT - All measurement points within limits")
    else:
        st.error("❌ NON-COMPLIANT - Some points exceed exposure limits")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Standard",
            metadata.get('standard', 'N/A'),
            metadata.get('category', '').replace('_', ' ').title()
        )

    with col2:
        st.metric(
            "Max Field",
            f"{summary.get('max_field_value_v_m', 0):.3f} V/m"
        )

    with col3:
        st.metric(
            "Max % of Limit",
            f"{summary.get('max_percentage_of_limit', 0):.1f}%"
        )

    with col4:
        total = summary.get('total_points', 1)
        compliant = summary.get('compliant_points', 0)
        st.metric(
            "Compliant Points",
            f"{compliant:,} / {total:,}",
            f"{100*compliant/total:.1f}%"
        )

    # Antenna information
    st.header("📡 Antenna Configuration")

    antennas = report.get('antennas', [])
    if antennas:
        antenna_data = []
        for ant in antennas:
            antenna_data.append({
                'ID': ant['id'],
                'Frequency (MHz)': ant['frequency_mhz'],
                'EIRP (W)': ant['power_eirp_watts'],
                'X (m)': ant['position']['x'],
                'Y (m)': ant['position']['y'],
                'Z (m)': ant['position']['z'],
                'Azimuth (°)': ant['orientation']['azimuth_deg'],
                'Tilt (°)': ant['orientation']['tilt_deg']
            })
        st.dataframe(antenna_data, use_container_width=True)

    # Visualization section
    st.header("🗺️ Visualization")

    # View selector
    view_mode = st.selectbox(
        "Select View",
        ["Summary (All Views)", "Field Strength", "Percentage of Limit", "Compliance Status", "Compliance Boundaries"]
    )

    # Get antenna positions for plotting
    antenna_positions = []
    for ant in antennas:
        antenna_positions.append({
            'id': ant['id'],
            'x': ant['position']['x'],
            'y': ant['position']['y']
        })

    # Generate and display appropriate plot
    if view_mode == "Summary (All Views)":
        fig = create_summary_figure(df, report)
        st.pyplot(fig)

    elif view_mode == "Field Strength":
        fig = create_field_heatmap(df, "Electric Field Strength (V/m)", antenna_positions)
        st.pyplot(fig)

    elif view_mode == "Percentage of Limit":
        fig = create_percentage_heatmap(df, "Percentage of Exposure Limit", antenna_positions)
        st.pyplot(fig)

    elif view_mode == "Compliance Status":
        fig = create_compliance_map(df, "Compliance Status Map", antenna_positions)
        st.pyplot(fig)

    elif view_mode == "Compliance Boundaries":
        boundaries = report.get('compliance_boundaries', {})
        fig = create_compliance_boundary_plot(df, boundaries, antenna_positions)
        st.pyplot(fig)

        # Show boundary distances
        if boundaries:
            st.subheader("Compliance Boundary Distances")
            for ant_id, distance in boundaries.items():
                st.write(f"**{ant_id}**: {distance:.1f} m")

    # Detailed statistics
    st.header("📈 Detailed Statistics")

    stats = get_statistics(df)
    max_point = get_max_exposure_point(df)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Point Statistics")
        st.write(f"- **Total Points**: {stats['total_points']:,}")
        st.write(f"- **Compliant**: {stats['compliant_count']:,} ({100*stats['compliant_count']/stats['total_points']:.1f}%)")
        st.write(f"- **Marginal**: {stats['marginal_count']:,} ({100*stats['marginal_count']/stats['total_points']:.1f}%)")
        st.write(f"- **Non-Compliant**: {stats['non_compliant_count']:,} ({100*stats['non_compliant_count']/stats['total_points']:.1f}%)")

    with col2:
        st.subheader("Field Statistics")
        st.write(f"- **Mean Field**: {stats['mean_field']:.4f} V/m")
        st.write(f"- **Max Field**: {stats['max_field']:.4f} V/m")
        st.write(f"- **Min Field**: {stats['min_field']:.6f} V/m")
        st.write(f"- **Mean % of Limit**: {stats['mean_percentage']:.2f}%")

    # Maximum exposure point details
    st.subheader("Maximum Exposure Point")
    st.write(f"- **Location**: ({max_point['x']:.1f}, {max_point['y']:.1f}, {max_point['z']:.1f}) m")
    st.write(f"- **Field Value**: {max_point['field_value']:.4f} V/m")
    st.write(f"- **Limit**: {max_point['limit']:.1f} V/m")
    st.write(f"- **Percentage**: {max_point['percentage']:.2f}%")
    st.write(f"- **Status**: {max_point['status']}")

    # Raw data viewer
    with st.expander("View Raw Data"):
        st.dataframe(df, use_container_width=True)

    # Download results
    st.header("📥 Download Results")

    col1, col2 = st.columns(2)

    with col1:
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Download Results CSV",
            data=csv_data,
            file_name="emf_results.csv",
            mime="text/csv"
        )

    with col2:
        import json
        json_data = json.dumps(report, indent=2)
        st.download_button(
            label="Download Report JSON",
            data=json_data,
            file_name="emf_report.json",
            mime="application/json"
        )


if __name__ == "__main__":
    main()
