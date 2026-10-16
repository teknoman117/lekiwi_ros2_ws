import importlib.util
import os

from ament_index_python.packages import get_package_share_directory


def manipulator_moveit_config():
    """lekiwi_moveit_config's builder, with my model (my robot plus the ground) and SRDF."""
    # Load lekiwi_moveit_config's launch/moveit_config.py by path, under its own module name.
    path = os.path.join(get_package_share_directory('lekiwi_moveit_config'), 'launch',
                        'moveit_config.py')
    spec = importlib.util.spec_from_file_location('lekiwi_moveit_config_builder', path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder.lekiwi_moveit_config(package='manipulator', robot_name='manipulator',
                                        urdf='config/manipulator_moveit.urdf.xacro',
                                        srdf='config/manipulator.srdf.xacro')
