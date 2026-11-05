from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Publishes the PC webcam on /pc_camera/image_raw and /pc_camera/camera_info
    return LaunchDescription([
        DeclareLaunchArgument('video_device', default_value='/dev/video0',
                              description='V4L2 capture device of the PC webcam'),
        DeclareLaunchArgument('image_size', default_value='[640,480]',
                              description='Capture resolution [width,height]'),
        Node(package='v4l2_camera', executable='v4l2_camera_node',
             namespace='pc_camera', name='v4l2_camera',
             parameters=[{
                 'video_device': LaunchConfiguration('video_device'),
                 'image_size': LaunchConfiguration('image_size'),
                 'camera_frame_id': 'pc_camera_optical_frame',
             }],
             output='screen'),
    ])
