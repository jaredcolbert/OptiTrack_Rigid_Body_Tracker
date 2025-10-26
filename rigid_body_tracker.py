#!/usr/bin/env python3
"""
Rigid Body Tracker
Gets positional data from femur tracker (ID 1) and stylus (ID 2) and prints when 'c' is pressed
"""

import mmap
from re import M
import sys
import time
import threading
import numpy as np
import csv
from datetime import datetime
from NatNetClient import NatNetClient
from position_calculations import PositionCalculator

# =============================================================================
# CONFIGURATION - Modify these settings as needed
# =============================================================================
# 
# To change IP addresses, modify the values below:
# - DEFAULT_SERVER_IP: The IP address of your NatNet server
# - DEFAULT_LOCAL_IP: The IP address of this client computer
# 
# You can also override these settings using command line arguments:
# python rigid_body_tracker.py --server 192.168.1.100 --local 192.168.1.50
#
# =============================================================================

# Network Configuration
DEFAULT_SERVER_IP = "192.168.86.39"  # NatNet server IP address
DEFAULT_LOCAL_IP = "192.168.86.39"   # Local client IP address

# Connection Settings
CONNECTION_TIMEOUT = 15.0             # Seconds without data before considering disconnected
CONNECTION_CHECK_INTERVAL = 2.0       # Seconds between connection checks

# Rigid Body IDs
DEFAULT_FEMUR_ID = 1                  # Femur tracker rigid body ID
DEFAULT_STYLUS_ID = 2                 # Stylus rigid body ID
DEFAULT_ROBOT_BASE_ID = 3             # Robot base rigid body ID

# =============================================================================

# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'  # Reset to default

class RigidBodyTracker:
    def __init__(self, femur_id=DEFAULT_FEMUR_ID, stylus_id=DEFAULT_STYLUS_ID, 
                 server_ip=DEFAULT_SERVER_IP, local_ip=DEFAULT_LOCAL_IP):
        self.client = NatNetClient()
        self.femur_id = femur_id
        self.stylus_id = stylus_id
        self.server_ip = server_ip
        self.local_ip = local_ip
        
        # Initialize position calculator
        self.calculator = PositionCalculator()
        
        # Current position data
        self.femur_position = None
        self.femur_rotation = None
        self.stylus_position = None
        self.stylus_rotation = None
        
        # Data reception flags
        self.femur_data_received = False
        self.stylus_data_received = False
        
        # Data storage
        self.captured_points = []  # List to store captured data points
        
        # Reference data for coordinate calculation
        self.reference_femur_position = None
        self.reference_femur_rotation = None
        self.reference_stylus_position = None
        self.reference_stylus_rotation = None
        self.reference_captured = False
        
        # Control flags
        self.running = True
        self.keyboard_thread = None
        
        # Connection status
        self.connected = False
        self.connection_attempted = False
        self.last_data_received = 0
        self.connection_timeout = CONNECTION_TIMEOUT
        self.connection_check_interval = CONNECTION_CHECK_INTERVAL
        self.last_connection_check = 0
        self.connection_start_time = 0
        self.showing_connection_animation = False
        
    def setup_connection(self, server_ip=None, local_ip=None):
        """Configure the NatNet client for unicast connection"""
        # Use instance variables if not provided
        if server_ip is None:
            server_ip = self.server_ip
        if local_ip is None:
            local_ip = self.local_ip
            
        # Set server IP address
        self.client.set_server_address(server_ip)
        
        # Set local IP address
        self.client.local_ip_address = local_ip
        
        # Disable multicast to use unicast
        self.client.set_use_multicast(False)
        
        # Suppress MoCap frame number messages
        self.client.set_print_level(0)
        
        # Set up rigid body listener
        self.client.rigid_body_listener = self.on_rigid_body_received
        
        print("Rigid Body Tracker")
        print("=" * 40)
        print(f"Server IP: {self.client.get_server_address()}")
        print(f"Local IP: {self.client.local_ip_address}")
        print(f"Femur Tracker ID: {self.femur_id}")
        print(f"Stylus ID: {self.stylus_id}")
        print("\nKeyboard Controls:")
        print("  'c' - Capture and print current positions")
        print("  's' - Store current positions as a data point")
        print("  'l' - List all stored data points")
        print("  'e' - Export data points to file")
        print("  'r' - Capture reference positions for coordinate calculation")
        print("  'u' - Calculate updated stylus position based on tracker movement")
        print("  'p' - Calculate mapped point position (L1-L10, M1-M10)")
        print("  't' - Test connection to NatNet server")
        print("  'q' - Quit the program")
        print("  'h' - Show this help")
        print("\nWorkflow: Press 'r' to capture reference, then 'u' to calculate updated position!")
        print(f"\n{Colors.CYAN}Configuration:{Colors.END}")
        print(f"  Server IP: {self.server_ip}")
        print(f"  Local IP: {self.local_ip}")
        print(f"  Femur ID: {self.femur_id}")
        print(f"  Stylus ID: {self.stylus_id}")
        print(f"  Timeout: {self.connection_timeout}s")
        
    def on_rigid_body_received(self, rigid_body_id, position, rotation):
        """Callback function called when rigid body data is received"""
        # Update last data received timestamp
        self.last_data_received = time.time()
        
        # Check if this is the femur tracker
        if rigid_body_id == self.femur_id:
            self.femur_position = list(position)
            self.femur_rotation = list(rotation)
            self.femur_data_received = True
            
        # Check if this is the stylus
        elif rigid_body_id == self.stylus_id:
            self.stylus_position = list(position)
            self.stylus_rotation = list(rotation)
            self.stylus_data_received = True
    
    def capture_positions(self):
        """Capture and print current positions of both rigid bodies"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=== POSITION CAPTURE [{timestamp}] ===")
        
        # Check connection status
        if not self.connected:
            print(f"{Colors.RED}{Colors.BOLD}WARNING: Not connected to NatNet server!{Colors.END}")
            print(f"{Colors.RED}Press 't' to test connection or check your network settings.{Colors.END}")
            print(f"{Colors.RED}Server IP: {self.client.get_server_address()}{Colors.END}")
            print("=" * 50)
            return
        
        # Check femur data
        if self.femur_data_received and self.femur_position is not None:
            femur_pos_mm = self.calculator.convert_to_millimeters(self.femur_position)
            print(f"Femur Tracker (ID {self.femur_id}):")
            print(f"  Position: X={femur_pos_mm[0]:.2f}mm, Y={femur_pos_mm[1]:.2f}mm, Z={femur_pos_mm[2]:.2f}mm")
            print(f"  Rotation: W={self.femur_rotation[0]:.3f}, X={self.femur_rotation[1]:.3f}, Y={self.femur_rotation[2]:.3f}, Z={self.femur_rotation[3]:.3f}")
        else:
            print(f"Femur Tracker (ID {self.femur_id}): NO DATA")
        
        # Check stylus data
        if self.stylus_data_received and self.stylus_position is not None:
            stylus_pos_mm = self.calculator.convert_to_millimeters(self.stylus_position)
            print(f"Stylus (ID {self.stylus_id}):")
            print(f"  Position: X={stylus_pos_mm[0]:.2f}mm, Y={stylus_pos_mm[1]:.2f}mm, Z={stylus_pos_mm[2]:.2f}mm")
            print(f"  Rotation: W={self.stylus_rotation[0]:.3f}, X={self.stylus_rotation[1]:.3f}, Y={self.stylus_rotation[2]:.3f}, Z={self.stylus_rotation[3]:.3f}")
        else:
            print(f"Stylus (ID {self.stylus_id}): NO DATA")
        
        print("=" * 50)
    
    def calculate_updated_stylus_position(self, reference_position, reference_rotation, reference_stylus_pos, 
                                         new_position, new_rotation):
        """Calculate the updated stylus position using the position calculator"""
        return self.calculator.calculate_updated_stylus_position(
            reference_position, reference_rotation, reference_stylus_pos, 
            new_position, new_rotation
        )
    
    def store_positions(self):
        """Store current positions as a data point"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if we have both data points
        if not self.femur_data_received or self.femur_position is None:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Femur Tracker (ID {self.femur_id}): No data available")
            print("Cannot store data without femur tracker position.")
            print("=" * 50)
            return
        
        if not self.stylus_data_received or self.stylus_position is None:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Stylus (ID {self.stylus_id}): No data available")
            print("Cannot store data without stylus position.")
            print("=" * 50)
            return
        
        # Convert to millimeters for storage
        femur_pos_mm = self.calculator.convert_to_millimeters(self.femur_position)
        stylus_pos_mm = self.calculator.convert_to_millimeters(self.stylus_position)
        
        # Create data point
        data_point = {
            'point_number': len(self.captured_points) + 1,
            'timestamp': timestamp,
            'femur_position': femur_pos_mm.copy(),
            'femur_rotation': self.femur_rotation.copy(),
            'stylus_position': stylus_pos_mm.copy(),
            'stylus_rotation': self.stylus_rotation.copy()
        }
        
        # Store the data point
        self.captured_points.append(data_point)
        
        print(f"\n=== DATA POINT STORED [{timestamp}] ===")
        print(f"Point #{data_point['point_number']} captured:")
        print(f"Femur Tracker (ID {self.femur_id}):")
        print(f"  Position: X={femur_pos_mm[0]:.2f}mm, Y={femur_pos_mm[1]:.2f}mm, Z={femur_pos_mm[2]:.2f}mm")
        print(f"  Rotation: W={self.femur_rotation[0]:.3f}, X={self.femur_rotation[1]:.3f}, Y={self.femur_rotation[2]:.3f}, Z={self.femur_rotation[3]:.3f}")
        print(f"Stylus (ID {self.stylus_id}):")
        print(f"  Position: X={stylus_pos_mm[0]:.2f}mm, Y={stylus_pos_mm[1]:.2f}mm, Z={stylus_pos_mm[2]:.2f}mm")
        print(f"  Rotation: W={self.stylus_rotation[0]:.3f}, X={self.stylus_rotation[1]:.3f}, Y={self.stylus_rotation[2]:.3f}, Z={self.stylus_rotation[3]:.3f}")
        print(f"Total data points stored: {len(self.captured_points)}")
        print("=" * 50)
    
    def list_stored_points(self):
        """List all stored data points"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=== STORED DATA POINTS [{timestamp}] ===")
        
        if not self.captured_points:
            print("No data points stored yet.")
            print("Use 's' to store current positions as a data point.")
        else:
            print(f"Total data points: {len(self.captured_points)}")
            print()
            
            for i, point in enumerate(self.captured_points, 1):
                print(f"Point #{point['point_number']} - {point['timestamp']}:")
                print(f"  Femur: X={point['femur_position'][0]:.2f}mm, Y={point['femur_position'][1]:.2f}mm, Z={point['femur_position'][2]:.2f}mm")
                print(f"  Stylus: X={point['stylus_position'][0]:.2f}mm, Y={point['stylus_position'][1]:.2f}mm, Z={point['stylus_position'][2]:.2f}mm")
                if i < len(self.captured_points):
                    print()
        
        print("=" * 50)
    
    def capture_reference(self):
        """Capture reference positions of both tracker and stylus"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if we have both data points
        if not self.femur_data_received or self.femur_position is None:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Femur Tracker (ID {self.femur_id}): No data available")
            print("Cannot capture reference without femur tracker position.")
            print("=" * 50)
            return
        
        if not self.stylus_data_received or self.stylus_position is None:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Stylus (ID {self.stylus_id}): No data available")
            print("Cannot capture reference without stylus position.")
            print("=" * 50)
            return
        
        # Store reference data
        self.reference_femur_position = self.calculator.convert_to_millimeters(self.femur_position)
        self.reference_femur_rotation = self.femur_rotation.copy()
        self.reference_stylus_position = self.calculator.convert_to_millimeters(self.stylus_position)
        self.reference_stylus_rotation = self.stylus_rotation.copy()
        self.reference_captured = True
        
        print(f"\n=== REFERENCE CAPTURED [{timestamp}] ===")
        print("Reference positions stored for coordinate calculation:")
        print(f"Femur Tracker (ID {self.femur_id}):")
        print(f"  Position: X={self.reference_femur_position[0]:.2f}mm, Y={self.reference_femur_position[1]:.2f}mm, Z={self.reference_femur_position[2]:.2f}mm")
        print(f"  Rotation: W={self.reference_femur_rotation[0]:.3f}, X={self.reference_femur_rotation[1]:.3f}, Y={self.reference_femur_rotation[2]:.3f}, Z={self.reference_femur_rotation[3]:.3f}")
        print(f"Stylus (ID {self.stylus_id}):")
        print(f"  Position: X={self.reference_stylus_position[0]:.2f}mm, Y={self.reference_stylus_position[1]:.2f}mm, Z={self.reference_stylus_position[2]:.2f}mm")
        print(f"  Rotation: W={self.reference_stylus_rotation[0]:.3f}, X={self.reference_stylus_rotation[1]:.3f}, Y={self.reference_stylus_rotation[2]:.3f}, Z={self.reference_stylus_rotation[3]:.3f}")
        print("Now move the tracker and press 'u' to calculate updated stylus position!")
        print("=" * 50)
    
    def calculate_updated_position(self):
        """Calculate and display updated stylus position based on tracker movement"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not self.reference_captured:
            print(f"\n=== ERROR [{timestamp}] ===")
            print("No reference captured yet.")
            print("Press 'r' to capture reference positions first.")
            print("=" * 50)
            return
        
        if not self.femur_data_received or self.femur_position is None:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Femur Tracker (ID {self.femur_id}): No current data available")
            print("Cannot calculate updated position without current tracker data.")
            print("=" * 50)
            return
        
        # Get current tracker position in mm
        current_femur_pos_mm = self.calculator.convert_to_millimeters(self.femur_position)
        
        # Calculate updated stylus position
        updated_stylus_pos = self.calculate_updated_stylus_position(
            self.reference_femur_position, self.reference_femur_rotation, self.reference_stylus_position,
            current_femur_pos_mm, self.femur_rotation
        )
        
        print(f"\n=== UPDATED STYLUS POSITION [{timestamp}] ===")
        print("Calculated stylus position based on tracker movement:")
        print(f"Femur Tracker (ID {self.femur_id}) - CURRENT:")
        print(f"  Position: X={current_femur_pos_mm[0]:.2f}mm, Y={current_femur_pos_mm[1]:.2f}mm, Z={current_femur_pos_mm[2]:.2f}mm")
        print(f"  Rotation: W={self.femur_rotation[0]:.3f}, X={self.femur_rotation[1]:.3f}, Y={self.femur_rotation[2]:.3f}, Z={self.femur_rotation[3]:.3f}")
        print(f"Stylus (ID {self.stylus_id}) - CALCULATED:")
        print(f"  Position: X={updated_stylus_pos[0]:.2f}mm, Y={updated_stylus_pos[1]:.2f}mm, Z={updated_stylus_pos[2]:.2f}mm")
        
        # Show actual stylus position if available for comparison
        if self.stylus_data_received and self.stylus_position is not None:
            actual_stylus_pos_mm = self.calculator.convert_to_millimeters(self.stylus_position)
            error_data = self.calculator.calculate_position_error(updated_stylus_pos, actual_stylus_pos_mm)
            
            print(f"Stylus (ID {self.stylus_id}) - ACTUAL:")
            print(f"  Position: X={actual_stylus_pos_mm[0]:.2f}mm, Y={actual_stylus_pos_mm[1]:.2f}mm, Z={actual_stylus_pos_mm[2]:.2f}mm")
            print()
            print("=== ERROR ANALYSIS ===")
            print(f"Position Error (Calculated vs Actual):")
            print(f"  X-axis error: {error_data['x_error']:+.2f}mm")
            print(f"  Y-axis error: {error_data['y_error']:+.2f}mm") 
            print(f"  Z-axis error: {error_data['z_error']:+.2f}mm")
            print(f"  3D Error Magnitude: {error_data['magnitude']:.2f}mm")
            print("=" * 25)
        else:
            print(f"Stylus (ID {self.stylus_id}): No actual data available for comparison")
        
        print("=" * 50)
    
    def show_connection_animation(self):
        """Show animated connection indicator"""
        if not self.showing_connection_animation:
            return
        
        current_time = time.time()
        elapsed = current_time - self.connection_start_time
        
        # Animation frames for connecting
        frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        frame_index = int(elapsed * 4) % len(frames)
        
        # Clear line and show animation
        print(f"\r{Colors.CYAN}{frames[frame_index]} Connecting to NatNet server... ({elapsed:.1f}s){Colors.END}", end='', flush=True)
    
    def start_connection_animation(self):
        """Start the connection animation"""
        self.showing_connection_animation = True
        self.connection_start_time = time.time()
        print(f"\n{Colors.CYAN}Starting connection to NatNet server...{Colors.END}")
    
    def stop_connection_animation(self):
        """Stop the connection animation"""
        if self.showing_connection_animation:
            self.showing_connection_animation = False
            print()  # New line after animation
    
    def is_connection_healthy(self):
        """Check if the connection to NatNet server is healthy"""
        current_time = time.time()
        
        # Check if we've received data recently
        if current_time - self.last_data_received > self.connection_timeout:
            return False
        
        # Check if the client reports being connected
        try:
            return self.client.connected()
        except:
            return False
    
    def update_connection_status(self):
        """Update connection status based on data reception and server communication"""
        current_time = time.time()
        
        # Show connection animation if we're trying to connect
        if self.showing_connection_animation:
            self.show_connection_animation()
        
        # Only check periodically to avoid excessive server calls
        if current_time - self.last_connection_check < self.connection_check_interval:
            return
        
        self.last_connection_check = current_time
        was_connected = self.connected
        self.connected = self.is_connection_healthy()
        
        # Stop animation if we're connected
        if self.connected and self.showing_connection_animation:
            self.stop_connection_animation()
        
        # Show connection status changes with delays
        if was_connected and not self.connected:
            # Only show error if we've been disconnected for a while
            time_since_data = current_time - self.last_data_received
            if time_since_data > self.connection_timeout:
                self.print_connection_lost()
        elif not was_connected and self.connected:
            self.print_connection_restored()
    
    def print_connection_lost(self):
        """Print red error message when connection is lost"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{Colors.RED}{Colors.BOLD}CONNECTION LOST [{timestamp}]{Colors.END}")
        print(f"{Colors.RED}No data received from NatNet server for {self.connection_timeout} seconds.{Colors.END}")
        print(f"{Colors.YELLOW}This might be normal if:{Colors.END}")
        print(f"{Colors.YELLOW}  - Rigid bodies are not being tracked{Colors.END}")
        print(f"{Colors.YELLOW}  - NatNet server is not running{Colors.END}")
        print(f"{Colors.YELLOW}  - Network connection issues{Colors.END}")
        print(f"{Colors.CYAN}Press 't' to test connection or 'c' to check for data{Colors.END}")
        print("=" * 50)
    
    def print_connection_restored(self):
        """Print green success message when connection is restored"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{Colors.GREEN}{Colors.BOLD}CONNECTION RESTORED [{timestamp}]{Colors.END}")
        print(f"{Colors.GREEN}Successfully receiving data from NatNet server.{Colors.END}")
        print("=" * 50)
    
    def check_connection_status(self):
        """Check and display connection status"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=== CONNECTION STATUS [{timestamp}] ===")
        print(f"Connection attempted: {self.connection_attempted}")
        
        if self.connected:
            print(f"{Colors.GREEN}Connected: {self.connected}{Colors.END}")
            print(f"{Colors.GREEN}✓ Successfully connected to NatNet server{Colors.END}")
        else:
            print(f"{Colors.RED}Connected: {self.connected}{Colors.END}")
            if self.connection_attempted:
                print(f"{Colors.RED}✗ Connection attempted but failed{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠ No connection attempt made yet{Colors.END}")
        
        print(f"Server IP: {self.client.get_server_address()}")
        print(f"Local IP: {self.client.local_ip_address}")
        print(f"Multicast enabled: {self.client.get_use_multicast()}")
        
        # Show additional connection info if available
        try:
            app_name = self.client.get_application_name()
            if app_name != "Not Set":
                print(f"Application: {app_name}")
            server_version = self.client.get_server_version()
            if server_version != (0, 0, 0, 0):
                print(f"Server Version: {server_version}")
        except:
            pass
        
        # Show data reception status
        current_time = time.time()
        time_since_data = current_time - self.last_data_received
        if self.last_data_received > 0:
            if time_since_data < self.connection_timeout:
                print(f"{Colors.GREEN}Last data received: {time_since_data:.1f} seconds ago{Colors.END}")
            else:
                print(f"{Colors.RED}Last data received: {time_since_data:.1f} seconds ago (TIMEOUT){Colors.END}")
        else:
            print(f"{Colors.RED}No data received yet{Colors.END}")
        
        print("=" * 50)
    
    def test_connection(self):
        """Test connection to NatNet server"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=== CONNECTION TEST [{timestamp}] ===")
        
        # Show animation while testing
        self.start_connection_animation()
        time.sleep(2)  # Give it a moment to show animation
        
        try:
            # Check if client reports being connected
            is_connected = self.client.connected()
            self.stop_connection_animation()
            
            if is_connected:
                print(f"{Colors.GREEN}Successfully connected to NatNet server!{Colors.END}")
                print(f"{Colors.GREEN}Client reports connection is active{Colors.END}")
                # Get additional connection info
                try:
                    app_name = self.client.get_application_name()
                    server_version = self.client.get_server_version()
                    print(f"{Colors.GREEN}Application: {app_name}{Colors.END}")
                    print(f"{Colors.GREEN}Server Version: {server_version}{Colors.END}")
                except:
                    pass
                self.connected = True
            else:
                print(f"{Colors.RED}✗ Client reports not connected{Colors.END}")
                self.connected = False
        except Exception as e:
            self.stop_connection_animation()
            print(f"{Colors.RED}✗ Connection test failed: {e}{Colors.END}")
            self.connected = False
        
        self.connection_attempted = True
        print("=" * 50)
    
    def export_data_points(self):
        """Export all stored data points to a CSV file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not self.captured_points:
            print(f"\n=== ERROR [{timestamp}] ===")
            print("No data points to export.")
            print("Use 's' to store some data points first.")
            print("=" * 50)
            return
        # Generate filename with timestamp
        export_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rigid_body_data_{export_timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                # Write header
                csvfile.write("Point_Number,Timestamp,Femur_X_mm,Femur_Y_mm,Femur_Z_mm,Femur_W,Femur_X,Femur_Y,Femur_Z,Stylus_X_mm,Stylus_Y_mm,Stylus_Z_mm,Stylus_W,Stylus_X,Stylus_Y,Stylus_Z\n")
                
                # Write data points
                for point in self.captured_points:
                    csvfile.write(f"{point['point_number']},{point['timestamp']},")
                    csvfile.write(f"{point['femur_position'][0]:.3f},{point['femur_position'][1]:.3f},{point['femur_position'][2]:.3f},")
                    csvfile.write(f"{point['femur_rotation'][0]:.6f},{point['femur_rotation'][1]:.6f},{point['femur_rotation'][2]:.6f},{point['femur_rotation'][3]:.6f},")
                    csvfile.write(f"{point['stylus_position'][0]:.3f},{point['stylus_position'][1]:.3f},{point['stylus_position'][2]:.3f},")
                    csvfile.write(f"{point['stylus_rotation'][0]:.6f},{point['stylus_rotation'][1]:.6f},{point['stylus_rotation'][2]:.6f},{point['stylus_rotation'][3]:.6f}\n")
            
            print(f"\n=== DATA EXPORTED [{timestamp}] ===")
            print(f"Successfully exported {len(self.captured_points)} data points to: {filename}")
            print("File format: CSV with columns for positions (mm) and rotations (quaternions)")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Failed to export data: {e}")
            print("=" * 50)
    
    def calculate_mapped_point(self, point_label, csv_filename='Attune_5_Left_Points.csv'):
        """
        Calculate the position of a specific mapped point (L1-L10 or M1-M10) based on current tracked femur data
        
        Args:
            point_label (str): Point label to calculate (e.g., 'L3', 'M7')
            csv_filename (str): Path to CSV file with reference data
        
        Returns:
            dict: Dictionary with calculated position and reference data, or None if point not found
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if we have current femur data
        if not self.femur_data_received or self.femur_position is None:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Femur Tracker (ID {self.femur_id}): No current data available")
            print("Cannot calculate mapped point without current tracker data.")
            print("=" * 50)
            return None
        
        # Load reference data from CSV
        try:
            points = {}
            with open(csv_filename, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    point_number = row['Point_Number']
                    femur_pos = [
                        float(row['Femur_Pos_X_mm']),
                        float(row['Femur_Pos_Y_mm']),
                        float(row['Femur_Pos_Z_mm'])
                    ]
                    stylus_pos = [
                        float(row['Stylus_Pos_X_mm']),
                        float(row['Stylus_Pos_Y_mm']),
                        float(row['Stylus_Pos_Z_mm'])
                    ]
                    points[point_number] = {
                        'femur': femur_pos,
                        'stylus': stylus_pos
                    }
        except FileNotFoundError:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"CSV file not found: {csv_filename}")
            print("=" * 50)
            return None
        except Exception as e:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Error reading CSV file: {e}")
            print("=" * 50)
            return None
        
        # Check if requested point exists
        if point_label not in points:
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Point '{point_label}' not found in CSV file")
            available_points = ', '.join(sorted(points.keys()))
            print(f"Available points: {available_points}")
            print("=" * 50)
            return None
        
        # Get reference data for the requested point
        ref_femur_pos_mm = points[point_label]['femur']
        ref_stylus_pos_mm = points[point_label]['stylus']
        
        # Get femur rotation from CSV
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
            print(f"\n=== ERROR [{timestamp}] ===")
            print(f"Could not find femur rotation for point '{point_label}'")
            print("=" * 50)
            return None
        
        # Convert current femur position to millimeters for calculations
        current_femur_pos_mm = self.calculator.convert_to_millimeters(self.femur_position)
        
        # Calculate updated stylus position
        calculated_position_mm = self.calculator.calculate_updated_stylus_position(
            ref_femur_pos_mm,          # Reference femur position (mm)
            femur_rotation,             # Reference femur rotation (quaternion)
            ref_stylus_pos_mm,         # Reference stylus position (mm)
            current_femur_pos_mm,      # Current femur position (mm)
            self.femur_rotation        # Current femur rotation (quaternion)
        )
        
        # Calculate 4x4 transformation matrix
        # The matrix represents the transformation from the tracked femur position to the calculated stylus position
        # Current rotation matrix from the femur tracker
        current_rotation_matrix = self.calculator.quaternion_to_rotation_matrix(self.femur_rotation)
        
        # Create 4x4 transformation matrix [R|t; 0|1]
        # This matrix transforms from femur tracker frame to the calculated stylus position
        transformation_matrix = np.zeros((4, 4))
        
        # Rotation part (3x3)
        transformation_matrix[0:3, 0:3] = current_rotation_matrix
        
        # Translation part (3x1) - this is the calculated stylus position
        transformation_matrix[0:3, 3] = calculated_position_mm
        
        # Bottom row [0, 0, 0, 1]
        transformation_matrix[3, 3] = 1.0
        
        # Display results
        print(f"\n=== CALCULATED POSITION FOR {point_label} [{timestamp}] ===")
        print(f"Current Femur Position:")
        print(f"  X={current_femur_pos_mm[0]:.2f}mm, Y={current_femur_pos_mm[1]:.2f}mm, Z={current_femur_pos_mm[2]:.2f}mm")
        print(f"Calculated Position:")
        print(f"  X={calculated_position_mm[0]:.2f}mm, Y={calculated_position_mm[1]:.2f}mm, Z={calculated_position_mm[2]:.2f}mm")
        print(f"Reference Femur Position (from {csv_filename}):")
        print(f"  X={ref_femur_pos_mm[0]:.2f}mm, Y={ref_femur_pos_mm[1]:.2f}mm, Z={ref_femur_pos_mm[2]:.2f}mm")
        print(f"Reference Stylus Position (from {csv_filename}):")
        print(f"  X={ref_stylus_pos_mm[0]:.2f}mm, Y={ref_stylus_pos_mm[1]:.2f}mm, Z={ref_stylus_pos_mm[2]:.2f}mm")
        print()
        print(f"4x4 Transformation Matrix:")
        print(f"  [{transformation_matrix[0,0]:10.6f}  {transformation_matrix[0,1]:10.6f}  {transformation_matrix[0,2]:10.6f}  {transformation_matrix[0,3]:10.3f}]")
        print(f"  [{transformation_matrix[1,0]:10.6f}  {transformation_matrix[1,1]:10.6f}  {transformation_matrix[1,2]:10.6f}  {transformation_matrix[1,3]:10.3f}]")
        print(f"  [{transformation_matrix[2,0]:10.6f}  {transformation_matrix[2,1]:10.6f}  {transformation_matrix[2,2]:10.6f}  {transformation_matrix[2,3]:10.3f}]")
        print(f"  [{transformation_matrix[3,0]:10.6f}  {transformation_matrix[3,1]:10.6f}  {transformation_matrix[3,2]:10.6f}  {transformation_matrix[3,3]:10.3f}]")
        print("=" * 50)
        
        return {
            'point_label': point_label,
            'calculated_position_mm': calculated_position_mm,
            'transformation_matrix': transformation_matrix.tolist(),
            'current_femur_pos_mm': current_femur_pos_mm,
            'reference_femur_pos_mm': ref_femur_pos_mm,
            'reference_stylus_pos_mm': ref_stylus_pos_mm,
            'reference_femur_rotation': femur_rotation
        }
    
    def keyboard_input_handler(self):
        """Handle keyboard input in a separate thread"""
        while self.running:
            try:
                key = input().strip().lower()
                
                if key == 'c':
                    self.capture_positions()
                elif key == 's':
                    self.store_positions()
                elif key == 'l':
                    self.list_stored_points()
                elif key == 'e':
                    self.export_data_points()
                elif key == 'r':
                    self.capture_reference()
                elif key == 'u':
                    self.calculate_updated_position()
                elif key == 't':
                    self.test_connection()
                elif key == 'p':
                    # Calculate mapped point
                    print("\nEnter point label to calculate (e.g., L1, M5):")
                    point_label = input().strip().upper()
                    self.calculate_mapped_point(point_label)
                elif key == 'q':
                    print("Quitting...")
                    self.running = False
                    break
                elif key == 'h':
                    print("\nKeyboard Controls:")
                    print("  'c' - Capture and print current positions")
                    print("  's' - Store current positions as a data point")
                    print("  'l' - List all stored data points")
                    print("  'e' - Export data points to file")
                    print("  'r' - Capture reference positions for coordinate calculation")
                    print("  'u' - Calculate updated stylus position based on tracker movement")
                    print("  'p' - Calculate mapped point position (L1-L10, M1-M10)")
                    print("  't' - Test connection to NatNet server")
                    print("  'q' - Quit the program")
                    print("  'h' - Show this help")
                else:
                    print("Unknown command. Press 'h' for help.")
                    
            except EOFError:
                break
            except Exception as e:
                print(f"Keyboard input error: {e}")
    
    def connect_and_run(self):
        """Connect to the server and start receiving data"""
        try:
            print("Starting NatNet client...")
            self.connection_attempted = True
            self.start_connection_animation()
            
            # Start the client with data thread
            if self.client.run('d'):
                self.stop_connection_animation()
                print(f"{Colors.GREEN}Successfully connected to NatNet server!{Colors.END}")
                self.connected = True
                print("Waiting for rigid body data...")
                print("Press 'c' to capture positions, 't' to test connection, 'q' to quit, or Ctrl+C to stop")
                
                # Start keyboard input thread
                self.keyboard_thread = threading.Thread(target=self.keyboard_input_handler, daemon=True)
                self.keyboard_thread.start()
                
                # Keep the script running with connection monitoring
                try:
                    while self.running:
                        # Update connection status periodically
                        self.update_connection_status()
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nStopping client...")
                    self.running = False
                    self.client.shutdown()
                    print("Client stopped.")
            else:
                self.stop_connection_animation()
                print(f"{Colors.RED}Failed to connect to NatNet server{Colors.END}")
                self.connected = False
                return False
                
        except Exception as e:
            print(f"Error: {e}")
            return False
            
        return True

def main():
    """Main function"""
    print("Starting Rigid Body Tracker...")
    
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description='Simple rigid body position tracker')
        parser.add_argument('--femur', type=int, default=DEFAULT_FEMUR_ID, 
                           help=f'Femur tracker rigid body ID (default: {DEFAULT_FEMUR_ID})')
        parser.add_argument('--stylus', type=int, default=DEFAULT_STYLUS_ID, 
                           help=f'Stylus rigid body ID (default: {DEFAULT_STYLUS_ID})')
        parser.add_argument('--server', type=str, default=DEFAULT_SERVER_IP, 
                           help=f'Server IP address (default: {DEFAULT_SERVER_IP})')
        parser.add_argument('--local', type=str, default=DEFAULT_LOCAL_IP, 
                           help=f'Local IP address (default: {DEFAULT_LOCAL_IP})')
        
        args = parser.parse_args()
        
        print(f"Tracking rigid bodies:")
        print(f"  Femur Tracker ID: {args.femur}")
        print(f"  Stylus ID: {args.stylus}")
        print(f"Server IP: {args.server}")
        print(f"Local IP: {args.local}")
        print()
        
        # Create and configure the tracker
        print("Creating tracker...")
        tracker = RigidBodyTracker(femur_id=args.femur, stylus_id=args.stylus, 
                                        server_ip=args.server, local_ip=args.local)
        
        print("Setting up connection...")
        tracker.setup_connection()
        
        print("Starting connection...")
        # Connect and start tracking
        result = tracker.connect_and_run()
        
        if result:
            print("Tracker completed successfully")
        else:
            print("Tracker failed to connect")
            
        return result
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        return False
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
