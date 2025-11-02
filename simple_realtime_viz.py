#!/usr/bin/env python3
"""
Simple Real-time Visualization
A more robust version that avoids threading issues
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import csv
from position_calculations import PositionCalculator

class SimpleRealtimeViz:
    def __init__(self, csv_filename='Attune_5_Left_Points.csv'):
        self.csv_filename = csv_filename
        self.calculator = PositionCalculator()
        self.reference_data = {}
        self.load_reference_data()
        
    def load_reference_data(self):
        """Load reference data from CSV file"""
        self.reference_data = {}
        
        try:
            with open(self.csv_filename, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    point_number = row['Point_Number']
                    
                    # Extract femur position and rotation
                    femur_pos = [
                        float(row['Femur_Pos_X_mm']),
                        float(row['Femur_Pos_Y_mm']),
                        float(row['Femur_Pos_Z_mm'])
                    ]
                    femur_rot = [
                        float(row['Femur_Rot_W']),
                        float(row['Femur_Rot_X']),
                        float(row['Femur_Rot_Y']),
                        float(row['Femur_Rot_Z'])
                    ]
                    
                    # Extract stylus position
                    stylus_pos = [
                        float(row['Stylus_Pos_X_mm']),
                        float(row['Stylus_Pos_Y_mm']),
                        float(row['Stylus_Pos_Z_mm'])
                    ]
                    
                    self.reference_data[point_number] = {
                        'femur_pos': femur_pos,
                        'femur_rot': femur_rot,
                        'stylus_pos': stylus_pos
                    }
                    
        except FileNotFoundError:
            print(f"Error: CSV file {self.csv_filename} not found")
            self.reference_data = {}
        except Exception as e:
            print(f"Error loading reference data: {e}")
            self.reference_data = {}
    
    def calculate_updated_positions(self, current_femur_pos_meters, current_femur_rot_quat):
        """Calculate updated positions for all L-M pairs"""
        if not current_femur_pos_meters or not current_femur_rot_quat:
            return None, None
            
        # Convert current position to mm
        current_femur_pos_mm = self.calculator.convert_to_millimeters(current_femur_pos_meters)
        
        # Calculate L-M pairs
        l_positions = []
        m_positions = []
        
        for i in range(1, 11):
            l_label = f'L{i}'
            m_label = f'M{i}'
            
            if l_label in self.reference_data and m_label in self.reference_data:
                # Get reference data
                l_ref = self.reference_data[l_label]
                m_ref = self.reference_data[m_label]
                
                # Calculate updated positions
                l_pos = self.calculator.calculate_updated_stylus_position(
                    l_ref['femur_pos'], l_ref['femur_rot'], l_ref['stylus_pos'],
                    current_femur_pos_mm, current_femur_rot_quat
                )
                
                m_pos = self.calculator.calculate_updated_stylus_position(
                    m_ref['femur_pos'], m_ref['femur_rot'], m_ref['stylus_pos'],
                    current_femur_pos_mm, current_femur_rot_quat
                )
                
                l_positions.append(l_pos)
                m_positions.append(m_pos)
        
        return l_positions, m_positions
    
    def show_visualization(self, current_femur_pos_meters, current_femur_rot_quat):
        """Show a single visualization frame"""
        if not current_femur_pos_meters or not current_femur_rot_quat:
            print("No tracker data available for visualization")
            return
            
        # Calculate updated positions
        l_positions, m_positions = self.calculate_updated_positions(
            current_femur_pos_meters, current_femur_rot_quat
        )
        
        if not l_positions or not m_positions:
            print("No reference data available for visualization")
            return
        
        # Convert tracker position to mm
        femur_pos_mm = self.calculator.convert_to_millimeters(current_femur_pos_meters)
        
        # Create the plot
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Draw tracker center as sphere
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 20)
        x_sphere = 10 * np.outer(np.cos(u), np.sin(v)) + femur_pos_mm[0]
        y_sphere = 10 * np.outer(np.sin(u), np.sin(v)) + femur_pos_mm[1]
        z_sphere = 10 * np.outer(np.ones(np.size(u)), np.cos(v)) + femur_pos_mm[2]
        
        ax.plot_surface(x_sphere, y_sphere, z_sphere, alpha=0.7, color='red', label='Tracker')
        
        # Draw L and M points
        l_array = np.array(l_positions)
        m_array = np.array(m_positions)
        
        ax.scatter(l_array[:, 0], l_array[:, 1], l_array[:, 2], 
                  c='blue', marker='o', s=50, label='L Points')
        ax.scatter(m_array[:, 0], m_array[:, 1], m_array[:, 2], 
                  c='red', marker='^', s=50, label='M Points')
        
        # Draw connecting lines
        for i in range(len(l_positions)):
            ax.plot([l_positions[i][0], m_positions[i][0]], 
                   [l_positions[i][1], m_positions[i][1]], 
                   [l_positions[i][2], m_positions[i][2]], 
                   'g-', alpha=0.7, linewidth=2)
        
        # Set labels and title
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('Tracker Visualization')
        
        # Set view range
        range_val = 100
        ax.set_xlim(femur_pos_mm[0] - range_val, femur_pos_mm[0] + range_val)
        ax.set_ylim(femur_pos_mm[1] - range_val, femur_pos_mm[1] + range_val)
        ax.set_zlim(femur_pos_mm[2] - range_val, femur_pos_mm[2] + range_val)
        
        # Add legend
        ax.legend()
        
        # Show the plot
        plt.tight_layout()
        plt.show()
        
        return fig, ax

