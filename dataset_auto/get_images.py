from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import os
import time
import re  # за намиране на номерата

SAVE_DIR = r"D:\TOOLS\Desktop\diplomna\dataset_auto\images"
os.makedirs(SAVE_DIR, exist_ok=True)

# Намери последния index от вече съществуващи снимки
existing_files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".jpg")]
if existing_files:
    indexes = []
    for f in existing_files:
        match = re.match(r"car(\d+)\.jpg", f)
        if match:
            indexes.append(int(match.group(1)))
    start_index = max(indexes) + 1 if indexes else 2
else:
    start_index = 2

count = 0  # брой нови свалени снимки

# Стартираме Chrome headless
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=options)

print("Въведи URL на обява (или 'q' за край):")

while True:
    url = input("URL: ").strip()
    if url.lower() == "q":
        break

    try:
        driver.get(url)
        time.sleep(2)  

        active_item = driver.find_element(By.CSS_SELECTOR, "div.owl-item.active")
        img = active_item.find_element(By.CSS_SELECTOR, "img.owl-lazy")
        src = img.get_attribute("data-src") or img.get_attribute("src")

        if src and "jpg" in src:
            file_name = f"car{start_index + count}.jpg"
            img_data = requests.get(src, timeout=10).content
            with open(os.path.join(SAVE_DIR, file_name), "wb") as f:
                f.write(img_data)
            count += 1
            print(f"Saved {file_name}")
        else:
            print("Не можа да намери jpg изображение.")

    except Exception as e:
        print("Грешка:", e)

driver.quit()
print(f"Finished downloading {count} new images")
