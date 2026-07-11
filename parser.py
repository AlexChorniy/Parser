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
    Directly maps explicit DOM layout elements on the company.aspx profile page.
    """
    data = {"address": "N/A", "tel": "N/A", "email": "N/A", "website": "N/A"}
    try:
        try:
            # FIXED: By.xpath -> By.XPATH
            web_element = driver.find_element(By.XPATH, "//tr[@id='content_row_company_website']//a")
            data["website"] = web_element.get_attribute("href").strip()
        except NoSuchElementException:
            pass

        try:
            text_cell = driver.find_element(By.ID, "content_cel_text")
            cell_html = text_cell.get_attribute("innerHTML")
            raw_lines = [line.strip() for line in re.split(r'<br\s*/?>', cell_html, flags=re.IGNORECASE)]
            
            address_parts = []
            for line_raw in raw_lines:
                line = re.sub(r'<[^>]+>', '', line_raw).strip()
                if not line:
                    continue
                
                if re.search(r'\b(tel|telephone|phone)\b', line, re.IGNORECASE):
                    tel_val = re.sub(r'^(tel|telephone|phone)[:\s]*', '', line, flags=re.IGNORECASE).strip()
                    data["tel"] = tel_val if tel_val else data["tel"]
                
                elif re.search(r'\b(email|e-mail|mail)\b', line, re.IGNORECASE):
                    email_val = re.sub(r'^(email|e-mail|mail)[:\s]*', '', line, flags=re.IGNORECASE).strip()
                    data["email"] = email_val if email_val else data["email"]
                
                elif "isletmeciligi" in line.lower() or "inc." in line.lower() or "co ltd" in line.lower() or "pty ltd" in line.lower():
                    continue
                
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
    txt_output_path = os.path.join(output_dir, "company_directory.txt")

    # Use the target query parameter link provided to jump directly to page 2 state
    target_url = "https://www.chinashipbuild.com/companys.aspx?nmkhTk8Pl4ENaoklppLwi94XgaclppkLL0p4JXapoljjlSLPHH4c"
    print(f"🔗 Connecting to target portal...")
    driver.get(target_url)
    time.sleep(5)
    
    scraped_pages_set = {1}
    BLACKLISTED_PAGES = [9, 64]

    while True:
        info_table_id = None
        for potential_id in ["content_tb_companys", "content_tb_info"]:
            try:
                driver.find_element(By.ID, potential_id)
                info_table_id = potential_id
                break
            except NoSuchElementException:
                continue

        # RECOVERY JUMP MECHANISM: If 1st page search page overrides the grid, navigate explicitly onto Page 2 control nodes
        if not info_table_id:
            print("⚠️ Grid elements hidden by 1st page layout state. Attempting bypass recovery click to Page 2...")
            try:
                # FIXED: By.xpath -> By.XPATH
                page_2_link = driver.find_element(By.XPATH, "//span[@id='content_lb_pager']/a[text()='2']")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", page_2_link)
                time.sleep(0.5)
                page_2_link.click()
                print("➡️ Successfully clicked Page 2 link to clear layout lock!")
                time.sleep(4)
                continue
            except NoSuchElementException:
                print("⚠️ Core pager elements unreadable. Refreshing context window...")
                driver.get(target_url)
                time.sleep(5)
                continue

        try:
            # FIXED: By.xpath -> By.XPATH
            current_pager_bold = driver.find_element(By.XPATH, "//span[@id='content_lb_pager']/b")
            page_number = int(current_pager_bold.text.strip())
        except (NoSuchElementException, ValueError):
            page_number = 2  # Default configuration state fallback if unable to resolve actively selected bold index text

        print(f"\n📖 --- Current Viewport: Page {page_number} ---")

        if page_number in BLACKLISTED_PAGES:
            print(f"🚫 Page {page_number} is blacklisted! Advancing track...")
            scraped_pages_set.add(page_number)
        elif page_number == 1:
            print("⏩ Page 1 layout caught in parsing loop. Forcing jump to pagination...")
            scraped_pages_set.add(1)
        elif page_number in scraped_pages_set:
            print(f"⏩ Page {page_number} already processed. Looking for next link...")
        else:
            processed_on_this_page = 0
            company_idx = 0
            
            while True:
                try:
                    info_table = driver.find_element(By.ID, info_table_id)
                    # FIXED: By.xpath -> By.XPATH
                    rows = info_table.find_elements(By.XPATH, ".//tr[td/a[contains(@href, 'company.aspx')]]")
                    
                    if company_idx >= len(rows):
                        break
                    
                    target_row = rows[company_idx]
                    # FIXED: By.xpath -> By.XPATH
                    link_element = target_row.find_element(By.XPATH, ".//td/a[contains(@href, 'company.aspx')]")
                    company_name = link_element.text.strip()
                    
                    if company_name and company_name not in [c['name'] for c in parsed_companies]:
                        print(f"🕵️‍♂️ [{len(parsed_companies) + 1}] Processing profile details for: {company_name}")
                        
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link_element)
                        time.sleep(0.2)
                        link_element.click()
                        
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "content_tb_company")))
                        profile = extract_clean_profile_data(driver)
                        
                        parsed_companies.append({
                            "name": company_name,
                            "url": profile["website"],
                            "address": profile["address"],
                            "tel": profile["tel"],
                            "email": profile["email"]
                        })
                        processed_on_this_page += 1
                        
                        with open(txt_output_path, "a", encoding="utf-8") as file:
                            file.write(f"Company name: {company_name};\n")
                            file.write(f"Website (URL): {profile['website']};\n")
                            file.write(f"Company address: {profile['address']};\n")
                            file.write(f"Tel: {profile['tel']};\n")
                            file.write(f"Email: {profile['email']}\n")
                            file.write("-" * 50 + "\n")

                        driver.back()
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, info_table_id)))
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

        # Smart Pagination Transitions
        try:
            # FIXED: By.xpath -> By.XPATH
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
                # FIXED: By.xpath -> By.XPATH
                forward_links = driver.find_elements(By.XPATH, "//span[@id='content_lb_pager']/a[text()='>>']")
                if forward_links:
                    print(f"⏩ Section exhaustion hit on page {page_number}. Clicking next deck index block '>>'...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", forward_links[0])
                    time.sleep(0.5)
                    forward_links[0].click()
                else:
                    print("🏁 Pagination tracks completely completed.")
                    break
            time.sleep(3)

        except Exception as pagination_err:
            print(f"⚠️ Pagination tracking engine execution halted: {pagination_err}")
            break

    print(f"\n🎉 ALL RUN EXECUTION METRICS COMPLETE!")
    driver.quit()

if __name__ == "__main__":
    main()