import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException

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
    print("🚀 Initializing Thorough Multi-Decade China Shipbuild Parser...")
    driver = setup_driver()
    parsed_companies = []
    
    target_url = "https://www.chinashipbuild.com/companys.aspx"
    print(f"🔗 Navigating to target portal...")
    driver.get(target_url)
    
    wait = WebDriverWait(driver, 15)
    
    # Accurate page tracking history
    highest_scraped_page = 0
    scraped_pages_set = set()
    
    # 🚫 BROKEN PAGES BLACKLIST
    BLACKLISTED_PAGES = [9, 64]

    while True:
        # 1. Page Stabilization Handshake
        try:
            wait.until(EC.presence_of_element_located((By.ID, "content_lb_pager")))
            wait.until(EC.presence_of_element_located((By.ID, "content_tb_info")))
        except TimeoutException:
            print("⚠️ Page layout timed out loading. Reloading base state to re-try...")
            try:
                driver.get(target_url)
                time.sleep(4)
                continue
            except Exception as re_err:
                print(f"❌ Portal inaccessible: {re_err}")
                break

        # 2. Extract Active Web Page State From DOM
        try:
            current_pager_bold = driver.find_element(By.XPATH, "//span[@id='content_lb_pager']/b")
            page_number = int(current_pager_bold.text.strip())
        except (NoSuchElementException, ValueError):
            print("⚠️ Pager elements missing or unreadable. Defaulting state configuration...")
            page_number = 1
            current_pager_bold = None

        print(f"\n📖 --- Current Viewport: Page {page_number} ---")

        # 3. Dynamic Skip/Scrape Gatekeeper
        if page_number in BLACKLISTED_PAGES:
            print(f"🚫 Current page ({page_number}) is blacklisted! Skipping data collection extraction...")
            page_items_count = 0
        elif page_number in scraped_pages_set:
            print(f"⏩ Page {page_number} already processed. Pre-navigating pagination track...")
            page_items_count = 0
        else:
            # Secure Core Row Data Extraction
            for retry in range(3):
                try:
                    info_table = driver.find_element(By.ID, "content_tb_info")
                    rows = info_table.find_elements(By.XPATH, ".//tr[td/a[contains(@href, 'company.aspx')]]")
                    page_items_count = 0

                    for row in rows:
                        try:
                            link_element = row.find_element(By.XPATH, ".//td/a[contains(@href, 'company.aspx')]")
                            company_title = link_element.text.strip()
                            company_url = link_element.get_attribute("href")
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
                    break
                except StaleElementReferenceException:
                    time.sleep(2)

            print(f"✅ Processed Page {page_number}. Added {page_items_count} entries. (Total: {len(parsed_companies)})")
            scraped_pages_set.add(page_number)
            if page_number > highest_scraped_page:
                highest_scraped_page = page_number

        # 4. Smart Navigation: Prioritize Lowest Unscraped Numeric Page
        try:
            # Look for all numbered page links visible inside the pager container
            visible_page_links = driver.find_elements(By.XPATH, "//span[@id='content_lb_pager']/a[not(text()='<<') and not(text()='>>')]")
            
            target_link_element = None
            target_page_val = None
            
            # Find the lowest visible page number that we have not scraped yet
            for link in visible_page_links:
                try:
                    val = int(link.text.strip())
                    if val not in scraped_pages_set and val not in BLACKLISTED_PAGES:
                        if target_page_val is None or val < target_page_val:
                            target_page_val = val
                            target_link_element = link
                except ValueError:
                    continue

            # If a valid local target is visible on screen, execute navigation step
            if target_link_element:
                print(f"➡️ Navigating towards Page {target_page_val}...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link_element)
                time.sleep(0.5)
                target_link_element.click()
            else:
                # If all visible numbers are exhausted, click '>>' to reveal the next cluster
                forward_links = driver.find_elements(By.XPATH, "//span[@id='content_lb_pager']/a[text()='>>']")
                if forward_links:
                    print(f"⏩ Visible numbers exhausted on page {page_number}. Advancing deck via '>>'...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", forward_links[0])
                    time.sleep(0.5)
                    forward_links[0].click()
                else:
                    print("🏁 Pagination tracks completely exhausted. Compilation complete.")
                    break

            if current_pager_bold:
                wait.until(EC.staleness_of(current_pager_bold))
            time.sleep(2.5)

        except (TimeoutException, StaleElementReferenceException) as state_err:
            print(f"🔄 Transition hitch encountered. Reloading to re-stabilize thread context...")
            time.sleep(3)
            continue
        except Exception as pagination_err:
            print(f"⚠️ Pagination engine execution halted: {pagination_err}")
            break

    # 5. Output Sync Export File Generation
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "company_directory.txt")
    
    with open(output_path, "w", encoding="utf-8") as file:
        for item in parsed_companies:
            file.write(f"Company: {item['name']}\n")
            file.write(f"URL: {item['url']}\n")
            file.write(f"Details:\n{item['raw_details']}\n")
            file.write("-" * 50 + "\n")
            
    print(f"\n💾 TASK COMPLETE: Data directory saved to: {output_path}")
    print("🔒 Shutting down browser engine session.")
    driver.quit()

if __name__ == "__main__":
    main()