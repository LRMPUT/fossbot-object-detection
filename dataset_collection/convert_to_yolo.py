import os
import argparse
import json
import random
import shutil
import numpy as np
from pathlib import Path
from PIL import Image

def parse_args():
    parser = argparse.ArgumentParser(description="Convert Isaac Sim dataset to YOLO format.")
    parser.add_argument("--data_dir", type=str, required=True, help="Path to collected data (e.g., shared/annotated_data)")
    parser.add_argument("--output_dir", type=str, required=True, help="Path to save YOLO dataset")
    parser.add_argument("--annotations_json", type=str, required=True, help="Path to annotations.json")
    parser.add_argument("--split", type=float, nargs=3, default=[0.7, 0.15, 0.15], help="Train/val/test split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    return parser.parse_args()

def normalize_map(raw):
    """Normalize label mappings depending on their structure."""
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list):
        return {str(i): v for i, v in enumerate(raw)}
    raise TypeError(f"Unsupported format: {type(raw)}")

def convert_to_yolo(box, img_w, img_h):
    """Convert [x_min, y_min, x_max, y_max] to YOLO format: [x_center, y_center, width, height] normalized"""
    x_min, y_min, x_max, y_max = box
    
    # Calculate center, width, and height bounds
    cx = ((x_min + x_max) / 2.0) / img_w
    cy = ((y_min + y_max) / 2.0) / img_h
    width = (x_max - x_min) / img_w
    height = (y_max - y_min) / img_h
    
    # Safely clamp between [0, 1] in case of edge straddles
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    width = max(0.0, min(1.0, width))
    height = max(0.0, min(1.0, height))
    
    return [cx, cy, width, height]

def main():
    args = parse_args()
    random.seed(args.seed)
    
    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    
    with open(args.annotations_json, "r") as f:
        annotations = json.load(f)
    
    # Map class names to persistent integers for YOLO
    class_names = sorted(list(annotations.keys()))
    class_name_to_id = {name: idx for idx, name in enumerate(class_names)}
    print(f"Mapped classes: {class_name_to_id}")
    
    # Force initialize the YOLO directory structure
    splits = ["train", "val", "test"]
    for split in splits:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        
    # Seed the YOLO `data.yaml` descriptor
    yaml_content = f"train: images/train\nval: images/val\ntest: images/test\n\nnc: {len(class_names)}\nnames: {class_names}\n"
    with open(output_dir / "data.yaml", "w") as f:
        f.write(yaml_content)
        
    # Traverse directory searching for Isaac output frames
    run_dirs = set()
    for img_path in data_dir.rglob("rgb_*.png"):
        if img_path.parent.name != "annotated":
            run_dirs.add(img_path.parent)
        
    total_imgs = 0
    total_boxes = 0
    
    for run_dir in sorted(list(run_dirs)):
        rel_path = run_dir.relative_to(data_dir)
        print(f"Splitting 70/15/15: {rel_path}")
        
        # Setup prefixes corresponding to the original subfolder hierarchy
        prefix = str(rel_path).replace(os.sep, "_")
        img_paths = sorted(list(run_dir.glob("rgb_*.png")))
        random.shuffle(img_paths)
        
        n_imgs = len(img_paths)
        n_train = int(n_imgs * args.split[0])
        n_val = int(n_imgs * args.split[1])
        
        for idx, img_path in enumerate(img_paths):
            if idx < n_train:
                split = "train"
            elif idx < n_train + n_val:
                split = "val"
            else:
                split = "test"
                
            suffix = img_path.stem.replace("rgb_", "")
            
            boxes_path = run_dir / f"bounding_box_2d_tight_{suffix}.npy"
            labels_path = run_dir / f"bounding_box_2d_tight_labels_{suffix}.json"
            
            if not boxes_path.exists() or not labels_path.exists():
                print(f"Warning: Missing numpy boxes or json data for run id: {suffix}, Skipping.")
                continue
                
            with Image.open(img_path) as img:
                img_w, img_h = img.size
                
            # Safely extract labels and geometries
            boxes = np.load(boxes_path)
            with open(labels_path, "r") as f:
                labels_raw = json.load(f)
            labels_map = normalize_map(labels_raw)
            
            # Format all targets found
            yolo_labels = []
            if boxes.ndim == 0:
                boxes = boxes.reshape(1)
                
            for box in boxes:
                semantic_id = str(int(box["semanticId"]))
                label_info = labels_map.get(semantic_id)
                if not label_info:
                    continue
                    
                class_name = label_info.get("class") if isinstance(label_info, dict) else str(label_info)
                
                # Skip background artifacts
                if class_name in class_name_to_id:
                    class_id = class_name_to_id[class_name]
                    raw_box = [float(box["x_min"]), float(box["y_min"]), float(box["x_max"]), float(box["y_max"])]
                    yolo_box = convert_to_yolo(raw_box, img_w, img_h)
                    yolo_labels.append(f"{class_id} " + " ".join(f"{coord:.6f}" for coord in yolo_box))
                    total_boxes += 1
            
            # Create deduplicated file artifacts strings
            new_img_name = f"{prefix}_{img_path.name}"
            new_label_name = f"{prefix}_{img_path.stem}.txt"
            
            dest_img_path = output_dir / "images" / split / new_img_name
            dest_label_path = output_dir / "labels" / split / new_label_name
            
            # Flush
            shutil.copy2(img_path, dest_img_path)
            with open(dest_label_path, "w") as f:
                f.write("\n".join(yolo_labels) + "\n")
                
            total_imgs += 1
            
    print(f"\nDone! Extracted {total_imgs} annotated images with {total_boxes} total targets.")
    print(f"YOLO footprint established within: {output_dir}")

if __name__ == "__main__":
    main()