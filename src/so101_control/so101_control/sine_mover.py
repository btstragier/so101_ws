import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import math

class SineMover(Node):
    def __init__(self):
        super().__init__('sine_mover')

        self.pub = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10)

        self.joint_names = ['shoulder_pan', 'shoulder_lift', 'elbow_flex',
                            'wrist_flex', 'wrist_roll']
        self.period = 0.01  # seconds between messages
        self.t0 = self.get_clock().now()
        self.timer = self.create_timer(self.period, self.on_timer)

    def on_timer(self):
        # seconds since the node started
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9

        positions = [0.0] * 5
        positions[0] = 0.5 * (1.0 + math.sin(2.0 * math.pi * 0.5 * t))
        # positions[1] = 0.5 * (1.0 + math.sin(2.0 * math.pi * 0.5 * t + math.pi / 5))
        # positions[2] = 0.5 * (1.0 + math.sin(2.0 * math.pi * 0.5 * t + 2 * math.pi / 5))
        # positions[3] = 0.5 * (1.0 + math.sin(2.0 * math.pi * 0.5 * t + 3 * math.pi / 5))
        # positions[4] = 0.5 * (1.0 + math.sin(2.0 * math.pi * 0.5 * t + 4 * math.pi / 5))

        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start = Duration(sec=0, nanosec=int(self.period * 1e9))

        msg = JointTrajectory()
        msg.joint_names = self.joint_names
        msg.points = [point]
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SineMover()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()