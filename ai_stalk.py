
#imported packages


import os
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")
import platform
import speech_recognition as sr
import time
from datetime import datetime
import pyttsx3
import socket
from deep_translator import GoogleTranslator
import yt_dlp
import vlc
import random
import webbrowser
import requests
import subprocess
import getpass
import threading

#this is for 0.96 oled screen skip this step
debug_mode = not("arm" in platform.machine())

if not debug_mode:
    try:
        from luna.core.interface.serial import i2c
        from luna.oled.device import ssd1306
        from luna.core.render import caanvas
        from PIL import ImageFont

        serial = i2c(port=1, address=0x3C)
        oled = ssd1306(serial)
        font = ImageFont.load_default()

        def show_on_oled(text):
            with canvas(oled) as draw:
                draw.text((0,0), text, font=font, fill=255)
        
    except Exception as e:
        print("OLED init failed:",e)
        debug_mode = True

if debug_mode:
    def show_on_oled(text):
        print("[OLED DEBUG]", text)

#our coding starts here

engine = pyttsx3.init()
recognizer = sr.Recognizer()
translator = GoogleTranslator(source='auto', target='hi')
speech_thread = None
stop_speech = False

song_history = []
current_index = -1
player = None

#speaking

def speak(text):
    global speech_thread, stop_speech

    def run_speech():
        global stop_speech
        print("STALK:",text)
        try:
            engine.say(text)
            engine.runAndWait()
        except:
            stop_speech = False

    if speech_thread and speech_thread.is_alive():
        stop_speech = True
        try:
            engine.stop()
        except:    
            pass

        time.sleep(0.2)


    speech_thread = threading.Thread(target=run_speech)
    speech_thread.daemon = True
    speech_thread.start()



#listening

def listen():
    with sr.Microphone() as source:
        print("🎙️ Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio).lower()
        print("you said:",command)
        return command
    except sr.UnknownValueError:
        speak("sorry, I didn't catch that. ") 
        return ""
    except sr.RequestError:
        speak("Network error.")
        return ""


#checks device is connected in network
def is_connected():
    try:
        socket.create_connection(("8.8.8.8",53), timeout = 3)
        return True
    except OSError:
        speak("⚠️ No internet is accessed")
        show_on_oled("No Internert!")
        return False

#offline jokes we need to add more
def offline_answer(command):
    jokes = ["Why did the computer sneeze? It had a virus!",
    "Why was the math book sad? Because it had too many problems",
    "Why don't scientists trust atoms? because they make up everything!",
    "Why did the scarecrow win an award? Because he was oustanding in the field.",
    "What did one wall say to the other? I'll meet you at the corner."
    ]
    
    if "your name" in command:
        return "My name is STALK."
    elif "creator" in command:
        return "I was made by STALK team"
    elif "joke" in command:
        return random.choice(jokes)
    else:
        return "Sorry, I cannot answer that offline"


#asking questions offline ollama AI 
def ask_ai(question):
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
    
            json={
                "model" : "tinyllama",
                "prompt" : question,
                "stream" : False
            }
            
        )
        return response.json()['response'].strip()
    except Exception as e:
        return "Sorry, I couldn't connect to the local AI model"
        
        

#username where stalk use call your name
def get_user_name():
    system_id = f"{getpass.getuser()}@{platform.node()}"



    if os.path.exists("config.txt"):
        with open("config.txt","r") as f:
            saved_id, saved_name = f.read().split("::")
            if saved_id == saved_id:
                return saved_name
    else:
        speak("Hi! What's your name?")
        text = listen().lower()
        if "my name is" in text:
            name = text.split("my name is")[-1].strip().capitalize()
            with open ("config.txt","w") as f:
                f.write(f"{system_id}::{name}")
            speak(f"Nice to meet you, {name}. I'll remember that.")
            return name
        return "Friend"



#Time shows the current time

def tell_time():
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%A, %B %d, %Y")
    speak(f"It is {time_str} on {date_str}.")


#setting alarm


def set_alarm(alarm_time):
    speak(f"Alarm set for {alarm_time}")
    while True:
        now = datetime.now().strftime("%H:%M")
        if now == alarm_time:
            speak("Wake up! This is your alarm.")
            break
        time.sleep(60)


#Translation

def translate(text, dest_lang='hi'):
    try:
        translated = GoogleTranslator(source='auto', target=dest_lang).translate(text)
        speak(f"Translation: {translated}")

    except:
        speak("Sorry, I couldn't translated that.")

#youtube audio into mp3 player currently not working

def play_youtube_audio(query):
    search = f"ytsearch1:{query}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet' : True,
        'noplaylist' : True,
        'outtmpl' : 'song.%(ext)s',
        'postprocessors': [{
            'key' : 'FFmegExtractAudio',
            'preferredcodec' : 'mp3',
            'preferredquality' : '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download = True)
        filename = ydl.prepare_filename(info)

    mp3_file = "song.mp3"
    if os.path.exists(mp3_file):
        player = vlc.MediaPlayer(mp3_file)
        player.play()
        song_history.append(mp3_file)
        player.play()
        song_history.append(mp3_file)
        current_index = len(song_history) - 1
        speak(f"Playing {query} from youtube. Say 'pause', 'resume', or 'stop' to control.")

        while True:
            command = listen().lower()
            if "pause" in command:
                player.pause()
                speak("Paused.")
            elif "play" in command or "resume" in command:
                player.play()
                speak("Playing")
            elif "next" in command:
                speak("Next not available. Only one song in queue.")
            elif "previous" in command and current_index > 0:
                player.stop()
                current_index -= 1
                player = vlc.MediaPlayer(song_history[current_index])
                player.play()
                speak("playing previous song.")
            elif "stop" in command:
                player.stop()
                speak("Stopped playback.")
                break
            time.sleep(1)

        os.remove(mp3_file)    



#Map

def open_map(location):
    url = f"https://www.google.com/maps/place/{location.replace(' ', '+')}"
    speak(f"Showing map for {location}")
    webbrowser.open(url)

#weather

def get_weather(city):
    api_key = "808a2ad833aab55e518aad830e8aaf64"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    if data["cod"] != 200:
        speak("Sorry, I couldn't find the weather for that location")
    else:
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        speak(f"The temperature in {city} is {temp} degrees in Celsius with {desc}.")


#shows your loaction

def get_location():
    try:
        ip_data = requests.get("https://ipinfo.io/json").json()
        city = ip_data.get("city", "unknown city")
        region = ip_data.get("region", "unknown region")
        country = ip_data.get("country", "unknown country")
        location = f"You are in {city}, {region}, {country}"
        speak(location)
    except Exception as e:
        speak("Sorry, I couldn't detect your location")


#conneting Wi-Fi

def connect_to_wifi():
    speak("What is your Wi-Fi name?")
    ssid = listen().strip()
    speak(f"Got it. Now tell me the password {ssid}.")
    password = listen().strip()

    wifi_config = f'''
    country=IN
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1
    network={{
        ssid="{ssid}"
        psk="{password}"
        key_mgmt=WPA-PSK
    }}
    '''

    try:
        with open("/etc/wpa_supplicant/wpa_supplicant.conf","w") as f:
            f.write(wifi_config)
        subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"])
        speak("Wi-Fi settings updated. trying to connect now.")
    except Exception as e:
        speak("Failed to connect to Wi-Fi. Please try again.")


#Handiling commands
    
def handle_command(command):
    if "time" in command:
        tell_time()
    elif "can you hear me" in command:
        speak("I can hear you!")
    elif "change my name" in command:
        speak("Okay, Let's update your name.")
        user = get_user_name(force_rename=True)
    elif "creator" in command:
        speak("I was made by stalk team")
    elif "alarm" in command:
        speak("Tell me the alarm time in 24-hour format, like 6:30")
        alarm_input = listen()
        set_alarm(alarm_input)
    elif "translate" in command:
        speak("What should I translate?")
        phrase = listen()
        translate(phrase)
    elif "play" in command or "youtube" in command:
        song = command.replace("play", "").replace("from youtube", "").strip()
        play_youtube_audio(song)
    elif "map" in command or "direction" in command:
        speak("Which location do you want o see?")
        location = listen()
        open_map(location)
    elif "weather" in command:
        speak("Which city do you want the weather for?")
        city = listen()
        get_weather(city)
    elif "connect to wifi" in command:
        connect_to_wifi()
    elif "where am i" in command or "location" in command:
        get_location()
    elif "stop" in command or "exit" in command:
        speak("Goodbye")
        exit()
    else:
        if is_connected():
            response = ask_ai(command)
        else:
            response = offline_answer(command)
        speak(response)



#running the stalk

def run_stalk():
    user = get_user_name()
    speak(f"Welcome back, {user}. I am STALK, your smart assistant.")


    while True:
        command = listen().lower()
        if "stop" in command:
            if speech_thread and speech_thread.is_alive():
                engine.stop()
                speak("Stopped speaking.")
                continue
        else:
            handle_command(command)




run_stalk()













