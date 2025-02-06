from flask import Flask, request, render_template, send_file
import os
import heapq
from collections import Counter
import ast
import tempfile

app = Flask(__name__)

class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq

def get_temp_path(filename):
    return os.path.join(tempfile.gettempdir(), filename)

def build_frequency_dict(text):
    return Counter(text)

def build_huffman_tree(frequency):
    priority_queue = [HuffmanNode(char, freq) for char, freq in frequency.items()]
    heapq.heapify(priority_queue)

    while len(priority_queue) > 1:
        left = heapq.heappop(priority_queue)
        right = heapq.heappop(priority_queue)
        merged = HuffmanNode(None, left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(priority_queue, merged)

    return priority_queue[0]

def build_huffman_codes(node, code="", codes=None):
    if codes is None:
        codes = {}
    
    if node:
        if node.char is not None:
            codes[node.char] = code
        build_huffman_codes(node.left, code + "0", codes)
        build_huffman_codes(node.right, code + "1", codes)
    return codes

def encode_text(text, huffman_codes):
    return ''.join(huffman_codes[char] for char in text)

def pad_encoded_text(encoded_text):
    extra_padding = 8 - len(encoded_text) % 8
    encoded_text = f"{encoded_text}{'0' * extra_padding}"
    padded_info = f"{extra_padding:08b}"
    return padded_info + encoded_text

def get_byte_array(padded_encoded_text):
    if len(padded_encoded_text) % 8 != 0:
        raise ValueError("Encoded text length is not a multiple of 8.")

    byte_array = bytearray()
    for i in range(0, len(padded_encoded_text), 8):
        byte = padded_encoded_text[i:i+8]
        byte_array.append(int(byte, 2))
    return byte_array

def remove_padding(padded_encoded_text):
    padding_info = padded_encoded_text[:8]
    extra_padding = int(padding_info, 2)
    encoded_text = padded_encoded_text[8:]
    return encoded_text[:-extra_padding]

def decode_text(encoded_text, huffman_codes):
    current_code = ""
    decoded_text = ""
    reverse_huffman_codes = {code: char for char, code in huffman_codes.items()}

    for bit in encoded_text:
        current_code += bit
        if current_code in reverse_huffman_codes:
            character = reverse_huffman_codes[current_code]
            decoded_text += character
            current_code = ""
    
    return decoded_text

def compress_file(input_path, output_path):
    with open(input_path, 'r') as file:
        text = file.read()

    frequency = build_frequency_dict(text)
    huffman_tree = build_huffman_tree(frequency)
    huffman_codes = build_huffman_codes(huffman_tree)

    encoded_text = encode_text(text, huffman_codes)
    padded_encoded_text = pad_encoded_text(encoded_text)
    byte_array = get_byte_array(padded_encoded_text)

    with open(output_path, 'wb') as output:
        huffman_codes_str = str(huffman_codes).encode('utf-8')
        output.write(len(huffman_codes_str).to_bytes(4, 'big'))
        output.write(huffman_codes_str)
        output.write(byte_array)

def decompress_file(input_path, output_path):
    with open(input_path, 'rb') as file:
        codes_length = int.from_bytes(file.read(4), 'big')
        huffman_codes_str = file.read(codes_length).decode('utf-8')
        huffman_codes = ast.literal_eval(huffman_codes_str)

        bit_string = ""
        byte = file.read(1)
        while byte:
            byte = ord(byte)
            bits = bin(byte)[2:].rjust(8, '0')
            bit_string += bits
            byte = file.read(1)

        encoded_text = remove_padding(bit_string)
        decompressed_text = decode_text(encoded_text, huffman_codes)

        with open(output_path, 'w') as output_file:
            output_file.write(decompressed_text)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return "No file part", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    
    input_path = get_temp_path(file.filename)
    output_path = get_temp_path(file.filename + '.huff')
    
    try:
        file.save(input_path)
        compress_file(input_path, output_path)
        
        response = send_file(output_path, as_attachment=True)
        
        # Clean up temp files after sending
        os.remove(input_path)
        os.remove(output_path)
        
        return response
    except Exception as e:
        # Clean up files in case of error
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        return str(e), 500

@app.route('/decompress', methods=['POST'])
def decompress():
    if 'file' not in request.files:
        return "No file part", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    
    input_path = get_temp_path(file.filename)
    output_path = get_temp_path(file.filename.replace('.huff', '.txt'))
    
    try:
        file.save(input_path)
        decompress_file(input_path, output_path)
        
        response = send_file(output_path, as_attachment=True)
        
        # Clean up temp files after sending
        os.remove(input_path)
        os.remove(output_path)
        
        return response
    except Exception as e:
        # Clean up files in case of error
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        return str(e), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)