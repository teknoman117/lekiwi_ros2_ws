import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # The IMU check (pico_lsm6ds3_ros2 validation.launch.py) with the IMU on the robot: the whole
    # IMU stack here (the driver, Madgwick, the display's static world -> odom), RViz on the
    # workstation (imu_test_workstation.launch.py). Instead of robot.launch.py, not alongside
    # it: Madgwick publishes odom -> imu_link for the display, where the robot model has imu_link
    # on the top plate, and sensors.launch.py would start a second driver.
    #   ros2 launch manipulator imu_test_robot.launch.py [device:=...]
    return LaunchDescription([
        DeclareLaunchArgument('device', default_value='',
                              description="The IMU's evdev node; empty: the first "
                                          '/dev/input/by-id/usb-2e8a_LSM6DS3*-event-*'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('pico_lsm6ds3_ros2'), 'launch',
                'validation.launch.py')),
            launch_arguments={'device': LaunchConfiguration('device'), 'rviz': 'false'}.items(),
        ),
    ])
