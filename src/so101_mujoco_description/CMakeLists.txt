cmake_minimum_required(VERSION 3.8)
project(so101_mujoco_description)

find_package(ament_cmake REQUIRED)

find_package(so101_description REQUIRED)

# In src/ the MJCF finds meshes via a relative meshdir. Under colcon's isolated
# install layout the packages are not siblings, so point meshdir at the real
# so101_description share dir in the installed copy instead.
get_filename_component(SO101_MESH_DIR "${so101_description_DIR}/../meshes" ABSOLUTE)
# re-run CMake whenever the MJCF changes, so the installed copy isn't stale
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS mjcf/so101.xml)
file(READ mjcf/so101.xml SO101_XML)
string(REPLACE "../../so101_description/meshes" "${SO101_MESH_DIR}" SO101_XML "${SO101_XML}")
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/mjcf/so101.xml "${SO101_XML}")

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/mjcf/so101.xml mjcf/scene.xml
  DESTINATION share/${PROJECT_NAME}/mjcf)
install(PROGRAMS scripts/urdf_to_mjcf.py DESTINATION lib/${PROJECT_NAME})

ament_package()
