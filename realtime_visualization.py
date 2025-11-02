#!/usr/bin/env python3
"""
Real-time Visualization Module
Displays tracker center as sphere and L-M planes in real-time
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import threading
import time
import csv
from position_calculations import PositionCalculator

class RealtimeVisualizer:
    def __init__(self, csv_filename='Attune_5_Left_Points.csv'):
        self.csv_filename = csv_filename
        self.calculator = PositionCalculator()
        self.running = False
        self.thread = None
        
        # Data storage
        self.current_femur_pos = None
        self.current_femur_rot = None
        self.calculated_planes = None
        self.reference_data = None
        
        # Load reference data
        self.load_reference_data()
        
        # Matplotlib setup
        self.fig = None
        self.ax = None
        self.sphere = None
        self.planes = []
        
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
    
    def update_tracker_data(self, femur_pos_meters, femur_rot_quat):
        """Update current tracker position and rotation"""
        self.current_femur_pos = femur_pos_meters
        self.current_femur_rot = femur_rot_quat
        
        # Calculate updated positions for all L-M pairs
        self.calculate_planes()
    
    def calculate_planes(self):
        """Calculate the L-M plane positions based on current tracker data"""
        if not self.current_femur_pos or not self.current_femur_rot:
            return
            
        self.calculated_planes = []
        
        # Convert current position to mm
        current_femur_pos_mm = self.calculator.convert_to_millimeters(self.current_femur_pos)
        
        # Calculate L-M pairs (L1-M1, L2-M2, etc.)
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
                    current_femur_pos_mm, self.current_femur_rot
                )
                
                m_pos = self.calculator.calculate_updated_stylus_position(
                    m_ref['femur_pos'], m_ref['femur_rot'], m_ref['stylus_pos'],
                    current_femur_pos_mm, self.current_femur_rot
                )
                
                self.calculated_planes.append({
                    'l_pos': l_pos,
                    'm_pos': m_pos,
                    'label': f'L{i}-M{i}'
                })
    
    def create_plane_polygon(self, l_pos, m_pos, center_pos, size=50):
        """Create a plane polygon from L and M points"""
        # Calculate the vector from L to M
        lm_vector = np.array(m_pos) - np.array(l_pos)
        lm_length = np.linalg.norm(lm_vector)
        
        if lm_length == 0:
            return None
            
        # Normalize the vector
        lm_unit = lm_vector / lm_length
        
        # Create perpendicular vector (cross with up vector)
        up_vector = np.array([0, 1, 0])
        if np.abs(np.dot(lm_unit, up_vector)) > 0.9:
            up_vector = np.array([1, 0, 0])
        
        perp_vector = np.cross(lm_unit, up_vector)
        perp_vector = perp_vector / np.linalg.norm(perp_vector)
        
        # Create the third perpendicular vector
        normal_vector = np.cross(lm_unit, perp_vector)
        
        # Create plane corners
        half_size = size / 2
        center = (np.array(l_pos) + np.array(m_pos)) / 2
        
        corners = [
            center + perp_vector * half_size + lm_unit * half_size,
            center + perp_vector * half_size - lm_unit * half_size,
            center - perp_vector * half_size - lm_unit * half_size,
            center - perp_vector * half_size + lm_unit * half_size
        ]
        
        return np.array(corners)
    
    def setup_plot(self):
        """Setup the 3D plot"""
        # Use a non-blocking backend
        import matplotlib
        matplotlib.use('TkAgg')  # Use TkAgg backend for better threading support
        
        self.fig = plt.figure(figsize=(12, 10))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Set labels
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')
        self.ax.set_title('Real-time Tracker Visualization')
        
        # Set equal aspect ratio
        self.ax.set_box_aspect([1,1,1])
        
        # Initialize empty plots
        self.sphere = None
        self.planes = []
        
        plt.ion()  # Interactive mode
        plt.show(block=False)  # Non-blocking show
    
    def update_plot(self):
        """Update the visualization"""
        if not self.fig or not self.ax:
            return
            
        # Clear previous plots
        self.ax.clear()
        
        # Set labels
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')
        self.ax.set_title('Real-time Tracker Visualization')
        
        if self.current_femur_pos:
            # Convert to mm for display
            femur_pos_mm = self.calculator.convert_to_millimeters(self.current_femur_pos)
            
            # Draw tracker center as sphere
            u = np.linspace(0, 2 * np.pi, 20)
            v = np.linspace(0, np.pi, 20)
            x_sphere = 10 * np.outer(np.cos(u), np.sin(v)) + femur_pos_mm[0]
            y_sphere = 10 * np.outer(np.sin(u), np.sin(v)) + femur_pos_mm[1]
            z_sphere = 10 * np.outer(np.ones(np.size(u)), np.cos(v)) + femur_pos_mm[2]
            
            self.ax.plot_surface(x_sphere, y_sphere, z_sphere, alpha=0.7, color='red')
            
            # Draw L-M planes
            if self.calculated_planes:
                colors = plt.cm.tab10(np.linspace(0, 1, len(self.calculated_planes)))
                
                for i, plane_data in enumerate(self.calculated_planes):
                    l_pos = plane_data['l_pos']
                    m_pos = plane_data['m_pos']
                    label = plane_data['label']
                    
                    # Draw L and M points
                    self.ax.scatter(l_pos[0], l_pos[1], l_pos[2], 
                                  c='blue', marker='o', s=50, label=f'{label} L' if i == 0 else "")
                    self.ax.scatter(m_pos[0], m_pos[1], m_pos[2], 
                                  c='red', marker='^', s=50, label=f'{label} M' if i == 0 else "")
                    
                    # Draw connecting line
                    self.ax.plot([l_pos[0], m_pos[0]], 
                               [l_pos[1], m_pos[1]], 
                               [l_pos[2], m_pos[2]], 
                               'g-', alpha=0.7, linewidth=2)
                    
                    # Draw plane
                    plane_poly = self.create_plane_polygon(l_pos, m_pos, femur_pos_mm)
                    if plane_poly is not None:
                        self.ax.plot_surface(
                            plane_poly[:, 0].reshape(2, 2),
                            plane_poly[:, 1].reshape(2, 2),
                            plane_poly[:, 2].reshape(2, 2),
                            alpha=0.3, color=colors[i]
                        )
        
        # Set equal aspect ratio
        if self.current_femur_pos:
            femur_pos_mm = self.calculator.convert_to_millimeters(self.current_femur_pos)
            range_val = 100  # 100mm range around tracker
            self.ax.set_xlim(femur_pos_mm[0] - range_val, femur_pos_mm[0] + range_val)
            self.ax.set_ylim(femur_pos_mm[1] - range_val, femur_pos_mm[1] + range_val)
            self.ax.set_zlim(femur_pos_mm[2] - range_val, femur_pos_mm[2] + range_val)
        
        # Add legend
        self.ax.legend()
        
        # Refresh the plot
        try:
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except Exception as e:
            print(f"Plot update error: {e}")
    
    def start_visualization(self):
        """Start the real-time visualization"""
        if self.running:
            return
            
        self.running = True
        
        def visualization_loop():
            try:
                self.setup_plot()
                while self.running:
                    self.update_plot()
                    time.sleep(0.1)  # Update at 10 FPS
            except Exception as e:
                print(f"Visualization error: {e}")
                self.running = False
        
        self.thread = threading.Thread(target=visualization_loop, daemon=True)
        self.thread.start()
        print("Real-time visualization started. Press 'v' to toggle off.")
    
    def stop_visualization(self):
        """Stop the real-time visualization"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)  # Wait max 1 second
        try:
            if self.fig:
                plt.close(self.fig)
                self.fig = None
                self.ax = None
        except Exception as e:
            print(f"Error closing plot: {e}")
        print("Real-time visualization stopped.")
    
    def toggle_visualization(self):
        """Toggle visualization on/off"""
        if self.running:
            self.stop_visualization()
        else:
            self.start_visualization()
