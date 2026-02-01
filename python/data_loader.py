"""
Data loader for EMF compliance analysis results.
Loads C++ output files (results.csv and report.json) for visualization.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple


def load_results_csv(filepath: str) -> pd.DataFrame:
    """
    Load grid results from CSV file.

    Args:
        filepath: Path to results.csv

    Returns:
        DataFrame with columns: x, y, z, field_value_v_m, limit_v_m,
                                percentage_of_limit, status
    """
    df = pd.read_csv(filepath)
    return df


def load_report_json(filepath: str) -> Dict:
    """
    Load compliance report from JSON file.

    Args:
        filepath: Path to report.json

    Returns:
        Dictionary containing report data
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def pivot_to_grid(df: pd.DataFrame, value_column: str = 'field_value_v_m') -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Pivot DataFrame to 2D grid for visualization.

    Args:
        df: DataFrame with x, y columns and value column
        value_column: Column name to use for grid values

    Returns:
        Tuple of (X, Y, Z) where X and Y are coordinate meshes
        and Z is the value grid
    """
    # Get unique coordinates
    x_unique = np.sort(df['x'].unique())
    y_unique = np.sort(df['y'].unique())

    # Create pivot table
    pivot = df.pivot_table(
        values=value_column,
        index='y',
        columns='x',
        aggfunc='mean'
    )

    # Create meshgrid
    X, Y = np.meshgrid(x_unique, y_unique)

    # Reindex to ensure proper alignment
    pivot = pivot.reindex(index=y_unique, columns=x_unique)
    Z = pivot.values

    return X, Y, Z


def get_compliance_mask(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Create masks for compliance visualization.

    Args:
        df: DataFrame with status column

    Returns:
        Tuple of (compliant_mask, marginal_mask, non_compliant_mask)
    """
    x_unique = np.sort(df['x'].unique())
    y_unique = np.sort(df['y'].unique())

    compliant = df.pivot_table(
        values='percentage_of_limit',
        index='y',
        columns='x',
        aggfunc=lambda x: 1 if all(df.loc[x.index, 'status'] == 'COMPLIANT') else 0
    ).reindex(index=y_unique, columns=x_unique).values

    marginal = df.pivot_table(
        values='percentage_of_limit',
        index='y',
        columns='x',
        aggfunc=lambda x: 1 if any(df.loc[x.index, 'status'] == 'MARGINAL') else 0
    ).reindex(index=y_unique, columns=x_unique).values

    non_compliant = df.pivot_table(
        values='percentage_of_limit',
        index='y',
        columns='x',
        aggfunc=lambda x: 1 if any(df.loc[x.index, 'status'] == 'NON_COMPLIANT') else 0
    ).reindex(index=y_unique, columns=x_unique).values

    return compliant.astype(bool), marginal.astype(bool), non_compliant.astype(bool)


def load_analysis_results(output_dir: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Load both results CSV and report JSON from output directory.

    Args:
        output_dir: Path to output directory containing results.csv and report.json

    Returns:
        Tuple of (results_df, report_dict)
    """
    output_path = Path(output_dir)

    results_csv = output_path / 'results.csv'
    report_json = output_path / 'report.json'

    if not results_csv.exists():
        raise FileNotFoundError(f"Results file not found: {results_csv}")
    if not report_json.exists():
        raise FileNotFoundError(f"Report file not found: {report_json}")

    df = load_results_csv(str(results_csv))
    report = load_report_json(str(report_json))

    return df, report


def get_max_exposure_point(df: pd.DataFrame) -> Dict:
    """
    Find the point with maximum exposure.

    Args:
        df: Results DataFrame

    Returns:
        Dictionary with max exposure point details
    """
    max_idx = df['percentage_of_limit'].idxmax()
    max_row = df.loc[max_idx]

    return {
        'x': max_row['x'],
        'y': max_row['y'],
        'z': max_row['z'],
        'field_value': max_row['field_value_v_m'],
        'limit': max_row['limit_v_m'],
        'percentage': max_row['percentage_of_limit'],
        'status': max_row['status']
    }


def get_statistics(df: pd.DataFrame) -> Dict:
    """
    Calculate statistics from results.

    Args:
        df: Results DataFrame

    Returns:
        Dictionary with statistics
    """
    return {
        'total_points': len(df),
        'compliant_count': len(df[df['status'] == 'COMPLIANT']),
        'marginal_count': len(df[df['status'] == 'MARGINAL']),
        'non_compliant_count': len(df[df['status'] == 'NON_COMPLIANT']),
        'mean_field': df['field_value_v_m'].mean(),
        'max_field': df['field_value_v_m'].max(),
        'min_field': df['field_value_v_m'].min(),
        'mean_percentage': df['percentage_of_limit'].mean(),
        'max_percentage': df['percentage_of_limit'].max()
    }
