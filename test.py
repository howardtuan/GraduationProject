import speech_recognition as sr
from pyray import *


SCREENWIDTH = 800
SCREENHEIGHT = 450

def Interface(text):
    begin_drawing()
    clear_background(RAYWHITE)
    draw_grid(20, 1.0)
    end_mode_3d()
    draw_text(text, 190, 200, 20, VIOLET)
    # draw_text_ex(font, text, (190, 200), 20, 5, VIOLET)
    end_drawing()

if __name__ == '__main__':
    
    
    # Initialize environment
    r = sr.Recognizer()
    
    init_window(SCREENWIDTH, SCREENHEIGHT, "Demo")
    # set_target_fps(60)
    
    
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration = 1)
        print("Say something... ")
        text = ""
        
        while not window_should_close():
            audio = r.listen(source)
            
            # Reconize audio
            try:
                text = r.recognize_google(audio, language='zh-TW', show_all = False) # 
                print(text)
            except:
                pass
            
            Interface(text)
        
        close_window()