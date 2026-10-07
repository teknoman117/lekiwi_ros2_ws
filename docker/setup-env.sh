#!/bin/bash
# Write docker/.env for this machine: the user and group ids the containers need, the devices,
# and (workstation) the robot's address. Values already in docker/.env are kept, except the ones
# detected from this machine. Rerun after plugging in different hardware, or after logging in
# again (the X authority file can move).
#
#   docker/setup-env.sh robot
#   ROBOT_IP=10.10.0.212 docker/setup-env.sh workstation
set -euo pipefail

role=${1:-}
if [[ $role != robot && $role != workstation ]]; then
    echo "usage: $0 robot|workstation" >&2
    exit 2
fi
cd "$(dirname "$0")"
env_file=.env

declare -A value
order=()
set_value() {   # set_value NAME VALUE: always
    [[ -v value[$1] ]] || order+=("$1")
    value[$1]=$2
}
set_default() { # set_default NAME VALUE: unless already set (in .env or the environment)
    if [[ -n ${!1:-} ]]; then
        set_value "$1" "${!1}"
    elif [[ ! -v value[$1] || -z ${value[$1]} ]]; then
        set_value "$1" "$2"
    fi
}
gid_of() { # the group of the first existing path, else the named group's id, else empty
    local path
    for path in "${@:2}"; do
        [[ -e $path ]] && { stat -c %g "$path"; return; }
    done
    getent group "$1" | cut -d: -f3 || true
}

# keep what is already in .env
if [[ -f $env_file ]]; then
    while IFS='=' read -r key val; do
        [[ $key =~ ^[A-Z_][A-Z0-9_]*$ ]] && set_value "$key" "${val%%#*}"
    done < "$env_file"
    for key in "${!value[@]}"; do value[$key]=$(echo "${value[$key]}" | xargs); done
fi

set_value HOST_UID "$(id -u)"
set_value HOST_GID "$(id -g)"
set_default ROS_DOMAIN_ID 0
set_default DISCOVERY_PORT 11811
input_gid=$(gid_of input /dev/input/js0 /dev/input/js1)
set_value INPUT_GID "${input_gid:-$(id -g)}"
set_default JOY_DEVICE 0
set_default JOY_DEADZONE 0.166

if [[ $role == robot ]]; then
    serial=${SERIAL_DEVICE:-${value[SERIAL_DEVICE]:-}}
    if [[ -z $serial ]]; then
        serial=$(ls /dev/serial/by-id/* 2>/dev/null | head -n 1 || true)
        serial=${serial:-/dev/ttyACM0}
    fi
    set_value SERIAL_DEVICE "$serial"
    serial_gid=$(gid_of dialout "$serial")
    set_value SERIAL_GID "${serial_gid:-20}"
    set_default USE_MOCK_HARDWARE false
    set_default LIMP false
    set_default MARKER_MODE free
    set_default MARKER_SPEED 0.08
    set_default ROBOT_JOY false
    [[ -e $serial ]] || echo "warning: $serial does not exist (set SERIAL_DEVICE)" >&2
else
    set_default ROBOT_IP ""
    set_default WORKSTATION_RVIZ true
    set_default WORKSTATION_JOY true
    video_gid=$(gid_of video /dev/dri/card0 /dev/dri/card1)
    render_gid=$(gid_of render /dev/dri/renderD128)
    set_value VIDEO_GID "${video_gid:-$(id -g)}"
    set_value RENDER_GID "${render_gid:-$(id -g)}"
    xauth=${XAUTHORITY:-$HOME/.Xauthority}
    [[ -f $xauth ]] && set_value XAUTHORITY_FILE "$xauth" || set_value XAUTHORITY_FILE ""
    [[ -n ${value[ROBOT_IP]} ]] || echo "note: ROBOT_IP is not set; set it in $PWD/$env_file or the environment" >&2
fi

{
    echo "# written by setup-env.sh ($role) on $(hostname); see .env.example"
    for key in "${order[@]}"; do echo "$key=${value[$key]}"; done
} > "$env_file"
echo "wrote $PWD/$env_file:"
grep -v '^#' "$env_file"
