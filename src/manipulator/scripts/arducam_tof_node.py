#!/usr/bin/env python3
"""Arducam ToF point cloud publisher, with the point cloud in my robot's frame.

Arducam's node (arducam_rclpy_tof_pointcloud, third_party/Arducam_tof_camera) publishes
'point_cloud' (PointCloud2) and 'depth_frame' (Float32MultiArray). This runs the same publisher,
with two changes:

- The cloud is stamped with the 'frame_id' parameter (default tof_optical_frame,
  urdf/manipulator.urdf.xacro); Arducam's node always uses 'map'. Its points are in optical
  coordinates (x right, y down, z forward), which is what that frame is.
- The camera is opened at its own video device. Arducam's node always opens index 0
  (/dev/video0), but on a Pi 5 each CSI port has its own block of video devices, and which port
  comes first can change (another camera, a kernel update, a reboot). With the ToF elsewhere,
  index 0 is the other camera, and the SDK fails with "I2C bus name doesn't match any bus
  present!". By default (--video-index auto) the ToF's index is found the way Arducam suggests
  (media-ctl -p): the media device whose topology has the arducam-pivariety sensor, and its
  lowest /dev/videoN.

Arguments: --cfg <camera configuration file> (optional, as Arducam's node),
           --video-index auto|<N> (default auto).
Needs Arducam's SDK (the ArducamDepthCamera Python module), the camera's driver on the Pi, and
media-ctl (v4l-utils) for --video-index auto.
"""

import glob
import re
import subprocess
import sys
from argparse import ArgumentParser

import rclpy
from rclpy.executors import ExternalShutdownException

SENSOR = 'arducam-pivariety'


def find_video_index(sensor=SENSOR):
    """The lowest /dev/videoN of the media device whose topology has 'sensor', or None."""
    for media in sorted(glob.glob('/dev/media*')):
        try:
            topology = subprocess.run(['media-ctl', '-d', media, '-p'], capture_output=True,
                                      text=True, timeout=5).stdout
        except (OSError, subprocess.TimeoutExpired):
            return None
        if sensor in topology:
            nodes = [int(n) for n in re.findall(r'device node name /dev/video(\d+)', topology)]
            if nodes:
                return min(nodes)
    return None


def main():
    rclpy.init(args=sys.argv)
    try:
        from arducam_rclpy_tof_pointcloud import tof_pointcloud as upstream
    except ImportError as e:   # usually the SDK: ArducamDepthCamera
        print(f'arducam_tof_node: cannot import the Arducam ToF publisher or SDK: {e}',
              file=sys.stderr)
        rclpy.try_shutdown()
        sys.exit(1)

    parser = ArgumentParser()
    parser.add_argument('--cfg', type=str, help='camera configuration file')
    parser.add_argument('--video-index', default='auto',
                        help="the ToF's /dev/videoN, or 'auto' (default) to find it")
    args, _ = parser.parse_known_args(rclpy.utilities.remove_ros_args(sys.argv)[1:])
    if args.video_index == 'auto':
        index = find_video_index()
        if index is None:
            print(f'arducam_tof_node: no media device with {SENSOR} found (is media-ctl '
                  'installed, and the ToF driver loaded?); trying /dev/video0', file=sys.stderr)
            index = 0
        else:
            print(f'arducam_tof_node: ToF camera found at /dev/video{index}')
    else:
        index = int(args.video_index)

    def init_camera(self, options):
        # Arducam's TOFPublisher.__init_camera, with the video device index
        tof = upstream.ArducamCamera()
        if options.cfg is not None:
            ret = tof.openWithFile(options.cfg, index)
        else:
            ret = tof.open(upstream.Connection.CSI, index)
        if ret != 0:
            print(f'Failed to open camera at /dev/video{index}. Error code:', ret)
            return None
        ret = tof.start(upstream.FrameType.DEPTH)
        if ret != 0:
            print('Failed to start camera. Error code:', ret)
            tof.close()
            return None
        info = tof.getCameraInfo()
        if info.device_type == upstream.DeviceType.HQVGA:
            self.width_ = info.width
            self.height_ = info.height
            tof.setControl(upstream.Control.RANGE, 4)
        elif info.device_type == upstream.DeviceType.VGA:
            self.width_ = info.width
            self.height_ = info.height // 10 - 1
        print(f'Open camera success, width: {self.width_}, height: {self.height_}')
        return tof

    class TofPublisher(upstream.TOFPublisher):
        # replaces the private (name-mangled) camera setup of Arducam's class
        _TOFPublisher__init_camera = init_camera

        def __init__(self, options):
            super().__init__(options)
            self.header.frame_id = self.declare_parameter('frame_id', 'tof_optical_frame').value
            self.get_logger().info(f'point cloud frame: {self.header.frame_id}, '
                                   f'camera /dev/video{index}')

    options = upstream.Option()
    options.cfg = args.cfg
    try:
        node = TofPublisher(options)
    except Exception as e:  # noqa: BLE001 -- the publisher raises a bare Exception
        print(f'arducam_tof_node: {e}', file=sys.stderr)
        rclpy.try_shutdown()
        sys.exit(1)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.stop()
        except KeyboardInterrupt:   # a second Ctrl-C (terminal and launch) while it waits
            pass
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
