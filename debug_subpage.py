import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def main():
    print("📸 Initializing Subpage Debug Renderer & Source Dumper...")
    driver = setup_driver()
    
    # Target one of the specific subpages that tripped the error loop
    test_subpage_url = "https://www.chinashipbuild.com/company.aspx?pklujyukkpp4cSXgX"
    
    try:
        print(f"🔗 Navigating directly to subpage: {test_subpage_url}")
        driver.get(test_subpage_url)
        
        # Give the page 5 seconds to settle down and completely process AJAX elements
        time.sleep(5)
        
        # Define output directory connected to your docker-compose host mapping
        output_dir = "/app/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Save visual screenshot page render
        screenshot_path = os.path.join(output_dir, "subpage_render.png")
        driver.save_screenshot(screenshot_path)
        print(f"💾 SUCCESS: Saved subpage image to {screenshot_path}")
        
        # 2. Save complete raw HTML source code
        source_path = os.path.join(output_dir, "subpage_source.html")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"💾 SUCCESS: Saved subpage DOM markup source to {source_path}")
        
        # Try a quick test extract to console for confirmation
        try:
            info_table = driver.find_element(By.ID, "content_tb_info")
            print(f"\n📄 Text preview element localized inside the page:\n{info_table.text[:200]}...")
        except Exception as text_err:
            print(f"⚠️ Warning: Element text context could not be read via ID: {text_err}")
            
    except Exception as e:
        print(f"❌ Diagnostic script encountered an exception error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()