from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import time

def capture_chart(symbol: str):
    # UPDATE_TIME環境変数で am/pm を判定（"930" → am、それ以外 → pm）
    update_time = os.environ.get("UPDATE_TIME", "930")
    suffix = "am" if update_time == "930" else "pm"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_filename = f"chart_{symbol}_{suffix}.html"
    html_file_path = os.path.join(script_dir, html_filename)
    url = f"file:///{html_file_path}"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--allow-file-access-from-files")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-extensions")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    driver.set_window_size(701, 565)

    print(f"⌛ チャート描画待ち...（{html_filename}）")
    time.sleep(10)

    screenshot_name = f"chart_{symbol}.png"
    screenshot_path = os.path.join(script_dir, screenshot_name)
    driver.save_screenshot(screenshot_path)
    print(f"✅ {screenshot_path} に保存完了")

    driver.quit()


if __name__ == "__main__":
    for symbol in ["xaujpy", "xauusd"]:
        capture_chart(symbol)
