# Dataset Collection Scripts for Object Detection with NVIDIA Isaac Sim

This directory contains scripts for generating synthetic datasets for object detection tasks using NVIDIA Isaac Sim.

Scenes are generated using a custom room only, with obstacle clutter sampled from the [YCB Object and Model Set](https://www.ycbbenchmarks.com/) (Calli et al.), downloaded directly from the official YCB benchmarks host and licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

- [Dataset Collection Scripts for Object Detection with NVIDIA Isaac Sim](#dataset-collection-scripts-for-object-detection-with-nvidia-isaac-sim)
  - [Docker](#docker)
    - [Build the Docker image](#build-the-docker-image)
    - [Run the container](#run-the-container)
  - [Getting the YCB obstacle assets](#getting-the-ycb-obstacle-assets)
  - [Collecting Data](#collecting-data)
  - [Data visualization](#data-visualization)
  - [Run automatic dataset collection](#run-automatic-dataset-collection)
  - [Convert the dataset to YOLO format](#convert-the-dataset-to-yolo-format)

>[!NOTE]
> The scripts are using NVIDIA Isaac Sim, which requires an NVIDIA GPU. It was tested on a workstation with an NVIDIA RTX 4070 GPU (12GM VRAM), but it should work on other NVIDIA GPUs with at least 8GB of VRAM.

## Docker

To run the dataset collection script, you can use the provided Dockerfile to build a container with all necessary dependencies.

### Build the Docker image

```bash
bash build_image.sh
```

### Run the container

```bash
bash start_container.sh
```

## Getting the YCB obstacle assets

Obstacle clutter is sampled from the YCB Object and Model Set. Download the meshes from the official host and convert them to USD once, before running `collect_data.py`:

```bash
bash python.sh download_ycb.py --output_dir /path/to/data/ycb
bash python.sh convert_ycb_to_usd.py --input_dir /path/to/data/ycb --output_dir /path/to/data/usd/ycb
```

Example:

```bash
bash python.sh download_ycb.py --output_dir /isaac-sim/shared/data/ycb
bash python.sh convert_ycb_to_usd.py --input_dir /isaac-sim/shared/data/ycb --output_dir /isaac-sim/shared/data/usd/ycb
```

>[!NOTE]
> Both scripts skip objects that were already downloaded/converted, so re-running them is safe and cheap.

## Collecting Data

Once you are inside the container, you can run the dataset collection script as follows:

```bash
bash python.sh collect_data.py --data_dir /path/to/data/ --output_dir /path/to/output/ --num_images {number_of_images} --objects_num {number_of_each_target_object} --obstacles_num {number_of_obstacles} --seed {random_seed}
```

Example:

```bash
bash python.sh collect_data.py --data_dir /isaac-sim/shared/data/ --output_dir /isaac-sim/shared/annotated_data/
```

>[!NOTE]
> You can get all available flags by running the script with the `--help` flag:
>```bash
>bash python.sh collect_data.py --help
>```

## Data visualization

You can visualize the generated dataset using the `visualize_dataset.py` script:

```bash
bash python.sh visualize_data.py --data_dir /path/to/annotated_data/ --save_path /path/to/save/visualizations/ --annotations_json /path/to/annotations.json --image_id {image_id_to_visualize}
```

Example:
```bash
bash python.sh visualize_data.py --data_dir shared/annotated_data/custom_room --save_path shared/annotated_data/custom_room/annotated --annotations_json shared/data/annotations.json --image_id 1
```

## Run automatic dataset collection

You can use the `collect_data.sh` script to automate the dataset collection process for multiple object/obstacle count configurations. 

```bash
bash collect_data.sh
```

## Convert the dataset to YOLO format

You can convert the generated dataset to YOLO format using the `convert_to_yolo.py` script:

```bash
bash python.sh convert_to_yolo.py \
    --data_dir <data_directory> \
    --output_dir <output_directory> \
    --annotations_json <path_to_annotations_json>
```

Example:

``` bash
bash python.sh convert_to_yolo.py \
    --data_dir /isaac-sim/shared/annotated_data \
    --output_dir /isaac-sim/shared/yolo_dataset \
    --annotations_json /isaac-sim/shared/data/annotations.json
```