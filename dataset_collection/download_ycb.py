import argparse
import os
import tarfile
import urllib.request

BASE_URL = "http://ycb-benchmarks.s3-website-us-east-1.amazonaws.com/data/google/"

YCB_OBJECTS = [
    "002_master_chef_can",
    "003_cracker_box",
    "004_sugar_box",
    "005_tomato_soup_can",
    "006_mustard_bottle",
    "007_tuna_fish_can",
    "008_pudding_box",
    "009_gelatin_box",
    "010_potted_meat_can",
    "011_banana",
    "019_pitcher_base",
    "021_bleach_cleanser",
    "024_bowl",
    "025_mug",
    "035_power_drill",
    "036_wood_block",
    "037_scissors",
    "040_large_marker",
    "051_large_clamp",
    "052_extra_large_clamp",
    "061_foam_brick",
]

def parse_args():
    parser = argparse.ArgumentParser(description="Download the YCB Object and Model Set (CC BY 4.0) from ycbbenchmarks.com")
    parser.add_argument("--output_dir", "-o", type=str, required=True, help="Directory to save the downloaded YCB meshes.")
    return parser.parse_args()

def safe_extract(archive_path, output_dir):
    with tarfile.open(archive_path) as tar:
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(output_dir, member.name))
            if not member_path.startswith(os.path.abspath(output_dir) + os.sep):
                raise ValueError(f"Unsafe path in archive: {member.name}")
        tar.extractall(output_dir)

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    for obj_name in YCB_OBJECTS:
        mesh_path = os.path.join(args.output_dir, obj_name, "google_16k", "textured.obj")

        if os.path.exists(mesh_path):
            print(f"Skipping {obj_name}, already downloaded.")
            continue

        url = f"{BASE_URL}{obj_name}_google_16k.tgz"
        archive_path = os.path.join(args.output_dir, f"{obj_name}_google_16k.tgz")

        print(f"Downloading {obj_name} from {url}")
        urllib.request.urlretrieve(url, archive_path)

        safe_extract(archive_path, args.output_dir)
        os.remove(archive_path)

    print(f"Done. YCB meshes (CC BY 4.0, Calli et al.) saved to {args.output_dir}")

if __name__ == "__main__":
    main()
