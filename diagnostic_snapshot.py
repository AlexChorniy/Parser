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
    print("📸 Initializing Standalone Diagnostic Web Snapshot Utility...")
    driver = setup_driver()
    
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Target URL from your prompt
    target_url = "https://www.chinashipbuild.com/companys.aspx?nmkhTk8Pl4ENaoklppLwi94XgaclppkLL0p4JXapoljjlSLPHH4c"
    
    print(f"🔗 Navigating directly to URL: {target_url}")
    driver.get(target_url)
    
    # Wait up to 10 seconds for the general body to ensure something loaded
    print("⏳ Waiting for page body presentation layer...")
    time.sleep(5)
    
    try:
        # Save structural image rendering
        png_path = os.path.join(output_dir, "page_snapshot.png")
        driver.save_screenshot(png_path)
        print(f"✅ Visual image captured successfully: '{png_path}'")
        
        # Save raw HTML source state
        html_path = os.path.join(output_dir, "page_snapshot.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"✅ Raw HTML markup saved successfully: '{html_path}'")
        
    except Exception as e:
        print(f"❌ Diagnostic capture process failed: {e}")
        
    finally:
        driver.quit()
        print("🏁 Diagnostic task complete. Shutting down browser instance.")

if __name__ == "__main__":
    main()