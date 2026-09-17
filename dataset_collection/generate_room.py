import argparse
import json
import os

def main():
    parser = argparse.ArgumentParser(description="Generate Custom Room USD for Isaac Sim")
    parser.add_argument("--config", type=str, required=True, help="Path to room.json")
    parser.add_argument("--output", type=str, required=True, help="Path to save custom_room.usd")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        room_config = json.load(f)

    from isaacsim import SimulationApp
    simulation_app = SimulationApp({"headless": True})

    from pxr import Usd, UsdGeom, UsdLux, UsdShade, Sdf, Gf

    if os.path.exists(args.output) and os.path.isfile(args.output):
        os.remove(args.output)

    output_dir = os.path.dirname(args.output)
    os.makedirs(output_dir, exist_ok=True)

    if not os.access(output_dir, os.W_OK):
        raise PermissionError(f"Output directory is not writable: {output_dir}")

    stage = Usd.Stage.CreateNew(args.output)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    root_path = "/CustomRoom"
    root_xform = UsdGeom.Xform.Define(stage, root_path)
    stage.SetDefaultPrim(root_xform.GetPrim())

    w = room_config["width_m"]
    d = room_config["depth_m"]
    h = room_config["height_m"]
    wt = room_config["wall_thickness_m"]
    ft = room_config["floor_thickness_m"]
    ct = room_config["ceiling_thickness_m"]

    def make_preview_material(material_path, color_rgb, roughness, specular):
        material = UsdShade.Material.Define(stage, material_path)
        shader = UsdShade.Shader.Define(stage, f"{material_path}/Shader")

        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color_rgb))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
        shader.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(float(specular))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

        shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput().ConnectToSource(shader.GetOutput("surface"))
        return material

    def bind_material(prim, material):
        UsdShade.MaterialBindingAPI.Apply(prim)
        UsdShade.MaterialBindingAPI(prim).Bind(material)

    def add_box(name, scale, pos, color):
        prim_path = f"{root_path}/{name}"
        box = UsdGeom.Cube.Define(stage, prim_path)
        box.GetSizeAttr().Set(1.0)
        UsdGeom.XformCommonAPI(box).SetTranslate(Gf.Vec3d(*pos))
        UsdGeom.XformCommonAPI(box).SetScale(Gf.Vec3f(*scale))
        box.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])
        return box.GetPrim()

    wall_material = make_preview_material(
        f"{root_path}/Materials/WallMatte",
        room_config.get("wall_color", [0.75, 0.75, 0.72]),
        roughness=0.95,
        specular=0.02,
    )

    floor_prim = add_box("Floor", (w, d, ft), (0, 0, -ft / 2.0), room_config["floor_color"])
    ceiling_prim = add_box("Ceiling", (w, d, ct), (0, 0, h + ct / 2.0), room_config["ceiling_color"])
    wall_back_prim = add_box("Wall_Back", (w, wt, h), (0, d / 2.0 + wt / 2.0, h / 2.0), room_config["wall_color"])
    wall_front_prim = add_box("Wall_Front", (w, wt, h), (0, -(d / 2.0 + wt / 2.0), h / 2.0), room_config["wall_color"])
    wall_left_prim = add_box("Wall_Left", (wt, d + 2 * wt, h), (-(w / 2.0 + wt / 2.0), 0, h / 2.0), room_config["wall_color"])
    wall_right_prim = add_box("Wall_Right", (wt, d + 2 * wt, h), (w / 2.0 + wt / 2.0, 0, h / 2.0), room_config["wall_color"])

    bind_material(wall_back_prim, wall_material)
    bind_material(wall_front_prim, wall_material)
    bind_material(wall_left_prim, wall_material)
    bind_material(wall_right_prim, wall_material)

    avg_intensity = (room_config["light_intensity_min"] + room_config["light_intensity_max"]) / 2.0
    avg_temperature = (room_config["light_temperature_min"] + room_config["light_temperature_max"]) / 2.0

    UsdGeom.Xform.Define(stage, f"{root_path}/Lights")

    for i, pos in enumerate(room_config["light_positions"]):
        light_path = f"{root_path}/Lights/Light_{i}"
        sphere_light = UsdLux.SphereLight.Define(stage, light_path)
        UsdGeom.XformCommonAPI(sphere_light).SetTranslate(Gf.Vec3d(*pos))
        sphere_light.GetIntensityAttr().Set(float(avg_intensity))
        sphere_light.GetEnableColorTemperatureAttr().Set(True)
        sphere_light.GetColorTemperatureAttr().Set(float(avg_temperature))
        sphere_light.GetExposureAttr().Set(2.5)
        sphere_light.GetRadiusAttr().Set(0.1)

    stage.GetRootLayer().Save()
    print(f"Successfully generated custom room USD at: {args.output}")

    simulation_app.close()

if __name__ == "__main__":
    main()