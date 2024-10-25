import os

ROOT_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

def abspath(local_path):
    return os.path.abspath(os.path.join(ROOT_DIRECTORY, local_path))
