import os
import time
from flask import Flask, request, jsonify
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from queue import Queue
import threading
from functools import wraps
import login_gmail_selenium.util as LGS_util
import login_gmail_selenium.common as LGS_common

app = Flask(__name__)
request_queue = Queue()
lock = threading.Lock()


def encode_non_bmp(text):
    encoded_text = ""
    for char in text:
        if ord(char) > 0xFFFF:  # Check if character is outside BMP
            encoded_char = "\\u{" + hex(ord(char))[2:] + "}"  # Encode as UTF-16 surrogate pair
            encoded_text += encoded_char
        else:
            encoded_text += char
    return encoded_text


BEARER_TOKEN = "your_bearer_token"


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            token = auth_header.split(' ')[1]

        if not token or token != BEARER_TOKEN:
            return {'message': 'Unauthorized'}, 401

        return f(*args, **kwargs)

    return decorated


@app.route('/', methods=['POST'])
@token_required
def handle_request():
    with lock:
        request_queue.put(request.json)
        last_element = []
        while not request_queue.empty():
            current_request = request_queue.get()
            text = encode_non_bmp(current_request['text'])
            proxy_folder = os.path.join(LGS_common.constant.PROXY_FOLDER, f'proxy_auth')
            profile = LGS_util.profiles.Profile(
                'private',
                None,
                '77.91.73.18:10002:dOKnD:WycLb',
                'http',
                proxy_folder)
            driver = profile.retrieve_driver()
            profile.start()
            driver.get('https://chat.openai.com/c/7a0d9576-c7de-422f-8220-113629036538')
            time.sleep(10)
            input_field = driver.find_element(By.ID, 'prompt-textarea')
            input_field.send_keys(text)
            input_field.send_keys(Keys.RETURN)
            time.sleep(20)
            elements = driver.find_elements(By.CLASS_NAME, 'markdown')
            last_element = elements[-1].text
            last_element = last_element.split('JAILBREAK] ')[1]
            driver.quit()

        response = {"message": "Success", "data": last_element}
        return jsonify(response)


if __name__ == '__main__':
    app.run()
