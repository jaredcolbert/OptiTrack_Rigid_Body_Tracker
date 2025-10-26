#!/usr/bin/env python3
"""
Position Calculations Module
Contains all mathematical calculations for rigid body position tracking
"""

import numpy as np


class PositionCalculator:
    """Handles all position and rotation calculations for rigid body tracking"""
    
    def __init__(self):
        pass
    
    def quaternion_to_rotation_matrix(self, q):
        """Convert quaternion [x, y, z, w] to rotation matrix"""
        x, y, z, w = q
        
        # Normalize quaternion
        norm = np.sqrt(x*x + y*y + z*z + w*w)
        if norm == 0:
            return np.eye(3)
        x, y, z, w = x/norm, y/norm, z/norm, w/norm
        
        # Convert to rotation matrix
        R = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])
        return R
    
    def calculate_updated_stylus_position(self, reference_position, reference_rotation, reference_stylus_pos, 
                                         new_position, new_rotation):
        """
        Calculate the updated stylus position based on tracker movement.
        Uses Y-up coordinate system: X-right, Y-up, Z-forward.
        
        Args:
            reference_position: List [x, y, z] in mm - reference tracker position
            reference_rotation: List [x, y, z, w] - reference tracker quaternion
            reference_stylus_pos: List [x, y, z] in mm - stylus position at reference
            new_position: List [x, y, z] in mm - new tracker position
            new_rotation: List [x, y, z, w] - new tracker quaternion
        
        Returns:
            List [x, y, z] in mm - updated stylus position
        """
        # Convert inputs to numpy arrays
        ref_pos = np.array(reference_position)
        ref_rot = np.array(reference_rotation)
        ref_stylus = np.array(reference_stylus_pos)
        new_pos = np.array(new_position)
        new_rot = np.array(new_rotation)
        
        # Get rotation matrices
        R_ref = self.quaternion_to_rotation_matrix(ref_rot)
        R_new = self.quaternion_to_rotation_matrix(new_rot)
        
        # Calculate the offset vector from tracker to stylus in reference frame
        offset_in_ref_frame = ref_stylus - ref_pos
        
        # Transform the offset to the tracker's local coordinate system at reference
        offset_local = R_ref.T @ offset_in_ref_frame
        
        # Transform the offset to the new tracker orientation
        offset_in_new_frame = R_new @ offset_local
        
        # Calculate the new stylus position
        new_stylus_pos = new_pos + offset_in_new_frame
        
        return new_stylus_pos.tolist()
    
    def calculate_position_error(self, calculated_position, actual_position):
        """
        Calculate the error between calculated and actual positions
        
        Args:
            calculated_position: List [x, y, z] in mm - calculated position
            actual_position: List [x, y, z] in mm - actual position
        
        Returns:
            dict with error components and magnitude
        """
        calc_pos = np.array(calculated_position)
        actual_pos = np.array(actual_position)
        
        error = actual_pos - calc_pos
        error_magnitude = np.sqrt(np.sum(error**2))
        
        return {
            'x_error': error[0],
            'y_error': error[1], 
            'z_error': error[2],
            'magnitude': error_magnitude
        }
    
    def convert_to_millimeters(self, position_meters):
        """
        Convert position from meters to millimeters
        
        Args:
            position_meters: List [x, y, z] in meters
        
        Returns:
            List [x, y, z] in millimeters
        """
        return [pos * 1000 for pos in position_meters]
    
    def convert_to_meters(self, position_millimeters):
        """
        Convert position from millimeters to meters
        
        Args:
            position_millimeters: List [x, y, z] in millimeters
        
        Returns:
            List [x, y, z] in meters
        """
        return [pos / 1000 for pos in position_millimeters]
