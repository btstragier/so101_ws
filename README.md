# SO-101 ROS 2 workspace

### Purpose

To practice my ROS2, reinforcement learning, control and perception skills.

### Packages

| Package | What it is |
| --- | --- |
| `so101_description` | URDF/xacro, meshes and RViz config for the SO-101 arm |
| `so101_bringup` | ros2_control bringup with **mock hardware** + RViz |
| `so101_control` | Python nodes: `sine_mover` (trajectory publisher), `fk_monitor` (Pinocchio forward kinematics) |
| `so101_mujoco_description` | MuJoCo (MJCF) model of the arm, generated from the URDF |
| `so101_mujoco_bringup` | ros2_control bringup running the arm in **MuJoCo** |

The mock and MuJoCo setups are independent and use the same controller names
(`joint_state_broadcaster`, `arm_controller`, `gripper_controller`), so the
nodes in `so101_control` work with either one.

### Requirements

- ROS 2 Jazzy
- `ros-jazzy-mujoco-ros2-control` and `ros-jazzy-mujoco-vendor` (MuJoCo setup only)
- `pinocchio` (for `fk_monitor`)

```bash
sudo apt install ros-jazzy-mujoco-ros2-control ros-jazzy-mujoco-vendor
```

### Build

```bash
cd ~/Desktop/Projects/so101_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

### Run

Each launch below needs its own terminal with the workspace sourced
(`source install/setup.bash`). Run only one bringup at a time.

#### View the model only

Joint sliders (joint_state_publisher_gui) + RViz, no controllers:

```bash
ros2 launch so101_description view_robot.launch.py
```

#### Mock hardware (ros2_control + RViz)

```bash
ros2 launch so101_bringup bringup.launch.py
```

This starts `robot_state_publisher`, `ros2_control_node` with
`mock_components/GenericSystem`, the three controllers and RViz.

> Fixed Frame to `base_link` and add a RobotModel display.

#### MuJoCo

```bash
ros2 launch so101_mujoco_bringup mujoco.launch.py
```

This opens the MuJoCo viewer and RViz, and starts `robot_state_publisher`, the
`mujoco_ros2_control` `ros2_control_node` (which also publishes the camera) and
the same three controllers.

Launch arguments:

| Argument | Default | Description |
| --- | --- | --- |
| `headless` | `false` | `true` runs MuJoCo without the GUI (camera topics still publish) |
| `rviz` | `true` | start RViz with the robot model and a Wrist Camera image display (`rviz/mujoco.rviz`) |
| `use_camera` | `true` | include the camera links in the URDF used by `robot_state_publisher`/TF (the MuJoCo model always has the camera) |

```bash
ros2 launch so101_mujoco_bringup mujoco.launch.py headless:=true
```

#### Wrist camera (MuJoCo)

The MuJoCo model has a wrist camera, `wrist_camera`, mounted on the gripper and
looking toward the jaws. The `mujoco_ros2_control` camera plugin publishes it
at 15 Hz (640x480, configured in
`so101_mujoco_bringup/config/mujoco_plugins.yaml`):

| Topic | Type |
| --- | --- |
| `/wrist_camera/image_raw` | `sensor_msgs/Image` (rgb8) |
| `/wrist_camera/depth` | `sensor_msgs/Image` |
| `/wrist_camera/camera_info` | `sensor_msgs/CameraInfo` |

To see what the camera sees, use either of these:

```bash
# 1. ROS image viewer (works headless too)
ros2 run rqt_image_view rqt_image_view /wrist_camera/image_raw

# 2. In the MuJoCo window (not headless), click the window first, then:
#      ]  or  [    cycle through cameras (free -> wrist_camera -> ...)
#      Esc         back to the free camera
#      Tab         show/hide the left panel (it has a Rendering section with a Camera dropdown)
```

(RViz also works: add an Image display on `/wrist_camera/image_raw`.)

The camera's field of view (`fovy="60"`) is a guess, not measured from the real
module. Change it in `scripts/urdf_to_mjcf.py` and regenerate the MJCF.

> Troubleshooting: if RViz dies with `symbol lookup error: /snap/core20/...`,
> your terminal was started from the VS Code snap and inherited its `GTK_*`/
> `GIO_*` variables. Use a normal terminal, or run
> `unset GTK_PATH GIO_MODULE_DIR GTK_EXE_PREFIX LOCPATH GTK_IM_MODULE_FILE GSETTINGS_SCHEMA_DIR`
> and reset `XDG_DATA_DIRS` before launching.

### Move and inspect the arm

With either bringup running, in other terminals:

```bash
# Check the controllers are active
ros2 control list_controllers

# Sweep shoulder_pan back and forth
ros2 run so101_control sine_mover

# Print the end-effector position (base frame) from forward kinematics
ros2 run so101_control fk_monitor

# Send a single move by hand
ros2 topic pub --once /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
  "{joint_names: [shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll], \
    points: [{positions: [0.5, -0.5, 0.5, 0.0, 0.0], time_from_start: {sec: 2}}]}"
```

### MuJoCo model

`so101_mujoco_description/mjcf/so101.xml` is generated from the URDF:

```bash
# needs ROS sourced and the `mujoco` Python package
python3 src/so101_mujoco_description/scripts/urdf_to_mjcf.py
```

The generated MJCF uses one collision mesh per link, a `wrist_camera` camera, position actuators with
ranges taken from the URDF joint limits, and no arm self-collision. Actuator
gains (`kp`, `kv`, `armature`) are tuned by hand in the script, not
identified from real STS3215 servos. Forward kinematics match the URDF
(checked against Pinocchio).

To look at the model without ROS:

```bash
python3 -m mujoco.viewer --mjcf=src/so101_mujoco_description/mjcf/scene.xml
```

### Credit

The URDF for the source model: TheRobotStudio/SO-ARM100
