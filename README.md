# minecraft-map-to-jpg
Convert a minecraft map to an image

# Usage

## Using Docker

1. Copy the `.env.example` file to `.env` and update the `X1`, `Z1`, `X2`, and `Z2` environment variables to specify the coordinates of the area you want to convert. You can delete the `MAP_PATH` and `MC_VERSION_FILE` environment variables **(you don't need them for this usage)**.
2. Edit the `docker-compose.yml` file to point to your Minecraft world save directory. For example, if your world is located at `/my/path/to/minecraft/saves/world`, you would add the following volume mapping:
   ```yaml
     - "/my/path/to/minecraft/saves/world:/app/world"
   ```
3. Run the following command to start the Docker container and generate the image:
   ```bash
   docker-compose up --build
   ```
4. The generated image will be saved in the `output` directory.

## Simple usage

1. Copy the `.env.example` file to `.env` and update the environment variables as needed.
2. Create a venv and install the dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the main script to convert a map to an image:
   ```bash
   python3 main.py
   ```

## Update the `colors.json` file

You can uptate the `colors.json` file to add new blocks for new versions of Minecraft for example.
1. Add the `MC_VERSION_FILE` environment variable to point to the Minecraft .jar file you want to extract colors from. (e.g., `MC_VERSION_FILE="/.../minecraft/versions/1.20.4/1.20.4.jar"`)
2. Run `python3 generate_colors.py` to generate a new `colors.json` file with the colors extracted from the specified Minecraft version.

## Relief shading

The renderer includes a terrain relief effect on non-water blocks to add visual depth (mountains, trees, cliffs, etc.).

- `TERRAIN_SHADE_STRENGTH`: intensity of the shading per height step (default: `12`)
- `TERRAIN_SHADE_MAX_DELTA`: maximum light/dark adjustment in RGB values (default: `72`)

## Custom block size

By default, each Minecraft block is rendered as a 1x1 pixel in the output image. You can adjust this by setting the `BLOCK_SIZE_PX` environment variable to a higher value (e.g., `2` for 2x2 pixels per block). Note that increasing the block size will also increase the dimensions of the output image accordingly.