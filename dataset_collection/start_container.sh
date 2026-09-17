#!/bin/bash
if [ -z "$SUDO_USER" ]
then
      user=$USER
else
      user=$SUDO_USER
fi

xhost +local:root

mkdir -p ./shared
mkdir -p ./docker/isaac-sim/cache/main \
         ./docker/isaac-sim/cache/computecache \
         ./docker/isaac-sim/logs \
         ./docker/isaac-sim/config \
         ./docker/isaac-sim/data \
         ./docker/isaac-sim/pkg

chmod -R a+rwX ./shared
chmod -R a+rwX ./docker

XAUTH=/tmp/.docker.xauth
if [ ! -f $XAUTH ]
then
    xauth_list=$(xauth nlist :0 | sed -e 's/^..../ffff/')
    if [ ! -z "$xauth_list" ]
    then
        echo $xauth_list | xauth -f $XAUTH nmerge -
    else
        touch $XAUTH
    fi
    chmod a+r $XAUTH
fi

docker run -it --rm \
    --name=fossbot-od-dataset-collection \
    --entrypoint /bin/bash \
    --shm-size=32g \
    --ulimit memlock=-1 \
    --env="DISPLAY=$DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    --env="ACCEPT_EULA=Y" \
    --env="NVIDIA_NGX_DISABLE=0" \
    --env="NVIDIA_NGX_ENABLE=1" \
    --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
    --volume ./docker/isaac-sim/cache/main:/isaac-sim/.cache:rw \
    --volume ./docker/isaac-sim/cache/computecache:/isaac-sim/.nv/ComputeCache:rw \
    --volume ./docker/isaac-sim/logs:/isaac-sim/.nvidia-omniverse/logs:rw \
    --volume ./docker/isaac-sim/config:/isaac-sim/.nvidia-omniverse/config:rw \
    --volume ./docker/isaac-sim/data:/isaac-sim/.local/share/ov/data:rw \
    --volume ./docker/isaac-sim/pkg:/isaac-sim/.local/share/ov/pkg:rw \
    --volume ../shared:/isaac-sim/shared:rw \
    --gpus 'all,"capabilities=compute,utility,graphics"' \
    --env="XAUTHORITY=$XAUTH" \
    --volume="$XAUTH:$XAUTH" \
    --env="NVIDIA_VISIBLE_DEVICES=all" \
    --env="NVIDIA_DRIVER_CAPABILITIES=all" \
    --network=host \
    --pid=host \
    --ipc=host \
    --privileged \
    fossbot-od-dataset-collection