# manipulator

My LeKiwi: the stock LeKiwi (`lekiwi_bringup`, unchanged) plus my sensors, which are not part of
the LeKiwi project:

| Sensor | Mounted on | Frames (the drivers' `frame_id`) | Driver |
|---|---|---|---|
| LDROBOT LD19 lidar (LD06 also works) | `upper_plate_link`: base 100 mm back, 35 mm up | `lidar_link` (scan centre) | `ldlidar_stl_ros2` (submodule `src/ldlidar_stl_ros2`) |
| Arducam ToF camera (frames only: the point cloud's origin, no geometry) | `base_link`: 100 mm forward, 30 mm up (the stock chassis camera's place) | `tof_link`, `tof_optical_frame` | Arducam's `arducam_rclpy_tof_pointcloud` (submodule, `third_party/`), run by `scripts/arducam_tof_node.py` |
| Raspberry Pi Camera 3 on a custom mount | `gripper_link` (turns with `wrist_roll`) | `wrist_camera_link`, `wrist_camera_optical_frame` (frames only) | `camera_ros` (TODO) |

The lidar and ToF poses are measured; **the wrist camera's pose is a placeholder**. The ToF and
wrist cameras are frames only (where their data is measured from); the lidar is a placeholder
cylinder: replace it with a mesh (`meshes/`) and regenerate the collision pairs (below). The
lidar's standoff is not modelled yet.

## Running

```bash
# robot (all of lekiwi_bringup robot.launch.py's arguments work here too)
ros2 launch manipulator robot.launch.py
ros2 launch manipulator robot.launch.py use_mock_hardware:=true sensors:=false   # testing
# workstation
ros2 launch manipulator workstation.launch.py
```

- `robot.launch.py`: `lekiwi_bringup`'s `robot.launch.py` with `description_file` =
  `urdf/manipulator.urdf.xacro` and `moveit_config_package` = `manipulator`, plus
  `sensors.launch.py` (`sensors:=false` to leave the drivers out).
- `sensors.launch.py`: `lidar`, `lidar_model` (`LDLiDAR_LD19`, or `LDLiDAR_LD06`), `lidar_port`
  (default `/dev/ldlidar`, the symlink the driver's udev rule creates), `tof`, `wrist_camera`. A driver that is not installed
  is skipped with a message.
- `workstation.launch.py`: `lekiwi_bringup`'s `workstation.launch.py` with this package's MoveIt
  and RViz configs (the robot model with the sensors; LaserScan `/scan`, PointCloud2
  `/tof/points`, Image `/wrist_camera/image_raw`).

## Files

| File | |
|---|---|
| `urdf/manipulator.urdf.xacro` | the stock robot (`lekiwi_bringup/urdf/lekiwi.urdf.xacro`) + the sensor macros, with the mount poses |
| `urdf/sensors/*.xacro` | one macro per sensor (`parent`, `name`, `*origin`) |
| `config/manipulator_moveit.urdf.xacro` | MoveIt's model: the robot + the ground (`lekiwi_moveit_config/config/ground.xacro`) |
| `config/manipulator.srdf.xacro` | the stock semantics (`lekiwi_semantic`) + the sensors' collision pairs |
| `config/*.yaml` | driver parameters |
| `launch/manipulator_moveit.py` | `lekiwi_moveit_config`'s builder with this package's model and SRDF |

## Collision pairs

The arm stays collision-checked against the lidar, the base and the ground (the ToF and wrist
cameras have no geometry). After changing a sensor, its geometry or its pose, regenerate the sensors'
disabled pairs and replace them in `config/manipulator.srdf.xacro` (needs `ros-jazzy-moveit-py`):

```bash
M=$(ros2 pkg prefix manipulator)/share/manipulator/config
ros2 run lekiwi_moveit_config compute_disabled_collisions.py \
  $M/manipulator_moveit.urdf.xacro $M/manipulator.srdf.xacro --new-only
```

With `--new-only` it prints only pairs the SRDF does not have yet, so delete the old sensor
pairs first.

## Drivers

- **LD19**: `ldlidar_stl_ros2`, node `lidar`, `/scan` in `lidar_link` (`config/ld06.yaml`). Port
  `/dev/ldlidar`: on the robot's host, install the driver's udev rule once
  (`sudo cp src/ldlidar_stl_ros2/scripts/ldlidar.rules /etc/udev/rules.d/`, then
  `sudo udevadm control --reload-rules && sudo udevadm trigger`). It needs a compile fix on Jazzy
  (a missing `#include <pthread.h>`), given in the workspace's `colcon.meta`. Do not run the
  driver's own launch files: they publish an example `base_link -> base_laser` transform.
- **Arducam ToF**: Arducam's publisher, run by `scripts/arducam_tof_node.py` (node `tof`), which
  stamps the cloud with `frame_id` (`tof_optical_frame`): Arducam's node always uses `map`.
  Topics `/tof/points` (PointCloud2) and `/tof/depth` (Float32MultiArray, metres). It opens the
  camera at its own video device (`tof_video_index`, default `auto`: the media device with the
  `arducam-pivariety` sensor, via `media-ctl`). Arducam's node always opens `/dev/video0`, which
  on a Pi 5 with the Camera Module 3 can be the other camera ("I2C bus name doesn't match any bus
  present!"); which port comes first can change with kernel updates and reboots. Needs
  Arducam's SDK (the `ArducamDepthCamera` Python module) and the camera's driver on the Pi; without
  them the node exits with a message.

## TODO (needs the Pi 5 and the cameras)

- The Arducam SDK and the ToF camera's driver on the Pi 5, natively, then in the robot image.
- `camera_ros` built against Raspberry Pi's libcamera (the Pi 5 needs it); its camera id and
  whether it takes `frame_id` (`config/pi_camera3.yaml`).
- The lidar's 0 degree direction: check `/scan` in RViz against an object in front of the robot.
- Docker: the camera stack (Arducam SDK, Raspberry Pi libcamera, `camera_ros`) in the robot
  image, and the camera devices in `docker/compose.robot.yaml`. The lidar is passed in already
  (`LIDAR_DEVICE`, set by `docker/setup-env.sh robot` when `/dev/ldlidar` exists).
