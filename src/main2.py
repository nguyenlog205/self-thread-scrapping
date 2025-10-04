# ============================================================================================
# FILE: src/main.py (PHIÊN BẢN CUỐI CÙNG - DỰA TRÊN PHÂN TÍCH HTML CHÍNH XÁC)
# Tác giả: Gemini & User
# Mô tả: Script này được viết lại để tập trung vào sự ổn định, sử dụng thuộc tính
# 'data-pressable-container' làm "mỏ neo" và logic chờ đợi thông minh để tránh lỗi.
# ============================================================================================

from utils import get_threads_account, load_driver
import time
import logging
import json
import csv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from selenium.webdriver.remote.remote_connection import LOGGER as seleniumLogger
seleniumLogger.setLevel(logging.WARNING)


# ============================================================================================
# CÁC HÀM LƯU FILE
# ============================================================================================

def save_to_json(data_list, filename):
    """Lưu danh sách dữ liệu vào file JSON."""
    if not data_list:
        logging.warning("Không có dữ liệu để lưu vào file JSON.")
        return
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu thành công {len(data_list)} mục vào file: {filename}")
    except IOError as e:
        logging.error(f"❌ Đã xảy ra lỗi khi ghi file JSON: {e}")

def save_to_csv(data_list, filename):
    """Lưu danh sách dữ liệu vào file CSV."""
    if not data_list:
        logging.warning("Không có dữ liệu để lưu vào file CSV.")
        return
    try:
        headers = sorted(list(set(key for item in data_list for key in item.keys())))
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data_list)
        print(f"✅ Đã lưu thành công {len(data_list)} mục vào file: {filename}")
    except IOError as e:
        logging.error(f"❌ Đã xảy ra lỗi khi ghi file CSV: {e}")

# ============================================================================================
# HÀM CRAWL DỮ LIỆU CHÍNH
# ============================================================================================

def scrape_posts(driver, max_scrolls=10):
    """
    Hàm này cuộn trang và bóc tách dữ liệu từ các container bài viết.
    """
    print("\nBắt đầu quá trình lướt trang để tải dữ liệu...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Đã lướt đến cuối trang.")
            break
        last_height = new_height
        scroll_count += 1
        print(f"Đã lướt lần thứ {scroll_count}...")

    print("Quá trình lướt trang hoàn tất. Bắt đầu thu thập dữ liệu...")
    all_posts_data = []
    
    # [LOGIC MỚI] Dùng "mỏ neo" bạn đã tìm ra
    post_containers = driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']")
    print(f"Tìm thấy tổng cộng {len(post_containers)} bài viết tiềm năng.")

    for container in post_containers:
        post_data = {
            'username': None, 'profile_url': None, 'content': '',
            'post_time_text': None, 'post_datetime': None, 'post_url': None,
            'likes': '0', 'replies': '0'
        }
        
        try:
            # Lấy URL bài viết làm định danh, nếu không có thì đây không phải bài viết
            time_link_element = container.find_element(By.XPATH, ".//a[.//time[@datetime]]")
            time_element = time_link_element.find_element(By.TAG_NAME, 'time')
            post_data['post_url'] = time_link_element.get_attribute('href')
            post_data['post_time_text'] = time_element.text.strip()
            post_data['post_datetime'] = time_element.get_attribute('datetime')

            # Lấy các thông tin còn lại một cách an toàn
            try:
                user_element = container.find_element(By.XPATH, ".//a[contains(@href, '/@')]")
                post_data['username'] = user_element.text.strip()
                post_data['profile_url'] = user_element.get_attribute('href')
            except NoSuchElementException: pass

            try:
                content_elements = container.find_elements(By.XPATH, ".//div[contains(@class, 'x1a6qonq')]/span")
                content_lines = [el.text.strip() for el in content_elements if el.text]
                post_data['content'] = "\n".join(content_lines).replace('Translate', '').strip()
            except NoSuchElementException: pass
            
            try:
                actions = {'likes': ('Thích', 'Like'), 'replies': ('Trả lời', 'Reply')}
                for key, (label_vi, label_en) in actions.items():
                    try:
                        xpath = f".//svg[@aria-label='{label_vi}' or @aria-label='{label_en}']/ancestor::div[@role='button']//span[string-length(text()) > 0]"
                        number_span = container.find_element(By.XPATH, xpath)
                        post_data[key] = number_span.text.strip()
                    except NoSuchElementException: pass
            except Exception: pass
            
            all_posts_data.append(post_data)

        except NoSuchElementException:
            # Bỏ qua các container không phải bài viết (ví dụ: gợi ý "follow")
            continue
    
    # Loại bỏ các bản ghi trùng lặp
    if all_posts_data:
        unique_posts = {p['post_url']: p for p in all_posts_data if p['post_url']}
        all_posts_data = list(unique_posts.values())

    return all_posts_data

# ============================================================================================
# LUỒNG CHẠY CHÍNH (PIPELINE)
# ============================================================================================
def pipeline(USERNAME, PASSWORD, keywords, scroll_per_keyword):
    driver = load_driver()
    if driver is None: return

    try:
        # --- 1. Đăng nhập ---
        driver.get("https://www.threads.com/login")
        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Username, phone or email']")))
        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='Password']")))
        login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(., 'Log in')]")))
        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        login_button.click()
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href="/search"]')))
        logging.info("✅ Đăng nhập thành công.")

        # --- 2. Bỏ qua Pop-ups ---
        time.sleep(2)
        try:
            not_now_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now' or text()='Lúc khác'] | //div[@role='button' and (text()='Not Now' or text()='Lúc khác')]")))
            not_now_button.click()
            logging.info("Đã bỏ qua pop-up đầu tiên.")
            time.sleep(1)
        except TimeoutException: pass
        try:
            dialog = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
            not_now_in_dialog = dialog.find_element(By.XPATH, ".//button[text()='Not Now' or text()='Lúc khác']")
            not_now_in_dialog.click()
            logging.info("Đã bỏ qua pop-up thứ hai.")
        except Exception: pass
            
        # --- 3. Bắt đầu tìm kiếm ---
        for keyword in keywords:
            logging.info(f"Đang tìm kiếm với từ khóa: '{keyword}'")
            driver.get("https://www.threads.net/search")
            
            search_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search'], input[placeholder='Tìm kiếm']")))
            old_element_ref = driver.find_element(By.TAG_NAME, 'html')
            
            search_input.clear()
            search_input.send_keys(keyword)
            time.sleep(2)
            search_input.send_keys(Keys.RETURN)
            
            logging.info("Đang chờ trang kết quả tìm kiếm tải...")
            WebDriverWait(driver, 15).until(EC.staleness_of(old_element_ref))
            
            # [WAIT THÔNG MINH] Chờ cho đến khi NỘI DUNG của bài viết xuất hiện
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']//a[contains(@href, '/@')]"))
            )
            
            logging.info("Trang kết quả đã tải. Bắt đầu thu thập.")
            extracted_data = scrape_posts(driver, max_scrolls=scroll_per_keyword)
            
            if extracted_data:
                logging.info(f"--- THU THẬP THÀNH CÔNG {len(extracted_data)} BÀI VIẾT CHO '{keyword}' ---")
                safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_')).rstrip()
                save_to_json(extracted_data, f"threads_posts_{safe_keyword.replace(' ', '_')}.json")
                save_to_csv(extracted_data, f"threads_posts_{safe_keyword.replace(' ', '_')}.csv")
            else:
                logging.warning(f"--- KHÔNG THU THẬP ĐƯỢC BÀI VIẾT NÀO CHO '{keyword}' ---")
            time.sleep(3)

    except Exception as e:
        logging.error(f"Đã xảy ra lỗi nghiêm trọng trong pipeline: {e}")
        driver.save_screenshot('error_screenshot.png')
        logging.info("Đã chụp ảnh màn hình lỗi vào file 'error_screenshot.png'")
    finally:
        print("\nHoàn tất quá trình. Đóng trình duyệt.")
        driver.quit()

# ============================================================================================
# ĐIỂM BẮT ĐẦU CHẠY SCRIPT
# ============================================================================================
if __name__ == '__main__':
    THREAD_USERNAME, THREAD_PASSWORD = get_threads_account()
    if THREAD_USERNAME and THREAD_PASSWORD:
        pipeline(
            USERNAME=THREAD_USERNAME,
            PASSWORD=THREAD_PASSWORD,
            keywords=["AI Engineer Job", "Data Scientist Vietnam"],
            scroll_per_keyword=2
        )
    else:
        logging.error("Không tìm thấy thông tin đăng nhập. Vui lòng kiểm tra file .env.")

