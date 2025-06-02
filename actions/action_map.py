import json

def build_button_action_map(config_path, controller, renderer=None):
    with open(config_path, 'r') as f:
        config = json.load(f)

    buttons = config.get("buttons", {})
    button_map = {}

    for key_str, entry in buttons.items():
        key = int(key_str)
        action_name = entry.get("action")
        args = entry.get("args", [])
        label = entry.get("label", "")
        icon = entry.get("icon", "")

        method = getattr(controller, action_name, None)
        if not callable(method):
            print(f"[WARN] No method '{action_name}' found in controller for button {key}")
            continue

        # Fetch icon if needed
        if icon == "fetch" and action_name == "play_playlist" and args:
            try:
                icon = controller.get_playlist_icon_url(args[0])
            except Exception as e:
                print(f"[WARN] Failed to fetch icon for playlist: {e}")

        # Update button display
        if renderer:
            try:
                renderer.update_button(key, text=label, image=icon)
            except Exception as e:
                print(f"[WARN] Failed to render button {key}: {e}")

        # Bind action (fix lambda closure bug using default args)
        button_map[key] = (lambda m=method, a=args: m(*a))

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

        # Bind action safely
        dial_map[dial_key] = (lambda m=method: m())

    return dial_map



