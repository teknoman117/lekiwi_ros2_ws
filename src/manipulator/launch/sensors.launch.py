import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def enabled(context, name):
    return LaunchConfiguration(name).perform(context).strip().lower() in ('true', '1')


def available(package):
    try:
        get_package_share_directory(package)
        return True
    except PackageNotFoundError:
        return False


def sensors(context):
    # Each driver starts when enabled and installed; a missing driver is reported, not fatal.
    config = os.path.join(get_package_share_directory('manipulator'), 'config')
    actions = []

    def missing(name, package):
        actions.append(LogInfo(msg=f'{name}: driver package {package} is not installed; skipped'))

    if enabled(context, 'lidar'):
        if available('ldlidar_stl_ros2'):
            actions.append(Node(
                package='ldlidar_stl_ros2', executable='ldlidar_stl_ros2_node', name='lidar',
                output='screen',
                parameters=[os.path.join(config, 'ld06.yaml'), {
                    'product_name': LaunchConfiguration('lidar_model').perform(context),
                    'port_name': LaunchConfiguration('lidar_port').perform(context),
                }],
            ))
        else:
            missing('lidar', 'ldlidar_stl_ros2')

    if enabled(context, 'tof'):
        if available('arducam_rclpy_tof_pointcloud'):
            # Arducam's publisher with the cloud in tof_optical_frame (scripts/arducam_tof_node.py)
            actions.append(Node(
                package='manipulator', executable='arducam_tof_node.py', name='tof',
                output='screen',
                arguments=['--video-index',
                           LaunchConfiguration('tof_video_index').perform(context)],
                parameters=[os.path.join(config, 'arducam_tof.yaml')],
                remappings=[('point_cloud', '/tof/points'), ('depth_frame', '/tof/depth')],
            ))
        else:
            missing('tof', 'arducam_rclpy_tof_pointcloud')

    if enabled(context, 'wrist_camera'):
        if available('camera_ros'):
            actions.append(Node(
                package='camera_ros', executable='camera_node', name='wrist_camera',
                output='screen',
                parameters=[os.path.join(config, 'pi_camera3.yaml')],
            ))
        else:
            missing('wrist_camera', 'camera_ros')
    return actions


def generate_launch_description():
    # My LeKiwi's sensor drivers. The frame ids in config/*.yaml are frames of
    # urdf/manipulator.urdf.xacro, so TF places the data.
    return LaunchDescription([
        DeclareLaunchArgument('lidar', default_value='true', description='LD19 (or LD06) lidar'),
        DeclareLaunchArgument('lidar_model', default_value='LDLiDAR_LD19',
                              description='LDLiDAR_LD19 or LDLiDAR_LD06'),
        DeclareLaunchArgument('lidar_port', default_value='/dev/ldlidar',
                              description="The lidar's serial port (the driver's udev rule creates /dev/ldlidar)"),
        DeclareLaunchArgument('tof', default_value='true', description='Arducam ToF camera'),
        DeclareLaunchArgument('tof_video_index', default_value='auto',
                              description="The ToF camera's /dev/videoN, or auto: the video "
                                          'device of the media device with the arducam-pivariety '
                                          'sensor (media-ctl)'),
        DeclareLaunchArgument('wrist_camera', default_value='true',
                              description='Pi Camera Module 3 on the wrist'),
        OpaqueFunction(function=sensors),
    ])
