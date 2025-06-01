import json

def load_profile(path, controller):
    with open(path, 'r') as f:
        config = json.load(f)

    action_map = {}

    # Buttons
    for button_id, entry in config["buttons"].items():
        action_name = entry["action"]
        args = entry.get("args", [])

        method = getattr(controller, action_name, None)
        if method:
            action_map[button_id] = lambda *_, m=method, a=args: m(*a)

    # TODO: add dial and touchscreen handlers later
    return action_map
