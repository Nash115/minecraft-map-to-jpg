import amulet
from PIL import Image, ImageDraw
from dotenv import load_dotenv
import os
import json

from tools.utils import load_json
from tools.block import Block
from tools.log import info, error, warning, fatal_error, success, progress

load_dotenv()

OUTPUT_WIDTH = int(os.getenv("OUTPUT_WIDTH", 1920))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
BLACKLIST_FILE = os.getenv("BLACKLIST_FILE", "data/blacklist.json")
COLOR_FILE = os.getenv("COLOR_FILE", "data/colors.json")
DEFAULT_COLOR = tuple(map(int, os.getenv("DEFAULT_COLOR", "255,0,255").split(",")))
PROGRESS_TEXT = os.getenv("PROGRESS_TEXT", 1)
COLOR_SET = load_json(COLOR_FILE)
BLACKLIST = load_json(BLACKLIST_FILE)

unknown_blocks = set()

def is_blacklisted(block: Block):
    if block.base_name in BLACKLIST.get("blocks", []):
        return True
    for keyword in BLACKLIST.get("all_keywords", []):
        if keyword in block.base_name:
            return True
    return False

def get_column_color(level, x, z):
    for y in range(319, -64, -1):
        try:
            block = Block(level.get_block(x, y, z, "minecraft:overworld"))
            if block.base_name == "air":
                continue
            elif block.base_name == "water":
                additional_color = [0,0,0]
                water_color_list = list(block.get_color(COLOR_SET) or DEFAULT_COLOR)
                for dy in range(y-1, -64, -1):
                    try:
                        below_block = Block(level.get_block(x, dy, z, "minecraft:overworld"))
                        if below_block.base_name != "water":
                            water_color_list[0] = min(water_color_list[0] + additional_color[0], 255)
                            water_color_list[1] = min(water_color_list[1] + additional_color[1], 255)
                            water_color_list[2] = min(water_color_list[2] + additional_color[2], 255)
                            return tuple(water_color_list)
                        else:
                            additional_color[0] = min(additional_color[0] - 10, - (water_color_list[0] // 2))
                            additional_color[1] = min(additional_color[1] - 10, - (water_color_list[1] // 2))
                            additional_color[2] = max(additional_color[2] - 10, - (water_color_list[2] // 2))
                    except Exception as e:
                        warning(f"Error reading block at ({x}, {dy}, {z}): {e}. Skipping.")
                        break
            if is_blacklisted(block):
                continue
            color = block.get_color(COLOR_SET)
            if not color:
                warning(f"Unknown block '{block.json()}' at ({x}, {y}, {z}).")
                unknown_blocks.add(json.dumps(block.json(), sort_keys=True))
                continue
            return color
        except Exception as e:
            warning(f"Error reading block at ({x}, {y}, {z}): {e}. Skipping.")
            continue
    warning(f"Could not find valid block at column ({x}, {z}). Using default color.")
    return DEFAULT_COLOR

def generate_map(world_path, x1, z1, x2, z2):
    x_min, z_min = min(x1, x2), min(z1, z2)
    x_max, z_max = max(x1, x2), max(z1, z2)

    width = x_max - x_min
    height = z_max - z_min

    if width <= 0 or height <= 0:
        error("Error: Invalid selection area. Aborting map generation.")
        return
    
    ratio = height / width
    img_width = OUTPUT_WIDTH
    img_height = int(OUTPUT_WIDTH * ratio)
    pixel_per_block = img_width / width

    info(f"Scanning area: {width}x{height} ({width * height} blocks)")
    info(f"Output image: {img_width}x{img_height} px")
    info(f"Scale: 1 block = {pixel_per_block:.2f} px")
    info(f"Loading world: {world_path}...")

    try:
        level = amulet.load_level(world_path)
    except Exception as e:
        error(f"Could not load world: {e}. Aborting map generation.")
        return
    
    image = Image.new('RGB', (img_width, img_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)

    info("Starting scan... (this may take a while for large areas)")

    try:
        for x in range(width):
            for z in range(height):
                if PROGRESS_TEXT == 1:
                    progress(f"Scanning map {int(((x * height + z) / (width * height)) * 100)}%")

                world_x = x_min + x
                world_z = z_min + z

                color = get_column_color(level, world_x, world_z)

                x1p = x * pixel_per_block
                z1p = z * pixel_per_block
                x2p = x1p + pixel_per_block
                z2p = z1p + pixel_per_block

                draw.rectangle([x1p, z1p, x2p, z2p], fill=color)

    except KeyboardInterrupt:
        print()
        warning("Map generation interrupted by user. Saving partial image...")
    finally:
        level.close()
    progress("Scanning map done !", done=True)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    output_path = os.path.join(OUTPUT_DIR, "map.jpg")
    image.save(output_path, quality=95)
    success(f"Done! Image saved to: {output_path}")


if __name__ == "__main__":
    MAP_PATH = os.getenv("MAP_PATH", None)
    if not MAP_PATH:
        fatal_error("MAP_PATH environment variable is not set")
    if not os.path.exists(MAP_PATH):
        fatal_error(f"MAP_PATH '{MAP_PATH}' does not exist")

    X1 = int(os.getenv("X1", False))
    Z1 = int(os.getenv("Z1", False))
    X2 = int(os.getenv("X2", False))
    Z2 = int(os.getenv("Z2", False))
    if X1 == False or Z1 == False or X2 == False or Z2 == False:
        fatal_error("X1, Z1, X2, and Z2 environment variables must be set")
    
    generate_map(MAP_PATH, X1, Z1, X2, Z2)

    if unknown_blocks:
        warning("Unknown blocks encountered during generation:")
        all_blocks = ""
        for block in unknown_blocks:
            print(f" - {block}")
            all_blocks += block + "\n"
        with open(os.path.join(OUTPUT_DIR, "unknown_blocks.txt"), "w") as f:
            f.write(all_blocks)
        info(f"List of unknown blocks saved to: {os.path.join(OUTPUT_DIR, 'unknown_blocks.txt')}")
