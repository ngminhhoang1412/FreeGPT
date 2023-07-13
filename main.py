import os
import time
from flask import Flask, request, jsonify
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from queue import Queue
import threading
from functools import wraps
from selenium.webdriver.support import expected_conditions as EC
import login_gmail_selenium.util as LGS_util
import login_gmail_selenium.common as LGS_common
from selenium.webdriver.support.wait import WebDriverWait

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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            token = auth_header.split(' ')[1]

        if not token or token != os.getenv('TOKEN'):
            return {'message': 'Unauthorized'}, 401

        return f(*args, **kwargs)

    return decorated


@app.route('/api', methods=['POST'])
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
                os.getenv('PROXY'),
                'http',
                proxy_folder)
            driver = profile.retrieve_driver()
            profile.start()
            driver.get(os.getenv('GPT_URL'))
            try:
                driver.find_element(By.XPATH, '//*[@id="__next"]/div[1]/div[1]/div[4]/button[1]').click()
                username = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "username")))
                username.send_keys(os.getenv('USERNAME_GPT', "thamkhang2003@gmail.com"))
                login_btn = driver.find_element(By.CLASS_NAME, 'cf772ffae')
                login_btn.click()
                password = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "password")))
                password.send_keys(os.getenv('PASSWORD', "thamkhang2003"))
                login_btn = driver.find_element(By.CLASS_NAME, 'cf772ffae')
                login_btn.click()
            except Exception:
                pass
            finally:
                time.sleep(10)
                input_field = driver.find_element(By.ID, 'prompt-textarea')
                input_field.send_keys(text)
                input_field.send_keys(Keys.RETURN)
                time.sleep(20)
                try:
                    elements = driver.find_elements(By.CLASS_NAME, 'markdown')
                    last_element = elements[-1].text
                    last_element = last_element.split('JAILBREAK] ')[1]
                finally:
                    driver.quit()

        response = {"message": "Success", "data": last_element}
        return jsonify(response)


if __name__ == '__main__':
    app.run()
