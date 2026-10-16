import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # My LeKiwi on the workstation: lekiwi_bringup's workstation.launch.py (RViz, joystick
    # driver) with my MoveIt config and RViz config (my model, and the sensor displays). Its
    # arguments (rviz, joy, joy_device, joy_deadzone) can be given here.
    lekiwi_bringup = get_package_share_directory('lekiwi_bringup')
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(lekiwi_bringup, 'launch', 'workstation.launch.py')),
            launch_arguments={'moveit_config_package': 'manipulator'}.items(),
        ),
    ])
