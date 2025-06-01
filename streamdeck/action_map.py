import json

import json

def build_button_action_map(config_path, controller, renderer=None):
    with open(config_path, 'r') as f:
        config = json.load(f)

    buttons = config.get("buttons", {})
    button_map = {}

    for key, entry in buttons.items():
        action_name = entry.get("action")
        args = entry.get("args", [])
        label = entry.get("label")
        icon = entry.get("icon")

        method = getattr(controller, action_name, None)
        if not callable(method):
            print(f"[WARN] No method '{action_name}' found in controller for button {key}")
            continue

        # Icon fetch logic
        if icon == "fetch" and action_name == "play_playlist" and args:
            icon_url = controller.get_playlist_icon_url(args[0])
        else:
            icon_url = icon

        # Render if renderer is present
        if renderer:
            try:
                renderer.update_button(int(key), text=label, image=icon_url)
            except Exception as e:
                print(f"[WARN] Failed to render button {key}: {e}")

        # Action binding
        button_map[key] = lambda *_, m=method, a=args: m(*a)

    return button_map

def build_dial_action_map(config_path, controller):
    with open(config_path, 'r') as f:
        config = json.load(f)

    dials = config.get("dials", {})
    dial_map = {}

    for dial_key, entry in dials.items():
        action_name = entry.get("action")
        method = getattr(controller, action_name, None)
        if not callable(method):
            print(f"[WARN] No method '{action_name}' found in controller for dial '{dial_key}'")
            continue
        dial_map[dial_key] = lambda *_, m=method: m()

    return dial_map



