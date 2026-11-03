#!/usr/bin/env python3
"""Convert so101.urdf.xacro into a raw MJCF (mjcf/so101_raw.xml).

Run with ROS sourced and the `mujoco` Python package available:
    python3 urdf_to_mjcf.py [--no-camera]
The raw output is a starting point; so101.xml is the hand-edited version
(actuators, floor, tuned contacts) that the simulation actually uses.
"""
import argparse
import os
import re
import tempfile

import mujoco
import xacro
from ament_index_python.packages import get_package_share_directory

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'mjcf', 'so101_raw.xml')
FINAL = os.path.join(HERE, '..', 'mjcf', 'so101.xml')
# Relative to mjcf/; resolves in both src/ and install/share/ layouts.
MESHDIR = '../../so101_description/meshes'

JOINTS = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex',
          'wrist_roll', 'gripper']
HEADER = '''  <compiler angle="radian" meshdir="%s"/>
  <option timestep="0.002" integrator="implicitfast"/>
  <default>
    <joint armature="0.01" damping="0.05" frictionloss="0.02"/>
    <position kp="30" kv="1" forcerange="-10 10"/>
    <!-- arm geoms collide with the world, never with each other -->
    <geom type="mesh" contype="1" conaffinity="0"/>
  </default>
''' % MESHDIR


def postprocess(raw_path, out_path):
    """Raw URDF import -> single geom per mesh, actuators, relative meshdir."""
    text = open(raw_path).read()
    # drop the visual-only duplicates (group=1, no contact)
    text = re.sub(r'\n\s*<geom [^>]*group="1"[^>]*/>', '', text)
    # type/contype now come from <default>
    text = text.replace(' type="mesh"', '')
    # swap the absolute compiler line for HEADER
    text = re.sub(r'  <compiler [^>]*/>\n', HEADER, text)
    ranges = dict(re.findall(
        r'<joint name="(\w+)" range="([^"]+)"', text))
    # Wrist camera. The URDF camera link's lens axis is +Z (barrel up to
    # z=0.0263 in the mesh); MuJoCo cameras look along their own -Z with +Y up,
    # so flip Z; X/Y are then swapped so image-up is world-up at the home
    # pose. fovy is a guess for a generic UVC module.
    text = re.sub(
        r'(<body name="wrist_camera_link"[^>]*>)',
        r'\1\n<camera name="wrist_camera" pos="0 0 0.0265" '
        r'xyaxes="0 1 0 1 0 0" fovy="60" resolution="640 480"/>',
        text, count=1)
    acts = ''.join(
        '    <position name="%s" joint="%s" ctrlrange="%s"/>\n'
        % (j, j, ranges[j]) for j in JOINTS)
    text = text.replace(
        '</mujoco>', '  <actuator>\n%s  </actuator>\n</mujoco>' % acts)
    open(out_path, 'w').write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-camera', action='store_true',
                    help='omit the wrist camera mount/body/<camera>')
    args = ap.parse_args()

    share = get_package_share_directory('so101_description')
    urdf = xacro.process_file(
        os.path.join(share, 'urdf', 'so101.urdf.xacro'),
        mappings={'use_camera': 'false' if args.no_camera else 'true'}).toxml()

    # MuJoCo can't resolve package:// and needs <mujoco><compiler/> to keep
    # the base link and not discard visual-only geometry.
    mesh_dir = os.path.join(share, 'meshes')
    urdf = urdf.replace('package://so101_description/meshes/', '')
    urdf = re.sub(r'<ros2_control.*?</ros2_control>', '', urdf, flags=re.S)
    urdf = urdf.replace(
        '<robot name="so101_new_calib_camera"',
        '<robot name="so101"', 1)
    urdf = re.sub(
        r'(<robot [^>]*>)',
        r'\1<mujoco><compiler meshdir="%s" balanceinertia="true" '
        r'discardvisual="false" fusestatic="false"/></mujoco>' % mesh_dir,
        urdf, count=1)

    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(urdf)
    model = mujoco.MjModel.from_xml_path(f.name)
    mujoco.mj_saveLastXML(OUT, model)
    print(f'wrote {os.path.abspath(OUT)}  (nq={model.nq}, nbody={model.nbody})')
    postprocess(OUT, FINAL)
    print(f'wrote {os.path.abspath(FINAL)}')


if __name__ == '__main__':
    main()
