from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import time
import io
import os

url = "https://www.gaitame.com/markets/chart/usdjpy.html?interval=5"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)

time.sleep(10)

png = driver.get_screenshot_as_png()
driver.quit()
print("✅ スクリーンショット取得完了")

img = Image.open(io.BytesIO(png))
crop_area = (660, 480, 1490, 850)
cropped = img.crop(crop_area)

script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "chart_usdjpy.png")
cropped.save(save_path)

print(f"✅ チャート部分を切り出して保存しました（{save_path}）")
