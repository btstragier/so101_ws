import os
import time

import cv2
import mediapipe as mp
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray


def _default_model_path():
    """Find hand_landmarker.task in the installed share dir, else the source tree."""
    share = os.path.join(
        get_package_share_directory('hand_tracking'),
        'models', 'hand_landmarker.task')
    if os.path.exists(share):
        return share
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'models', 'hand_landmarker.task')


class HandTrackingNode(Node):

    def __init__(self):
        super().__init__('hand_tracking_node')

        self.declare_parameter('camera_topic', '/pc_camera/image_raw')
        self.declare_parameter('num_hands', 2)
        self.declare_parameter('model_path', '')

        self.camera_topic = self.get_parameter('camera_topic').value
        num_hands = self.get_parameter('num_hands').value
        model_path = self.get_parameter('model_path').value or _default_model_path()

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f'MediaPipe model not found: {model_path}. Download '
                'hand_landmarker.task into hand_tracking/models/ or pass '
                '-p model_path:=/path/to/hand_landmarker.task')

        self.bridge = CvBridge()

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5)
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

        # v4l2_camera publishes with the sensor-data (best effort) QoS; a
        # default reliable subscriber would never connect to it.
        self.subscription = self.create_subscription(
            Image, self.camera_topic, self.image_callback, qos_profile_sensor_data)
        self.publisher = self.create_publisher(
            Float32MultiArray, '/hand_landmarks', 10)

        self.start_time = time.monotonic()
        self.last_timestamp = -1

        self.get_logger().info('MediaPipe hand tracking initialized')
        self.get_logger().info(f'Subscribing to: {self.camera_topic}')
        self.get_logger().info('Publishing landmarks to: /hand_landmarks '
                               '(flat [hand_id, landmark_id, x, y, z] * N)')

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            rgb_frame = np.ascontiguousarray(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # VIDEO mode needs strictly increasing timestamps in milliseconds
            timestamp_ms = int((time.monotonic() - self.start_time) * 1000)
            timestamp_ms = max(timestamp_ms, self.last_timestamp + 1)
            self.last_timestamp = timestamp_ms

            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

            output = Float32MultiArray()
            for hand_id, hand_landmarks in enumerate(result.hand_landmarks or []):
                for landmark_id, lm in enumerate(hand_landmarks):
                    output.data.extend([float(hand_id), float(landmark_id),
                                        float(lm.x), float(lm.y), float(lm.z)])
            self.publisher.publish(output)

        except Exception as e:
            self.get_logger().error(f'Hand tracking error: {e}')

    def destroy_node(self):
        self.landmarker.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HandTrackingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
