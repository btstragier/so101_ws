import threading
import time

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class WebcamNode(Node):
    """Publishes a PC webcam as sensor_msgs/Image using OpenCV.

    Unlike v4l2_camera this can request MJPG, which is what lets most
    webcams actually reach 30 fps.
    """

    def __init__(self):
        super().__init__('webcam_node')

        self.declare_parameter('video_device', '/dev/video0')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('fourcc', 'MJPG')
        self.declare_parameter('frame_id', 'pc_camera_optical_frame')

        device = self.get_parameter('video_device').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        fps = self.get_parameter('fps').value
        fourcc = self.get_parameter('fourcc').value
        self.frame_id = self.get_parameter('frame_id').value

        # a bare number means a device index, anything else is a path
        self.cap = cv2.VideoCapture(
            int(device) if str(device).isdigit() else device, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError(f'could not open camera {device}')
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # 1 halves the frame rate (no double buffering)

        got = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
               int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
               self.cap.get(cv2.CAP_PROP_FPS))
        self.get_logger().info(
            f'{device}: requested {width}x{height}@{fps} {fourcc}, '
            f'driver reports {got[0]}x{got[1]}@{got[2]:.0f}')

        self.publisher = self.create_publisher(
            Image, 'image_raw', qos_profile_sensor_data)

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        # blocking reads in their own thread so we always publish the
        # newest frame instead of letting frames queue up
        count, t0 = 0, time.monotonic()
        while self.running and rclpy.ok():
            ok, frame = self.cap.read()
            if not ok:
                self.get_logger().warn('camera read failed',
                                       throttle_duration_sec=2.0)
                continue
            msg = Image()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            msg.height, msg.width = frame.shape[:2]
            msg.encoding = 'bgr8'
            msg.step = msg.width * 3
            msg.data = frame.tobytes()
            self.publisher.publish(msg)
            count += 1
            if time.monotonic() - t0 >= 5.0:
                self.get_logger().info(f'publishing {count / (time.monotonic() - t0):.1f} fps')
                count, t0 = 0, time.monotonic()

    def destroy_node(self):
        self.running = False
        self.thread.join(timeout=1.0)
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebcamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
