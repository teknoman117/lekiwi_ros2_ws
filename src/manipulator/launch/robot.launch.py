import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from ament_index_python.packages import get_package_share_directory


def robot_and_navigation(context):
    # With navigation, twist_mux drives the base, and joy_teleop is one of its inputs
    manipulator = get_package_share_directory('manipulator')
    lekiwi_bringup = get_package_share_directory('lekiwi_bringup')
    nav = LaunchConfiguration('nav').perform(context).strip().lower()
    if nav not in ('false', 'mapping', 'localization'):
        raise RuntimeError(f'nav:={nav}: use false, mapping or localization')

    actions = [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(lekiwi_bringup, 'launch', 'robot.launch.py')),
        launch_arguments={
            'description_file': os.path.join(manipulator, 'urdf', 'manipulator.urdf.xacro'),
            'moveit_config_package': 'manipulator',
            'base_cmd_vel_topic':
                '/omni_wheel_drive_controller/cmd_vel' if nav == 'false' else '/cmd_vel_joy',
        }.items(),
    )]
    if nav != 'false':
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(manipulator, 'launch', 'navigation.launch.py')),
            launch_arguments={
                'slam_mode': nav,
                'map': LaunchConfiguration('map'),
            }.items(),
        ))
    return actions


def generate_launch_description():
    # My LeKiwi on the robot: lekiwi_bringup's robot.launch.py with my model and MoveIt config,
    # plus my sensors, and optionally navigation (navigation.launch.py). All of robot.launch.py's
    # arguments (port, use_mock_hardware, limp, marker_mode, joy, ...) and sensors.launch.py's
    # (lidar, lidar_port, tof, wrist_camera, ...) can be given here.
    manipulator = get_package_share_directory('manipulator')

    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(manipulator, 'launch', 'sensors.launch.py')),
        condition=IfCondition(LaunchConfiguration('sensors')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('sensors', default_value='true',
                              description='Start the sensor drivers (sensors.launch.py)'),
        DeclareLaunchArgument('nav', default_value='false',
                              description='Navigation (slam_toolbox, Nav2, twist_mux): false, '
                                          'mapping (build a map) or localization (in map)'),
        DeclareLaunchArgument('map', default_value='',
                              description='nav:=localization: the serialized map, without '
                                          'extension (e.g. /maps/apartment)'),
        OpaqueFunction(function=robot_and_navigation),
        sensors,
    ])
