from utils import get_base_dir, get_threads_account, load_driver

import time
import logging
import json

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
import time
import logging
import json
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def scrape_posts(driver, max_scrolls=10):
    """
    Hàm này thực hiện cuộn trang để tải tất cả bài viết và sau đó bóc tách dữ liệu.
    *** PHIÊN BẢN HOÀN CHỈNH: Sửa lỗi dữ liệu lặp lại và sai lệch. ***
    """
    print("Bắt đầu quá trình lướt trang để tải dữ liệu...")
    
    # --- PHẦN 1: LƯỚT VÔ CỰC (Không đổi) ---
    # ... (giữ nguyên code cuộn trang)
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Đã lướt đến cuối trang.")
            break
        last_height = new_height
        scroll_count += 1
        print(f"Đã lướt lần thứ {scroll_count}...")


    print("Quá trình lướt trang hoàn tất. Bắt đầu thu thập dữ liệu...")

    all_posts_data = []
    
    # [SỬA LỖI #1] Sử dụng selector chính xác hơn để tránh lặp dữ liệu
    post_elements = driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']/div/div[2]")
    
    print(f"Tìm thấy tổng cộng {len(post_elements)} bài viết tiềm năng.")

    for i, post in enumerate(post_elements):
        post_data = { 'username': None, 'profile_url': None, 'content': None, 'post_time_text': None, 
                      'post_datetime': None, 'post_url': None, 'likes': 0, 'replies': 0, 'reposts': 0, 'shares': 0 }

        # [SỬA LỖI #2] Làm cho các selector con "chặt chẽ" hơn
        
        # Khu vực header chứa username và time
        header_area = None
        try:
            header_area = post.find_element(By.XPATH, "./div[1]")
        except NoSuchElementException:
            continue # Nếu không có header thì bỏ qua bài viết này

        try:
            user_element = header_area.find_element(By.XPATH, ".//a[contains(@href, '/@')]")
            post_data['username'] = user_element.get_attribute('textContent').strip()
            post_data['profile_url'] = user_element.get_attribute('href')
        except NoSuchElementException: pass

        # Khu vực body chứa content và các nút actions
        body_area = None
        try:
            body_area = post.find_element(By.XPATH, "./div[2]")
        except NoSuchElementException:
             pass # Một số post có thể không có body (chỉ có header)

        if body_area:
            try:
                content_element = body_area.find_element(By.XPATH, ".//span[@dir='auto']")
                raw_content = content_element.get_attribute('textContent').strip()
                post_data['content'] = raw_content.replace('Translate', '').strip()
            except NoSuchElementException:
                post_data['content'] = ""

            actions = { 'likes': ('Thích', 'Like'), 'replies': ('Trả lời', 'Reply'), 
                        'reposts': ('Đăng lại', 'Repost'), 'shares': ('Chia sẻ', 'Share') }
            
            for key, (label_vi, label_en) in actions.items():
                try:
                    xpath = f".//svg[@aria-label='{label_vi}' or @aria-label='{label_en}']/ancestor::div[@role='button']//span[contains(@class, 'x1o0tod')]"
                    number_span = body_area.find_element(By.XPATH, xpath)
                    post_data['key'] = number_span.get_attribute('textContent').strip()
                except NoSuchElementException: pass

        try:
            time_element = header_area.find_element(By.TAG_NAME, 'time')
            post_data['post_time_text'] = time_element.get_attribute('textContent').strip()
            post_data['post_datetime'] = time_element.get_attribute('datetime')
            post_data['post_url'] = time_element.find_element(By.XPATH, "./parent::a").get_attribute('href')
        except NoSuchElementException: pass
        
        if post_data.get('post_url'):
            all_posts_data.append(post_data)
        else:
            logging.warning(f"Bỏ qua một thẻ div vì không có thông tin định danh (URL).")
            
    # [SỬA LỖI #1] Xử lý hậu kỳ để loại bỏ các bản ghi trùng lặp
    # Dùng dictionary để loại bỏ các bài viết có post_url trùng nhau, chỉ giữ lại bản ghi cuối cùng
    unique_posts = {p['post_url']: p for p in all_posts_data if p['post_url']}
    all_posts_data = list(unique_posts.values())

    return all_posts_data


def save_to_json(data_list, filename):
    """
    Hàm này lưu một danh sách các dictionary vào file JSON.

    Args:
        data_list (list): Danh sách các dictionary chứa dữ liệu.
        filename (str): Tên file để lưu (ví dụ: 'posts.json').
    """
    if not data_list:
        print("Không có dữ liệu để lưu vào file JSON.")
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # ensure_ascii=False để lưu ký tự tiếng Việt đúng chuẩn
            # indent=2 để file JSON được định dạng đẹp, dễ đọc
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu thành công {len(data_list)} mục vào file: {filename}")
    except IOError as e:
        print(f"❌ Đã xảy ra lỗi khi ghi file: {e}")
# ============================================================================================
# PIPELINE
# ============================================================================================
def pipeline(USERNAME, PASSWORD, keywords, scroll_per_keyword):
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
            not_now_button_save_info = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and (text()='Not Now' or text()='Lúc khác')]"))
            )
            not_now_button_save_info.click()
        except Exception as e:
            print(f"Error: {e}")

        try:
            # Chờ tối đa 10 giây cho nút 'Not Now' hoặc 'Lúc khác'
            not_now_button_notifications = WebDriverWait(driver, 1).until(
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
            
            # ------------------------------------------------------------
            # Search keyword
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="/search"]'))
            )
            search_button.click()
            
            search_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search'], input[placeholder='Tìm kiếm']"))
            )
            search_input.clear()  
            search_input.send_keys(keyword)
            
            # [SỬA LỖI QUAN TRỌNG NHẤT] - LOGIC CHỜ MỚI
            
            # 1. Tìm một phần tử bất kỳ trên trang HIỆN TẠI (trang cũ) để làm "mốc"
            # Ta sẽ dùng chính ô tìm kiếm làm mốc
            old_element_reference = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Search'], input[placeholder='Tìm kiếm']")
            
            # 2. Thực hiện hành động gây ra việc tải trang mới (nhấn Enter)
            search_input.send_keys(Keys.RETURN)
            
            # 3. Đợi cho đến khi phần tử "mốc" của trang cũ biến mất (trở nên "stale")
            # Điều này đảm bảo trang đã bắt đầu chuyển sang trang kết quả tìm kiếm
            print("Đang chờ trang kết quả tìm kiếm tải...")
            WebDriverWait(driver, 15).until(
                EC.staleness_of(old_element_reference)
            )
            
            # 4. (Cẩn thận hơn) Đợi cho một bài viết của trang MỚI xuất hiện
            # Dùng lại selector "vàng" của chúng ta
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'x1lliihq') and .//article]"))
            )
            
            print("Trang kết quả đã tải. Bắt đầu thu thập.")

            # 5. Bây giờ mới gọi hàm scrape
            extracted_data = scrape_posts(driver, max_scrolls=scroll_per_keyword)
            if extracted_data:
                print(f"\n--- THU THẬP THÀNH CÔNG {len(extracted_data)} BÀI VIẾT ---")

                # === BẠN CHỈ CẦN GỌI HÀM LƯU FILE Ở ĐÂY ===

                # Ví dụ: Lưu ra cả 2 định dạng file
                # Tạo tên file động dựa trên từ khóa
                json_filename = f"threads_posts_{keyword.replace(' ', '_')}.json"
                csv_filename = f"threads_posts_{keyword.replace(' ', '_')}.csv"

                save_to_json(extracted_data, json_filename)
                
                # ============================================

            else:
                print("--- KHÔNG THU THẬP ĐƯỢC BÀI VIẾT NÀO ---")

    except Exception as e:
        logging.error(f"Error during searching: {e}")
    






    


    




pipeline(
    USERNAME=THREAD_USERNAME,
    PASSWORD=THREAD_PASSWORD,
    keywords=["AI Engineer Job"],
    scroll_per_keyword=1
)




