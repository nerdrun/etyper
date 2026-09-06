import display
import keyboard

def main():
    epd = display.init_display()
    
    try:
        keyboard.listen_for_keys(update_callback=display.trigger_update)
    except KeyboardInterrupt:
        print("\nExiting program...")
    finally:
        display.cleanup_display(epd)

if __name__ == "__main__":
    main()
