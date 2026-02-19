# minecraft-map-to-jpg
Convert a minecraft map to an image

# Usage

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