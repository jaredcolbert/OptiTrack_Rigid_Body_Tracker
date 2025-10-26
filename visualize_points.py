#!/usr/bin/env python3
"""
Point Visualization
Visualizes femoral tracker positions and connecting lines from CSV data
"""

import csv
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from position_calculations import PositionCalculator

def load_csv_data(filename):
    """Load point data from CSV file"""
    points = {}
    
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            point_number = row['Point_Number']
            
            # Extract femur position
            femur_pos = [
                float(row['Femur_Pos_X_mm']),
                float(row['Femur_Pos_Y_mm']),
                float(row['Femur_Pos_Z_mm'])
            ]
            
            # Extract stylus position
            stylus_pos = [
                float(row['Stylus_Pos_X_mm']),
                float(row['Stylus_Pos_Y_mm']),
                float(row['Stylus_Pos_Z_mm'])
            ]
            
            points[point_number] = {
                'femur': femur_pos,
                'stylus': stylus_pos
            }
    
    return points

def visualize_points(filename='Attune_5_Left_Points.csv'):
    """Visualize femoral tracker positions and connecting lines"""
    
    # Load data
    points = load_csv_data(filename)
    
    print("Loaded points:", list(points.keys()))
    
    # Create figure and 3D axis
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Separate L and M points
    l_points = []
    m_points = []
    
    for i in range(1, 11):
        l_label = f'L{i}'  # L points have labels L1-L10
        m_label = f'M{i}'  # M points have labels M1-M10
        
        if l_label in points:
            l_points.append(points[l_label]['femur'])
        if m_label in points:
            m_points.append(points[m_label]['femur'])
    
    # Convert to numpy arrays
    l_points = np.array(l_points)
    m_points = np.array(m_points)
    
    # Only plot if we have points
    if len(l_points) > 0 and len(m_points) > 0:
        # Ensure 2D arrays (handle case where only 1 point)
        if l_points.ndim == 1:
            l_points = l_points.reshape(1, -1)
        if m_points.ndim == 1:
            m_points = m_points.reshape(1, -1)
        
        # Plot L points
        ax.scatter(l_points[:, 0], l_points[:, 1], l_points[:, 2], 
                   c='blue', marker='o', s=100, label='L Points', edgecolors='black', linewidths=1)
        
        # Plot M points
        ax.scatter(m_points[:, 0], m_points[:, 1], m_points[:, 2], 
                   c='red', marker='^', s=100, label='M Points', edgecolors='black', linewidths=1)
        
        # Draw connecting lines between L and M points
        for i in range(len(l_points)):
            ax.plot([l_points[i, 0], m_points[i, 0]], 
                    [l_points[i, 1], m_points[i, 1]], 
                    [l_points[i, 2], m_points[i, 2]], 
                    'g-', alpha=0.5, linewidth=2)
            
            # Add labels
            ax.text(l_points[i, 0], l_points[i, 1], l_points[i, 2], 
                    f'L{i+1}', fontsize=8)
            ax.text(m_points[i, 0], m_points[i, 1], m_points[i, 2], 
                    f'M{i+1}', fontsize=8)
        
        # Set labels
        ax.set_xlabel('X (mm)', fontsize=12)
        ax.set_ylabel('Y (mm)', fontsize=12)
        ax.set_zlabel('Z (mm)', fontsize=12)
        ax.set_title('Femoral Tracker Positions (L1-M1 to L10-M10)', fontsize=14, fontweight='bold')
        
        # Add legend
        ax.legend(fontsize=10)
        
        # Set equal aspect ratio for better visualization
        max_range = np.array([
            np.max([l_points, m_points]) - np.min([l_points, m_points])
        ]).max()
        
        mid_x = (np.max(l_points[:, 0]) + np.min(l_points[:, 0])) / 2
        mid_y = (np.max(l_points[:, 1]) + np.min(l_points[:, 1])) / 2
        mid_z = (np.max(l_points[:, 2]) + np.min(l_points[:, 2])) / 2
        
        ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
        ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
        ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
        
        # Show plot
        plt.tight_layout()
        plt.show()
    else:
        print("Error: Could not load points from CSV file")
        print(f"L points found: {len(l_points)}")
        print(f"M points found: {len(m_points)}")

def calculate_point_position(point_label, current_femur_pos_meters, current_femur_rot_quat, 
                             csv_filename='Attune_5_Left_Points.csv'):
    """
    Calculate the position of a specific point (L1-L10 or M1-M10) based on current tracked femur data
    
    Args:
        point_label (str): Point label to calculate (e.g., 'L3', 'M7')
        current_femur_pos_meters (list): Current femoral tracker position [X, Y, Z] in meters
        current_femur_rot_quat (list): Current femoral tracker rotation quaternion [W, X, Y, Z]
        csv_filename (str): Path to CSV file with reference data
    
    Returns:
        dict: Dictionary with calculated position and reference data, or None if point not found
    """
    # Load reference data from CSV
    points = load_csv_data(csv_filename)
    
    # Check if requested point exists
    if point_label not in points:
        print(f"Error: Point '{point_label}' not found in CSV file")
        available_points = ', '.join(sorted(points.keys()))
        print(f"Available points: {available_points}")
        return None
    
    # Get reference data for the requested point
    ref_femur_pos_mm = points[point_label]['femur']
    ref_stylus_pos_mm = points[point_label]['stylus']
    
    # Get femur rotation from CSV (we need to extract this from the CSV properly)
    # For now, we'll need to read it directly from the CSV
    femur_rotation = None
    with open(csv_filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Point_Number'] == point_label:
                femur_rotation = [
                    float(row['Femur_Rot_W']),
                    float(row['Femur_Rot_X']),
                    float(row['Femur_Rot_Y']),
                    float(row['Femur_Rot_Z'])
                ]
                break
    
    if femur_rotation is None:
        print(f"Error: Could not find femur rotation for point '{point_label}'")
        return None
    
    # Convert reference positions from mm to meters for calculations
    calculator = PositionCalculator()
    ref_femur_pos_meters = calculator.convert_to_meters(ref_femur_pos_mm)
    ref_stylus_pos_meters = calculator.convert_to_meters(ref_stylus_pos_mm)
    
    # Convert current femur position to millimeters for display
    current_femur_pos_mm = calculator.convert_to_millimeters(current_femur_pos_meters)
    
    # Calculate updated stylus position
    calculated_position_mm = calculator.calculate_updated_stylus_position(
        ref_femur_pos_mm,              # Reference femur position (mm)
        femur_rotation,                 # Reference femur rotation (quaternion)
        ref_stylus_pos_mm,             # Reference stylus position (mm)
        current_femur_pos_mm,          # Current femur position (mm)
        current_femur_rot_quat         # Current femur rotation (quaternion)
    )
    
    return {
        'point_label': point_label,
        'calculated_position_mm': calculated_position_mm,
        'current_femur_pos_mm': current_femur_pos_mm,
        'reference_femur_pos_mm': ref_femur_pos_mm,
        'reference_stylus_pos_mm': ref_stylus_pos_mm,
        'reference_femur_rotation': femur_rotation
    }

def interactive_point_calculator(current_femur_pos_meters, current_femur_rot_quat):
    """
    Interactive function to calculate positions for user-requested points
    
    Args:
        current_femur_pos_meters (list): Current femoral tracker position [X, Y, Z] in meters
        current_femur_rot_quat (list): Current femoral tracker rotation quaternion [W, X, Y, Z]
    """
    print("\n=== Point Position Calculator ===")
    print("Enter point labels (e.g., L1, M5) or 'q' to quit")
    print("Valid points: L1-L10, M1-M10\n")
    
    while True:
        try:
            point_label = input("Enter point label (or 'q' to quit): ").strip().upper()
            
            if point_label.lower() == 'q':
                print("Exiting calculator...")
                break
            
            # Validate point label format
            if not (point_label.startswith('L') or point_label.startswith('M')):
                print("Error: Point label must start with 'L' or 'M' (e.g., L3, M7)")
                continue
            
            # Calculate position
            result = calculate_point_position(
                point_label, 
                current_femur_pos_meters, 
                current_femur_rot_quat
            )
            
            if result:
                print(f"\n=== CALCULATED POSITION FOR {result['point_label']} ===")
                print(f"Current Femur Position: X={result['current_femur_pos_mm'][0]:.2f}mm, "
                      f"Y={result['current_femur_pos_mm'][1]:.2f}mm, Z={result['current_femur_pos_mm'][2]:.2f}mm")
                print(f"Calculated Position: X={result['calculated_position_mm'][0]:.2f}mm, "
                      f"Y={result['calculated_position_mm'][1]:.2f}mm, Z={result['calculated_position_mm'][2]:.2f}mm")
                print(f"Reference Femur Position: X={result['reference_femur_pos_mm'][0]:.2f}mm, "
                      f"Y={result['reference_femur_pos_mm'][1]:.2f}mm, Z={result['reference_femur_pos_mm'][2]:.2f}mm")
                print(f"Reference Stylus Position: X={result['reference_stylus_pos_mm'][0]:.2f}mm, "
                      f"Y={result['reference_stylus_pos_mm'][1]:.2f}mm, Z={result['reference_stylus_pos_mm'][2]:.2f}mm")
                print("=" * 50 + "\n")
            
        except KeyboardInterrupt:
            print("\nExiting calculator...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # Interactive mode - can be called from tracker
        print("Interactive point calculator mode")
        print("This mode requires current femur position and rotation")
        print("Call interactive_point_calculator(femur_pos, femur_rot) from tracker")
    else:
        # Default: show visualization
        visualize_points()
