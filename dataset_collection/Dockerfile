# Use the Isaac Sim 5.1.0 image
FROM nvcr.io/nvidia/isaac-sim:5.1.0

WORKDIR /isaac-sim

# Set ROS environment variables
ENV ROS_DOMAIN_ID=11
ENV ROS_DISTRO=jazzy
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/isaac-sim/exts/isaacsim.ros2.bridge/jazzy/lib

COPY . /isaac-sim/