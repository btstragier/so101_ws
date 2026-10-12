import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    desc_share = get_package_share_directory('so101_description')
    bringup_share = get_package_share_directory('so101_bringup')

    xacro_path = os.path.join(desc_share, 'urdf', 'so101.urdf.xacro')
    robot_description = xacro.process_file(
        xacro_path, mappings={'use_camera': 'true'}).toxml()
    controllers_yaml = os.path.join(bringup_share, 'config', 'controllers.yaml')
    rviz_config = os.path.join(desc_share, 'rviz', 'view_robot.rviz')

    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_description}]),
        Node(package='controller_manager', executable='ros2_control_node',
             parameters=[{'robot_description': robot_description}, controllers_yaml],
             output='screen'),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster']),
        Node(package='controller_manager', executable='spawner',
             arguments=['arm_controller']),
        Node(package='controller_manager', executable='spawner',
             arguments=['gripper_controller']),
        Node(package='rviz2', executable='rviz2', arguments=['-d', rviz_config]),
    ])