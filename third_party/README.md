# third_party

Repositories that are not ROS workspaces themselves. colcon ignores this directory
(`COLCON_IGNORE`); the ROS packages inside them are symlinked into `src/`:

| Repository | Package | Symlink |
|---|---|---|
| `Arducam_tof_camera` (submodule) | `arducam_rclpy_tof_pointcloud` | `src/arducam_rclpy_tof_pointcloud` |

(Arducam's repository root is a CMake project that needs their SDK; colcon would try to build it
as a package if it were under `src/`.)
