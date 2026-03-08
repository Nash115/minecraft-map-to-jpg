import amulet
from PIL import Image, ImageDraw
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import re

from tools.utils import load_json
from tools.block import Block
from tools.log import info, error, warning, fatal_error, success, progress

load_dotenv()

BLOCK_SIZE_PX = int(os.getenv("BLOCK_SIZE_PX", 1))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
BLACKLIST_FILE = os.getenv("BLACKLIST_FILE", "data/blacklist.json")
COLOR_FILE = os.getenv("COLOR_FILE", "data/colors.json")
DEFAULT_COLOR = tuple(map(int, os.getenv("DEFAULT_COLOR", "255,0,255").split(",")))
PROGRESS_TEXT = os.getenv("PROGRESS_TEXT", 1)
COLOR_SET = load_json(COLOR_FILE)
BLACKLIST = load_json(BLACKLIST_FILE)

unknown_blocks = set()

DATE_IMAGE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.jpg$")

# Height-based shading for terrain relief (mountains, trees, cliffs, etc.)
TERRAIN_SHADE_STRENGTH = int(os.getenv("TERRAIN_SHADE_STRENGTH", 12))
TERRAIN_SHADE_MAX_DELTA = int(os.getenv("TERRAIN_SHADE_MAX_DELTA", 72))

def is_blacklisted(block: Block):
    if block.base_name in BLACKLIST.get("blocks", []):
        return True
    for keyword in BLACKLIST.get("all_keywords", []):
        if keyword in block.base_name:
            return True
    return False

def clamp_rgb(color):
    return tuple(max(0, min(255, int(c))) for c in color)


def get_column_surface(level, x, z):
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
                            return {
                                "color": clamp_rgb(tuple(water_color_list)),
                                "y": y,
                                "is_water": True,
                            }
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
            return {
                "color": color,
                "y": y,
                "is_water": False,
            }
        except Exception as e:
            warning(f"Error reading block at ({x}, {y}, {z}): {e}. Skipping.")
            continue
    warning(f"Could not find valid block at column ({x}, {z}). Using default color.")
    return {
        "color": DEFAULT_COLOR,
        "y": -64,
        "is_water": False,
    }


def get_surface_cached(level, x, z, surface_cache):
    key = (x, z)
    if key not in surface_cache:
        surface_cache[key] = get_column_surface(level, x, z)
    return surface_cache[key]


def shade_terrain_color(base_color, dx_height, dz_height):
    # Simulate a fixed light direction from north-west by combining local slopes.
    delta = dx_height + dz_height
    shade = max(-TERRAIN_SHADE_MAX_DELTA, min(TERRAIN_SHADE_MAX_DELTA, delta * TERRAIN_SHADE_STRENGTH))
    return clamp_rgb((base_color[0] + shade, base_color[1] + shade, base_color[2] + shade))


def cleanup_old_images(output_dir: str):
    dated_images = []

    for file_name in os.listdir(output_dir):
        match = DATE_IMAGE_PATTERN.match(file_name)
        if not match:
            continue

        try:
            file_date = datetime.strptime(file_name[:-4], "%Y-%m-%d")
        except ValueError:
            # Ignore files that look similar but are not valid dates.
            continue

        dated_images.append((file_name, file_date))

    if not dated_images:
        return

    current_year = datetime.now().year
    keep_by_month_current_year = {}
    keep_by_year_past = {}

    for file_name, file_date in dated_images:
        if file_date.year == current_year:
            key = (file_date.year, file_date.month)
            prev = keep_by_month_current_year.get(key)
            if prev is None or file_date > prev[1]:
                keep_by_month_current_year[key] = (file_name, file_date)
        elif file_date.year < current_year:
            key = file_date.year
            prev = keep_by_year_past.get(key)
            if prev is None or file_date > prev[1]:
                keep_by_year_past[key] = (file_name, file_date)

    files_to_keep = {entry[0] for entry in keep_by_month_current_year.values()}
    files_to_keep.update(entry[0] for entry in keep_by_year_past.values())

    removed_count = 0
    for file_name, _ in dated_images:
        if file_name in files_to_keep:
            continue

        try:
            os.remove(os.path.join(output_dir, file_name))
            removed_count += 1
        except OSError as e:
            warning(f"Could not delete old image '{file_name}': {e}")

    if removed_count > 0:
        info(f"Cleanup done: removed {removed_count} old image(s) based on retention rules.")

def generate_map(world_path, x1, z1, x2, z2):
    x_min, z_min = min(x1, x2), min(z1, z2)
    x_max, z_max = max(x1, x2), max(z1, z2)

    width = x_max - x_min
    height = z_max - z_min

    if width <= 0 or height <= 0:
        error("Error: Invalid selection area. Aborting map generation.")
        return
    
    img_width = width * BLOCK_SIZE_PX
    img_height = height * BLOCK_SIZE_PX
    pixel_per_block = BLOCK_SIZE_PX

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
    surface_cache = {}

    try:
        for x in range(width):
            for z in range(height):
                if PROGRESS_TEXT == 1:
                    progress(f"Scanning map {int(((x * height + z) / (width * height)) * 100)}%")

                world_x = x_min + x
                world_z = z_min + z

                center = get_surface_cached(level, world_x, world_z, surface_cache)
                color = center["color"]

                # Keep existing water behavior untouched; add terrain relief only on non-water surfaces.
                if not center["is_water"]:
                    east = get_surface_cached(level, world_x + 1, world_z, surface_cache)
                    north = get_surface_cached(level, world_x, world_z - 1, surface_cache)
                    dx_height = center["y"] - east["y"]
                    dz_height = center["y"] - north["y"]
                    color = shade_terrain_color(color, dx_height, dz_height)

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

    image_name = f"{datetime.now().strftime('%Y-%m-%d')}.jpg"
    output_path = os.path.join(OUTPUT_DIR, image_name)
    image.save(output_path, quality=95)
    success(f"Done! Image saved to: {output_path}")
    cleanup_old_images(OUTPUT_DIR)


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
