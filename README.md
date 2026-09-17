# Object detection with FOSSBot
Scripts for FOSSBot4AI - Lab 9 (Object detection)

This repository contains scripts for generating synthetic datasets for object detection tasks and a Jupyter notebook for training a YOLOv11n model.

The structure of the repository is as follows:
- [dataset_collection](dataset_collection) directory contains a Dockerfile and scripts for generating synthetic datasets for object detection tasks using NVIDIA Isaac Sim. For more information, see the README file in the `dataset_collection` directory;
-  [training](training) directory contains a Jupyter notebook for training a YOLOv11n model on the generated dataset. The notebook was created using Google Colab and it is recommended to run it in Google Colab (but it can also be run locally);
-  [shared](shared) directory contains blender files used for generating synthetic datasets. The objects were exported to both `.usd` and `.stl` formats. The `.usd` files are used for generating synthetic datasets, while the `.stl` files can be used for 3D printing the objects. If you print the 3D objects, you can adjust the `colors.json` file, so the dataset creation process spawns the objects in the desired color. This directory is also used for sharing data between the Docker container from `dataset_collection`.

Link to the dataset: <>