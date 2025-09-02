from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import json
import urllib.parse

   # 開啟瀏覽器
options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

   # 去網站找寶藏
url = "https://ehm.hpa.gov.tw/EHM/admin/park!map.action"
driver.get(url)

   # 準備放寶藏的籃子
parks = []

   # 定義縣市和它的 value
city_values = {
       "臺北市": "6300000000"  
       "新北市": "6500000000"
   }

   # 選不同縣市和行政區
for city, city_value in city_values.items():
       try:
           # 等待縣市選單出現
           city_select = WebDriverWait(driver, 15).until(
               EC.presence_of_element_located((By.CLASS_NAME, "sideBarHeadCitySelect.countySelector"))
           )
           select_city = Select(city_select)
           select_city.select_by_value(city_value)  # 選縣市

           # 等待行政區選單出現
           WebDriverWait(driver, 15).until(
               EC.presence_of_element_located((By.CLASS_NAME, "sideBarHeadCitySelect.townSelector"))
           )
           district_select = Select(driver.find_element(By.CLASS_NAME, "sideBarHeadCitySelect.townSelector"))

           # 獲取所有行政區選項
           districts = [(option.get_attribute("value"), option.text) for option in district_select.options]
           for value, district in districts[1:]:  # 跳過第一個空值
               try:
                   select_district = Select(driver.find_element(By.CLASS_NAME, "sideBarHeadCitySelect.townSelector"))
                   select_district.select_by_value(value)  # 選行政區

                   # 等待類型選單出現
                   WebDriverWait(driver, 15).until(
                       EC.presence_of_element_located((By.CLASS_NAME, "sideBarHeadCitySelect.typeSelector"))
                   )
                   type_select = Select(driver.find_element(By.CLASS_NAME, "sideBarHeadCitySelect.typeSelector"))
                   type_select.select_by_value("park")  # 選「公園」

                   # 等頁面更新
                   time.sleep(3)

                   # 等待側邊欄內容穩定
                   WebDriverWait(driver, 15).until(
                       EC.presence_of_element_located((By.CLASS_NAME, "sideBarContent"))
                   )

                   # 重新找公園盒子
                   boxes = WebDriverWait(driver, 10).until(
                       EC.presence_of_all_elements_located((By.CLASS_NAME, "sideBarContentBox"))
                   )
                   for box in boxes:
                       try:
                           # 等待並找元素
                           name = WebDriverWait(box, 10).until(
                               EC.presence_of_element_located((By.CLASS_NAME, "sideBarContentBoxTitle"))
                           ).text.strip()
                           data_div = WebDriverWait(box, 10).until(
                               EC.presence_of_element_located((By.CLASS_NAME, "sideBarContentBoxData"))
                           )
                           # 檢查地址（目前可能空）
                           address = data_div.text.strip() if data_div.text.strip() else ""
                           # 提取器材資訊
                           equipment_divs = box.find_elements(By.CLASS_NAME, "countBox.countAdult")
                           equipment = []
                           for div in equipment_divs:
                               spans = div.find_elements(By.TAG_NAME, "span")
                               if len(spans) >= 2:
                                   equip_name = spans[0].text.strip()  # 器材名稱
                                   equip_count = spans[1].text.strip()  # 數量
                                   equipment.append(f"{equip_name} ({equip_count})")
                           if not equipment:
                               equipment = []

                           # 構建 Google Maps 連結
                           full_address = f"{city}{district}{name}".encode('utf-8').decode('utf-8')
                           map_link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(full_address)}"

                           park = {
                               "name": name,
                               "city": city,
                               "district": district,
                               "type": "公園",
                               "address": address,
                               "equipment": equipment,
                               "map_link": map_link
                           }
                           parks.append(park)
                       except Exception as e:
                           print(f"找不到 {name} 的資訊: {e}")

                   time.sleep(2)

               except Exception as e:
                   print(f"行政區 {district} 找不到了: {e}")

       except Exception as e:
           print(f"縣市 {city} 找不到了: {e}")

   # 關掉瀏覽器
driver.quit()

   # 存進 parks.json
with open('parks.json', 'w', encoding='utf-8') as f:
       json.dump(parks, f, ensure_ascii=False, indent=2)

print(f"找到 {len(parks)} 個公園，存進 parks.json 了！")
