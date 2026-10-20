# manipulator

My LeKiwi: the stock LeKiwi (`lekiwi_bringup`, unchanged) plus my sensors, which are not part of
the LeKiwi project:

| Sensor | Mounted on | Frames (the drivers' `frame_id`) | Driver |
|---|---|---|---|
| LDROBOT LD19 lidar (LD06 also works) | `upper_plate_link`: base 100 mm back, 35 mm up | `lidar_link` (scan centre) | `ldlidar_stl_ros2` (submodule `src/ldlidar_stl_ros2`) |
| Arducam ToF camera (frames only: the point cloud's origin, no geometry) | `base_link`: 100 mm forward, 30 mm up (the stock chassis camera's place) | `tof_link`, `tof_optical_frame` | Arducam's `arducam_rclpy_tof_pointcloud` (submodule, `third_party/`), run by `scripts/arducam_tof_node.py` |
| Pico 2 + LSM6DS3 IMU (USB) | `upper_plate_link`: 30 mm back, 70 mm left, 4 mm up | `imu_link` (frame only) | `pico_lsm6ds3_ros2` (submodule `src/pico_lsm6ds3_ros2`): `/imu/data_raw`, `/imu/data` (Madgwick orientation) |
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
- `sensors.launch.py`: `lidar`, `lidar_filter` (the robot out of `/scan`, below), `imu`, `imu_device`, `imu_stationary_source`, `lidar_model` (`LDLiDAR_LD19`, or `LDLiDAR_LD06`), `lidar_port`
  (default `/dev/ldlidar`, the symlink the driver's udev rule creates), `tof`, `wrist_camera`. A driver that is not installed
  is skipped with a message.
- `workstation.launch.py`: `lekiwi_bringup`'s `workstation.launch.py` with this package's MoveIt
  and RViz configs (the robot model with the sensors; LaserScan `/scan`, PointCloud2
  `/tof/points`, Image `/wrist_camera/image_raw`), plus the navigation displays (below).
- `robot.launch.py nav:=mapping` / `nav:=localization map:=...`: navigation, below.

## Files

| File | |
|---|---|
| `urdf/manipulator.urdf.xacro` | the stock robot (`lekiwi_bringup/urdf/lekiwi.urdf.xacro`) + the sensor macros, with the mount poses |
| `urdf/sensors/*.xacro` | one macro per sensor (`parent`, `name`, `*origin`) |
| `config/manipulator_moveit.urdf.xacro` | MoveIt's model: the robot + the ground (`lekiwi_moveit_config/config/ground.xacro`) |
| `config/manipulator.srdf.xacro` | the stock semantics (`lekiwi_semantic`) + the sensors' collision pairs |
| `config/*.yaml` | driver parameters |
| `config/slam_toolbox.yaml`, `config/nav2_params.yaml`, `config/twist_mux.yaml` | navigation |
| `launch/navigation.launch.py`, `launch/slam.launch.py` | navigation: slam_toolbox, the Nav2 servers, twist_mux |
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

## Odometry: wheels + IMU

`robot.launch.py` (`ekf:=true`, the default) runs `robot_localization`'s EKF
(`config/ekf.yaml`): the wheel odometry's `vx`, `vy` and yaw rate, and the IMU's yaw rate
(`/imu/data_raw`), into `odom -> base_footprint` and `/odometry/filtered`, which Nav2 uses. The
omni controller's own TF is off then (`config/omni_ekf.yaml`, through `lekiwi_bringup`'s
`extra_controller_config`); it still publishes `/omni_wheel_drive_controller/odom`.

Rotation comes from the gyro: the covariances decide (the wheels' yaw-rate variance 0.03
(rad/s)^2, the gyro's ~3e-6), and the gyro does not see wheel slip. Translation still comes from
the wheels, so a wheel spinning in place is still an error that only slam_toolbox's scan
matching corrects. 2D mode: a level `base_footprint`, as Nav2 and slam_toolbox expect.

`ekf:=false`: the omni controller's odometry and TF alone, as before; then set Nav2's
`odom_topic` (`config/nav2_params.yaml`) back to `/omni_wheel_drive_controller/odom`.

Check: the odometry checks (Navigation, below), with the yaw from `/odometry/filtered`, and a loop
over carpet edges back to a floor mark, comparing `/odometry/filtered` with
`/omni_wheel_drive_controller/odom`.

## Navigation

slam_toolbox (map and `map -> odom` from `/scan` and the wheel odometry), Nav2 (MPPI, omni motion
model) and twist_mux, all on the robot. `robot.launch.py nav:=...` adds `navigation.launch.py`
and points joy_teleop at twist_mux:

```
joy_teleop -> /cmd_vel_joy (priority 100) --+
Nav2 ... collision_monitor -> /cmd_vel (10) -+-> twist_mux -> /omni_wheel_drive_controller/cmd_vel
```

The joystick always wins: touch it to take over from Nav2, release it and Nav2 continues after
0.5 s. Everything is TwistStamped. The omni controller stops the wheels 0.5 s after the last
command (`cmd_vel_timeout`).

**Before the first map**, check on the robot (in RViz, fixed frame `odom`):

1. Odometry: drive 1 m forward, 1 m sideways and turn 360 degrees with the joystick, and compare
   `/omni_wheel_drive_controller/odom` with a tape measure. More than ~5% off: fix
   `wheel_radius`, `robot_radius` or `wheel_offset` in
   `lekiwi_description/config/omni_controllers.yaml`, or a wheel's direction.
2. Lidar: the scan must line up with the walls and stay still while the robot turns in place
   (the lidar's 0 degree direction, TODO below).
3. Self-hits: the lidar sees the arm. `sensors.launch.py` removes the points inside a box
   around the robot (`config/lidar_filter.yaml`, `laser_filters`): the driver publishes
   `/scan_raw`, the filter `/scan`. In RViz, enable "Lidar raw (with the robot)" (red) and check
   that the box removes all of the arm, and nothing outside the robot.
4. `robot_radius` (0.18 m in `config/nav2_params.yaml`): the base plus the stowed arm.

**Build a map**: `nav:=mapping` (Docker: `--profile mapping`, see the workspace README). Drive around slowly with the joystick,
and turn slowly (under ~0.5 rad/s): the LD19 takes 0.1 s per turn, so a fast turn smears the
scan. Go back to rooms already seen to close loops. Then save it, in the robot's `shell`:

```bash
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/maps/apartment'}"                       # for nav:=localization
ros2 run nav2_map_server map_saver_cli -f /maps/apartment \
  --ros-args -p save_map_timeout:=10.0                  # an image of it (.pgm, .yaml)
```

You can already send goals while mapping (RViz: 2D Goal Pose).

**Navigate in it**: `nav:=localization map:=/maps/apartment` (Docker: `--profile localization`,
the map from `NAV_MAP`, default `/maps/apartment`; `/maps` is `MAPS_DIR` on the host, default
`lekiwi_ros2_ws/maps`).
In RViz, set the fixed frame to `map`, give the robot's pose with 2D Pose Estimate, then goals
with 2D Goal Pose.

Tuning, in `config/nav2_params.yaml`: speeds (`vx_max`, `vy_max`, `wz_max` in MPPI and
`velocity_smoother`), `inflation_radius` (doorways), MPPI's `batch_size` (lower it if the
controller warns that it misses its 20 Hz rate on the Pi).

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

- **IMU**: `pico_lsm6ds3_ros2` (Pico 2 + LSM6DS3 over USB HID; firmware
  `teknoman117/pico-lsm6ds3-hid`), started by `sensors.launch.py` with `publish_tf:=false`. The
  gyro bias is measured whenever the IMU itself is at rest (`imu_stationary_source:=imu`).
  `both` also requires the wheel odometry to be still, but then nothing is measured without
  odometry (early in the bringup, `limp:=true`), and the driver publishes uncorrected rates. `/imu/data_raw` (rates, acceleration) and `/imu/data` (plus Madgwick's
  orientation), in `imu_link`. On the robot's host the event node must be readable by the
  container's input group (`INPUT_GID`); `/dev/input` is already passed in.

  **IMU axes**: the model takes the chip's axes to match the base's (x forward, y left, z up).
  Check after mounting, with `ros2 topic echo /imu/data_raw`:
  1. At rest on the floor: `linear_acceleration` about (0, 0, +9.8).
  2. Lift the front of the robot (nose up): `linear_acceleration.x` goes positive (the
     accelerometer reads +g along whichever axis points up).
  3. Lift the left side: `linear_acceleration.y` goes positive.
  4. Turn it counter-clockwise (seen from above): `angular_velocity.z` goes positive.
  A sign or axis that disagrees means the chip is turned: put the rotation in the `imu_joint`
  `rpy` in `urdf/manipulator.urdf.xacro`.

## TODO (needs the Pi 5 and the cameras)

- The Arducam SDK and the ToF camera's driver on the Pi 5, natively, then in the robot image.
- `camera_ros` built against Raspberry Pi's libcamera (the Pi 5 needs it); its camera id and
  whether it takes `frame_id` (`config/pi_camera3.yaml`).
- The lidar's 0 degree direction: check `/scan` in RViz against an object in front of the robot.
- Docker: the camera stack (Arducam SDK, Raspberry Pi libcamera, `camera_ros`) in the robot
  image, and the camera devices in `docker/compose.robot.yaml`. The lidar is passed in already
  (`LIDAR_DEVICE`, set by `docker/setup-env.sh robot` when `/dev/ldlidar` exists).
