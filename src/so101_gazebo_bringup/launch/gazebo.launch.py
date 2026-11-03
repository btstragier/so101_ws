import os
import re

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription, OpaqueFunction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _launch_setup(context):
    gui = LaunchConfiguration('gui').perform(context) == 'true'
    rviz = LaunchConfiguration('rviz').perform(context) == 'true'

    desc_share = get_package_share_directory('so101_description')
    gz_desc_share = get_package_share_directory('so101_gazebo_description')
    bringup_share = get_package_share_directory('so101_gazebo_bringup')
    controllers = os.path.join(bringup_share, 'config', 'controllers.yaml')
    world = os.path.join(gz_desc_share, 'worlds', 'so101_world.sdf')

    # Reuse the existing xacro; swap the mock <hardware> block for
    # gz_ros2_control and splice in the Gazebo extras (world joint, plugin
    # tag, camera sensor) just before </robot>.
    urdf = xacro.process_file(
        os.path.join(desc_share, 'urdf', 'so101.urdf.xacro'),
        mappings={'use_camera': 'true'}).toxml()
    urdf, n = re.subn(
        r'<hardware>.*?</hardware>',
        '<hardware><plugin>gz_ros2_control/GazeboSimSystem</plugin></hardware>',
        urdf, flags=re.S)
    if n != 1:
        raise RuntimeError('expected exactly one <hardware> block in the xacro')
    with open(os.path.join(gz_desc_share, 'urdf', 'so101_gazebo.urdf.xml')) as f:
        extras = f.read().replace('@CONTROLLERS@', controllers)
    urdf = urdf.replace('</robot>', extras + '</robot>')

    gz_launch = os.path.join(
        get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
    # -r: start running; -s: server only (no GUI); --headless-rendering lets
    # the camera render without a display.
    gz_args = f'-r {world}' if gui else f'-r -s --headless-rendering {world}'

    nodes = [
        # package://so101_description/... mesh URIs resolve through this path
        AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH', os.path.dirname(desc_share)),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch),
            launch_arguments={'gz_args': gz_args}.items()),
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             parameters=[{'robot_description': urdf, 'use_sim_time': True}]),
        Node(package='ros_gz_sim', executable='create',
             arguments=['-topic', 'robot_description', '-name', 'so101'],
             output='screen'),
        # Gazebo -> ROS: clock and the wrist camera
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             arguments=[
                 '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                 '/wrist_camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
                 '/wrist_camera/camera_info@sensor_msgs/msg/CameraInfo'
                 '[gz.msgs.CameraInfo'],
             output='screen'),
    ]
    # the controller_manager only exists once the model is spawned
    for name in ('joint_state_broadcaster', 'arm_controller',
                 'gripper_controller'):
        nodes.append(Node(
            package='controller_manager', executable='spawner',
            arguments=[name, '--controller-manager-timeout', '120']))
    if rviz:
        nodes.append(Node(
            package='rviz2', executable='rviz2',
            arguments=['-d', os.path.join(bringup_share, 'rviz', 'gazebo.rviz')],
            parameters=[{'use_sim_time': True}]))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true',
                              description='Show the Gazebo window (false = server only)'),
        DeclareLaunchArgument('rviz', default_value='true',
                              description='Start RViz (robot model + wrist camera image)'),
        OpaqueFunction(function=_launch_setup),
    ])
