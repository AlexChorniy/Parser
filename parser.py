import os
import time
import re
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

def extract_clean_profile_data(driver):
    """
    Directly maps explicit DOM layout elements on the company.aspx page
    to avoid pulling in garbage menu text or fleet tables into the address block.
    """
    data = {"address": "N/A", "tel": "N/A", "email": "N/A", "website": "N/A"}
    
    try:
        # 1. Grab the clean website link from its dedicated cell row anchor
        try:
            web_element = driver.find_element(By.XPATH, "//tr[@id='content_row_company_website']//a")
            data["website"] = web_element.get_attribute("href").strip()
        except NoSuchElementException:
            pass

        # 2. Extract specific lines from the text detail container cell
        try:
            text_cell = driver.find_element(By.ID, "content_cel_text")
            # Get raw HTML break-split lines or text splits to accurately capture fields
            cell_html = text_cell.get_attribute("innerHTML")
            raw_lines = [line.strip() for line in re.split(r'<br\s*/?>', cell_html, flags=re.IGNORECASE)]
            
            address_parts = []
            for line_raw in raw_lines:
                # Strip HTML tags if any remain
                line = re.sub(r'<[^>]+>', '', line_raw).strip()
                if not line:
                    continue
                
                # Check for Telephone variations
                if re.search(r'\b(tel|telephone|phone)\b', line, re.IGNORECASE):
                    tel_val = re.sub(r'^(tel|telephone|phone)[:\s]*', '', line, flags=re.IGNORECASE).strip()
                    data["tel"] = tel_val if tel_val else data["tel"]
                
                # Check for Email variations
                elif re.search(r'\b(email|e-mail|mail)\b', line, re.IGNORECASE):
                    email_val = re.sub(r'^(email|e-mail|mail)[:\s]*', '', line, flags=re.IGNORECASE).strip()
                    data["email"] = email_val if email_val else data["email"]
                
                # Skip duplicating the company name inside the address field if possible
                elif "isletmeciligi" in line.lower() or "inc." in line.lower() or "co ltd" in line.lower() or "pty ltd" in line.lower():
                    continue
                
                # If it's a structural street address block before contact numbers
                else:
                    address_parts.append(line)
            
            if address_parts:
                data["address"] = ", ".join(address_parts)
                
        except NoSuchElementException:
            pass
            
    except Exception as e:
        print(f"⚠️ Layout mapping execution error: {e}")
        
    return data

def main():
    print("🚀 Initializing Failure-Resilient Native Click China Shipbuild Parser...")
    driver = setup_driver()
    parsed_companies = []
    
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "company_directory.txt")
    
    target_url = "https://www.chinashipbuild.com/companys.aspx"
    print(f"🔗 Navigating to target portal...")
    driver.get(target_url)
    
    wait = WebDriverWait(driver, 15)
    scraped_pages_set = set()
    BLACKLISTED_PAGES = [9, 64]

    while True:
        try:
            wait.until(EC.presence_of_element_located((By.ID, "content_lb_pager")))
            wait.until(EC.presence_of_element_located((By.ID, "content_tb_info")))
        except TimeoutException:
            print("⚠️ Page layout timed out loading. Reloading core window handle...")
            driver.get(target_url)
            time.sleep(4)
            continue

        try:
            current_pager_bold = driver.find_element(By.XPATH, "//span[@id='content_lb_pager']/b")
            page_number = int(current_pager_bold.text.strip())
        except (NoSuchElementException, ValueError):
            page_number = 1
            current_pager_bold = None

        print(f"\n📖 --- Current Viewport: Page {page_number} ---")

        if page_number in BLACKLISTED_PAGES:
            print(f"🚫 Page {page_number} is blacklisted! Advancing track...")
            scraped_pages_set.add(page_number)
        elif page_number in scraped_pages_set:
            print(f"⏩ Page {page_number} already processed. Looking for next link...")
        else:
            processed_on_this_page = 0
            company_idx = 0
            
            while True:
                try:
                    info_table = driver.find_element(By.ID, "content_tb_info")
                    rows = info_table.find_elements(By.XPATH, ".//tr[td/a[contains(@href, 'company.aspx')]]")
                    
                    if company_idx >= len(rows):
                        break
                    
                    target_row = rows[company_idx]
                    link_element = target_row.find_element(By.XPATH, ".//td/a[contains(@href, 'company.aspx')]")
                    company_name = link_element.text.strip()
                    
                    if company_name and company_name not in [c['name'] for c in parsed_companies]:
                        print(f"🕵️‍♂️ [{len(parsed_companies) + 1}] Processing profile details for: {company_name}")
                        
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link_element)
                        time.sleep(0.2)
                        link_element.click()
                        
                        # Wait for the company table to structure
                        wait.until(EC.presence_of_element_located((By.ID, "content_tb_company")))
                        
                        # Execute clean localized element DOM pull
                        profile = extract_clean_profile_data(driver)
                        
                        parsed_companies.append({
                            "name": company_name,
                            "url": profile["website"],
                            "address": profile["address"],
                            "tel": profile["tel"],
                            "email": profile["email"]
                        })
                        processed_on_this_page += 1
                        
                        # Output values straight to file with precise formatting layouts
                        with open(output_path, "a", encoding="utf-8") as file:
                            file.write(f"Company name: {company_name};\n")
                            file.write(f"Website (URL): {profile['website']};\n")
                            file.write(f"Company address: {profile['address']};\n")
                            file.write(f"Tel: {profile['tel']};\n")
                            file.write(f"Email: {profile['email']}\n")
                            file.write("-" * 50 + "\n")

                        driver.back()
                        wait.until(EC.presence_of_element_located((By.ID, "content_tb_info")))
                        time.sleep(0.4)
                    
                    company_idx += 1
                    
                except (StaleElementReferenceException, TimeoutException):
                    print("🔄 DOM shift detected during extraction. Recalibrating tracking row context...")
                    time.sleep(2)
                    continue
                except Exception as e:
                    print(f"⚠️ Skipping row element due to an error: {e}")
                    company_idx += 1
                    continue

            print(f"✅ Processed Page {page_number}. Extracted {processed_on_this_page} entries on this pass.")
            scraped_pages_set.add(page_number)

        # 3. Smart Pagination Transitions
        try:
            visible_page_links = driver.find_elements(By.XPATH, "//span[@id='content_lb_pager']/a[not(text()='<<') and not(text()='>>')]")
            target_link_element = None
            target_page_val = None
            
            for link in visible_page_links:
                try:
                    val = int(link.text.strip())
                    if val not in scraped_pages_set and val not in BLACKLISTED_PAGES:
                        if target_page_val is None or val < target_page_val:
                            target_page_val = val
                            target_link_element = link
                except ValueError:
                    continue

            if target_link_element:
                print(f"➡️ Transitioning towards Page {target_page_val}...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link_element)
                time.sleep(0.5)
                target_link_element.click()
            else:
                forward_links = driver.find_elements(By.XPATH, "//span[@id='content_lb_pager']/a[text()='>>']")
                if forward_links:
                    print(f"⏩ Section exhaustion hit on page {page_number}. Clicking next deck index block '>>'...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", forward_links[0])
                    time.sleep(0.5)
                    forward_links[0].click()
                else:
                    print("🏁 Pagination tracks completely completed.")
                    break

            if current_pager_bold:
                wait.until(EC.staleness_of(current_pager_bold))
            time.sleep(2.5)

        except Exception as pagination_err:
            print(f"⚠️ Pagination tracking engine execution halted: {pagination_err}")
            break

    print(f"\n🎉 ALL RUN EXECUTION METRICS COMPLETE: Clean output logs finalized at {output_path}")
    driver.quit()

if __name__ == "__main__":
    main()