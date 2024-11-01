from itertools import compress

from PIL import Image

GRADIENT = " .-:=+*#%@"

def get_gradient_color(brightness):
    index = round((len(GRADIENT) - 1) * brightness)
    return GRADIENT[index]

def image_load(filepath):
    image = Image.open(filepath)
    return image

def image_pixels(image):
    return image.load()

def image_width(image):
    return image.size[0]

def image_height(image):
    return image.size[1]

def image_get_brightness(pixels, x, y):
    pixel = pixels[x, y]
    brightness = (pixel[0] + pixel[1] + pixel[2]) // 3
    return brightness

def image_to_bytes(image):
    width = image_width(image)
    height = image_height(image)
    pixels = image_pixels(image)
    image_bytes = bytearray(image_len_bytes(image))

    for y in range(height):
        for x in range(width):
            print(get_gradient_color(get_brightness_float(image_get_brightness(pixels, x, y))), end='')
            image_bytes[y * width + x] = image_get_brightness(pixels, x, y)
        print("\n")

    return image_bytes

def get_brightness_float(brightness):
    return brightness / 255

def image_len_bytes(image):
    width = image_width(image)
    height = image_height(image)
    return width * height

def iter_compressed_bytes(image_bytes):
    for byte in image_bytes:
        brightness = get_brightness_float(byte)
        yield get_gradient_color(brightness)

def image_to_compressed_bytes(image):
    len_final = image_len_bytes(image) + 2
    image_bytes = image_to_bytes(image)
    compressed_bytes = bytearray(len_final)
    i = 2
    compressed_bytes[0] = image_width(image)
    compressed_bytes[1] = image_height(image)

    for byte in iter_compressed_bytes(image_bytes):
        compressed_bytes[i] = ord(byte)
        i += 1

    return compressed_bytes

def write_bin_file(filepath, bin_data):
    print(bin_data)
    with open(filepath, "wb") as file:
        file.write(bin_data)

def main():
    filepath = input("Enter file path to convert: ")
    image = image_load(filepath)
    compressed = image_to_compressed_bytes(image)

    print("Converted successfully!")
    filepath = input("Enter file path to save compressed image: ")
    write_bin_file(filepath, compressed)

if __name__ == "__main__":
    main()