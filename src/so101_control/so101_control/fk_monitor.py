import os

import numpy as np
import pinocchio as pin
import rclpy
import xacro
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from sensor_msgs.msg import JointState


class FkMonitor(Node):
    def __init__(self):
        super().__init__('fk_monitor')

        # Build the robot model once, from the same xacro the launch file uses
        xacro_path = os.path.join(
            get_package_share_directory('so101_description'),
            'urdf', 'so101.urdf.xacro')
        urdf_xml = xacro.process_file(
            xacro_path, mappings={'use_camera': 'false'}).toxml()
        self.model = pin.buildModelFromXML(urdf_xml)
        self.data = self.model.createData()

        # Which point on the robot do we want the position of?
        self.ee_frame_id = self.model.getFrameId('gripper_frame_link')
        if self.ee_frame_id >= self.model.nframes:
            raise RuntimeError('gripper_frame_link not found in model')

        self.sub = self.create_subscription(
            JointState, '/joint_states', self.on_joint_state, 10)

    def on_joint_state(self, msg):
        # Put each joint value in the slot Pinocchio expects, matched by name
        q = np.zeros(self.model.nq)
        for name, pos in zip(msg.name, msg.position):
            jid = self.model.getJointId(name)
            if jid < self.model.njoints:   # skip names Pinocchio doesn't know
                q[self.model.joints[jid].idx_q] = pos

        # Forward kinematics: where is every frame for this q?
        pin.forwardKinematics(self.model, self.data, q)
        pin.updateFramePlacements(self.model, self.data)

        # Position of the end-effector, expressed in the base frame
        p = self.data.oMf[self.ee_frame_id].translation
        self.get_logger().info(
            f'end effector: x={p[0]:.3f} y={p[1]:.3f} z={p[2]:.3f}',
            throttle_duration_sec=0.5)


def main(args=None):
    rclpy.init(args=args)
    node = FkMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()