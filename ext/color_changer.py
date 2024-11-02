def main():
    filepath = input("enter filepath: ")
    character = input("enter character: ")
    output = bytearray()
    with open(filepath, "rb") as file:
        count = 0
        for char in file.read():
            if count < 2:
                output.append(char)
                count += 1
            else:
                if char == ord(" "):
                    output.append(ord(" "))
                else:
                    output.append(ord(character))
    filepath2 = input("enter save filepath (or 'o' to overwrite): ")
    if filepath2 == "o":
        with open(filepath, "wb") as file:
            file.write(output)
    else:
        with open(filepath2, "wb") as file:
            file.write(output)

if __name__ == '__main__':
    main()