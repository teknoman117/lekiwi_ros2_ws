import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # My LeKiwi on the robot: lekiwi_bringup's robot.launch.py with my model and MoveIt config,
    # plus my sensors. All of robot.launch.py's arguments (port, use_mock_hardware, limp,
    # marker_mode, joy, ...) and sensors.launch.py's (lidar, lidar_port, tof, wrist_camera, ...)
    # can be given here.
    manipulator = get_package_share_directory('manipulator')
    lekiwi_bringup = get_package_share_directory('lekiwi_bringup')

    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(lekiwi_bringup, 'launch', 'robot.launch.py')),
        launch_arguments={
            'description_file': os.path.join(manipulator, 'urdf', 'manipulator.urdf.xacro'),
            'moveit_config_package': 'manipulator',
        }.items(),
    )

    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(manipulator, 'launch', 'sensors.launch.py')),
        condition=IfCondition(LaunchConfiguration('sensors')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('sensors', default_value='true',
                              description='Start the sensor drivers (sensors.launch.py)'),
        robot,
        sensors,
    ])
