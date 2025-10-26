# Rigid Body Tracker

A real-time motion capture tracking system that uses OptiTrack's NatNet protocol to track femoral tracker and stylus positions, calculate mapped point positions, and provide visualization capabilities.

## Features

- **Real-time Tracking**: Track femoral tracker (ID 1) and stylus (ID 2) positions using NatNet protocol
- **Position Calculations**: Calculate updated positions based on tracker movement using quaternion-based rotation transformations
- **Mapped Point Calculation**: Calculate the position of any mapped point (L1-L10, M1-M10) based on current femur tracker data
- **4x4 Transformation Matrices**: Get 4x4 transformation matrices representing the calculated position
- **Data Storage**: Store and export captured position data to CSV files
- **Connection Monitoring**: Robust connection monitoring with health checks and error reporting
- **3D Visualization**: Visualize captured points with connecting lines between L and M point pairs
- **Modular Design**: Separate calculation logic in dedicated module for easy maintenance

## Requirements

- Python 3.7+
- NumPy
- Matplotlib (for visualization)
- OptiTrack NatNet SDK (NatNetClient, MoCapData, DataDescriptions)

## Installation

1. Clone or download this repository
2. Install required Python packages:
   ```bash
   pip install numpy matplotlib
   ```
3. Ensure NatNet SDK files are present in the directory:
   - `NatNetClient.py`
   - `MoCapData.py`
   - `DataDescriptions.py`

## Configuration

### IP Address Settings

Edit the following variables in `rigid_body_tracker.py`:

```python
DEFAULT_SERVER_IP = "192.168.86.39"  # NatNet server IP address
DEFAULT_LOCAL_IP = "192.168.86.39"   # Local client IP address
```

Or use command line arguments:

```bash
python rigid_body_tracker.py --server 192.168.1.100 --local 192.168.1.50
```

### Rigid Body IDs

The default IDs are:
- Femur Tracker: ID 1
- Stylus: ID 2
- Robot Base: ID 3

These can be modified in the configuration section or via command line arguments.

## Usage

### Starting the Tracker

Run the main tracker:

```bash
python rigid_body_tracker.py
```

Or with custom IP addresses:

```bash
python rigid_body_tracker.py --server 192.168.1.100 --local 192.168.1.50
```

### Keyboard Commands

Once running, use the following keyboard commands:

| Key | Command | Description |
|-----|---------|-------------|
| **c** | Capture positions | Print current positions of femur tracker and stylus |
| **s** | Store data point | Store current positions as a data point |
| **l** | List stored points | Display all stored data points |
| **e** | Export data | Export all stored data points to CSV file |
| **r** | Capture reference | Capture reference positions for coordinate calculation |
| **u** | Calculate updated position | Calculate updated stylus position based on tracker movement |
| **p** | Calculate mapped point | Calculate position for a specific mapped point (L1-L10, M1-M10) |
| **t** | Test connection | Test connection to NatNet server |
| **h** | Help | Show available commands |
| **q** | Quit | Exit the program |

### Workflow Example

1. **Start the tracker**: `python rigid_body_tracker.py`
2. **Test connection**: Press `t` to verify connection to NatNet server
3. **Capture reference**: Press `r` to capture reference positions
4. **Move the tracker** to a new position
5. **Calculate updated position**: Press `u` to see the calculated stylus position
6. **Calculate mapped point**: Press `p` and enter a point label (e.g., `L3`) to get a 4x4 transformation matrix

### Mapped Point Calculation

The 'p' command allows you to calculate the position of any mapped point based on:
- Current femur tracker position and rotation
- Reference data from the CSV file (`Attune_5_Left_Points.csv`)

The output includes:
- Calculated stylus position in 3D space (X, Y, Z in mm)
- Current femur tracker position
- Reference data from the CSV
- **4x4 transformation matrix** representing the transformation

### Visualization

To visualize the mapped points:

```bash
python visualize_points.py
```

This opens a 3D plot showing:
- Blue circles for L points (L1-L10)
- Red triangles for M points (M1-M10)
- Green lines connecting L1-M1, L2-M2, ..., L10-M10

## File Structure

```
Tracker_Testing/
├── rigid_body_tracker.py       # Main tracker application
├── position_calculations.py    # Mathematical calculation module
├── visualize_points.py         # 3D visualization script
├── Attune_5_Left_Points.csv    # Reference data for mapped points
├── NatNetClient.py             # NatNet client library
├── MoCapData.py                # Motion capture data structures
├── DataDescriptions.py         # Data description utilities
└── README.md                   # This file
```

## Understanding the 4x4 Transformation Matrix

When you calculate a mapped point (using the 'p' command), you receive a 4x4 transformation matrix in the format:

```
[R11  R12  R13  Tx]
[R21  R22  R23  Ty]
[R31  R32  R33  Tz]
[0    0    0    1 ]
```

Where:
- **Top-left 3x3 block (R)**: Rotation matrix representing the current femur tracker orientation
- **Top-right 3x1 block (T)**: Translation vector containing the calculated stylus position (X, Y, Z in mm)
- **Bottom row**: [0, 0, 0, 1] for proper homogeneous coordinate transformation

This matrix can be used for robotics applications, coordinate transformations, or further mathematical calculations.

## Coordinate System

The system uses **Y-up, X-right, Z-forward** coordinate system:
- **X-axis**: Right (positive values go right)
- **Y-axis**: Up (positive values go up)
- **Z-axis**: Forward (positive values go forward)

## Connection Settings

- **Connection Timeout**: 15 seconds without data before considering disconnected
- **Connection Check Interval**: 2 seconds between health checks
- **Connection Animation**: Visual spinner during connection attempts

## Troubleshooting

### No Data Received

If you're not receiving data:
1. Check that NatNet server is running
2. Verify IP addresses are correct
3. Ensure rigid bodies are being actively tracked
4. Press 't' to test the connection

### Connection Issues

- Verify network connectivity to the server
- Check firewall settings
- Ensure the correct network adapter is being used
- Try using multicast if unicast fails

### Import Errors

If you get import errors:
```bash
pip install numpy matplotlib
```

## License

This project is provided as-is for educational and research purposes.

## Support

For issues or questions, check the NatNet SDK documentation or contact your OptiTrack representative.
