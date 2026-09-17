import argparse
import asyncio
import os

def main():
    parser = argparse.ArgumentParser(description="Convert downloaded YCB OBJ meshes to USD for Isaac Sim")
    parser.add_argument("--input_dir", type=str, required=True, help="Directory containing YCB meshes downloaded via download_ycb.py.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the converted USD files.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    from isaacsim import SimulationApp
    simulation_app = SimulationApp({"headless": True})

    import omni.kit.asset_converter as converter

    async def convert(in_path, out_path):
        task_manager = converter.get_instance()
        task = task_manager.create_converter_task(in_path, out_path)
        success = await task.wait_until_finished()
        if not success:
            print(f"[WARN] Failed to convert {in_path}: {task.get_status()} {task.get_detailed_error()}")
        return success

    obj_names = sorted(
        name for name in os.listdir(args.input_dir)
        if os.path.isdir(os.path.join(args.input_dir, name))
    )

    for obj_name in obj_names:
        in_path = os.path.join(args.input_dir, obj_name, "google_16k", "textured.obj")
        out_path = os.path.join(args.output_dir, f"{obj_name}.usd")

        if not os.path.exists(in_path):
            print(f"Skipping {obj_name}, mesh not found at {in_path}")
            continue

        if os.path.exists(out_path):
            print(f"Skipping {obj_name}, already converted.")
            continue

        print(f"Converting {obj_name}...")
        asyncio.get_event_loop().run_until_complete(convert(in_path, out_path))

    print(f"Done. Converted USD files saved to {args.output_dir}")
    simulation_app.close()

if __name__ == "__main__":
    main()
