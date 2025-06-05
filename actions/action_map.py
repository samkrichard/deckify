import json

def build_button_action_map(config_path, controller, renderer=None):
    with open(config_path, 'r') as f:
        config = json.load(f)

    buttons = config.get("buttons", {})
    button_map = {}
    # map of button key to long-press (method, args, timeout)
    long_map = {}

    for key_str, entry in buttons.items():
        key = int(key_str)
        action_name = entry.get("action")
        args = entry.get("args", [])
        label = entry.get("label", "")
        icon = entry.get("icon", "")

        # Setup generic long-press action if configured (non-like buttons)
        if not entry.get("icon_add") and not entry.get("icon_remove"):
            long_action = entry.get("long_action")
            if long_action:
                method_long = getattr(controller, long_action, None)
                if callable(method_long):
                    timeout = entry.get("long_timeout", 1.0)
                    long_args = entry.get("long_args", [])
                    long_map[key] = (method_long, long_args, timeout)
                else:
                    print(f"[WARN] No method '{long_action}' found in controller for long press button {key}")

        # Bind like-button toggle (add/remove) and optional playlist-add mode icon & long-press
        add_icon = entry.get("icon_add")
        remove_icon = entry.get("icon_remove")
        if add_icon and remove_icon:
            try:
                liked = controller.is_current_track_liked()
            except Exception as e:
                print(f"[WARN] Failed to check liked status for button {key}: {e}")
                liked = False
            initial_icon = remove_icon if liked else add_icon
            if renderer:
                try:
                    renderer.update_button(key, text=label, image=initial_icon)
                except Exception as e:
                    print(f"[WARN] Failed to render button {key}: {e}")
            # Register toggle-like (short press)
            method = getattr(controller, action_name, None)
            if callable(method):
                button_map[key] = (lambda m=method, k=key, ai=add_icon, ri=remove_icon: m(k, ai, ri))
            # Register playlist-add mode (long press) if configured
            mode_icon = entry.get("icon_mode")
            long_action = entry.get("long_action")
            if mode_icon and long_action:
                method_mode = getattr(controller, long_action, None)
                if callable(method_mode):
                    timeout = entry.get("long_timeout", 1.0)
                    # pass button key, icons, and optional mode timeout
                    playlist_timeout = entry.get("playlist_add_timeout", None)
                    args_mode = [key, add_icon, remove_icon, mode_icon]
                    if playlist_timeout is not None:
                        args_mode.append(playlist_timeout)
                    long_map[key] = (method_mode, args_mode, timeout)
                else:
                    print(f"[WARN] No method '{long_action}' found in controller for long press button {key}")
            continue

        # Fetch icon if needed for standard action
        if icon == "fetch" and action_name == "play_playlist" and args:
            try:
                icon = controller.get_playlist_icon_url(args[0])
            except Exception as e:
                print(f"[WARN] Failed to fetch icon for playlist: {e}")

        # Update button display for standard action
        if renderer:
            try:
                renderer.update_button(key, text=label, image=icon)
            except Exception as e:
                print(f"[WARN] Failed to render button {key}: {e}")

        # Register initial playlist hotkey mapping for play_playlist entries
        if action_name == "play_playlist" and args:
            try:
                controller.register_playlist_hotkey(key, args[0])
            except Exception as e:
                print(f"[WARN] Failed to register playlist hotkey for button {key}: {e}")
        # Bind standard action (short press)
        method = getattr(controller, action_name, None)
        if callable(method):
            button_map[key] = (lambda m=method, a=args: m(*a))
        else:
            print(f"[WARN] No method '{action_name}' found in controller for button {key}")

    return button_map, long_map


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



