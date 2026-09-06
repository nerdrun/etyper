import sys
import time
from evdev import InputDevice, categorize, ecodes, list_devices

SHIFT_MAP = {
    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
    '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
    '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
}

SYMBOL_MAP = {
    'KEY_DOT': '.', 'KEY_COMMA': ',', 'KEY_SLASH': '/',
    'KEY_BACKSLASH': '\\', 'KEY_SEMICOLON': ';', 'KEY_APOSTROPHE': "'",
    'KEY_LEFTBRACE': '[', 'KEY_RIGHTBRACE': ']', 'KEY_MINUS': '-',
    'KEY_EQUAL': '=', 'KEY_GRAVE': '`',
}

def listen_for_keys(update_callback):
    """Monitors ALL connected input devices simultaneously."""
    device_paths = list_devices()
    devices = []
    
    for path in device_paths:
        try:
            dev = InputDevice(path)
            devices.append(dev)
        except Exception:
            pass

    if not devices:
        print("Error: No input devices found!")
        sys.exit(1)

    print(f"Monitoring {len(devices)} input devices simultaneously...")
    print("\n--- Shift & Special Character E-Typewriter Ready ---")
    print("Type freely! Shift, Caps Lock, and punctuation are enabled.\n")

    current_text = ""
    shift_pressed = False
    caps_lock_active = False

    try:
        while True:
            # Poll all open input devices
            for dev in devices:
                try:
                    event = dev.read_one()
                except Exception:
                    continue

                if event and event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    keycode = key_event.keycode
                    if isinstance(keycode, list):
                        keycode = keycode[0]

                    # --- Handle Shift Press / Release ---
                    if keycode in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'):
                        shift_pressed = (key_event.keystate in (1, 2))
                        continue

                    # --- Handle Caps Lock Toggle ---
                    if keycode == 'KEY_CAPSLOCK' and key_event.keystate == 1:
                        caps_lock_active = not caps_lock_active
                        continue

                    # Process key-down events (keystate == 1)
                    if key_event.keystate == 1:
                        char_to_add = None

                        # --- Action: ENTER ---
                        if keycode == 'KEY_ENTER':
                            current_text += "\n"
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                            update_callback(current_text)
                            continue

                        # --- Action: BACKSPACE ---
                        elif keycode == 'KEY_BACKSPACE':
                            if len(current_text) > 0:
                                current_text = current_text[:-1]
                                sys.stdout.write("\b \b")
                                sys.stdout.flush()
                                update_callback(current_text)
                            continue

                        # --- Action: SPACEBAR ---
                        elif keycode == 'KEY_SPACE':
                            current_text += " "
                            sys.stdout.write(" ")
                            sys.stdout.flush()
                            update_callback(current_text)
                            continue

                        # --- Action: Punctuation & Symbols ---
                        elif keycode in SYMBOL_MAP:
                            base_char = SYMBOL_MAP[keycode]
                            char_to_add = SHIFT_MAP.get(base_char, base_char) if shift_pressed else base_char

                        # --- Action: Alphanumeric Keys ---
                        elif str(keycode).startswith('KEY_'):
                            raw_key = str(keycode).replace('KEY_', '').lower()

                            if len(raw_key) == 1:
                                if raw_key.isalpha():
                                    use_upper = shift_pressed ^ caps_lock_active
                                    char_to_add = raw_key.upper() if use_upper else raw_key
                                elif raw_key.isdigit():
                                    char_to_add = SHIFT_MAP.get(raw_key, raw_key) if shift_pressed else raw_key

                        # Append character if mapped successfully
                        if char_to_add:
                            current_text += char_to_add
                            sys.stdout.write(char_to_add)
                            sys.stdout.flush()
                            update_callback(current_text)

            # Prevent high CPU spinning while idle
            time.sleep(0.005)

    finally:
        for dev in devices:
            try:
                dev.close()
            except Exception:
                pass
