from utils import get_base_dir, get_threads_account, load_driver

import time
import logging

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException


# ============================================================================================
# CONFIGURATION
# ============================================================================================
BASE_DIR = get_base_dir()
THREAD_USERNAME, THREAD_PASSWORD = get_threads_account()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ============================================================================================
# MAIN FUNCTION
# ============================================================================================
def scrape_posts(driver, max_scrolls=10):
    """
    Hàm này thực hiện cuộn trang để tải tất cả bài viết và sau đó bóc tách dữ liệu.
    """
    print("Bắt đầu quá trình lướt trang để tải dữ liệu...")
    
    # --- PHẦN 1: LƯỚT VÔ CỰC (Không đổi) ---
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Đã lướt đến cuối trang.")
            break
        last_height = new_height
        scroll_count += 1
        print(f"Đã lướt lần thứ {scroll_count}...")

    print("Quá trình lướt trang hoàn tất. Bắt đầu thu thập dữ liệu...")

    # --- PHẦN 2: BÓC TÁCH DỮ LIỆU ---
    all_posts_data = []
    
    # [SELECTOR MỚI] Dựa trên việc mỗi post phải có link user và thẻ time. Rất ổn định.
    post_elements = driver.find_elements(By.XPATH, "//div[.//a[contains(@href, '/@')] and .//time[@datetime]]")
    
    print(f"Tìm thấy tổng cộng {len(post_elements)} bài viết.")

    for i, post in enumerate(post_elements):
        post_data = {}
        try:
            # 1. Lấy Tên User và Link Profile
            # Vẫn dùng selector cũ vì nó khá ổn định
            user_element = post.find_element(By.XPATH, ".//a[contains(@href, '/@')]")
            # Lấy username từ span trong cùng để đảm bảo sạch
            post_data['username'] = user_element.find_element(By.XPATH, ".//span/span").text
            post_data['profile_url'] = user_element.get_attribute('href')

            # 2. Lấy Nội dung bài viết
            # [SELECTOR MỚI] Tìm span có dir='auto' không nằm trong link <a>
            content_element = post.find_element(By.XPATH, ".//span[@dir='auto' and not(ancestor::a)]/span")
            post_data['content'] = content_element.text

            # 3. Lấy Thời gian đăng bài và Link bài viết
            time_element = post.find_element(By.TAG_NAME, 'time')
            post_data['post_time_text'] = time_element.text
            post_data['post_datetime'] = time_element.get_attribute('datetime')
            post_data['post_url'] = time_element.find_element(By.XPATH, "./parent::a").get_attribute('href')
            
            # 4. Lấy Likes, Replies, Reposts, Shares một cách linh hoạt
            # [CÁCH TIẾP CẬN MỚI] Dùng vòng lặp và aria-label
            actions = {
                'likes': 'Thích',
                'replies': 'Trả lời',
                'reposts': 'Đăng lại',
                'shares': 'Chia sẻ'
            }
            
            for key, label in actions.items():
                try:
                    # Tìm div nút bấm dựa vào aria-label của svg bên trong
                    button_div = post.find_element(By.XPATH, f".//div[@role='button' and .//svg[@aria-label='{label}']]")
                    # Tìm số liệu bên trong nút đó
                    number_span = button_div.find_element(By.XPATH, ".//span[contains(@class, 'x1o0tod')]")
                    post_data[key] = number_span.text
                except NoSuchElementException:
                    # Nếu không tìm thấy (ví dụ bài viết 0 like), gán giá trị 0
                    post_data[key] = 0
            
            all_posts_data.append(post_data)

        except Exception as e:
            logging.warning(f"Bỏ qua bài viết #{i+1} do lỗi: {e.__class__.__name__} - {e}")
            
    return all_posts_data

# ============================================================================================
# PIPELINE
# ============================================================================================
def pipeline(USERNAME, PASSWORD, keywords):
    keywords = ["AI Engineer Job"]

    driver = load_driver()
    if driver is None:
        raise

    # -----------------------------------------------------------
    # Log in
    try:
        driver.get("https://www.threads.com/login")
        time.sleep(2)

        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Username, phone or email']"))
        )
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='Password']"))
        )
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(., 'Log in')]"))
        )

        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        login_button.click()

        time.sleep(10)
        
    except Exception as e:
        logging.error(f"Error during login: {e}")
        driver.quit()
        return

    # ------------------------------------------------------------
    # Search for keywords
    try:
        # -------------------------------------------------------------
        # Ignore pop-ups if they appear
        try:
            # Chờ tối đa 10 giây cho nút 'Not Now' hoặc 'Lúc khác'
            not_now_button_save_info = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and (text()='Not Now' or text()='Lúc khác')]"))
            )
            not_now_button_save_info.click()
        except Exception as e:
            print(f"Error: {e}")

        try:
            # Chờ tối đa 10 giây cho nút 'Not Now' hoặc 'Lúc khác'
            not_now_button_notifications = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now' or text()='Lúc khác']"))
            )
            not_now_button_notifications.click()
            print("Đã bỏ qua pop-up 'Bật thông báo'.")
        except Exception as e:
            print(f"Error: {e}")

        # -------------------------------------------------------------
        # Start searching for each keyword
        

        for keyword in keywords:
            print(f"Đang tìm kiếm với từ khóa: '{keyword}'")
            posts = []

            # ------------------------------------------------------------
            # Search keyword
            driver.get("https://www.threads.com/")
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="/search"]'))
            )
            search_button.click()
            search_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search'], input[placeholder='Tìm kiếm']"))
            )
            search_input.clear()  
            search_input.send_keys(keyword)
            search_input.send_keys(Keys.RETURN)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[.//a[contains(@href, '/@')] and .//time[@datetime]]"))
            )

            # ------------------------------------------------------------
            # Scrape posts

            extracted_data = scrape_posts(driver, max_scrolls=20)
            if extracted_data:
                import json
                print(json.dumps(extracted_data[0], indent=2, ensure_ascii=False))

            time.sleep(600)


    except Exception as e:
        logging.error(f"Error during searching: {e}")
    






    


    




pipeline(
    USERNAME=THREAD_USERNAME,
    PASSWORD=THREAD_PASSWORD,
    keywords=["AI Engineer Job"]
)




