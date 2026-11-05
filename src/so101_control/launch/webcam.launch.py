from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Publishes the PC webcam on /pc_camera/image_raw (bgr8)
    return LaunchDescription([
        DeclareLaunchArgument('video_device', default_value='/dev/video0',
                              description='V4L2 capture device of the PC webcam'),
        DeclareLaunchArgument('width', default_value='640'),
        DeclareLaunchArgument('height', default_value='480'),
        DeclareLaunchArgument('fps', default_value='30'),
        DeclareLaunchArgument('fourcc', default_value='MJPG',
                              description='Pixel format requested from the camera (MJPG or YUYV)'),
        Node(package='so101_control', executable='webcam_node',
             namespace='pc_camera', name='webcam_node',
             parameters=[{
                 'video_device': LaunchConfiguration('video_device'),
                 'width': LaunchConfiguration('width'),
                 'height': LaunchConfiguration('height'),
                 'fps': LaunchConfiguration('fps'),
                 'fourcc': LaunchConfiguration('fourcc'),
             }],
             output='screen'),
    ])
