
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
import re
import random
import webbrowser
import requests
import subprocess
import getpass
import threading
import shutil
import ffmpeg

#this is for 0.96 oled screen skip this step
debug_mode = not("arm" in platform.machine())

if not debug_mode:
    try:
        from luna.core.interface.serial import i2c
        from luna.oled.device import ssd1306
        from luna.core.render import canvas
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
speech_lock = threading.Lock()



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


def tell_joke():
    if is_connected():
        try:
            joke = ask_ai("Tell me a short and funny joke.")
            speak(joke)
        except:
            speak("Couldn't fetch an online joke. Let me try a classic one.")
            speak(random.choice(offline_jokes))
    else:
        speak(random.choice(offline_jokes))



#offline jokes we need to add more



def offline_jokes(command):
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
def get_user_name(force_rename = False):
    system_id = f"{getpass.getuser()}@{platform.node()}"



    if os.path.exists("config.txt") and not force_rename:
        with open("config.txt","r") as f:
            saved_id, saved_name = f.read().split("::")
            if saved_id == system_id:
                return saved_name

    speak("Hi! What's your name?")
    text = listen().lower()
    if "my name is" in text:
        name = text.split("my name is")[-1].strip().capitalize()
            
    else:
        name = text.strip().capitalize()

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




#timer

def parse_time_input(time_input):
    time_input = time_input.lower()
    hours = minutes = seconds = 0

    hour_match = re.search(r"(\d+)\s*(hour|hr)", time_input)
    if hour_match:
        hours = int(hour_match.group(1))

    minute_match = re.search(r"(\d+)\s*(minute|min)", time_input)
    if minute_match:
        minutes = int(minute_match.group(1))

    second_match = re.search(r"(\d+)\s*(second|sec)", time_input)
    if second_match:
        seconds = int(second_match.group(1))

    # Support formats like "1:20:30"
    if ":" in time_input:
        try:
            parts = list(map(int, time_input.strip().split(":")))
            if len(parts) == 3:
                hours, minutes, seconds = parts
            elif len(parts) == 2:
                minutes, seconds = parts
            elif len(parts) == 1:
                seconds = parts[0]
        except:
            pass

    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds if total_seconds > 0 else None




def set_timer():
    speak("Please tell me the timer duration.")
    time_input = listen()
    total_seconds = parse_time_input(time_input)

    if total_seconds is None:
        speak("Sorry, I could not understand the timer duration. Please try again with a clear format.")
        return

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    duration_str = []
    if hours:
        duration_str.append(f"{hours} hours")
    if minutes:
        duration_str.append(f"{minutes} minutes")
    if seconds:
        duration_str.append(f"{seconds} seconds")
    speak(f"Timer set for {', '.join(duration_str)}.")

    while total_seconds > 0:
        mins, secs = divmod(total_seconds, 60)
        hrs, mins = divmod(mins, 60)
        time_display = f"{hrs:02}:{mins:02}:{secs:02}"
        show_on_oled(f"Timer: {time_display}")
        time.sleep(1)
        total_seconds -= 1

    # Loop "Time's up!" until the user says stop
    speak("Time's up! Say 'stop' to stop the alarm.")
    while True:
        show_on_oled("Time's Up!")
        speak("Time's up!")
        time.sleep(5)
        command = listen().lower()
        if "stop" in command:
            speak("Timer stopped.")
            break

#Translation

def translate(text, dest_lang='hi'):
    try:
        translated = GoogleTranslator(source='auto', target=dest_lang).translate(text)
        speak(f"Translation: {translated}")

    except:
        speak("Sorry, I couldn't translated that.")

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



def mood_response():
    speak("How are you doing?")
    mood = listen()
    if any(phrase in mood for phrase in["i'm good","i'm fine","i am good","i am fine","great","awesome","doing well","not bad"]):
        speak("Glad to hear that")
    elif any(phrase in mood for phrase in["bad","not good","sad","upset","angry"]):
        speak("I'm sorry to hear that. Would you like me to tell a joke or play your favoruite song?")
        response = listen()
        if "joke" in response:
            joke = offline_jokes("joke")
            speak(joke)
        elif "song" in response:
            speak("Tell me the song name.")
            song = listen()
            threading.Thread(target=play_youtube_audio, args=(song), daemon=True).start()
        else:
            speak("I'm here for you anytime.")






#youtube audio into mp3 player currently not working

TEMP_FOLDER = "temp_songs"

if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

player = None
playlist = []
current_index = 0

def speak(text):
    print("STALK:", text)
    engine.say(text)
    engine.runAndWait()

def schedule_deletion(file_path,delay=3600):
    def delete_file():
        time.sleep(delay)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[Auto Deleted] {file_path}")
    threading.Thread(target=delete_file, daemon = True).start()


def download_song(query):
    search = f"ytsearch1:{query}"
    output_template = os.path.join(TEMP_FOLDER, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'outtmpl': output_template,
        'ffmpeg_location': r'D:\\ffmpeg-7.1.1-essentials_build\\bin',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=True)
            title = info['title']
            mp3_file = os.path.join(TEMP_FOLDER, f"{title}.mp3")
            playlist.append(mp3_file)
            schedule_deletion(mp3_file)
            return mp3_file
    except Exception as e:
        speak("Failed to download the song.")
        print("Download error:", e)
        return None



def play_next_song():
    global current_index, player
    if current_index < len(playlist):
        if player:
            player.stop()
            mp3_file = playlist[current_index]
            player = vlc.MediaPlayer(mp3_file)
            player.play()
            speak(f"Now playing {os.path.basename(mp3_file)}")
        else:
            speak("No more songs in the playlist")


def play_youtube_audio(query):
    global current_index
    mp3_file = download_song(query)
    if mp3_file:
        current_index = len(playlist) - 1
        play_next_song()
        while True:
            command = listen()
            if "pause" in command:
                player.pause()
                speak("Paused.")
            elif "resume" in command or "play" in command:
                player.play()
                speak("Resumed.")
            elif "stop" in command or "close" in command:
                player.stop()
                speak("Stopped playback.")
                break
            elif "next" in command:
                current_index += 1
                if current_index < len(playlist):
                    play_next_song()
                else:
                    speak("No next song available.")
            time.sleep(0.5)




#Handiling commands
    
def handle_command(command):
    global player

    if "what time" in command or "tell time" in command:
        tell_time()

    elif "can you hear me" in command:
        speak("I can hear you!")

    elif "change my name" in command:
        speak("Okay, Let's update your name.")
        user = get_user_name(force_rename=True)

    elif "creator" in command:
        speak("I was made by STALK team.")
        
    elif "how are you" in command or "how do you feel" in command or "i am feeling" in command:
        speak("I am always good")
        mood_response()

    elif "about you" in command or "who are you" in command:
        speak("I am STALK smart Assistant")

    elif "alarm" in command:
        speak("Tell me the alarm time in 24-hour format, like 6:30")
        alarm_input = listen()
        set_alarm(alarm_input)
    
    elif "set timer" in command or "start timer" in command:
        set_timer()

    elif "translate" or "can you translate" in command:
        speak("What should I translate?")
        phrase = listen()
        translate(phrase)

    elif "play" in command or "youtube" in command:
        song = command.replace("play", "").replace("from youtube", "").strip()
        if not song:
            speak("Which song should I play?")
            song = listen()
        if song:
            threading.Thread(target=play_youtube_audio, args=(song,), daemon=True).start()

    elif "pause" in command:
        if player:
            player.pause()
            speak("Playback paused.")
        else:
            speak("No song is currently playing.")

    elif "resume" in command or ("play" in command and "song" in command):
        if player:
            player.play()
            speak("Resuming playback.")
        else:
            speak("No song is paused right now.")

    elif "stop" in command and "song" in command:
        if player:
            player.stop()
            speak("Stopped the music.")
        else:
            speak("No music is playing currently.")

    elif "next" in command:
        play_next_song()

    elif "map" in command or "direction" in command:
        speak("Which location do you want to see?")
        location = listen()
        open_map(location)

    elif "weather" in command:
        speak("Which city do you want the weather for?")
        city = listen()
        get_weather(city)

    elif "connect to wifi" in command:
        connect_to_wifi()

    elif "what's my name" in command or "what is my name" in command:
        user = get_user_name()
        speak(f"Your name is {user}.")

    elif "where am i" in command or "location" in command:
        get_location()

    elif "stop" in command or "exit" in command:
        speak("Goodbye.")
        exit()

    else:
        if is_connected():
            response = ask_ai(command)
        else:
            response = offline_jokes(command)
        speak(response)


#running the stalk

def run_stalk():
    user = get_user_name()
    speak(f"Welcome back, {user}. How you doing? Hope your doing well")


    while True:
        command = listen().lower()
        if "stop" in command and speech_thread and speech_thread.is_alive():
                engine.stop()
                speak("Stopped speaking.")
                continue
        else:
            handle_command(command)




run_stalk()













