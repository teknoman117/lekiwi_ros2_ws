import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Navigation on the robot: slam_toolbox (slam.launch.py), the Nav2 servers and twist_mux.
    # The base driver and the lidar come from robot.launch.py (nav:=mapping or
    # nav:=localization starts this too). Goals come from RViz (Nav2 Goal) on the workstation.
    #
    # Only the Nav2 servers needed to drive to a pose, not nav2_bringup's navigation_launch.py,
    # which also starts the docking, route, smoother and waypoint servers: less to configure
    # and less load on the Pi. config/nav2_params.yaml has the velocity chain.
    config = os.path.join(get_package_share_directory('manipulator'), 'config')
    nav2_params = os.path.join(config, 'nav2_params.yaml')
    # The Nav2 servers use relative cmd_vel names; see nav2_params.yaml for the chain
    nav_cmd_vel = [('cmd_vel', 'cmd_vel_nav')]

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('manipulator'), 'launch', 'slam.launch.py')),
        launch_arguments={
            'slam_mode': LaunchConfiguration('slam_mode'),
            'map': LaunchConfiguration('map'),
        }.items(),
    )

    def nav2_node(package, executable, remappings=()):
        return Node(
            package=package,
            executable=executable,
            name=executable,
            output='screen',
            parameters=[nav2_params],
            remappings=list(remappings),
        )

    # (package, node, remappings); the lifecycle manager brings them up in this order
    servers = [
        ('nav2_controller', 'controller_server', nav_cmd_vel),
        ('nav2_planner', 'planner_server', ()),
        ('nav2_behaviors', 'behavior_server', nav_cmd_vel),
        ('nav2_bt_navigator', 'bt_navigator', ()),
        ('nav2_velocity_smoother', 'velocity_smoother', nav_cmd_vel),
        ('nav2_collision_monitor', 'collision_monitor', ()),
    ]
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': [name for _, name, _ in servers],
        }],
    )

    # The joystick (joy_teleop, cmd_vel_topic /cmd_vel_joy) over Nav2 (/cmd_vel), to the base
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        name='twist_mux',
        output='screen',
        parameters=[os.path.join(config, 'twist_mux.yaml')],
        remappings=[('cmd_vel_out', '/omni_wheel_drive_controller/cmd_vel')],
    )

    return LaunchDescription([
        DeclareLaunchArgument('slam_mode', default_value='mapping',
                              description='mapping: build a map; localization: localize in map'),
        DeclareLaunchArgument('map', default_value='',
                              description='Serialized map for localization, without extension '
                                          '(e.g. /maps/apartment)'),
        slam,
        *(nav2_node(*server) for server in servers),
        lifecycle_manager,
        twist_mux,
    ])
