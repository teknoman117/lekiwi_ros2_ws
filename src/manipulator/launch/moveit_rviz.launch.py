import os
import sys

from moveit_configs_utils.launches import generate_moveit_rviz_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manipulator_moveit import manipulator_moveit_config  # noqa: E402


def generate_launch_description():
    # RViz with the MotionPlanning panel, the arm marker and my sensors (workstation.launch.py)
    return generate_moveit_rviz_launch(manipulator_moveit_config())
