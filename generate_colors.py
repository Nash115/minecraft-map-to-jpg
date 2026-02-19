import zipfile
import json
import io
import os
from dotenv import load_dotenv
from PIL import Image

from tools.log import info, error, fatal_error, success
from tools.utils import load_json

load_dotenv()

INPUT_FILE = os.getenv("MC_VERSION_FILE", None)
BLACKLIST_FILE = os.getenv("BLACKLIST_FILE", "data/blacklist.json")
COLOR_FILE = os.getenv("COLOR_FILE", "data/colors.json")

if not INPUT_FILE:
    fatal_error("MC_VERSION_FILE environment variable not set. Please specify the path to the Minecraft .jar file.")

TINTS = {
    "grass_block_top": (124, 189, 107),
    "grass_block_side_overlay": (124, 189, 107),
    "foliage": (71, 160, 50),
    "water_still": (63, 118, 228),
    "lava_still": (255, 100, 0),
    "spruce_leaves": (97, 153, 97),
    "birch_leaves": (128, 167, 85),
    "oak_leaves": (72, 181, 24),
    "jungle_leaves": (48, 187, 11),
    "acacia_leaves": (80, 203, 52),
    "dark_oak_leaves": (72, 181, 24)
}

def load_blacklist():
    data = load_json(BLACKLIST_FILE)
    return data.get("all_keywords",[]) + data.get("textures_keywords",[])
    
BLACKLIST = load_blacklist()

def calculate_average_color(img_data, filename):
    try:
        with Image.open(io.BytesIO(img_data)) as img:
            img = img.convert("RGBA")
            pixels = list(img.get_flattened_data())
            
            r_total, g_total, b_total = 0, 0, 0
            count = 0
            
            for r, g, b, a in pixels:
                if a > 10:
                    r_total += r
                    g_total += g
                    b_total += b
                    count += 1
            
            if count == 0:
                return None

            avg_color = (r_total // count, g_total // count, b_total // count)

            stem = filename.replace(".png", "")
            
            final_tint = None
            
            if "grass" in stem and "overlay" in stem:
                 final_tint = TINTS["grass_block_top"]
            elif "grass_block_top" in stem:
                 final_tint = TINTS["grass_block_top"]
            elif "leaves" in stem:
                for key, tint in TINTS.items():
                    if key in stem:
                        final_tint = tint
                        break
                if not final_tint and "oak" in stem: 
                     final_tint = TINTS["oak_leaves"]

            if final_tint:
                r = (avg_color[0] * final_tint[0]) // 255
                g = (avg_color[1] * final_tint[1]) // 255
                b = (avg_color[2] * final_tint[2]) // 255
                return (r, g, b)

            return avg_color

    except Exception as e:
        error(f"Error processing image {filename}: {e}")
        return None

def generate_colors_json(jar_path, output_file=COLOR_FILE):
    info(f"Reading {jar_path}...")
    
    colors = {}
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            files = [f for f in jar.namelist() if f.startswith("assets/minecraft/textures/block/") and f.endswith(".png")]
            
            info(f"{len(files)} block textures found. Processing...")
            
            for filepath in files:
                filename = os.path.basename(filepath)

                if any(x in filename for x in BLACKLIST):
                    continue

                img_data = jar.read(filepath)
                
                avg_rgb = calculate_average_color(img_data, filename)
                
                if avg_rgb:
                    key_name = filename.replace(".png", "")
                    
                    if key_name == "grass_block_top":
                        colors["grass_block"] = avg_rgb
                    
                    colors[key_name] = avg_rgb

    except FileNotFoundError:
        error("Error: Minecraft .jar file not found. Please check the MC_VERSION_FILE environment variable.")
        return
    except Exception as e:
        error(f"Error processing .jar file: {e}")
        return

    colors["default"] = [255, 0, 255]

    colors["water"] = [63, 118, 228]
    colors["lava"] = [255, 100, 0]

    with open(output_file, 'w') as f:
        json.dump(colors, f, sort_keys=True)
    
    success(f"Colors JSON generated successfully with {len(colors)} entries. Saved to {output_file}.")

if __name__ == "__main__":
    generate_colors_json(INPUT_FILE)