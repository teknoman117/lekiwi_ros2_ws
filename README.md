# LeKiwi ROS 2 Workspace

A workspace for using the LeKiwi Low-Cost Mobile Manipulator (an omnidirectional base with an
SO-101 arm) under ROS 2 Jazzy.

## Packages

| Package | What it is |
|---|---|
| `waveshare_servos` | ros2_control hardware interface for the Feetech/Waveshare servo bus |
| `lekiwi_description` | the base: URDF macro, ros2_control joints, base controllers |
| `so101_description` | the arm: URDF macro, ros2_control joints, arm and gripper controllers |
| `lekiwi_bringup` | the combined robot, and the launch files for the robot and the workstation |
| `so101_moveit_config` | MoveIt for the arm on its own (planning groups, IK, controllers) |
| `lekiwi_moveit_config` | MoveIt for the arm on the LeKiwi, with collisions against the base and the ground |
| `lekiwi_teleop` | the RViz marker follower (`arm_marker`) and the joystick teleop (`joy_teleop`) |

Each package has a README with the details.

## Robot / workstation split

The robot runs everything that controls the hardware and does all the computation: the servo
driver and controllers, `move_group`, the marker follower and the joystick teleop. The workstation
runs RViz and, usually, the joystick driver. Both must be on the same network, with the same
`ROS_DOMAIN_ID`, and must not share that domain ID with any other ROS system on the network.

```
robot (robot.launch.py)                                     workstation (workstation.launch.py)
  waveshare_servos + controllers  <-- arm / base commands     RViz: MotionPlanning, arm marker
  move_group (planning, IK, collisions)                       joy_node  --- /joy --->  joy_teleop
  arm_marker (marker and joystick arm control)
  joy_teleop (joystick -> base and arm)
```

## Setup

Copy the workspace to the robot (without the build output):

```bash
rsync -a --exclude build --exclude install --exclude log lekiwi_ros2_ws/ <robot>:<path>/lekiwi_ros2_ws/
```

### Robot

```bash
docker run -it --rm --network=host --ipc=host -e ROS_DOMAIN_ID=42 \
  --device=/dev/ttyACM0 -v $PWD/lekiwi_ros2_ws:/lekiwi_ros2_ws:rw osrf/ros:jazzy-desktop-full

# inside the container
cd /lekiwi_ros2_ws && source /opt/ros/jazzy/setup.bash
apt update && rosdep update && rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch lekiwi_bringup robot.launch.py
```

Before launching: keep the arm clear or supported (the servos switch on their torque at start),
and stop anything else that uses `/dev/ttyACM0`. The log should show
`You can start planning now!` (move_group) and `marker ready` (arm_marker).

### Workstation

```bash
docker run -it --rm --network=host --ipc=host --device=/dev/dri --group-add video --device=/dev/input \
  -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
  -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY \
  -e ROS_DOMAIN_ID=42 \
  -v $PWD/lekiwi_ros2_ws:/lekiwi_ros2_ws:rw osrf/ros:jazzy-desktop-full

# inside the container
cd /lekiwi_ros2_ws && source /opt/ros/jazzy/setup.bash
apt update && rosdep update
rosdep install --from-paths src/lekiwi_description src/so101_description src/lekiwi_bringup \
  src/so101_moveit_config src/lekiwi_moveit_config --ignore-src -r -y
colcon build --symlink-install --packages-select lekiwi_description so101_description \
  lekiwi_bringup so101_moveit_config lekiwi_moveit_config
source install/setup.bash
ros2 launch lekiwi_bringup workstation.launch.py
```

The workstation needs the description and MoveIt packages (RViz loads the robot model, the
meshes and the IK plugin), but not `waveshare_servos` or `lekiwi_teleop`.

With `--rm`, every new container repeats the `apt`/`rosdep` step. To skip it, keep a named
container (`--name lekiwi` instead of `--rm`, then `docker start -ai lekiwi`).

## Launch options

`robot.launch.py`:

| Argument | Default | |
|---|---|---|
| `port` | `/dev/ttyACM0` | servo bus |
| `use_mock_hardware` | `false` | simulated servos, for testing without the robot |
| `limp` | `false` | torque never switched on; joint states only, nothing moves (see `lekiwi_bringup/README.md`) |
| `moveit` | `true` | start `move_group` |
| `arm_marker` | `true` | start the marker follower (needs `moveit`) |
| `marker_mode` | `free` | initial marker mode: `free`, `claw` or `planar` |
| `marker_speed` | `0.08` | the follower's maximum gripper speed, m/s |
| `joy_teleop` | `true` | start the joystick teleop |
| `joy` | `false` | start `joy_node` here, for a joystick plugged into the robot |
| `joy_device`, `joy_deadzone` | `0`, `0.166` | `joy_node` settings |

`workstation.launch.py`:

| Argument | Default | |
|---|---|---|
| `rviz` | `true` | RViz with the MotionPlanning panel and the arm marker |
| `joy` | `true` | start `joy_node` here, for a joystick plugged into the workstation |
| `joy_device`, `joy_deadzone` | `0`, `0.166` | `joy_node` settings |

For a joystick plugged into the robot: `robot.launch.py joy:=true` and
`workstation.launch.py joy:=false`.

## Joystick

| Input | Does |
|---|---|
| axis 1 / axis 0 | base forward/back, left/right (0.25 m/s) |
| axis 3 | base turn (1.0 rad/s) |
| axis 7 | arm up (+1) / down (-1) (0.04 m/s) |
| axis 6 | arm forward (-1) / back (+1) |
| button 0 / button 2 | gripper tip turns toward / away from the robot |
| button 4 / button 5 | base circles left / right around the gripper's goal, facing it |
| button 6 / button 7 | gripper open / close |

The joystick controls the arm in planar mode: `shoulder_pan` held at 0 and `wrist_roll` at
-90 deg, so the gripper moves in the vertical plane in front of the robot; sideways motion is the
base's job. The first arm input switches to planar mode with a planned move. Arm directions are
the robot's, not the gripper's. The arm's motion is collision-checked against the base and the
ground, and stops at the edge of its reach. Axis and button numbers, speeds and the gripper
positions are parameters of `joy_teleop` (`lekiwi_teleop/README.md`).

## RViz

- **Arm marker** (blue sphere at the fingertips): drag it and the arm follows. Right-click for
  "Reset to gripper" and "Mode": `free` (position, and orientation where reachable), `claw`
  (gripper pointing straight down, x/y/z and yaw) and `planar` (as the joystick). The joystick
  moves the same marker.
- **MotionPlanning panel**: plan and execute moves (groups `arm`, `arm_position_only`,
  `gripper`; named poses `zero`, `open`, `closed`). Do not drag the arm marker or use the
  joystick arm controls while a planned move executes: the follower replaces it.

## Troubleshooting

| Symptom | Check |
|---|---|
| The workstation sees no robot nodes | same `ROS_DOMAIN_ID`, `--network=host` on both, firewall allows UDP multicast; `ros2 node list` |
| Two copies of a node | another ROS system on the same domain: use a different `ROS_DOMAIN_ID`; `ros2 node list` |
| No robot model in RViz | the workstation's workspace is out of date: rebuild it from the same `src/` as the robot |
| Joystick does nothing | `ros2 topic echo /joy --once` on the workstation; inside the container `ls /dev/input/js*` |
| The arm does not follow the marker or joystick | the robot's log: `arm_marker` says why it stopped (out of reach, blocked, mode switch) |
| A servo does not answer | stop the launch, then `ros2 run waveshare_servos scan --ros-args -p port:=/dev/ttyACM0` |
