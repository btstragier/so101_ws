import os
import re

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            OpaqueFunction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile


def _launch_setup(context):
    headless = LaunchConfiguration('headless').perform(context)
    use_camera = LaunchConfiguration('use_camera').perform(context)
    rviz = LaunchConfiguration('rviz').perform(context)
    webcam = LaunchConfiguration('webcam').perform(context)

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
    plugins = os.path.join(bringup_share, 'config', 'mujoco_plugins.yaml')
    nodes = [
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             parameters=[{'robot_description': urdf}]),
        Node(package='mujoco_ros2_control', executable='ros2_control_node',
             parameters=[{'robot_description': urdf}, controllers,
                         ParameterFile(plugins)],
             output='screen'),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster']),
        Node(package='controller_manager', executable='spawner',
             arguments=['arm_controller']),
        Node(package='controller_manager', executable='spawner',
             arguments=['gripper_controller']),
    ]
    if rviz == 'true':
        nodes.append(Node(
            package='rviz2', executable='rviz2',
            arguments=['-d', os.path.join(bringup_share, 'rviz', 'mujoco.rviz')]))
    if webcam == 'true':
        nodes.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('so101_control'),
                         'launch', 'webcam.launch.py'))))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run MuJoCo without the GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                              description='Start RViz (robot model + wrist camera image)'),
        DeclareLaunchArgument('use_camera', default_value='true',
                              description='Include camera links in the URDF (the MuJoCo model always has the camera)'),
        DeclareLaunchArgument('webcam', default_value='false',
                              description='Also publish the PC webcam on /pc_camera/image_raw'),
        OpaqueFunction(function=_launch_setup),
    ])
