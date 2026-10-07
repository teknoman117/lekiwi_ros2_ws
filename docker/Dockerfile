# syntax=docker/dockerfile:1
#
# LeKiwi images, built on the machine that runs them (amd64 or arm64; ros:jazzy-ros-base is
# published for both). Build context: the workspace root (lekiwi_ros2_ws), with the submodules
# checked out. Targets:
#
#   robot        everything that runs on the robot: the servo driver and controllers, MoveIt,
#                the teleop nodes, and the Fast DDS discovery server. No GUI.
#   workstation  RViz (MoveIt panel, arm marker) and the joystick driver.
#
# The compose files in this directory build and run them.

ARG ROS_DISTRO=jazzy

# --- common base: a user matching the host, the entrypoint --------------------------------------
FROM ros:${ROS_DISTRO}-ros-base AS base
ARG HOST_UID=1000
ARG HOST_GID=1000
ENV DEBIAN_FRONTEND=noninteractive \
    WORKSPACE=/opt/lekiwi_ws
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# The image's 'ubuntu' user (uid 1000) is replaced by 'lekiwi' with the host's uid and gid, so
# files and sockets shared with the host (X11, devices) have matching owners.
RUN if id -u ubuntu >/dev/null 2>&1; then userdel -r ubuntu; fi \
    && if ! getent group "${HOST_GID}" >/dev/null; then groupadd -g "${HOST_GID}" lekiwi; fi \
    && useradd -m -s /bin/bash -u "${HOST_UID}" -g "${HOST_GID}" -G dialout,video lekiwi

RUN apt-get update && rosdep update --rosdistro "${ROS_DISTRO}" && rm -rf /var/lib/apt/lists/*

COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]

# --- package manifests only, so dependency layers survive source changes -----------------------
FROM base AS manifests
COPY src /tmp/src
RUN mkdir -p /tmp/manifests \
    && cd /tmp/src \
    && find . -name package.xml -not -path '*/test/*' -exec cp --parents {} /tmp/manifests \;

# --- robot ---------------------------------------------------------------------------------------
FROM base AS robot-deps
COPY --from=manifests /tmp/manifests ${WORKSPACE}/src
# All packages, without the GUI-only dependencies and without test dependencies. No '-r': a
# dependency that cannot be resolved fails the build.
RUN apt-get update \
    && rosdep install -y --from-paths ${WORKSPACE}/src --ignore-src --rosdistro "${ROS_DISTRO}" \
        --dependency-types build --dependency-types buildtool --dependency-types build_export \
        --dependency-types buildtool_export --dependency-types exec \
        --skip-keys "rviz2 moveit_ros_visualization joint_state_publisher_gui" \
    && rm -rf /var/lib/apt/lists/*

FROM robot-deps AS robot
COPY src ${WORKSPACE}/src
RUN cd ${WORKSPACE} \
    && source /opt/ros/${ROS_DISTRO}/setup.bash \
    && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    && rm -rf build log
USER lekiwi
WORKDIR /home/lekiwi

# --- workstation ---------------------------------------------------------------------------------
FROM base AS workstation-deps
COPY --from=manifests /tmp/manifests ${WORKSPACE}/src
# Only what RViz needs: the robot model, the meshes, the MoveIt configs (RViz's MotionPlanning
# panel loads the SRDF and the IK plugin) and the launch file. Not the servo driver or teleop
# (ignored by colcon too: the descriptions name waveshare_servos as a run dependency).
RUN apt-get update \
    && rosdep install -y --rosdistro "${ROS_DISTRO}" --ignore-src \
        --from-paths ${WORKSPACE}/src/lekiwi_description ${WORKSPACE}/src/so101_description \
                     ${WORKSPACE}/src/lekiwi_bringup ${WORKSPACE}/src/so101_moveit_config \
                     ${WORKSPACE}/src/lekiwi_moveit_config \
        --dependency-types build --dependency-types buildtool --dependency-types build_export \
        --dependency-types buildtool_export --dependency-types exec \
        --skip-keys "waveshare_servos" \
    && rm -rf /var/lib/apt/lists/*

FROM workstation-deps AS workstation
COPY src ${WORKSPACE}/src
RUN cd ${WORKSPACE} \
    && source /opt/ros/${ROS_DISTRO}/setup.bash \
    && colcon build --cmake-args -DBUILD_TESTING=OFF \
        --packages-ignore waveshare_servos lekiwi_teleop \
    && rm -rf build log
USER lekiwi
WORKDIR /home/lekiwi
