import argparse
import glob
import json
import os
import random
import math
import traceback
import numpy as np
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Isaac Sim Obstacle Detection Data Generation")
    parser.add_argument("--data_dir", "-d", type=str, required=True, help="Path to directory containing config file and the data.")
    parser.add_argument("--output_dir", "-o", type=str, required=True, help="Directory to save the generated dataset.")
    parser.add_argument("--num_images", "-n", type=int, default=100, help="Number of images to generate.")
    parser.add_argument("--objects_num", "-t", type=int, default=3, help="Number of EACH target object per scene.")
    parser.add_argument("--obstacles_num", "-b", type=int, default=1, help="Number of EACH obstacle per scene.")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed for reproducibility.")

    parser.add_argument("--target_min_dist", "-tm", type=float, default=0.5, help="Minimum distance targets can spawn from camera.")
    parser.add_argument("--target_max_dist", "-tM", type=float, default=4.0, help="Maximum distance targets can spawn from camera.")
    parser.add_argument("--obstacle_min_dist", "-ob", type=float, default=0.7, help="Minimum distance obstacles can spawn from camera.")
    parser.add_argument("--obstacle_max_dist", "-oM", type=float, default=7.5, help="Maximum distance obstacles can spawn from camera.")

    parser.add_argument("--ray_tracing_samples", "-rt", type=int, default=16, help="Number of ray tracing samples to use for rendering (higher = better quality but slower).")

    parser.add_argument("--headless", action="store_true", help="Run Isaac Sim in headless mode (no GUI).")
    
    args = parser.parse_args()

    if args.objects_num < 1:
        raise ValueError("--objects_num must be at least 1.")
    if args.obstacles_num < 0:
        raise ValueError("--obstacles_num must be at least 0.")

    return args

def main():
    args = parse_args()

    from isaacsim import SimulationApp
    simulation_app = SimulationApp({"headless": args.headless})

    try:
        import omni.usd
        from pxr import UsdGeom, Gf, Usd, UsdLux, UsdShade
        import omni.replicator.core as rep
        
        from isaacsim.core.utils.stage import open_stage
        from isaacsim.core.utils.prims import define_prim
        from isaacsim.core.utils.semantics import add_labels
        from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
        from isaacsim.core.prims import SingleXFormPrim as XFormPrim

        random.seed(args.seed)
        np.random.seed(args.seed)

        # Load configs
        with open(os.path.join(args.data_dir, "annotations.json"), "r") as f:
            target_config = json.load(f)

        with open(os.path.join(args.data_dir, "colors.json"), "r") as f:
            color_definitions = json.load(f)

        with open(os.path.join(args.data_dir, "room.json"), "r") as f:
            room_config = json.load(f)

        # Obstacles (YCB Object and Model Set, Yale-CMU-Berkeley, CC BY 4.0)
        # Run download_ycb.py and convert_ycb_to_usd.py first to populate this directory.
        ycb_usd_dir = os.path.join(args.data_dir, "usd", "ycb")
        obstacle_usd_paths = sorted(glob.glob(os.path.join(ycb_usd_dir, "*.usd")))
        if not obstacle_usd_paths:
            raise FileNotFoundError(
                f"No YCB USD files found in {ycb_usd_dir}. Run download_ycb.py and convert_ycb_to_usd.py first!"
            )

        # Background
        custom_room_usd = os.path.join(args.data_dir, "usd", "room.usd")
        if not os.path.exists(custom_room_usd):
            raise FileNotFoundError(f"Generated USD not found at {custom_room_usd}. Run the generator script first!")

        # Open Stage and Setup Scene
        open_stage(custom_room_usd)
        stage = omni.usd.get_context().get_stage()

        for prim in stage.Traverse():
            path = str(prim.GetPath())
            if "Floor" in path:
                add_labels(prim, labels=["floor"])
            elif "Ceiling" in path:
                add_labels(prim, labels=["ceiling"])
            elif "Wall" in path:
                add_labels(prim, labels=["wall"])

        # Setup camera and render product
        camera_path = "/World/Camera"
        define_prim(camera_path, "Camera")
        camera_xform = XFormPrim(camera_path)
        
        camera_geom = UsdGeom.Camera(stage.GetPrimAtPath(camera_path))
        camera_geom.GetFocalLengthAttr().Set(3.04)
        camera_geom.GetHorizontalApertureAttr().Set(3.68)
        camera_geom.GetClippingRangeAttr().Set(Gf.Vec2f(0.01, 1000.0))

        render_product = rep.create.render_product(camera_path, (1280, 720))

        # Spawn assets
        define_prim("/World/Targets", "Xform")
        define_prim("/World/Obstacles", "Xform")

        spawned_targets = []
        for class_name, item_data in target_config.items():
            absolute_usd_path = os.path.abspath(os.path.join(args.data_dir, item_data["usd_path"]))
            local_usd_uri = Path(absolute_usd_path).as_uri()

            for i in range(args.objects_num):
                prim_path = f"/World/Targets/{class_name}_{i}"
                target_prim = stage.DefinePrim(prim_path, "Xform")
                target_prim.GetReferences().AddReference(local_usd_uri)
                add_labels(target_prim, labels=[class_name])
                
                for child in Usd.PrimRange(target_prim):
                    if child.IsA(UsdGeom.Mesh):
                        UsdShade.MaterialBindingAPI(child).UnbindAllBindings()
                
                spawned_targets.append({
                    "xform": XFormPrim(prim_path),
                    "prim": target_prim,
                    "colors": item_data.get("colors", [])
                })

        spawned_obstacles = []
        if args.obstacles_num > 0:
            for obs_path in obstacle_usd_paths:
                for i in range(args.obstacles_num):
                    obs_name = os.path.splitext(os.path.basename(obs_path))[0]
                    if obs_name[0].isdigit():
                        obs_name = f"_{obs_name}"
                    prim_path = f"/World/Obstacles/{obs_name}_{i}"
                    obs_prim = stage.DefinePrim(prim_path, "Xform")
                    obs_prim.GetReferences().AddReference(Path(obs_path).as_uri())
                    spawned_obstacles.append(XFormPrim(prim_path))

        # Collect default light settings
        initial_lights = []
        for prim in stage.Traverse():
            intensity_attr = prim.GetAttribute("inputs:intensity") if prim.GetAttribute("inputs:intensity").IsValid() else prim.GetAttribute("intensity")
            temp_attr = prim.GetAttribute("inputs:colorTemperature") if prim.GetAttribute("inputs:colorTemperature").IsValid() else prim.GetAttribute("colorTemperature")
            
            # Check if it's a light by looking for an intensity attribute, and if valid, store it for later randomization
            if intensity_attr and intensity_attr.IsValid():
                val = intensity_attr.Get()
                if val is not None:
                    light_data = {"intensity_attr": intensity_attr, "initial_intensity": val}
                    
                    if temp_attr and temp_attr.IsValid():
                        t_val = temp_attr.Get()
                        if t_val is not None:
                            light_data["temp_attr"] = temp_attr
                            light_data["initial_temp"] = t_val
                            
                    initial_lights.append(light_data)

        # Warmup the renderer
        print("Warming up shaders and materials...")
        rep.orchestrator.step(rt_subframes=16)

        absolute_output_dir = os.path.abspath(os.path.join(args.output_dir, "custom_room"))
        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(
            output_dir=absolute_output_dir,
            rgb=True,
            bounding_box_2d_tight=True,
            semantic_types=["class"],
        )
        writer.attach([render_product])

        # Randomize & Capture Frames
        print(f"Starting standard generation for {args.num_images} images...")

        bound_x = max(3.5, (room_config["width_m"] / 2.0) - 0.5)
        bound_y = max(3.0, (room_config["depth_m"] / 2.0) - 0.5)
        z_offset = 0.0

        for frame in range(args.num_images):

            # Move Camera
            cx = random.uniform(-bound_x, bound_x)
            cy = random.uniform(-bound_y, bound_y)
            cz = random.uniform(0.08, 0.12) + z_offset

            camera_rot = np.array([math.pi / 2, 0.0, random.uniform(-math.pi, math.pi)])
            camera_xform.set_world_pose(
                position=np.array([cx, cy, cz]), 
                orientation=euler_angles_to_quats(camera_rot)
            )

            # Randomize lights relative to their original state
            for light_data in initial_lights:
                random_scale = random.uniform(0.9, 1.1)
                new_intensity = light_data["initial_intensity"] * random_scale
                light_data["intensity_attr"].Set(new_intensity)
                
                if "initial_temp" in light_data:
                    temp_scale = random.uniform(0.9, 1.1)
                    new_temp = light_data["initial_temp"] * temp_scale
                    light_data["temp_attr"].Set(new_temp)

            # Move Targets
            for target in spawned_targets:
                angle = random.uniform(0, 2 * math.pi)
                
                # Look for a valid coordinate that is inside the walls
                for _ in range(50):
                    r = random.uniform(args.target_min_dist, args.target_max_dist)
                    px = cx + r * math.cos(angle)
                    py = cy + r * math.sin(angle)
                    
                    if -bound_x <= px <= bound_x and -bound_y <= py <= bound_y: 
                        break
                    angle = random.uniform(0, 2 * math.pi)

                target["xform"].set_world_pose(
                    position=np.array([px, py, z_offset]),
                    orientation=euler_angles_to_quats(np.array([0.0, 0.0, random.uniform(-math.pi, math.pi)]))
                )

                if target["colors"]:
                    color_name = random.choice(target["colors"])
                    color = color_definitions[color_name]
                else:
                    color = [random.uniform(0.2, 1.0), random.uniform(0.2, 1.0), random.uniform(0.2, 1.0)]
                
                for child in Usd.PrimRange(target["prim"]):
                    if child.IsA(UsdGeom.Mesh):
                        UsdGeom.Mesh(child).GetDisplayColorAttr().Set([Gf.Vec3f(*color)])

            # Move Obstacles
            for obstacle in spawned_obstacles:
                angle = random.uniform(0, 2 * math.pi)
                r = random.uniform(args.obstacle_min_dist, args.obstacle_max_dist)
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle) 
                
                s = random.uniform(0.5, 1.25)
                obstacle.set_local_scale(np.array([s, s, s]))
                obstacle.set_world_pose(
                    position=np.array([px, py, z_offset]),
                    orientation=euler_angles_to_quats(np.array([0.0, 0.0, random.uniform(-math.pi, math.pi)]))
                )

            # Capture Frame
            rep.orchestrator.step(rt_subframes=16)
            print(f"Generated frame {frame + 1}/{args.num_images}")

        print(f"Data generation complete! Dataset cleanly saved to {absolute_output_dir}")

    except Exception as exc:
        print("\n[ERROR] Generation failed:")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise

    finally:
        simulation_app.close()

if __name__ == "__main__":
    main()