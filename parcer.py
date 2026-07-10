import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    """
    Configures and initializes a headless native Chromium/ChromeDriver session 
    optimized for Linux running inside Docker environments.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Target native paths provided by the debian slim chromium-driver package
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def main():
    print("🚀 Initializing Multi-Page China Shipbuild Parser...")
    driver = setup_driver()
    parsed_companies = []
    
    # Dynamically seed tracking variable based on target initial state (e.g., Page 30)
    page_number = 30
    
    try:
        target_url = "https://www.chinashipbuild.com/companys.aspx?nmkhTk8Pl4ENaoklppLwi94XgaclppkLL0p4JXapoljjlSLPHH4J"
        print(f"🔗 Navigating to target portal...")
        driver.get(target_url)
        
        wait = WebDriverWait(driver, 15)

        while True:
            print(f"\n📖 --- Processing Page {page_number} ---")
            
            # 1. Wait for the master data table structure to stabilize in the DOM viewport
            info_table = wait.until(
                EC.presence_of_element_located((By.ID, "content_tb_info"))
            )
            
            # Validate table text anchor changes before/after network roundtrips
            first_row_text_before = info_table.text[:100]

            # 2. Match only tr elements containing company links (skipping height spacers)
            rows = info_table.find_elements(By.XPATH, ".//tr[td/a[contains(@href, 'company.aspx')]]")
            page_items_count = 0

            for row in rows:
                try:
                    # Isolate link element cleanly using precise inner child xpath context
                    link_element = row.find_element(By.XPATH, ".//td/a[contains(@href, 'company.aspx')]")
                    company_title = link_element.text.strip()
                    company_url = link_element.get_attribute("href")
                    
                    # Capture unsegmented descriptive block underneath the anchor
                    full_text = row.text.strip()
                    
                    if company_title and company_title not in [c['name'] for c in parsed_companies]:
                        parsed_companies.append({
                            "name": company_title,
                            "url": company_url,
                            "raw_details": full_text
                            })
                        page_items_count += 1
                except Exception:
                    continue

            print(f"✅ Extracted {page_items_count} entries from Page {page_number}. (Total: {len(parsed_companies)})")

           # 3. Enhanced Pagination Engine: Scalable Cluster Navigation (60+ Pages)
            try:
                next_page_str = str(page_number + 1)
                
                # Try to locate the exact next numeric sequence link
                pagination_links = driver.find_elements(
                    By.XPATH, f"//span[@id='content_lb_pager']/a[text()='{next_page_str}']"
                )

                if pagination_links:
                    next_button = pagination_links[0]
                    print(f"➡️ Navigating towards Page {next_page_str}...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                    time.sleep(0.5)
                    next_button.click()
                    page_number += 1
                    
                else:
                    # If the next digit isn't visible, find the '>>' button to advance the decade cluster
                    forward_links = driver.find_elements(
                        By.XPATH, "//span[@id='content_lb_pager']/a[text()='>>']"
                    )
                    
                    if forward_links:
                        print(f"⏩ Decade boundary reached at Page {page_number}. Advancing page cluster...")
                        next_button = forward_links[0]
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(0.5)
                        next_button.click()
                        
                        # When clicking '>>', ASP.NET usually loads the first page of the new group
                        page_number += 1 
                    else:
                        print("🏁 Target numerical controls completely exhausted. Final page reached.")
                        break
                
                # Await DOM mutation before allowing the loop to process the next segment
                wait.until(lambda d: d.find_element(By.ID, "content_tb_info").text[:100] != first_row_text_before)
                time.sleep(2.5)  # Slightly elevated cooldown to safeguard against aggressive automated rate limits
                
            except Exception as pagination_err:
                print(f"⚠️ Pagination tracking halted due to an element state change: {pagination_err}")
                break

        # 4. Export Clean Artifact Profiles
        output_dir = "/app/output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "company_directory.txt")
        
        with open(output_path, "w", encoding="utf-8") as file:
            for item in parsed_companies:
                file.write(f"Company: {item['name']}\n")
                file.write(f"URL: {item['url']}\n")
                file.write(f"Details:\n{item['raw_details']}\n")
                file.write("-" * 50 + "\n")
                
        print(f"\n💾 TASK COMPLETE: Exported {len(parsed_companies)} company records to: {output_path}")

    except Exception as e:
        print(f"❌ Scraping pipeline halted due to general exception: {e}")
        
    finally:
        print("🔒 Shutting down browser engine session.")
        driver.quit()

if __name__ == "__main__":
    main()