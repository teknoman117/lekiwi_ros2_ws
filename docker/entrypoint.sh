#!/bin/bash
# Source ROS and the workspace, then run the command.
set -e
source "/opt/ros/${ROS_DISTRO}/setup.bash"
if [ -f "${WORKSPACE}/install/setup.bash" ]; then
    source "${WORKSPACE}/install/setup.bash"
fi
exec "$@"
