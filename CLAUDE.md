# CLAUDE.md

ROS 2 Jazzy workspace for the SO-101 arm (5 arm joints + gripper). One xacro is the single source of truth. Three interchangeable bringups share the same controllers: mock hardware, MuJoCo and Gazebo Harmonic. See `README.md` for fuller setup notes.

## Packages (`src/`)

| Package | Type | Purpose |
|---|---|---|
| `so101_description` | ament_cmake | Xacro URDF, STL meshes, RViz config, view-only launch |
| `so101_bringup` | ament_cmake | Mock-hardware ros2_control bringup |
| `so101_control` | ament_python | Nodes `sine_mover` and `fk_monitor` |
| `so101_mujoco_description` | ament_cmake | MJCF model + `scripts/urdf_to_mjcf.py` |
| `so101_mujoco_bringup` | ament_cmake | MuJoCo ros2_control bringup |
| `so101_gazebo_description` | ament_cmake | Gazebo world + URDF fragment |
| `so101_gazebo_bringup` | ament_cmake | Gazebo Harmonic bringup |

Naming: `so101_<thing>` and `so101_<sim>_{description,bringup}`.

## Build and run

```bash
source /opt/ros/jazzy/setup.bash
colcon build            # --packages-select <pkg> for one package
source install/setup.bash
```

```bash
ros2 launch so101_description view_robot.launch.py      # no controllers
ros2 launch so101_bringup bringup.launch.py             # mock hardware
ros2 launch so101_mujoco_bringup mujoco.launch.py [headless:=false] [rviz:=true] [use_camera:=true]
ros2 launch so101_gazebo_bringup gazebo.launch.py [gui:=true] [rviz:=true]
ros2 run so101_control sine_mover                       # or fk_monitor
ros2 control list_controllers
```

- Run only one bringup at a time. They share controller and topic names. For isolation set a unique `ROS_DOMAIN_ID` and `GZ_PARTITION`.
- Extra apt dependencies: `ros-jazzy-mujoco-ros2-control`, `ros-jazzy-mujoco-vendor`, `ros-jazzy-ros-gz`, `ros-jazzy-gz-ros2-control`. `fk_monitor` also needs `pinocchio` for Python.
- Tests: only the template ament linter stubs in `so101_control/test/` (`colcon test --packages-select so101_control`). There is no CI.
- View MJCF without ROS: `python3 -m mujoco.viewer --mjcf=src/so101_mujoco_description/mjcf/scene.xml`

## Architecture

- **Single source**: `so101_description/urdf/so101.urdf.xacro`. The `use_camera` arg (default true) adds the wrist camera links. It ends with a `<ros2_control>` block defaulting to `mock_components/GenericSystem`.
- **Hardware swap**: `mujoco.launch.py` and `gazebo.launch.py` process the xacro, then regex-replace the `<hardware>` block with the MuJoCo or Gazebo plugin. They raise an error unless there is exactly one `<hardware>` block, so keep it that way.
- **Gazebo**: the launch file also splices `so101_gazebo_description/urdf/so101_gazebo.urdf.xml` before `</robot>`. That file is a fragment, not a standalone URDF. It adds the `world` link, the gz_ros2_control plugin and the camera sensor, and `@CONTROLLERS@` is substituted with the yaml path. World: `worlds/so101_world.sdf`.
- **Controllers** (`config/controllers.yaml`, 100 Hz): `joint_state_broadcaster`, `arm_controller` (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll) and `gripper_controller` (gripper). Both are `JointTrajectoryController` with position commands. **The yaml is copied in three bringup packages and must be kept in sync by hand.**
- **MuJoCo model**: `urdf_to_mjcf.py` generates `mjcf/so101_raw.xml` (gitignored), then `mjcf/so101.xml` is hand-edited. Re-running the script may overwrite those edits. CMake rewrites the mesh path at install time, so **rebuild after editing the MJCF**. Plugin config is in `so101_mujoco_bringup/config/mujoco_plugins.yaml`.
- **Camera**: the name `wrist_camera` must match across the MJCF, `mujoco_plugins.yaml` and the Gazebo sensor. Topics: `/wrist_camera/image_raw`, `camera_info`, and `depth` (MuJoCo only).
- **Control nodes** (`so101_control/so101_control/`):
  - `sine_mover` publishes `JointTrajectory` to `/arm_controller/joint_trajectory` at 100 Hz, sweeping shoulder_pan 0 to 1 rad at 0.5 Hz.
  - `fk_monitor` builds a Pinocchio model from the installed xacro (`use_camera=false`). It subscribes to `/joint_states` and logs the `gripper_frame_link` position in the base frame, throttled to 0.5 s.

## Conventions

- Launch files are Python: 4-space indent, single quotes, `get_package_share_directory`, `OpaqueFunction` with `_launch_setup(context)` for the newer ones. URDF is produced in the launch file with `xacro.process_file(...).toxml()`.
- Keep controller names and topics identical across sims, so nodes work with any of them.
- Install rules are per-package in CMake (`launch config rviz urdf meshes ...`). Add new directories there.

## Known issues

- `view_robot.launch.py` loads `rviz/robot_view.rviz` and `bringup.launch.py` loads `rviz/view_robot.rviz`. Neither exists. Only `so101_description/rviz/basic_description.rviz` does.
- `so101_control/**/__pycache__/*.pyc` are tracked in git despite `.gitignore`.
- The linter stubs in `so101_control/test/` are unmodified template and likely fail (no license headers or docstrings).
- `so101_description/urdf/so101_new_calib_camera.urdf` is a stale static URDF and is unused.
- Licences are inconsistent: Apache-2.0 in `so101_description`, MIT in the other package.xml files.
- The MuJoCo actuator gains (kp=30, kv=1) and camera fovy (60) are hand-tuned guesses, not identified from hardware.
- If RViz fails with `symbol lookup error: /snap/core20/...` (VS Code snap terminal), unset the `GTK_*` and `GIO_*` variables.
