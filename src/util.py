import os
from enum import Enum, auto

class Message(Enum):
    EXIT            = auto()
    TIMESTEP        = auto()
    DELTA           = auto()
    KEY_PRESS       = auto()
    KEY_RELEASE     = auto()
    ENTITY_CREATED  = auto()
    ENTITY_UPDATE   = auto()
    ENTITY_ANIMATE  = auto()
    LEVEL_CHANGED   = auto()
    FOCUS_ID        = auto()

ROOT_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

def abspath(local_path):
    return os.path.abspath(os.path.join(ROOT_DIRECTORY, local_path.lstrip(os.path.sep)))
