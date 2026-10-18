import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode, ParameterFile

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Navigation on the robot: slam_toolbox (slam.launch.py), the Nav2 servers and twist_mux.
    # The base driver and the lidar come from robot.launch.py (nav:=mapping or
    # nav:=localization starts this too). Goals come from RViz (Nav2 Goal) on the workstation.
    #
    # Only the Nav2 servers needed to drive to a pose, not nav2_bringup's navigation_launch.py,
    # which also starts the docking, route, smoother and waypoint servers: less to configure
    # and less load on the Pi. config/nav2_params.yaml has the velocity chain.
    #
    # The servers and their lifecycle manager share one process (one DDS participant). As
    # separate processes, each found the others through the discovery server, slowly on the
    # Pi, and a server could answer a lifecycle transition before it had discovered the
    # manager's response reader: "failed to send response to /controller_server/change_state
    # (timeout)", and the bringup hung there.
    config = os.path.join(get_package_share_directory('manipulator'), 'config')
    nav2_params = ParameterFile(os.path.join(config, 'nav2_params.yaml'), allow_substs=True)
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

    # (package, plugin, node, remappings); the lifecycle manager brings them up in this order
    servers = [
        ('nav2_controller', 'nav2_controller::ControllerServer', 'controller_server',
         nav_cmd_vel),
        ('nav2_planner', 'nav2_planner::PlannerServer', 'planner_server', []),
        ('nav2_behaviors', 'behavior_server::BehaviorServer', 'behavior_server', nav_cmd_vel),
        ('nav2_bt_navigator', 'nav2_bt_navigator::BtNavigator', 'bt_navigator', []),
        ('nav2_velocity_smoother', 'nav2_velocity_smoother::VelocitySmoother',
         'velocity_smoother', nav_cmd_vel),
        ('nav2_collision_monitor', 'nav2_collision_monitor::CollisionMonitor',
         'collision_monitor', []),
    ]
    nav2 = ComposableNodeContainer(
        package='rclcpp_components',
        executable='component_container_isolated',  # one executor (thread) per server
        name='nav2_container',
        namespace='',
        output='screen',
        # The whole file for the process too, as nav2_bringup does: a loaded node gets only its
        # own section, and the costmaps inside controller_server and planner_server
        # (local_costmap, global_costmap) get theirs from the process's --params-file.
        parameters=[nav2_params],
        composable_node_descriptions=[
            ComposableNode(package=package, plugin=plugin, name=name,
                           parameters=[nav2_params], remappings=remappings)
            for package, plugin, name, remappings in servers
        ] + [
            ComposableNode(
                package='nav2_lifecycle_manager',
                plugin='nav2_lifecycle_manager::LifecycleManager',
                name='lifecycle_manager_navigation',
                parameters=[{
                    'autostart': True,
                    'node_names': [name for _, _, name, _ in servers],
                }],
            ),
        ],
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
        nav2,
        twist_mux,
    ])
