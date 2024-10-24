from src.render import ConsoleGUI, Texture
import cProfile

def main():
    console = ConsoleGUI(480, 360, 100, 100)
    console.begin()

if __name__ == "__main__":
    #image = Image("res/legendmixer.bin")
    cProfile.run("main()")
