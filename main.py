import math
import os
import time
import base64
import pickle
import pandas as pd
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc


def get_local_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data', 'message_sheet.csv')

    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        print(f"📊 Loaded {len(df)} rows from {file_path}")
        return df
    else:
        print(f"❌ ERROR: File not found at {file_path}")
        return None

def get_driver():
    options = uc.ChromeOptions()
    
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146 Safari/537.36"
    )
    # Force English to avoid unexpected popups in other languages
    options.add_argument("--lang=en-US")
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-images")
    
    options.page_load_strategy = 'eager'
    
    driver = uc.Chrome(options=options, version_main=146)
    return driver

def is_logged_in(driver: webdriver.Chrome):
    """Kiểm tra xem đã đăng nhập thành công chưa bằng cách tìm kiếm phần tử đặc trưng trên trang feed"""
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'global-nav__me-photo'))
        )
        return True
    except TimeoutException:
        return False

def save_cookies(driver: webdriver.Chrome, file_name: str = "cookies.pkl"):
    """Lưu cookies vào file"""
    with open(file_name, "wb") as cookies_file:
        pickle.dump(driver.get_cookies(), cookies_file)
    print("INFO: COOKIES SAVED!")
    
def get_cookies_from_env():
    """Lấy cookies đã được mã hóa từ biến môi trường và giải mã nó"""
    encoded_cookies = os.getenv("LINKEDIN_COOKIES")
    if not encoded_cookies:
        print("ERROR: LINKEDIN_COOKIES environment variable not found!")
        return None

    try:
        decoded_bytes = base64.b64decode(encoded_cookies)
        cookies = pickle.loads(decoded_bytes)
        print("INFO: Cookies loaded from environment variable!")
        return cookies
    except Exception as e:
        print(f"ERROR: Failed to decode cookies: {e}")
        return None

def handle_cookie_acceptance(driver: webdriver.Chrome):
    """Xử lý chấp nhận cookies nếu có"""
    try:
        # Tăng timeout và thử nhiều loại button text thường gặp
        cookie_xpath = "//button[contains(., 'Accept') or contains(., 'Agree') or contains(., 'Cho phép')]"
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, cookie_xpath))
        )
        accept_btn.click()
        print("INFO: ✅ Cookie banner accepted")
    except:
        print("INFO: ℹ️ No cookie banner detected or already handled")

def human_type(element, text: str):
    import random, time
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))
        
        


def handle_code_verification(driver: webdriver.Chrome):
    """Handle 2FA verification - can read from env var in automated mode"""
    try:
        # Tìm trường nhập mã xác thực
        ID_FIELD = "input__email_verification_pin"
        print("[2FA] ⏳ Waiting up to 30s for 2FA field to appear...")
        
        try:
            verification_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, ID_FIELD))
            )
        except TimeoutException:
            print("[2FA] ℹ️ No 2FA required for this login.")
            return True
        # Tìm nút submit
        ID_FIELD = "email-pin-submit-button"
        CONDITION = EC.element_to_be_clickable((By.ID, ID_FIELD))
        submit_button = WebDriverWait(driver, 10).until(CONDITION)

        # Try to get code from environment variable first (for automated runs)
        code = os.getenv("LINKEDIN_2FA_CODE")
        
        if not code:
            # If running interactively, ask user
            import sys
            if sys.stdin.isatty():
                code = input("[2FA] Verification code required! Check your email and enter the code: ")
            else:
                print("[2FA] ⚠️ Code required but in automated mode and no LINKEDIN_2FA_CODE env var set")
                print("[2FA] Skipping 2FA - may fail if actually required")
                return False
        
        if code:
            verification_field.send_keys(code)
            time.sleep(1)
            submit_button.click()
            time.sleep(2)
            print("[2FA] ✅ Code submitted")
            return True
            
    except TimeoutException:
        print("[2FA] ℹ️ No 2FA verification detected")
        return True
    except Exception as e:
        print(f"[2FA] ⚠️ Error checking for 2FA: {e}")
        driver.save_screenshot("error_login.png")
        return True

def load_session_with_cookies(driver: webdriver.Chrome) -> bool:
    cookies = get_cookies_from_env()
    
    if not cookies:
        print("[SESSION] ❌ No stored cookies found in environment variables")
        return False
    
    print("[SESSION] 🍪 Attempting stealth injection...")
    
    driver.get("https://www.linkedin.com/")
    time.sleep(3)  # Wait for the page to load
    valid_cookies = []
    
    for cookie in cookies:
        cookie.pop('sameSite', None)
        cookie.pop('expiry', None)  # sometimes breaks injection
        try:
            driver.add_cookie(cookie)
            valid_cookies.append(cookie)
        except Exception as e:
            print(f"[SESSION] ⚠️ Failed to add cookie: {e}")
            continue
        
    print(f"[SESSION] ✅ Injected {len(valid_cookies)}/{len(cookies)} cookies successfully")
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(5)  # Wait for the feed to load
    
    # Check if login was successful by looking for profile avatar
    return is_logged_in(driver)

def login(driver: webdriver.Chrome, username: str, password: str):
    driver.get("https://www.linkedin.com/feed")
    time.sleep(3)

    if is_logged_in(driver):
        print("✅ Already logged in — skipping login")
        return True
    """Đăng nhập vào LinkedIn and save session (first time only)"""
    XPATH_USERNAME = '//*[@id="username"]'
    XPATH_PASSWORD = '//*[@id="password"]'
    XPATH_LOGIN_BUTTON = '//button[contains(@class, "btn__primary--large")]'
    
    print("🔐 Starting LinkedIn login process...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)
    
    handle_cookie_acceptance(driver)
    
    driver.save_screenshot("login_page.png")
    
    try: 
        print("⏳ Waiting for login form...")
        username_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, XPATH_USERNAME)))
        username_field.click()
        time.sleep(random.uniform(0.5, 1.5))
        human_type(username_field, username)
        if random.random() < 0.2:
            print("⌨️ Oops, retyping username...")
            username_field.clear()
            time.sleep(random.uniform(1, 2))
            human_type(username_field, username)
        time.sleep(random.uniform(1, 2))
        
        
        password_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, XPATH_PASSWORD)))
        password_field.click()
        time.sleep(random.uniform(0.5, 1.5))
        human_type(password_field, password)
        if random.random() < 0.2:
            print("⌨️ Oops, retyping password...")
            password_field.clear()
            time.sleep(random.uniform(1, 2))
            human_type(password_field, password)
        time.sleep(random.uniform(1, 2))
        
        print("🤔 Reviewing credentials...")
        time.sleep(random.uniform(2, 4))

        print("🚀 Clicking login button...")
        for _ in range(2):
            login_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, XPATH_LOGIN_BUTTON)))
            login_button.click()
            time.sleep(5)
            handle_code_verification(driver)
            time.sleep(5)
            current_url = driver.current_url

            if "checkpoint" in current_url or "challenge" in current_url:
                print("🚨 LinkedIn triggered verification checkpoint!")
                return False
            
            if is_logged_in(driver):
                print("✅ SUCCESS: ĐĂNG NHẬP THÀNH CÔNG!")
                save_cookies(driver)
                 
                print("🧍 Settling after login...")
                time.sleep(random.uniform(10, 20))

                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(random.uniform(5, 10))
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(random.uniform(2, 5))
                return True

            print("[LOGIN] 🔄 Retry clicking login...")
            time.sleep(random.uniform(2, 4))
    except TimeoutException:
      # Use when the page says Welcome Back instead
      try:
        welcome_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.member-profile__details"))
        )

        print("[LOGIN] 🔄 Found an account!")
        welcome_button.click()
        time.sleep(2)

        handle_code_verification(driver)

        time.sleep(5)
        if is_logged_in(driver):
            print("✅ SUCCESS: ĐĂNG NHẬP THÀNH CÔNG!")
            save_cookies(driver)
                
            print("🧍 Settling after login...")
            time.sleep(random.uniform(10, 20))

            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(5, 1))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(2, 5))
            return True

        save_cookies(driver)

        print("INFO: Login successful! Cookies and credentials saved!")
        return True
      except TimeoutException:
          print(f"ERROR: LOGIN NOT SUCCESSFUL")
          return False
      except: # Now this is genuinely unable to login
        print("ERROR: LOGIN FAILED")
        return False
    except Exception as e:
        print(f"❌ ERROR: Login failed: {e}")
        driver.save_screenshot("login_error.png")
        return False



"""# **XPATH và CSS SELECTOR**"""

# XPATH ỨNG VỚI NÚT MESSAGE.
#BUTTON_MESSAGE = "/html/body/div[5]/div[3]/div/div/div[2]/div/div/main/section[1]/div[2]/div[3]/div/div[1]/button"
BUTTON_MESSAGE = "//main//section[1]//a[contains(@href, 'messaging') or contains(., 'Message')]"
SHADOW_DOM_ID = "#interop-outlet"
# CSS_SELECTOR ỨNG VỚI KHUNG TIN NHẮN. (CLASS NAME)
FIELD_MESSAGE = ".msg-form__contenteditable"
# CSS_SELECTOR ỨNG VỚI KHUNG ĐÍNH KÈM TỆP. (CLASS NAME)
FIELD_ATTACHMENT = "input[type='file']"
# CSS_SELECTOR ỨNG VỚI NÚT GỬI TIN NHẮN. (CLASS NAME)
BUTTON_SUBMIT_MESSAGE = ".msg-form__send-button"

"""# **HÀM GỬI TIN NHẮN**"""

def check_datum(datum):
    '''Check the datum to make sure it has the required fields and the attachment file exists (if any). Replace the {{Name}} placeholder in the message with the actual name.'''
    # KIỂM TRA TÊN.
    name = datum["Name"]
    message = datum["Message"]
    attachment = datum["Attachment"]
    if not name or not message:
        print("ERROR: NAME OR MESSAGE NOT FOUND!")
        return None
    # KIỂM TRA TỆP ĐÍNH KÈM.

    abs_path = None
    if attachment and not (isinstance(attachment, float) and math.isnan(attachment)):
        attachment = str(attachment).strip()
        if attachment:
            abs_path = os.path.abspath(os.path.join("attachments", attachment))
            if not os.path.exists(abs_path):
                print("ERROR: ATTACHMENT NOT FOUND!")
                abs_path = None
    final_message = message.replace("{{Name}}", name)

    return {
        "Name": name,
        "Message": final_message,
        "Attachment": abs_path
    }

class MessageSender:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.shadow_host = None
        self.message_field = None
    
    def run(self, datum):
        '''
            Main function to run the message sending process. It will clean up any open message windows, open a new chat, prepare the message field, write the message, attach the file (if any), send the message, and then close the chat window.
        '''
        processed = check_datum(datum)
        if not processed:
            return "ERROR: DATA INVALID"
        
        try:
            self.reset()  # Reset state before starting
            self.cleanup()
            self.open_chat()
            self.prepare_field()
            self.write(processed["Message"])
            if processed["Attachment"]:
                self.attach_file(processed["Attachment"])
            self.send()
            return "SUCCESS"
        except Exception as e:
            print(f"❌ ERROR: Failed to send message to {processed['Name']}: {e}")
            return f"ERROR: {e}"
        finally:
            self.close()
    
    def cleanup(self):
        '''
            Close all open message windows by finding the close button inside each shadow DOM instance. This is important to ensure we start with a clean slate before sending a new message.
        '''
        self.driver.execute_script("""
            document.querySelectorAll("#interop-outlet").forEach(host => {
                if (host.shadowRoot) {
                    const btn = host.shadowRoot.querySelector('svg[data-test-icon="close-small"]');
                    if (btn) btn.closest("button").click();
                }
            });
        """)   
        
    def write(self, message):
        actions = ActionChains(self.driver)

        self.message_field.click()
        time.sleep(1)

        # Clear field properly
        actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        actions.send_keys(Keys.DELETE).perform()
        time.sleep(0.5)

        # Type like a human (but faster than your old version)
        for line in message.split("\n"):
            actions.send_keys(line)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)
        actions.perform()

        time.sleep(2)
        
    def open_chat(self):
        '''
            Open the chat window by clicking the message button. This will allow us to access the shadow DOM where the message field and send button are located.
        '''
        index = 0
        last_error = None
        wait = WebDriverWait(self.driver, 10)
        buttons = self.driver.find_elements(By.XPATH, BUTTON_MESSAGE)
        if not buttons:
            self.driver.save_screenshot("message_button_not_found.png")
            raise Exception("Message button not found on the page")
        for attempt in range(3):
            try:
                message_btn = wait.until(EC.element_to_be_clickable((By.XPATH, BUTTON_MESSAGE)))
                message_btn.click()
                time.sleep(2)  # Wait for shadow DOM to load

                hosts = self.driver.find_elements(By.CSS_SELECTOR, SHADOW_DOM_ID)
                if hosts:
                    print("✅ Chat window opened successfully")
                    self.shadow_host = hosts[0]
                    return
            except Exception as e:
                index += 1
                last_error = e
                print(f"⚠️ Attempt {attempt} failed: {e}")
                self.driver.refresh()
                time.sleep(random.uniform(5, 10))
                index += 1
        self.driver.save_screenshot(f"fail_{index}.png")
        raise Exception(f"Failed to open chat window: {last_error}")
    def prepare_field(self):
        '''
            Get the message field inside the shadow DOM and prepare it for typing. This includes clicking on it to focus and clearing any existing text.
        '''        
        
        # Try to get the message field with retries, as it may take time to load after opening the chat. Give 5 attempts
        for _ in range(10):
            try:
                self.message_field = self.driver.execute_script(
                    f'return arguments[0].shadowRoot.querySelector("{FIELD_MESSAGE}")',
                    self.shadow_host
                )
                
                if self.message_field:
                    self.message_field.click()
                    time.sleep(random.uniform(0.5, 1.0))
                    self.driver.execute_script("arguments[0].innerText = '';", self.message_field)
                    return
            except Exception:
                time.sleep(1)
                
        raise Exception("Message field not found in shadow DOM")
    
    def attach_file(self, path):
        '''
            If there is an attachment, find the file input inside the shadow DOM and send the file path to it. This will upload the file to the message.
        '''
        file_inputs = self.driver.execute_script(
            f'return arguments[0].shadowRoot.querySelectorAll("{FIELD_ATTACHMENT}")',
            self.shadow_host
        )
        
        if len(file_inputs) == 2:
            file_input = file_inputs[1]
            file_input.send_keys(path)
            print(f"📎 File attached: {path}")
            time.sleep(3)

            check_overlay_script = """
              var host = arguments[0];
              if (host && host.shadowRoot) {
                  var btn = host.shadowRoot.querySelector('button.artdeco-button--primary, button.jp-attachment-v2-edit-view__done-button');
                  if (btn && (btn.innerText.includes('Done') || btn.innerText.includes('Add') || btn.innerText.includes('Xong'))) {
                      btn.click();
                      return true;
                    }
                }
                return false;
            """
            
            has_overlay = self.driver.execute_script(check_overlay_script, self.shadow_host)
            if has_overlay:
                print("INFO: Found and clicked the attachment confirmation popup")
                time.sleep(2)
            else:
                print("INFO: No attachment confirmation popup found, proceeding")
        else:
            print("ERROR: Attachment input not found in shadow DOM")
            raise Exception("Attachment input not found")
        
    def send(self):
        self.driver.save_screenshot("before_send.png")
        for attempt in range(15):  # wait longer
            try:
                send_btn = self.driver.execute_script(
                    f'return arguments[0].shadowRoot.querySelector("button{BUTTON_SUBMIT_MESSAGE}")',
                    self.shadow_host
                )

                if send_btn:
                    # Scroll into view (important in headless)
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", send_btn)
                    time.sleep(0.5)

                    # Check if clickable via JS (more reliable than is_enabled)
                    is_disabled = self.driver.execute_script(
                        "return arguments[0].disabled;", send_btn
                    )

                    if not is_disabled:
                        self.driver.execute_script("arguments[0].click();", send_btn)
                        print("✅ Message sent successfully")
                        time.sleep(1)
                        return

                print(f"⏳ Waiting for send button... ({attempt+1})")
                time.sleep(1.5)

            except Exception as e:
                print(f"⚠️ Send attempt error: {e}")
                time.sleep(1)

        raise Exception("Send button not found or disabled")
    
    def close(self):
        '''
            Close the chat window after sending the message to keep the interface clean for the next message.
        '''
        if not self.shadow_host:
            print("INFO: No shadow host found, skipping close")
            return
        try:
            self.driver.execute_script("""
                    var icon = arguments[0].shadowRoot.querySelector("svg[data-test-icon='close-small']");
                    if (!icon) return;

                    var btn = icon.closest("button");
                    if (btn) btn.click();

                    var discard = document.querySelector('button.artdeco-modal__confirm-dialog-btn');
                    if (discard) discard.click();
                """, 
                self.shadow_host
            )
        except:
            pass
    def reset(self):
        '''
            Reset the message sender state by clearing the shadow host and message field references. This can be useful if we encounter an error and want to start fresh for the next message.
        '''
        self.shadow_host = None
        self.message_field = None

def delay():
    r = random.random()

    if r < 0.6:
        # Most of the time: normal delay
        delay = random.uniform(30, 90)
    elif r < 0.85:
        # Sometimes: fast action
        delay = random.uniform(10, 25)
    else:
        # Rarely: long pause (coffee break ☕)
        delay = random.uniform(120, 300)

    print(f"⏳ Sleeping for {round(delay, 1)} seconds")
    time.sleep(delay)

def main():
    # Take a random break at the start to avoid being detected as a bot if running on a schedule
    # time.sleep(random.randint(60, 1800))    
    driver = get_driver()
    driver.set_page_load_timeout(300)  # 5 minutes
    
    sender = MessageSender(driver)
    try:
        # Get data from CSV
        df = get_local_data()
        if df is None:
            print("[CRON] ❌ ERROR: Could not load data file")
            return False
        
        username = os.getenv("LINKEDIN_USERNAME")
        password = os.getenv("LINKEDIN_PASSWORD")
        if not username or not password:
            print("[CRON] ❌ ERROR: LinkedIn credentials not set in environment variables")
            return False
        
        
        print("[CRON] 🔄 Attempting to restore session with cookies...")
        if load_session_with_cookies(driver):
            print("[CRON] ✅ Using cached session - no fresh login needed")
        else:
            # Step 2: If cookies failed, do a fresh login (will update cookies)
            print("[CRON] 🔐 Cookies invalid/missing. Doing fresh login...")
            if not login(driver, username, password):
                print("[CRON] ❌ Failed to login. Exiting...")
                return False
            print("[CRON] ✅ Successfully logged in and cookies saved!")
        
        print("[CRON] ✅ Ready to send connections")
        
        # Get credentials from environment variables

        count = 0 
        message_sent = 0
        limit = 20 # Limit the number of messages sent in one run to avoid detection
        
        for index, row in df.iterrows():
            # Stop if we've reached the daily limit
            if count >= limit:
                print(f"[CRON] ⏹️ Reached daily connection limit ({limit}). Stopping.")
                break
            
            # If status is already SUCCESS, skip
            if row.get("Status") == "SUCCESS":
                print(f"[CRON] ℹ️ Row {index} already marked as SUCCESS, skipping.")
                continue
            print(f"[CRON] 🚀 Processing row {index}: {row['Name']}")
            
            if message_sent >= random.randint(8, 15):
                print("[CRON] ⏸️ Taking a long break to avoid detection...")
                time.sleep(random.randint(600, 1800))
                message_sent = 0
                
            for attempt in range(3):
                try:
                    driver.get(row["Link"])
                    break
                except Exception as e:
                    print(f"⚠️ Page load failed (attempt {attempt+1}): {e}")
                    if attempt == 2:
                        raise
                    time.sleep(random.uniform(5, 15))
            time.sleep(random.uniform(5, 10))
                        
            status = sender.run(row)
            
            # Save the result back to the dataframe
            df.at[index, "Status"] = status
            if "SUCCESS" in status:
                count += 1
                message_sent += 1
            df.to_csv('data/message_sheet.csv', index=False) # Save progress after each message
            if index < len(df) - 1:
                delay() # Random delay between messages
        
        return True  
    except Exception as e:
        print(f"[CRON] ❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        
if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)  # Exit with status code for cron-job.org
