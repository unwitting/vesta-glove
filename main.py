from picographics import PicoGraphics, DISPLAY_LCD_240X240, PEN_RGB332
from pimoroni_bus import SPIBus
import network
import math
import time
import urequests
import ujson
import machine
import gc

WIFI_SSID = "vesta"
WIFI_PASSWORD = "vestavesta"
DEVICE_HOSTNAME = "vestaglove"

CONTROLLER_ID = "vesta"

LOG_FONT_SCALE = 1
LOG_LINE_RETENTION = 20

RUN_LOOP_PERIOD = 5

SCREEN_ROTATE = 180

spibus = SPIBus(cs=17, dc=16, sck=18, mosi=19)
display = PicoGraphics(display=DISPLAY_LCD_240X240, bus=spibus, pen_type=PEN_RGB332, rotate=SCREEN_ROTATE)

controller_ip = None
current_mode = None

logs = []

def log(s, render=True):
    global logs
    logs.insert(0, {"body": s})
    logs = logs[:LOG_LINE_RETENTION]
    print(f"Device log: {s}")
    if render:
        paint_background(display, 255, 89, 158)
        render_text_lines(display, [l["body"] for l in logs], 255, 255, 255, prefix=">")
        display.update()

def delay_log(s):
    return log(s, render=False)

def log_break():
    return log("", render=False)

def find_controller_ip(own_ip):
    log(f"Finding controller IP for {CONTROLLER_ID}")
    (one, two, three, four) = own_ip.split('.')
    for i_base in range(0, 256):
        i = ((i_base + 150) % 256) + 1
        if i == int(four):
            continue
        ip = f"{one}.{two}.{three}.{i}"
        log(f"Attempting {ip}")
        url = f"http://{ip}:10000/discover"
        try:
            response = urequests.get(url, timeout=0.5).json()
            if response['service'] != CONTROLLER_ID:
                log(f"Incorrect controller ID: {response['service']}")
            else:
                log(f"Found {CONTROLLER_ID} at {ip}!")
                global controller_ip
                controller_ip = ip
                return ip
        except Exception as e:
            print(e)

def get_current_mode():
    url = f"http://{controller_ip}:10000/mode"
    global current_mode
    current_mode = urequests.get(url, timeout=0.5).json()['mode']
    log(f"Current mode: {current_mode}")
    return current_mode

def attempt_wifi_connect():
    network.hostname(DEVICE_HOSTNAME)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    
    if sta_if.isconnected():
        log(f"Successfully connected!")
        (ip, subnet_mask, gateway, dns_ip) = sta_if.ifconfig()
        log(f"IP: {ip}")
        return (True, ip)

    log(f"Attempting to connect to wifi...")
    sta_if.connect(WIFI_SSID, WIFI_PASSWORD)
    time.sleep(1)

    if sta_if.isconnected():
        log(f"Successfully connected!")
        (ip, subnet_mask, gateway, dns_ip) = sta_if.ifconfig()
        log(f"IP: {ip}")
        return (True, ip)
        
    log(f"Couldn't connect :(")
    return (False, )

def free(full=False):
  F = gc.mem_free()
  A = gc.mem_alloc()
  T = F+A
  P = '{0:.2f}%'.format(F/T*100)
  if not full:
      return P
  else:
      return ('Total:{0} Free:{1} ({2})'.format(T,F,P))   

def paint_background(display, r, g, b, update=False):
    pen = display.create_pen(r, g, b)
    display.set_pen(pen)
    display.clear()

    if update:
        display.update()
        
def render_text_lines(display, lines, r, g, b, prefix=None, update=False):
    pen = display.create_pen(r, g, b)
    display.set_pen(pen)
    
    font_scale = LOG_FONT_SCALE
    w, h = display.get_bounds()
    font = "bitmap8"
    base_font_size = 8
    base_font_width = 4
    border = 4
    font_size = font_scale * base_font_size
    font_width = font_scale * base_font_width
    fixed_width = True

    display.set_font(font)
    
    prefixed_lines = [f"{prefix} {line}" if prefix else line for line in lines]
    
    x = border
    y = border
    
    for i, line in enumerate(prefixed_lines):
        c = 0
        sub_line_i = 0
        while c < len(line):
            sub_line = ""
            for char in line[c:]:
                prospective_sub_line = sub_line + char
                prospective_sub_line_width = display.measure_text(prospective_sub_line, scale=font_scale, fixed_width=fixed_width)

                if prospective_sub_line_width > (w - (2 * border)):
                    break

                do_not_add = (len(sub_line) == 0 and char == " ")
                if not do_not_add:
                    sub_line += char
                c += 1

            display.text(sub_line, x, y, scale=font_scale, fixed_width=fixed_width)
            sub_line_i += 1
            y += font_size + border

    if update:
        display.update()

def run_demo():
    while True:
        url = f"http://{controller_ip}:10000/run/demo/lines"
        lines = urequests.get(url, timeout=4).json()['lines']
        paint_background(display, 0, 0, 255)
        render_text_lines(display, lines, 255, 255, 255, update=True)
        time.sleep(0.5)

def run():
    while True:
        (connected, ip) = attempt_wifi_connect()
        if connected:
            break
        time.sleep(2)
    
    log_break()
    controller_ip = find_controller_ip(ip)
    
    log_break()
    mode = get_current_mode()
    
    log_break()
    
    try:
        if mode == 'demo':
            log("Running demo mode...")
            time.sleep(1)
            run_demo()
    except Exception as e:
        print(f"Error running mode program: {e}")

log("Hey, Tink!")
log_break()
while True:
    run()

    gc.collect()
    time.sleep(RUN_LOOP_PERIOD)

    log_break()
    log(free(full=True))
    log_break()

