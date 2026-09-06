import sys
import threading
import queue
import textwrap
from PIL import Image, ImageDraw, ImageFont

sys.path.append("./lib")
from waveshare_epd import epd7in5_V2, epdconfig

render_queue = queue.Queue(maxsize=1)

def display_worker(epd, font):
    """Background worker handling lightning-fast line-based partial refreshes."""
    previous_last_idx = 0
    
    while True:
        text = render_queue.get()
        if text is None:
            break

        canvas_w = max(epd.width, epd.height)  # 800
        canvas_h = min(epd.width, epd.height)  # 480

        image = Image.new('1', (canvas_w, canvas_h), 255)
        draw = ImageDraw.Draw(image)

        formatted_lines = []
        for raw_line in text.split('\n'):
            if raw_line:
                wrapped = textwrap.wrap(raw_line, width=62)
                formatted_lines.extend(wrapped if wrapped else [""])
            else:
                formatted_lines.append("")

        # --- STRICT 8-PIXEL BYTE ALIGNMENT ---
        # The hardware controller demands X-coordinates be multiples of 8.
        # When rotated, our Y becomes the hardware's X.
        Y_MARGIN = 24    # 24 % 8 = 0
        LINE_HEIGHT = 32 # 32 % 8 = 0
        
        # Render line by line
        for idx, line in enumerate(formatted_lines):
            y_pos = Y_MARGIN + (idx * LINE_HEIGHT)
            draw.text((28, y_pos), line, font=font, fill=0)

        # --- TIGHT BOUNDING BOX LOGIC ---
        current_last_idx = max(0, len(formatted_lines) - 1)
        
        # Determine exactly which lines changed (handles backspace rolling up a line)
        start_idx = min(previous_last_idx, current_last_idx)
        end_idx = max(previous_last_idx, current_last_idx) + 1
        previous_last_idx = current_last_idx

        # Calculate exact pixel boundaries to send
        landscape_y_start = Y_MARGIN + (start_idx * LINE_HEIGHT)
        landscape_y_end = Y_MARGIN + ((end_idx + 1) * LINE_HEIGHT)
        landscape_y_end = min(landscape_y_end, canvas_h) # Clamp to edge

        # Map to hardware coordinates
        if epd.width < epd.height:
            image_to_send = image.rotate(90, expand=True)
            hw_x_start = landscape_y_start
            hw_x_end = landscape_y_end
            hw_y_start = 0
            hw_y_end = epd.height
        else:
            image_to_send = image
            hw_x_start = 0
            hw_x_end = epd.width
            hw_y_start = landscape_y_start
            hw_y_end = landscape_y_end

        buffer = epd.getbuffer(image_to_send)
        
        # Push only the tiny byte-aligned sliver that actually changed
        epd.display_Partial(buffer, hw_x_start, hw_y_start, hw_x_end, hw_y_end)
        render_queue.task_done()

def init_display():
    print("Initializing Waveshare 7.5inch V2 E-ink Display...")
    
    # --- HARDWARE OVERCLOCK ---
    # Boost SPI speed from default 2MHz to 16MHz for instant data transfer
    try:
        epdconfig.SPI.max_speed_hz = 16000000
        print("SPI Overclocked to 16MHz successfully!")
    except Exception as e:
        print(f"Note: Could not overclock SPI ({e})")

    epd = epd7in5_V2.EPD()
    epd.init()
    epd.Clear()
    epd.init_part()

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    worker = threading.Thread(target=display_worker, args=(epd, font), daemon=True)
    worker.start()
    return epd

def trigger_update(text):
    if render_queue.full():
        try:
            render_queue.get_nowait()
        except queue.Empty:
            pass
    render_queue.put(text)

def cleanup_display(epd):
    render_queue.put(None)
    epd.sleep()
