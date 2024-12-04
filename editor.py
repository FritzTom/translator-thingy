
import os

DEBUG = False

def ex_import_texts(values, titles = None, ignore_titles = False):
    while True:
        inp = input("\x1b[42mi\x1b[0mmport, \x1b[42me\x1b[0mxport, \x1b[42mq\x1b[0muit ?: ")
        if len(inp) < 1: continue
        inp = inp.lower()
        inp = inp[0]
        if not inp in "qie":
            print("Invalid input.")
            continue
        break
    if inp == "q": return None
    if inp == "e":
        ng = 0
        data = ""
        for i in range(len(values)):
            data += f"{i}: "
            for j in range(len(values[i])):
                if titles and titles[i][j]:
                    name = titles[i][j]
                else:
                    name = ng
                    ng += 1
                data += f";N;{name};O;"
                data += f"{values[i][j].decode('shift-jis', errors='ignore')};A;"
            if data.endswith(";A;"):
                data = data[:-3]
            data += ";B;\n"
        data = data[:-4]
        with open("exported", "w", encoding="utf-8") as f:
            f.write(data)
        return None
    ov = values
    with open("exported", "r", encoding="utf-8") as f:
        data = f.read()
    data = data.split(";B;\n")
    values = []
    for i in range(len(data)):
        if i != int(data[i].split(": ", 1)[0]):
            print("Improperly ordered file.\nAborting!")
            exit(1)
        values.append([])
        current_values = data[i].split(": ", 1)[1]
        if len(current_values) > 0:
            current_values = current_values.split(";A;")
        else:
            current_values = []
        for j in range(len(current_values)):
            value = current_values[j]
            if not ignore_titles:
                if value.startswith(";N;"):
                    if not (titles and len(titles) > i and len(titles[i]) > j):
                        print("Too many names.\nAborting!")
                        exit(1)
                    if value[3:].split(";O;")[0] != titles[i][j]:
                        print("Invalid name.\nAborting!")
                        exit(1)
                elif titles and len(titles) > i and len(titles[i]) > j:
                    print("Missing name.\nAborting!")
                    exit(1)
            if value.startswith(";N;"):
                value = value.split(";O;", 1)[1]
            values[i].append(value.encode("shift-jis"))
        if i >= len(ov):
            print("Too many entries.\nAborting!")
            exit(1)
        if len(values[i]) != len(ov[i]):
            print("Invalid sub entry amount.\nAborting!")
            exit(1)
    if len(values) != len(ov):
        print("Invalid length.\nAborting!")
        exit(1)
    return values

def check_file(content):
    file_length = int.from_bytes(content[0x8:0x8 + 3], "big")
    if file_length != len(content):
        print("Invalid file length!")
        return False

    scenario_data_offset = int.from_bytes(content[0x17:0x17 + 2], "big")

    number_offsets = content[0x1c:0x1c + 2]
    number_offsets = int.from_bytes(number_offsets, "big")

    string_offsets_raw = content[0x1e:scenario_data_offset]
    if len(string_offsets_raw) % 3 != 0:
        print("Offset misalignment!")
        return False

    offsets = []
    for i in range(len(string_offsets_raw) // 3):
        offsets.append(int.from_bytes(string_offsets_raw[i * 3:(i + 1) * 3], "big"))

    if len(offsets) != number_offsets:
        print("Incorrect number of offsets!")
        return False

    return True

def get_offsets(content):

    scenario_data_offset = int.from_bytes(content[0x17:0x17 + 2], "big")

    string_offsets_raw = content[0x1e:scenario_data_offset]
    if len(string_offsets_raw) % 3 != 0:
        print("Offset misalignment!")
        return False

    offsets = []
    for i in range(len(string_offsets_raw) // 3):
        offsets.append(int.from_bytes(string_offsets_raw[i * 3:(i + 1) * 3], "big"))

    return offsets

def set_offsets(content, offsets):

    offsets_raw = b""
    for i in offsets:
        offsets_raw = offsets_raw + i.to_bytes(3, "big")

    scenario_data_offset = int.from_bytes(content[0x17:0x17 + 2], "big")

    if len(offsets_raw) != (scenario_data_offset - 0x1e):
        print("Warning: Changing amount of offsets.")

    content = content[:0x1e] + offsets_raw + content[scenario_data_offset:]

    return content

def create_offsets(offsets):

    offsets_raw = b""
    for i in offsets:
        offsets_raw = offsets_raw + i.to_bytes(3, "big")

    return offsets_raw

def fix_file_length(content):
    file_length = len(content).to_bytes(3, "big")
    content = content[:0x8] + file_length + content[0x8 + 3:]
    return content

def fix_headers(content):
    fix_file_length(content)
    data = extract_data(content)
    data = [i for i in data if i[0][1][0] == 0x33]
    offsets = [i[0][0] - 2 for i in data]
    content = set_offsets(content, offsets)
    return content

def get_header(content):
    beginning_data = int.from_bytes(content[0x17:0x17 + 2], "big")  # start at scenario data
    return content[:beginning_data]

def extract_data(content):
    beginning_data = int.from_bytes(content[0x17:0x17 + 2], "big") # start at scenario data with parsing
    return parse_data(content[beginning_data:], beginning_data)

def parse_data(data, offset_offset):
    data = bytearray(data)
    values = []
    state = [data, 0]
    while state[1] < len(state[0]):
        if peak(state, 2) == b"\x0a\x0d":
            consume(state, 2)
            packet = []
            while True:
                current = b""
                offset = get_index(state, offset_offset)
                while not ((peak(state) == b"\xff") or (peak(state, 2) == b"\x0a\x0d")):
                    current = current + consume(state)
                packet.append((offset, current))
                if peak(state, 1) == b"\xff":
                    consume(state)
                    if state[1] >= len(state[0]):
                        packet.append((get_index(state, offset_offset), b""))
                        break
                else:
                    break
            values.append(packet)
        else:
            print("Encountered unknown data!")
            skip(state)
    print(f"Found {len(values)} data segments total.")
    return values

def create_data(values):
    data = bytearray()
    for i in values:
        data.extend(b"\x0a\x0d")
        data.extend(i[0][1])
        for j in i[1:]:
            data.append(0xff)
            o = j[0]
            v = j[1]
            data.extend(v)
    data.append(255)
    return bytes(data)

def create_content(offsets, values):
    data = create_data(values)
    header_size = 30
    content = bytearray()
    content.extend([0x48, 0x69, 0x6D, 0x61, 0x75, 0x72, 0x69, 0x00])
    content.extend((len(data) + len(offsets) * 3 + header_size).to_bytes(3, "big"))
    content.extend([0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x1E, 0xFF, 0x00, 0x54, 0xFF, 0x00])
    content.extend((len(offsets) * 3 + header_size).to_bytes(2, "big"))
    content.extend([0x05, 0x10, 0xFF])
    content.extend(len(offsets).to_bytes(2, "big"))

    content.extend(create_offsets(offsets))

    content.extend(data)

    return bytes(content)

def offset_offsets(values, offset):
    new_values = []
    for i in values:
        new_values.append([])
        for j in i:
            new_values[-1].append((j[0] + offset, j[1]))
    return new_values

def normalize_offsets(values, offset):
    data = create_data(values)
    values = parse_data(data, offset)
    return values

def create_content_without_offsets(values):
    header_size = 30
    strings = [i for i in values if i[0][1][0] == 0x33]
    values = normalize_offsets(values, len(strings) * 3 + header_size)
    offsets = [i[0][0] - 2 for i in strings]
    return create_content(offsets, values)

def peak(state, amount = 1): return state[0][state[1]:state[1] + amount]
def consume(state, amount = 1):
    state[1] = state[1] + amount
    return state[0][state[1] - amount:state[1]]
def get_index(state, beginning_data): return state[1] + beginning_data
def skip(state):
    data = state[0]
    i = state[1]
    while (i < len(data)) and peak(state, 2) != b"\x0a\x0d": i += 1
    state[1] = i

def main(prefix = None):
    while True:
        file_path = "701.him"
        #file_path = input("Enter the path to your binary file: ")  # Prompt for file path
        if prefix:
            file_path = os.path.join(prefix, file_path)
        if not os.path.isfile(file_path):
            print("The specified file does not exist, please check the path and try again.")
            continue
        break

    with open(file_path, "rb") as f:
        content = f.read()

    # Code here


    print("Quitting.")

    with open(file_path, "wb") as f:
        f.write(content)

    print("Changes saved to sub file.")


def filter_data(data):
    filtered_data = []
    for item in data:
        if len(item) > 0 and len(item[0]) > 1:
            if item[0][1][0] not in [0x36, 0x32]:
                filtered_data.append(item)
    return filtered_data

def extract_strings(data):
    strings = [item for item in data if len(item) > 0 and len(item[0]) > 1 and item[0][1][0] == 0x33]
    new_strings = []

    for current in strings:
        if len(current) < 2:
            continue
        value = current[-1][1] if len(current[-1]) > 1 else current[-2][1]
        if b"\x01" in value and b"\x00" in value:
            value = value[value.index(b"\x01", 1) + 3:]
            value = value[:value.index(b"\x00")]
            new_strings.append(value)

    return new_strings

def update_data_with_new_strings(data, new_strings):
    for i in range(len(data)):
        if data[i][0][1][0] == 0x33:
            if not new_strings:
                break
            new_string = new_strings.pop(0)[0]
            current = data[i]
            if len(current) < 2:
                continue
            value = current[-1][1] if len(current[-1]) > 1 else current[-2][1]
            index = -1 if len(current[-1][1]) > 0 else -2
            
            if b"\x01" in value and b"\x00" in value:
                start = value.index(b"\x01", 1) + 3
                end = value.index(b"\x00", start) + start
                
                value = current[index][1]
                value = value[:start] + new_string + value[end:]
                data[i][index] = (0, value)
    return data


if __name__ == "__main__":
    main()