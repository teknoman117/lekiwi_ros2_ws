import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from ament_index_python.packages import get_package_share_directory
from nav2_common.launch import RewrittenYaml


def slam(context):
    # slam_toolbox's own launch files, so the node's lifecycle handling matches the installed
    # version: online_async_launch.py to build a map, localization_launch.py to localize in a
    # saved one. Both with config/slam_toolbox.yaml.
    mode = LaunchConfiguration('slam_mode').perform(context)
    map_file = LaunchConfiguration('map').perform(context)
    if mode not in ('mapping', 'localization'):
        raise RuntimeError(f'slam_mode:={mode}: use mapping or localization')

    rewrites = {'mode': mode}
    if mode == 'localization':
        if not map_file:
            raise RuntimeError('slam_mode:=localization needs map:=<serialized map, without '
                               'the .posegraph/.data extension>')
        rewrites['map_file_name'] = map_file

    params = RewrittenYaml(
        source_file=os.path.join(
            get_package_share_directory('manipulator'), 'config', 'slam_toolbox.yaml'),
        param_rewrites=rewrites,
        convert_types=True,
    )
    launch_file = 'online_async_launch.py' if mode == 'mapping' else 'localization_launch.py'
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', launch_file)),
        launch_arguments={
            'slam_params_file': params,
            'use_sim_time': 'false',  # their default is true
        }.items(),
    )]


def generate_launch_description():
    # slam_toolbox on the robot: the map and map -> odom from /scan and the wheel odometry.
    #   ros2 launch manipulator slam.launch.py                    # build a map
    #   ros2 launch manipulator slam.launch.py slam_mode:=localization map:=/maps/apartment
    # Save a map while mapping (both: the serialized one to localize in later, and an image):
    #   ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
    #     "{filename: '/maps/apartment'}"
    #   ros2 run nav2_map_server map_saver_cli -f /maps/apartment
    return LaunchDescription([
        DeclareLaunchArgument('slam_mode', default_value='mapping',
                              description='mapping: build a map; localization: localize in map'),
        DeclareLaunchArgument('map', default_value='',
                              description='Serialized map for localization, without extension '
                                          '(e.g. /maps/apartment)'),
        OpaqueFunction(function=slam),
    ])
