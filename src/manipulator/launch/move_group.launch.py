import os
import sys

from moveit_configs_utils.launches import generate_move_group_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manipulator_moveit import manipulator_moveit_config  # noqa: E402


def generate_launch_description():
    # move_group for my LeKiwi (robot.launch.py starts it on the robot)
    return generate_move_group_launch(manipulator_moveit_config())
