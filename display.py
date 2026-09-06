import sys
import threading
import queue
import textwrap
from PIL import Image, ImageDraw, ImageFont

sys.path.append("./lib")
from waveshare_epd import epd7in5_V2

render_queue = queue.Queue(maxsize=1)
CURSOR_CHAR = "█"

def display_worker(epd, font):
    """Worker rendering text with minimal buffer latency."""
    while True:
        payload = render_queue.get()
        if payload is None:
            break

        text, cursor_index = payload

        canvas_w = max(epd.width, epd.height)  # 800
        canvas_h = min(epd.width, epd.height)  # 480

        image = Image.new('1', (canvas_w, canvas_h), 255)
        draw = ImageDraw.Draw(image)

        text_with_cursor = text[:cursor_index] + CURSOR_CHAR + text[cursor_index:]

        formatted_lines = []
        for raw_line in text_with_cursor.split('\n'):
            if raw_line:
                wrapped = textwrap.wrap(raw_line, width=62)
                formatted_lines.extend(wrapped if wrapped else [""])
            else:
                formatted_lines.append("")

        display_text = "\n".join(formatted_lines)
        draw.text((28, 28), display_text, font=font, fill=0)

        if epd.width < epd.height:
            image_to_send = image.rotate(90, expand=True)
        else:
            image_to_send = image

        buffer = epd.getbuffer(image_to_send)
        epd.display_Partial(buffer, 0, 0, epd.width, epd.height)
        render_queue.task_done()

def init_display():
    print("Initializing Waveshare 7.5inch V2 E-ink Display...")
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

    trigger_update("", 0)
    return epd

def trigger_update(text, cursor_index=0):
    if render_queue.full():
        try:
            render_queue.get_nowait()
        except queue.Empty:
            pass
    render_queue.put((text, cursor_index))

def cleanup_display(epd):
    render_queue.put(None)
    epd.sleep()
