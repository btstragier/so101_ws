import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray

# MediaPipe's 21-point hand skeleton (wrist=0, then 4 points per finger)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # pinky + palm
]

# BGR colour per hand id
HAND_COLORS = [(0, 255, 0), (255, 128, 0)]


class HandVisualizerNode(Node):
    """Draws /hand_landmarks on top of the camera image and publishes it."""

    def __init__(self):
        super().__init__('hand_visualizer_node')

        self.declare_parameter('camera_topic', '/pc_camera/image_raw')
        self.declare_parameter('landmarks_topic', '/hand_landmarks')
        self.declare_parameter('output_topic', '/hand_vis')
        # landmarks older than this are not drawn (hand left the frame)
        self.declare_parameter('max_age', 0.5)

        camera_topic = self.get_parameter('camera_topic').value
        landmarks_topic = self.get_parameter('landmarks_topic').value
        output_topic = self.get_parameter('output_topic').value
        self.max_age = self.get_parameter('max_age').value

        self.bridge = CvBridge()
        self.hands = []  # list of (N, 2) arrays of normalized x, y
        self.hands_time = None

        self.create_subscription(
            Image, camera_topic, self.image_callback, qos_profile_sensor_data)
        self.create_subscription(
            Float32MultiArray, landmarks_topic, self.landmarks_callback, 10)
        self.publisher = self.create_publisher(Image, output_topic, 10)

        self.get_logger().info(
            f'Overlaying {landmarks_topic} on {camera_topic} -> {output_topic}')

    def landmarks_callback(self, msg):
        # flat [hand_id, landmark_id, x, y, z] * N
        data = np.asarray(msg.data, dtype=np.float32).reshape(-1, 5)
        hands = {}
        for hand_id, _, x, y, _ in data:
            hands.setdefault(int(hand_id), []).append((x, y))
        self.hands = [np.array(pts) for _, pts in sorted(hands.items())]
        self.hands_time = self.get_clock().now()

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8').copy()
        h, w = frame.shape[:2]

        fresh = (self.hands_time is not None and
                 (self.get_clock().now() - self.hands_time).nanoseconds * 1e-9
                 < self.max_age)
        if fresh:
            for i, pts in enumerate(self.hands):
                color = HAND_COLORS[i % len(HAND_COLORS)]
                px = [(int(x * w), int(y * h)) for x, y in pts]
                for a, b in HAND_CONNECTIONS:
                    if a < len(px) and b < len(px):
                        cv2.line(frame, px[a], px[b], color, 2)
                for p in px:
                    cv2.circle(frame, p, 4, (0, 0, 255), -1)

        out = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        out.header = msg.header
        self.publisher.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = HandVisualizerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
