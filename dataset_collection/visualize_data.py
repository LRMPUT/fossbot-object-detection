import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def parse_args():
    parser = argparse.ArgumentParser(description="Visualize collected dataset images with target bounding boxes.")
    parser.add_argument("--data_dir", type=str, required=True)
    parser.add_argument("--image_id", type=int, required=True, help="ID of the image to visualize (e.g. 0 for rgb_0000.png). Use -1 to visualize all images in data_dir.")
    parser.add_argument(
        "--annotations_json",
        type=str,
        default=None,
        help="Path to annotations.json. If omitted, it is auto-found from data_dir.",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        default=None,
        help="Directory to save annotated images. Output will be annotated_XXXX.png.",
    )
    return parser.parse_args()

def resolve_save_path(save_dir, image_id):
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / f"annotated_{image_id:04d}.png"

def load_target_classes(annotations_json):
    with open(annotations_json, "r") as f:
        annotations = json.load(f)
    return set(annotations.keys())

def load_boxes(data_dir, image_id):
    suffix = f"{image_id:04d}"
    data_dir = Path(data_dir)

    image_path = data_dir / f"rgb_{suffix}.png"
    boxes_path = data_dir / f"bounding_box_2d_tight_{suffix}.npy"
    labels_path = data_dir / f"bounding_box_2d_tight_labels_{suffix}.json"
    prim_paths_path = data_dir / f"bounding_box_2d_tight_prim_paths_{suffix}.json"

    if not image_path.exists():
        raise FileNotFoundError(f"Missing image: {image_path}")
    if not boxes_path.exists():
        raise FileNotFoundError(f"Missing boxes: {boxes_path}")
    if not labels_path.exists():
        raise FileNotFoundError(f"Missing labels: {labels_path}")
    if not prim_paths_path.exists():
        raise FileNotFoundError(f"Missing prim paths: {prim_paths_path}")

    image = plt.imread(image_path)
    boxes = np.load(boxes_path)

    with open(labels_path, "r") as f:
        labels_raw = json.load(f)

    with open(prim_paths_path, "r") as f:
        prim_paths_raw = json.load(f)

    print(f"boxes.shape = {boxes.shape}")

    return image, boxes, labels_raw, prim_paths_raw, image_path

def normalize_map(raw):
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list):
        return {str(i): v for i, v in enumerate(raw)}
    raise TypeError(f"Unsupported format: {type(raw)}")

def extract_boxes(boxes, labels_map, prim_map, target_classes):
    selected = []

    if boxes.ndim == 0:
        boxes = boxes.reshape(1)

    for idx, box in enumerate(boxes):
        semantic_id = str(int(box["semanticId"]))
        label_info = labels_map.get(semantic_id)
        prim_path = prim_map.get(semantic_id, "")

        if label_info is None:
            continue

        class_name = label_info.get("class") if isinstance(label_info, dict) else str(label_info)

        if target_classes is not None and class_name not in target_classes:
            continue

        selected.append(
            {
                "class_name": class_name,
                "prim_path": prim_path,
                "box": (
                    float(box["x_min"]),
                    float(box["y_min"]),
                    float(box["x_max"]),
                    float(box["y_max"]),
                ),
            }
        )

    return selected

def draw(image, selected_boxes, title, save_path):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(image)
    ax.set_title(title)
    ax.axis("off")

    colors = {}
    palette = [
        "red",
        "lime",
        "cyan",
        "yellow",
        "orange",
        "magenta",
        "deepskyblue",
        "chartreuse",
    ]

    for item in selected_boxes:
        class_name = item["class_name"]
        x_min, y_min, x_max, y_max = item["box"]

        if class_name not in colors:
            colors[class_name] = palette[len(colors) % len(palette)]

        rect = patches.Rectangle(
            (x_min, y_min),
            x_max - x_min,
            y_max - y_min,
            linewidth=2,
            edgecolor=colors[class_name],
            facecolor="none",
        )
        ax.add_patch(rect)

        ax.text(
            x_min,
            max(0, y_min - 5),
            class_name,
            color="black",
            fontsize=10,
            bbox=dict(facecolor=colors[class_name], alpha=0.75, pad=2, edgecolor="none"),
        )

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved annotated image to {save_path}")

def find_image_ids(data_dir):
    ids = []
    for image_path in Path(data_dir).glob("rgb_*.png"):
        suffix = image_path.stem.replace("rgb_", "")
        if suffix.isdigit():
            ids.append(int(suffix))
    return sorted(ids)

def main():
    args = parse_args()

    data_dir = Path(args.data_dir).resolve()

    if args.annotations_json is None:
        annotations_json = data_dir.parents[1] / "data" / "annotations.json"
    else:
        annotations_json = Path(args.annotations_json)

    if not annotations_json.exists():
        raise FileNotFoundError(f"Missing annotations.json: {annotations_json}")

    target_classes = load_target_classes(annotations_json)
    print(f"Loaded target classes from annotations.json: {sorted(target_classes)}")

    if args.image_id == -1:
        image_ids = find_image_ids(data_dir)
    else:
        image_ids = [args.image_id]

    if args.save_path is None:
        save_dir = args.data_dir
    else:
        save_dir = args.save_path

    for image_id in image_ids:
        image, boxes, labels_raw, prim_paths_raw, image_path = load_boxes(args.data_dir, image_id)
        labels_map = normalize_map(labels_raw)
        prim_map = normalize_map(prim_paths_raw)
        selected_boxes = extract_boxes(boxes, labels_map, prim_map, target_classes)

        print(f"Loaded {len(boxes)} boxes for image {image_id}")
        print(f"Showing {len(selected_boxes)} target boxes for image {image_id}")

        save_path = resolve_save_path(save_dir, image_id)
        title = f"{image_path.name} | image_id={image_id}"
        draw(image, selected_boxes, title, save_path)

if __name__ == "__main__":
    main()