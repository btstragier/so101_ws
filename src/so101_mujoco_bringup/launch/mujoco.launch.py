import os
import re

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _launch_setup(context):
    headless = LaunchConfiguration('headless').perform(context)
    use_camera = LaunchConfiguration('use_camera').perform(context)

    desc_share = get_package_share_directory('so101_description')
    bringup_share = get_package_share_directory('so101_mujoco_bringup')
    model_path = os.path.join(
        get_package_share_directory('so101_mujoco_description'),
        'mjcf', 'scene.xml')

    # Reuse the existing xacro (joints + command/state interfaces) and only
    # swap its mock_components <hardware> block for the MuJoCo plugin.
    urdf = xacro.process_file(
        os.path.join(desc_share, 'urdf', 'so101.urdf.xacro'),
        mappings={'use_camera': use_camera}).toxml()
    hardware = (
        '<hardware>'
        '<plugin>mujoco_ros2_control/MujocoSystemInterface</plugin>'
        f'<param name="mujoco_model">{model_path}</param>'
        f'<param name="headless">{headless}</param>'
        '</hardware>')
    urdf, n = re.subn(r'<hardware>.*?</hardware>', hardware, urdf, flags=re.S)
    if n != 1:
        raise RuntimeError('expected exactly one <hardware> block in the xacro')

    controllers = os.path.join(bringup_share, 'config', 'controllers.yaml')
    return [
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             parameters=[{'robot_description': urdf}]),
        Node(package='mujoco_ros2_control', executable='ros2_control_node',
             parameters=[{'robot_description': urdf}, controllers],
             output='screen'),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster']),
        Node(package='controller_manager', executable='spawner',
             arguments=['arm_controller']),
        Node(package='controller_manager', executable='spawner',
             arguments=['gripper_controller']),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run MuJoCo without the GUI'),
        DeclareLaunchArgument('use_camera', default_value='false'),
        OpaqueFunction(function=_launch_setup),
    ])
