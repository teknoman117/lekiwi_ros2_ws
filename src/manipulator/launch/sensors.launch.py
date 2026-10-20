import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
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
            # With the filter, the driver publishes /scan_raw and the filter /scan (the robot
            # removed, config/lidar_filter.yaml); without it, the driver publishes /scan.
            lidar_filter = enabled(context, 'lidar_filter')
            if lidar_filter and not available('laser_filters'):
                missing('lidar_filter', 'laser_filters')
                lidar_filter = False
            actions.append(Node(
                package='ldlidar_stl_ros2', executable='ldlidar_stl_ros2_node', name='lidar',
                output='screen',
                parameters=[os.path.join(config, 'ld06.yaml'), {
                    'product_name': LaunchConfiguration('lidar_model').perform(context),
                    'port_name': LaunchConfiguration('lidar_port').perform(context),
                    'topic_name': 'scan_raw' if lidar_filter else 'scan',
                }],
            ))
            if lidar_filter:
                actions.append(Node(
                    package='laser_filters', executable='scan_to_scan_filter_chain',
                    name='scan_to_scan_filter_chain', output='screen',
                    parameters=[os.path.join(config, 'lidar_filter.yaml')],
                    remappings=[('scan', '/scan_raw'), ('scan_filtered', '/scan')],
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

    if enabled(context, 'imu'):
        if available('pico_lsm6ds3_ros2'):
            # The driver (/imu/data_raw) and Madgwick (/imu/data), in imu_link. No TF from
            # Madgwick: robot_localization owns odom -> base_footprint once the IMU is fused.
            # imu_stationary_source decides when the gyro bias is measured. Not "both" by
            # default: the driver then also waits for the wheel odometry, which is missing early
            # in the bringup and with limp:=true, and publishes uncorrected rates meanwhile.
            actions.append(IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(
                    get_package_share_directory('pico_lsm6ds3_ros2'), 'launch', 'imu.launch.py')),
                launch_arguments={
                    'device': LaunchConfiguration('imu_device').perform(context),
                    'frame_id': 'imu_link',
                    'publish_tf': 'false',
                    'stationary_source':
                        LaunchConfiguration('imu_stationary_source').perform(context),
                }.items(),
            ))
        else:
            missing('imu', 'pico_lsm6ds3_ros2')
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
        DeclareLaunchArgument('lidar_filter', default_value='true',
                              description='Remove the robot (the arm) from the scan: the driver '
                                          'publishes /scan_raw, laser_filters /scan '
                                          '(config/lidar_filter.yaml)'),
        DeclareLaunchArgument('tof', default_value='true', description='Arducam ToF camera'),
        DeclareLaunchArgument('tof_video_index', default_value='auto',
                              description="The ToF camera's /dev/videoN, or auto: the video "
                                          'device of the media device with the arducam-pivariety '
                                          'sensor (media-ctl)'),
        DeclareLaunchArgument('wrist_camera', default_value='true',
                              description='Pi Camera Module 3 on the wrist'),
        DeclareLaunchArgument('imu', default_value='true',
                              description='Pico + LSM6DS3 IMU (pico_lsm6ds3_ros2)'),
        DeclareLaunchArgument('imu_stationary_source', default_value='imu',
                              description='When the IMU driver measures the gyro bias: imu (the '
                                          'IMU at rest), odom (the wheel odometry still) or both'),
        DeclareLaunchArgument('imu_device', default_value='',
                              description="The IMU's evdev node; empty: the first "
                                          '/dev/input/by-id/usb-2e8a_LSM6DS3*-event-*'),
        OpaqueFunction(function=sensors),
    ])
