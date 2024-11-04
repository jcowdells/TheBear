import os
from enum import Enum, auto

class Message(Enum):
    EXIT                 = auto()
    TIMESTEP             = auto()
    DELTA                = auto()
    KEY_PRESS            = auto()
    KEY_RELEASE          = auto()
    ENTITY_CREATED       = auto()
    ENTITY_UPDATE        = auto()
    ENTITY_ANIMATE       = auto()
    ENTITY_VISIBLE       = auto()
    ENTITY_KILL          = auto()
    MENU_CREATED         = auto()
    MENU_ADD_ITEM        = auto()
    MENU_REMOVE_ITEM     = auto()
    MENU_CHANGE_INDEX    = auto()
    MENU_VISIBLE         = auto()
    MENU_SET_FORMATTING  = auto()
    TEXT_BOX_CREATED     = auto()
    TEXT_BOX_VISIBLE     = auto()
    TEXT_BOX_DELETED     = auto()
    GAME_STATE_CHANGED   = auto()
    LEVEL_CHANGED        = auto()
    FOCUS_ID             = auto()
    COMMAND              = auto()
    INPUT_BEGIN          = auto()
    INPUT_END            = auto()
    UPDATE_SETTING       = auto()
    PROGRESS_BAR_CREATED = auto()
    PROGRESS_BAR_VISIBLE = auto()
    PROGRESS_BAR_UPDATE  = auto()

ROOT_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

def abspath(local_path):
    return os.path.abspath(os.path.join(ROOT_DIRECTORY, local_path.lstrip(os.path.sep)))

def flatten(t):
    for x in t:
        if isinstance(x, tuple):
            yield from flatten(x)
        else:
            yield x

def find_string_size(string):
    lines = string.split("\n")
    max_height = len(lines)
    max_width = 0
    for line in lines:
        len_line = len(line)
        if len_line > max_width:
            max_width = len_line
    return max_width, max_height

def is_valid_colour(colour):
    if len(colour) != 6:
        return False
    chars = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"]
    for char in colour:
        if char not in chars:
            return False
    return True
