#!/bin/bash
# Source ROS and the workspace, then run the command.
set -e
# compose.workstation.yaml: ROS_DISCOVERY_SERVER is ":port" when ROBOT_IP is not set
if [[ ${ROS_DISCOVERY_SERVER:-} == :* ]]; then
    echo "error: set ROBOT_IP to the robot's address, in the environment or docker/.env" >&2
    exit 1
fi
source "/opt/ros/${ROS_DISTRO}/setup.bash"
if [ -f "${WORKSPACE}/install/setup.bash" ]; then
    source "${WORKSPACE}/install/setup.bash"
fi
exec "$@"
