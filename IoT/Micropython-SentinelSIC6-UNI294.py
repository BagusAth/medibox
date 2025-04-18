from machine import Pin, ADC, PWM, SoftI2C
import ssd1306
import dht
import time
import network
import requests

# ========= Hardware Configuration ========= #
led_pins = [2, 4, 5, 18, 19]
leds = [Pin(pin, Pin.OUT) for pin in led_pins]

pir = Pin(15, Pin.IN)
last_pir_state = False
pir_debounce_time = time.ticks_ms()

ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
LDR_THRESHOLD = 1000

dht_sensor = dht.DHT11(Pin(13))

buzzer = PWM(Pin(23), freq=1000, duty=0)

button_yes = Pin(25, Pin.IN, Pin.PULL_UP)
button_no = Pin(26, Pin.IN, Pin.PULL_UP)

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ========= WiFi and Server Configuration ========= #
FLASK_SERVER = "http://192.168.43.229:8080/send_data"
WIFI_SSID = "Redmi Note 9"
WIFI_PASSWORD = "Brama123"

wifi_client = network.WLAN(network.STA_IF)

def connect_wifi():
    wifi_client.active(True)
    if not wifi_client.isconnected():
        print("🔄 Connecting to WiFi...")
        wifi_client.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 10
        while not wifi_client.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    if wifi_client.isconnected():
        print("✅ WiFi Connected! IP:", wifi_client.ifconfig()[0])
    else:
        print("❌ Failed to connect to WiFi")

connect_wifi()

# ========= Status Variables ========= #
obat_diminum = [False] * 5
kotak_terbuka = False
kotak_last_state = False
jumlah_obat_diminum = 0  # Declare globally

# ========= Functions ========= #
def baca_dht():
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        return temperature, humidity
    except:
        return None, None

def tampilkan_oled(pesan1, pesan2=""):
    oled.fill(0)
    oled.text(pesan1, 0, 10)
    if pesan2:
        oled.text(pesan2, 0, 30)
    oled.show()

def aktifkan_buzzer(ms=1000):
    buzzer.duty(512)
    time.sleep_ms(ms)
    buzzer.duty(0)

def deteksi_kotak_terbuka():
    return ldr.read() > LDR_THRESHOLD

def deteksi_gerakan():
    global pir_debounce_time
    if pir.value() and time.ticks_diff(time.ticks_ms(), pir_debounce_time) > 1000:
        pir_debounce_time = time.ticks_ms()
        return True
    return False

def cek_button_yes():
    debounce_time = 300  # ms
    if not button_yes.value():
        start = time.ticks_ms()
        while not button_yes.value():
            if time.ticks_diff(time.ticks_ms(), start) > debounce_time:
                return True
    return False

def kirim_data_ke_server(temperature, humidity, motion, ldr_value):
    global jumlah_obat_diminum  # Declare as global here
    if not wifi_client.isconnected():
        print("⚠️ WiFi disconnected, trying to reconnect...")
        connect_wifi()

    try:
        data = {
            "temperature": temperature,
            "humidity": humidity,
            "motion": motion,
            "ldr_value": ldr_value,
            "medicine_taken": jumlah_obat_diminum > 0  # Include the global variable
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(FLASK_SERVER, json=data, headers=headers)
        print("📤 Data sent! Response:", response.status_code)
        print("Response content:", response.text)  # Debug response
        response.close()
        
        # Reset counter after successfully sending data
        if response.status_code == 200:
            jumlah_obat_diminum = 0
    except Exception as e:
        print("❌ Failed to send data:", e)

# ========= Main Loop ========= #
def loop():
    global kotak_terbuka, kotak_last_state, jumlah_obat_diminum

    while True:
        temperature, humidity = baca_dht()
        kotak_terbuka = deteksi_kotak_terbuka()
        gerakan_terdeteksi = deteksi_gerakan()
        ldr_value = ldr.read()

        print("LDR Intensity:", ldr_value)

        if temperature is not None and humidity is not None:
            tampilkan_oled("Temp: {}C".format(temperature), "LDR: {}".format(ldr_value))
            kirim_data_ke_server(temperature, humidity, gerakan_terdeteksi, ldr_value)

        if kotak_terbuka and not kotak_last_state:
            print("Box Opened")
            for i in range(5):
                if not obat_diminum[i]:
                    leds[i].value(1)
            aktifkan_buzzer(300)

        elif not kotak_terbuka and kotak_last_state:
            print("Box Closed")
            for led in leds:
                led.value(0)
            tampilkan_oled("Have you", "taken your medicine?")
            timeout = time.ticks_ms() + 10000
            while time.ticks_ms() < timeout:
                if cek_button_yes():
                    print("Medicine confirmed taken")
                    for i in range(5):
                        if not obat_diminum[i]:
                            obat_diminum[i] = True
                            leds[i].value(0)
                            break
                    jumlah_obat_diminum += 1
                    print("jumlah_obat_diminum:", jumlah_obat_diminum)
                    tampilkan_oled("Thank you!")
                    aktifkan_buzzer(200)
                    time.sleep(1)
                    break
                elif not button_no.value():
                    print("Medicine not taken")
                    tampilkan_oled("Don't forget to take it!")
                    aktifkan_buzzer(500)
                    break

        tampilkan_oled("Medicine Taken:", str(jumlah_obat_diminum))
        kotak_last_state = kotak_terbuka
        time.sleep(1)

# ========= Start ========= #
tampilkan_oled("Medicine Box", "Ready for use")
time.sleep(2)
loop()

