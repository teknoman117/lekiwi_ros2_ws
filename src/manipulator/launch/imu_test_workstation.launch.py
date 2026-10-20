import os

from launch import LaunchDescription
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # The workstation side of the IMU check with the IMU on the robot (imu_test_robot.launch.py
    # there): only RViz, with pico_lsm6ds3_ros2's validation display. Needs the robot's discovery
    # server (ROBOT_IP).
    #   ros2 launch manipulator imu_test_workstation.launch.py
    return LaunchDescription([
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', os.path.join(get_package_share_directory('pico_lsm6ds3_ros2'),
                                          'rviz', 'validation.rviz')],
        ),
    ])
