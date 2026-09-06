import display
import keyboard

def main():
    # 1. Initialize display hardware and start background worker thread
    epd = display.init_display()
    
    try:
        # 2. Listen to all input devices simultaneously
        keyboard.listen_for_keys(update_callback=display.trigger_update)
    except KeyboardInterrupt:
        print("\nExiting program...")
    finally:
        # 3. Safely put the screen to sleep on exit
        display.cleanup_display(epd)

if __name__ == "__main__":
    main()
