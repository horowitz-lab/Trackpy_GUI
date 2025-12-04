"""
Sizing Utilities Module

Description: Finds various screen, window, and widget sizes for various files
"""
from PySide6.QtWidgets import QApplication

WIN_WIDTH = 0
FIG_WIDTH_PX = 0
FIG_HEIGHT_PX = 0
FIG_WIDTH_IN = 0
FIG_HEIGHT_IN = 0
STANDARD_DPI = 100

def get_screen_dims():
    # app = QApplication()
    qapp = QApplication.instance()
    screen = qapp.primaryScreen()
    screen_width = screen.size().width()
    screen_height = screen.size().height()
    return screen_width, screen_height

def get_main_win_dims():
    screen_width, screen_height = get_screen_dims()
    win_width = screen_width*0.95
    win_height = screen_height*0.95
    # global WIN_WIDTH, WIN_HEIGHT
    global WIN_WIDTH
    WIN_WIDTH = win_width
    # WIN_HEIGHT = win_height
    return win_width, win_height

def get_main_window_geometry():
    screen_width, screen_height = get_screen_dims()
    win_width, win_height = get_main_win_dims()
    x_left = (screen_width/2) - (win_width/2)
    y_up = (screen_height/2) - (win_height/2)
    return x_left, y_up, win_width, win_height

def get_frame_player_dims():
    screen_width, screen_height = get_screen_dims()
    win_width, win_height = get_main_win_dims()
    frame_player_width = win_width*0.3
    frame_player_height = win_height*0.45
    return frame_player_width, frame_player_height

def get_errant_particle_dims():
    screen_width, screen_height = get_screen_dims()
    win_width, win_height = get_main_win_dims()
    photo_size = frame_player_height = win_height*0.2
    return photo_size

def get_start_screen_geometry():
    screen_width, screen_height = get_screen_dims()
    start_screen_width = screen_width*0.4
    start_screen_height = screen_height*0.7
    x_left = (screen_width/2) - (start_screen_width/2)
    y_up = (screen_height/2) - (start_screen_height/2)
    return x_left, y_up, start_screen_width, start_screen_height

def set_figure_sizes():
    "want 4:5 ratio based on width"
    if WIN_WIDTH == 0:
        try:
            get_main_win_dims()
        except Exception:
            # QApplication not running, stick to the fallback
            pass
    global FIG_WIDTH_PX
    global FIG_HEIGHT_PX
    print(WIN_WIDTH)
    fig_width = WIN_WIDTH*0.3
    if fig_width < 500:
        FIG_WIDTH_PX = 500
        FIG_HEIGHT_PX = 400
    else:
        fig_height = fig_width*5/4
        FIG_WIDTH_PX = fig_width
        FIG_HEIGHT_PX = fig_height

    global FIG_WIDTH_IN
    global FIG_HEIGHT_IN
    FIG_WIDTH_IN = FIG_WIDTH_PX/STANDARD_DPI*2
    FIG_HEIGHT_IN = FIG_HEIGHT_PX/STANDARD_DPI*2

