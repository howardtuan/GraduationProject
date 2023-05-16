import sys

from pygame import *
from pygame.locals import QUIT

SCREENWIDTH = 800
SCREENHEIGHT = 600 

if __name__ == '__main__':
    
    init()
    user_interface = display.set_mode((SCREENWIDTH, SCREENHEIGHT))
    display.set_caption('測試')
    user_interface.fill((255, 255, 255))

    head_font = font.Font("assets/font/Kaiu.ttf", 60)
    display.update()
    
    idx = 0
    while True:
        idx += 1
        text_surface = head_font.render(str(idx), True, (0, 0, 0))
        user_interface.blit(text_surface, (10, 10))
        for events in event.get():
            if events.type == QUIT:
                quit()
                sys.exit()
        display.update()