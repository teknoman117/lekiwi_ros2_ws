cmake_minimum_required(VERSION 3.8)
project(manipulator)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  launch
  meshes
  urdf
  DESTINATION share/${PROJECT_NAME}
)

# MoveIt's config builder reads the model and SRDF names from it (else it warns)
install(FILES .setup_assistant DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/arducam_tof_node.py DESTINATION lib/${PROJECT_NAME})

ament_package()
