import sys
import time
import textwrap
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

LINE_WIDTH = 62

def move_vertical_fast(text, cursor_idx, direction):
    """Calculates vertical movement ONLY when Up/Down is actually pressed."""
    if not text:
        return 0

    line_starts = []
    current_pos = 0
    raw_lines = text.split('\n')
    
    for r_idx, raw in enumerate(raw_lines):
        if r_idx > 0:
            current_pos += 1  # \n
        wrapped = textwrap.wrap(raw, width=LINE_WIDTH) if raw else [""]
        if not wrapped:
            wrapped = [""]
        for w in wrapped:
            line_starts.append((current_pos, current_pos + len(w)))
            current_pos += len(w)

    current_line = 0
    col_offset = 0
    for idx, (start, end) in enumerate(line_starts):
        if start <= cursor_idx <= end:
            current_line = idx
            col_offset = cursor_idx - start
            break

    target_line = current_line + direction
    if target_line < 0 or target_line >= len(line_starts):
        return cursor_idx

    t_start, t_end = line_starts[target_line]
    target_len = t_end - t_start
    new_col = min(col_offset, target_len)
    
    return t_start + new_col

def print_console_preview(text, cursor_index):
    terminal_text = text[:cursor_index] + "█" + text[cursor_index:]
    sys.stdout.write("\033[H\033[J")
    sys.stdout.write("--- E-Typewriter Live Console ---\n\n")
    sys.stdout.write(terminal_text)
    sys.stdout.flush()

def listen_for_keys(update_callback):
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
    
    current_text = ""
    cursor_index = 0
    shift_pressed = False
    caps_lock_active = False

    print_console_preview(current_text, cursor_index)

    try:
        while True:
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

                    if keycode in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'):
                        shift_pressed = (key_event.keystate in (1, 2))
                        continue

                    if keycode == 'KEY_CAPSLOCK' and key_event.keystate == 1:
                        caps_lock_active = not caps_lock_active
                        continue

                    if key_event.keystate == 1:
                        
                        # --- LEFT / RIGHT ARROWS (Fast Path) ---
                        if keycode == 'KEY_LEFT':
                            if cursor_index > 0:
                                cursor_index -= 1
                                print_console_preview(current_text, cursor_index)
                                update_callback(current_text, cursor_index)
                            continue

                        elif keycode == 'KEY_RIGHT':
                            if cursor_index < len(current_text):
                                cursor_index += 1
                                print_console_preview(current_text, cursor_index)
                                update_callback(current_text, cursor_index)
                            continue

                        # --- UP / DOWN ARROWS (On-Demand Calculation) ---
                        elif keycode == 'KEY_UP':
                            cursor_index = move_vertical_fast(current_text, cursor_index, -1)
                            print_console_preview(current_text, cursor_index)
                            update_callback(current_text, cursor_index)
                            continue

                        elif keycode == 'KEY_DOWN':
                            cursor_index = move_vertical_fast(current_text, cursor_index, 1)
                            print_console_preview(current_text, cursor_index)
                            update_callback(current_text, cursor_index)
                            continue

                        # --- ENTER KEY ---
                        elif keycode == 'KEY_ENTER':
                            current_text = current_text[:cursor_index] + "\n" + current_text[cursor_index:]
                            cursor_index += 1
                            print_console_preview(current_text, cursor_index)
                            update_callback(current_text, cursor_index)
                            continue

                        # --- BACKSPACE KEY ---
                        elif keycode == 'KEY_BACKSPACE':
                            if cursor_index > 0:
                                current_text = current_text[:cursor_index - 1] + current_text[cursor_index:]
                                cursor_index -= 1
                                print_console_preview(current_text, cursor_index)
                                update_callback(current_text, cursor_index)
                            continue

                        # --- SPACEBAR ---
                        elif keycode == 'KEY_SPACE':
                            current_text = current_text[:cursor_index] + " " + current_text[cursor_index:]
                            cursor_index += 1
                            print_console_preview(current_text, cursor_index)
                            update_callback(current_text, cursor_index)
                            continue

                        # --- PUNCTUATION & SYMBOLS ---
                        char_to_add = None
                        if keycode in SYMBOL_MAP:
                            base_char = SYMBOL_MAP[keycode]
                            char_to_add = SHIFT_MAP.get(base_char, base_char) if shift_pressed else base_char

                        # --- ALPHANUMERIC KEYS ---
                        elif str(keycode).startswith('KEY_'):
                            raw_key = str(keycode).replace('KEY_', '').lower()
                            if len(raw_key) == 1:
                                if raw_key.isalpha():
                                    use_upper = shift_pressed ^ caps_lock_active
                                    char_to_add = raw_key.upper() if use_upper else raw_key
                                elif raw_key.isdigit():
                                    char_to_add = SHIFT_MAP.get(raw_key, raw_key) if shift_pressed else raw_key

                        if char_to_add:
                            current_text = current_text[:cursor_index] + char_to_add + current_text[cursor_index:]
                            cursor_index += 1
                            print_console_preview(current_text, cursor_index)
                            update_callback(current_text, cursor_index)

            time.sleep(0.002)

    finally:
        for dev in devices:
            try:
                dev.close()
            except Exception:
                pass
