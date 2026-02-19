from tools.log import fatal_error

aliases = {
    "grass_path": "dirt_path",
    "stained_terracotta": "terracotta",
}

class Block:
    def __init__(self, block):
        self.base_name = block.base_name
        for alias, target in aliases.items():
            if self.base_name == alias:
                self.base_name = target
                break
        self.properties = block.properties
        if self.base_name is None or self.properties is None:
            fatal_error(f"Invalid block data: {block}")
    def json(self, sort_keys=True):
        # Convert properties to JSON-serializable types
        serializable_props = {}
        for key, value in self.properties.items():
            if hasattr(value, '__str__'):
                serializable_props[key] = str(value)
            else:
                serializable_props[key] = value
        return {
            "base_name": self.base_name,
            "properties": serializable_props
        }
    def get_color(self, COLOR_SET:dict) -> tuple | None:
        if COLOR_SET.get(self.base_name):
            return tuple(COLOR_SET[self.base_name])
        if COLOR_SET.get(f"{self.base_name}_top"):
            return tuple(COLOR_SET[f"{self.base_name}_top"])
        if COLOR_SET.get(f"{self.base_name.replace('_block', '')}"):
            return tuple(COLOR_SET[f"{self.base_name.replace('_block', '')}"])
        
        material_prop = self.properties.get("material", "")
        if material_prop:
            new_names = [
                f"{material_prop}_{self.base_name}",
                f"{material_prop}",
                f"{material_prop}s",
                f"{material_prop}_planks"
            ]
            for new_name in new_names:
                if COLOR_SET.get(new_name):
                    return tuple(COLOR_SET[new_name])
        color_prop = self.properties.get("color", "")
        if color_prop:
            new_names = [
                f"{color_prop}_{self.base_name}"
            ]
            for new_name in new_names:
                if COLOR_SET.get(new_name):
                    return tuple(COLOR_SET[new_name])
        
        return None
