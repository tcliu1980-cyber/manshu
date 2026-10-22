# main.py — Pico W 雙風扇 Wi-Fi 控制（DRV8833）
# 適用：Raspberry Pi Pico W + MicroPython + HW-627 / DRV8833
# 請先拆下螺旋槳，檢查接線，再測試。

import network
import socket
import time
from machine import Pin, PWM

# ============================================================
# ★ 每艘船一定要改成不同 SSID！例如 fan01、fan02、fan03。
# ★ 密碼至少 8 個字元。88888888 只適合教學示範。
# ============================================================
SSID = "fan00"
PASSWORD = "88888888"

# 第一次測試將 PWM 輸出上限限制為 70%。
# 注意：PWM 上限不等於穩壓，不可取代 3.7V 穩壓器。
MAX_PWM_PERCENT = 70

# 超過此時間（毫秒）收不到控制指令，就自動停止兩顆馬達。
CONTROL_TIMEOUT_MS = 1100
PWM_FREQUENCY = 1000

# Pico GP14 -> DRV8833 IN1；GP15 -> IN2
# Pico GP16 -> DRV8833 IN3；GP17 -> IN4
left_pwm = PWM(Pin(14))
left_direction = Pin(15, Pin.OUT, value=0)
right_pwm = PWM(Pin(16))
right_direction = Pin(17, Pin.OUT, value=0)
left_pwm.freq(PWM_FREQUENCY)
right_pwm.freq(PWM_FREQUENCY)
left_pwm.duty_u16(0)
right_pwm.duty_u16(0)

current_left = 0
current_right = 0
last_command_ms = time.ticks_ms()


def set_motors(left, right):
    """接收 0~100 的控制百分比；只允許正向推進。"""
    global current_left, current_right
    left = max(0, min(100, int(left)))
    right = max(0, min(100, int(right)))
    # 先固定 H 橋另一個方向輸入為 LOW。
    left_direction.value(0)
    right_direction.value(0)
    # 兩根拉桿的 100% 對應 MAX_PWM_PERCENT 的占空比。
    scale = 65535 * MAX_PWM_PERCENT // 100
    left_pwm.duty_u16(left * scale // 100)
    right_pwm.duty_u16(right * scale // 100)
    current_left, current_right = left, right


def stop_motors():
    set_motors(0, 0)


# Pico W 自己送給手機的 HTML；不需要另外上傳 index.html。
# 拉桿垂直排列：上方 100%，下方 0%。
CONTROL_PAGE = r'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>雙風扇遙控台</title>
<style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,"Noto Sans TC",sans-serif}
*{box-sizing:border-box}body{margin:0;background:#0d1728;color:#f5f8ff;padding:18px 12px 25px}
main{max-width:520px;margin:auto}h1{text-align:center;margin:8px 0 4px;font-size:1.65rem}
.sub{text-align:center;color:#9db1c9;font-size:.86rem;margin:0 0 15px}
.status{padding:11px 12px;border-radius:13px;background:#23324a;text-align:center;font-weight:700;margin-bottom:14px}
.status.ok{background:#104b3a;color:#aef8dc}.status.bad{background:#5a222c;color:#ffe4e4}
.motors{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.motor{min-width:0;border:1px solid #304761;border-radius:18px;background:#142339;text-align:center;padding:14px 5px 12px}
.motor h2{margin:0;font-size:1.1rem}.num{font-weight:850;font-size:2rem;color:#62e5cb;margin-top:8px}
.track{height:292px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.track input{width:252px;height:48px;transform:rotate(-90deg);accent-color:#55dcbf;touch-action:none;cursor:pointer}
.tick{font-size:.75rem;color:#95a9c0;margin-top:-5px}
button{font:inherit;cursor:pointer;touch-action:manipulation}
#stop{display:block;width:100%;margin-top:17px;border:none;background:#dd3143;color:white;padding:18px;border-radius:16px;font-size:1.45rem;font-weight:900}
.help{font-size:.86rem;line-height:1.65;color:#b8c8dc;margin-top:15px}
</style>
</head>
<body><main>
<h1>🚤 雙風扇遙控台</h1>
<p class="sub">目前船隻：<b>__SSID__</b> ｜ 向上加速、向下減速</p>
<div class="status" id="status">連線確認中…</div>
<div class="motors">
  <section class="motor"><h2>左風扇</h2><div class="num" id="lv">0%</div>
    <div class="track"><input id="left" aria-label="左風扇速度" type="range" min="0" max="100" value="0" step="1"></div>
    <div class="tick">下方 0%　↑　上方 100%</div></section>
  <section class="motor"><h2>右風扇</h2><div class="num" id="rv">0%</div>
    <div class="track"><input id="right" aria-label="右風扇速度" type="range" min="0" max="100" value="0" step="1"></div>
    <div class="tick">下方 0%　↑　上方 100%</div></section>
</div>
<button id="stop" type="button">■ 緊急停止｜兩顆歸零</button>
<p class="help">兩根拉桿彼此獨立。數字是「控制百分比」，並非實際 RPM。<br>
若連線中斷，Pico W 約 1.1 秒收不到指令就會停轉。<br>
嚴禁觸碰旋轉螺旋槳；使用前請確認四周無人接近。</p>
</main>
<script>
const left=document.getElementById('left');
const right=document.getElementById('right');
const lv=document.getElementById('lv');
const rv=document.getElementById('rv');
const statusEl=document.getElementById('status');
let busy=false, stopped=false;
function values(){return [Number(left.value),Number(right.value)]}
function refresh(){lv.textContent=left.value+'%';rv.textContent=right.value+'%'}
function say(txt,kind){statusEl.textContent=txt;statusEl.className='status '+kind}
async function send(){
  if(busy||stopped||document.hidden)return;
  busy=true;
  const [l,r]=values();
  try{
    const res=await fetch('/api/set?l='+l+'&r='+r,{cache:'no-store'});
    if(!res.ok)throw Error('HTTP '+res.status);
    say('● 已連線｜左 '+l+'% ／右 '+r+'%','ok');
  }catch(e){
    say('● 連線中斷：Pico W 將自動停轉','bad');
    left.value=0;right.value=0;refresh();
  }finally{busy=false}
}
function emergency(){
  stopped=true;left.value=0;right.value=0;refresh();
  say('■ 已送出停止指令','bad');
  fetch('/api/stop',{cache:'no-store',keepalive:true}).catch(()=>{}).finally(()=>{stopped=false});
}
[left,right].forEach(el=>el.addEventListener('input',()=>{refresh();send()}));
document.getElementById('stop').addEventListener('click',emergency);
window.addEventListener('pagehide',emergency);
document.addEventListener('visibilitychange',()=>{if(document.hidden)emergency()});
refresh();
// 固定送心跳，否則 Pico W 看門狗會自動停轉。
setInterval(send,300);
send();
</script>
</body></html>'''


def configure_ap():
    """建立有密碼的無線基地台；同時兼容新舊命名方式。"""
    if len(PASSWORD) < 8:
        raise ValueError("Wi-Fi 密碼至少 8 個字元")
    try:
        ap = network.WLAN(network.WLAN.IF_AP)  # 新版 MicroPython
    except AttributeError:
        ap = network.WLAN(network.AP_IF)         # 舊版 MicroPython
    ap.active(False)
    try:
        # 新版常用 ssid / key；3 表示 WPA2-PSK。
        ap.config(ssid=SSID, key=PASSWORD, security=3)
    except (ValueError, TypeError):
        # 早期韌體使用 essid / password。
        ap.config(essid=SSID, password=PASSWORD, security=3)
    ap.active(True)
    for _ in range(40):
        if ap.active():
            break
        time.sleep_ms(100)
    if not ap.active():
        raise RuntimeError("無法啟動 Pico W 無線基地台")
    return ap


def reply(client, status, data, content_type="text/plain; charset=utf-8"):
    """送出 HTTP 回應；資料先轉為 UTF-8 位元組。"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    head = ("HTTP/1.1 " + status + "\r\n"
            + "Content-Type: " + content_type + "\r\n"
            + "Content-Length: " + str(len(data)) + "\r\n"
            + "Cache-Control: no-store\r\nConnection: close\r\n\r\n")
    client.write(head.encode("utf-8"))
    for i in range(0, len(data), 512):
        client.write(data[i:i+512])


def parse_percent(text):
    """只接受 0 至 100 的純數字，避免無效命令誤動馬達。"""
    if not text or not text.isdigit():
        raise ValueError("invalid percent")
    n = int(text)
    if n > 100:
        raise ValueError("percent exceeds 100")
    return n


def handle(client, page_bytes):
    global last_command_ms
    client.settimeout(0.45)
    raw = client.recv(1024)
    if not raw:
        return
    line = raw.split(b"\r\n", 1)[0].decode("ascii", "ignore")
    fields = line.split(" ")
    if len(fields) < 2 or fields[0] != "GET":
        reply(client, "405 Method Not Allowed", "Only GET supported")
        return
    path = fields[1]
    if path == "/" or path == "/index.html":
        reply(client, "200 OK", page_bytes, "text/html; charset=utf-8")
    elif path.startswith("/api/set?"):
        try:
            params = {}
            for pair in path.split("?", 1)[1].split("&"):
                k, v = pair.split("=", 1)
                params[k] = v
            l = parse_percent(params["l"])
            r = parse_percent(params["r"])
        except (ValueError, KeyError):
            stop_motors()
            reply(client, "400 Bad Request", "速度必須是 0～100")
            return
        set_motors(l, r)
        last_command_ms = time.ticks_ms()
        reply(client, "200 OK", "OK")
    elif path == "/api/stop":
        stop_motors()
        last_command_ms = time.ticks_ms()
        reply(client, "200 OK", "STOP")
    elif path == "/favicon.ico":
        reply(client, "204 No Content", b"")
    else:
        reply(client, "404 Not Found", "Not found")


def main():
    global last_command_ms
    stop_motors()  # 開機先停止，避免突然轉動。
    ap = configure_ap()
    ip = ap.ifconfig()[0]
    page = CONTROL_PAGE.replace("__SSID__", SSID).encode("utf-8")
    print("Wi-Fi 名稱:", SSID)
    print("手機連上 Wi-Fi 後，輸入 http://%s/" % ip)
    server = socket.socket()
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", 80))
        server.listen(2)
        server.settimeout(0.15)
        last_command_ms = time.ticks_ms()
        print("已啟動 HTTP 伺服器；等待手機連線...")
        while True:
            # 重要：即使手機關閉網頁，也會因為逾時而停轉。
            if time.ticks_diff(time.ticks_ms(), last_command_ms) > CONTROL_TIMEOUT_MS:
                if current_left or current_right:
                    stop_motors()
                    print("逾時：兩顆馬達已自動停止")
            client = None
            try:
                client, address = server.accept()
                handle(client, page)
            except OSError as e:
                # socket.timeout 往往是 OSError；屬於輪詢的正常情況。
                pass
            except Exception as e:
                stop_motors()
                print("請求錯誤：", e)
            finally:
                if client is not None:
                    client.close()
    finally:
        stop_motors()
        server.close()
        ap.active(False)


if __name__ == "__main__":
    try:
        main()
    finally:
        stop_motors()
