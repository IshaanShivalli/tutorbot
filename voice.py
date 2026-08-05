import pyttsx3 as pt3
import speech_recognition as sr

engine = pt3.init()

# Initialize speech recognizer
voice = sr.Recognizer()

with sr.Microphone() as source:
    print("Please Wait...")
    voice.adjust_for_ambient_noise(source, duration=1)
    
    print("Listening... Speak now!")
    audio_data = voice.listen(source)
    
    try:
        text = voice.recognize_google(audio_data)
        
        engine.say(f"You said {text}")
        print(f"You said: {text}")
        
    except sr.UnknownValueError:
        engine.say("I didn't understand what you said.")
        print("Could not understand audio.")
        
    except sr.RequestError as e:
        engine.say("There was a connection error.")
        print(f"Error: {e}")

engine.runAndWait()
