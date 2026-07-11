import os
import time
import re
import csv
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

def parse_vessel_amount(vessels_text):
    """
    Parses structural character patterns to return an isolated vessel count.
    """
    if not vessels_text or vessels_text == "N/A":
        return "N/A"
    
    # Matches patterns like: "约有36艘", "5艘大灵便型", "规模约120艘", "船队有7艘"
    amount_match = re.search(r'(?:拥有|规模约|约有|有|拥有约|船队有|共|大约有)\s*(\d+)\s*艘', vessels_text)
    if amount_match:
        return amount_match.group(1).strip()
        
    fallback_match = re.search(r'(\d+)\s*艘', vessels_text)
    if fallback_match:
        return fallback_match.group(1).strip()
        
    return "N/A"

def extract_clean_profile_data(driver):
    """
    Extracts data from the unified text cell container (id='content_cel_text'),
    then uses regex to split it into clean address, email, and vessel blocks.
    """
    data = {
        "address": "N/A", 
        "tel": "N/A", 
        "email": "N/A", 
        "website": "N/A",
        "vessels": "N/A",
        "vessel_amount": "N/A"
    }
    
    try:
        # 1. Grab clean website address from its anchor row mapping if it exists
        try:
            web_element = driver.find_element(By.XPATH, "//tr[@id='content_row_company_website']//a")
            data["website"] = web_element.get_attribute("href").strip()
        except NoSuchElementException:
            pass

        # 2. Extract and split the giant combined text cell block
        text_cell = driver.find_element(By.ID, "content_cel_text")
        cell_html = text_cell.get_attribute("innerHTML")
        
        # Split block elements cleanly across HTML line break nodes
        raw_lines = [line.strip() for line in re.split(r'<br\s*/?>', cell_html, flags=re.IGNORECASE)]
        
        address_lines = []
        vessel_lines = []
        extracted_emails = []
        
        for line_raw in raw_lines:
            # Strip remaining inner HTML formatting tags
            line = re.sub(r'<[^>]+>', '', line_raw).strip()
            if not line:
                continue
                
            # Parse Tel lines
            if re.search(r'\b(tel|telephone|phone|fax)[:\s]*', line, re.IGNORECASE):
                if "tel" in line.lower() or "phone" in line.lower() or data["tel"] == "N/A":
                    clean_tel = re.sub(r'^(tel|telephone|phone|fax)[:\s]*', '', line, flags=re.IGNORECASE).strip()
                    data["tel"] = clean_tel if clean_tel else data["tel"]
                continue
                
            # Extract and isolate pure emails from the line
            line_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
            if line_emails:
                extracted_emails.extend(line_emails)
                continue
                
            # Separate physical address from descriptive notes based on character sets
            if re.search(r'[\u4e00-\u9fff]', line):  # Line contains Chinese characters -> Description Note
                vessel_lines.append(line)
            else:
                # English/Latin characters are categorized as the physical address
                if not any(kwd in line.lower() for kwd in ["isletmeciligi", "inc.", "co ltd", "pty ltd"]):
                    address_lines.append(line)

        # Map findings back to the data dictionary
        if address_lines:
            data["address"] = ", ".join(address_lines).strip().rstrip(',').strip()
        if extracted_emails:
            data["email"] = "; ".join(list(set(extracted_emails)))
        if vessel_lines:
            data["vessels"] = " ".join(vessel_lines).strip()
            data["vessel_amount"] = parse_vessel_amount(data["vessels"])
            
    except Exception as e:
        print(f"⚠️ Combined cell block layout parser error: {e}")
        
    return data

def main():
    print("🚀 Initializing Failure-Resilient Native Click China Shipbuild Parser...")
    driver = setup_driver()
    parsed_companies = []
    
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    txt_output_path = os.path.join(output_dir, "company_directory.txt")
    excel_output_path = os.path.join(output_dir, "company_directory.xls")
    
    # Initialize the Excel file structure
    with open(excel_output_path, "w", encoding="utf-8-sig", newline="") as xl_file:
        xl_writer = csv.writer(xl_file, delimiter="\t")
        xl_writer.writerow(["Company Name", "Website (URL)", "Company Address", "Tel", "Email", "Vessels Amount", "Vessels/Description"])
        xl_file.flush()
        os.fsync(xl_file.fileno())

    target_url = "https://www.chinashipbuild.com/companys.aspx?nmkhTk8Pl4ENaoklppLwi94XgaclppkLL0p4JXapoljjlSLPHH4c"
    print(f"🔗 Connecting to target portal...")
    driver.get(target_url)
    time.sleep(5)
    
    scraped_pages_set = {1}
    BLACKLISTED_PAGES = []

    while True:
        info_table_id = None
        for potential_id in ["content_tb_companys", "content_tb_info"]:
            try:
                driver.find_element(By.ID, potential_id)
                info_table_id = potential_id
                break
            except NoSuchElementException:
                continue

        # RECOVERY JUMP MECHANISM
        if not info_table_id:
            print("⚠️ Grid elements hidden by 1st page layout state. Attempting bypass recovery click to Page 2...")
            try:
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
            current_pager_bold = driver.find_element(By.XPATH, "//span[@id='content_lb_pager']/b")
            page_number = int(current_pager_bold.text.strip())
        except (NoSuchElementException, ValueError):
            page_number = 2  

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
                        
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "content_tb_company")))
                        
                        # Execute deep parsing block
                        profile = extract_clean_profile_data(driver)
                        
                        parsed_companies.append({"name": company_name})
                        processed_on_this_page += 1
                        
                        # 📝 1. Real-time Text file update
                        with open(txt_output_path, "a", encoding="utf-8") as file:
                            file.write(f"Company name: {company_name};\n")
                            file.write(f"Website (URL): {profile['website']};\n")
                            file.write(f"Company address: {profile['address']};\n")
                            file.write(f"Tel: {profile['tel']};\n")
                            file.write(f"Email: {profile['email']};\n")
                            file.write(f"Vessels amount: {profile['vessel_amount']};\n")
                            file.write(f"Vessels/Description: {profile['vessels']}\n")
                            file.write("-" * 50 + "\n")
                            file.flush()
                            os.fsync(file.fileno())

                        # 📊 2. Real-time Tabbed Excel file update
                        with open(excel_output_path, "a", encoding="utf-8-sig", newline="") as xl_file:
                            xl_writer = csv.writer(xl_file, delimiter="\t")
                            xl_writer.writerow([
                                company_name, 
                                profile["website"], 
                                profile["address"], 
                                profile["tel"], 
                                profile["email"], 
                                profile["vessel_amount"], 
                                profile["vessels"]
                            ])
                            xl_file.flush()
                            os.fsync(xl_file.fileno())

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
            time.sleep(3)

        except Exception as pagination_err:
            print(f"⚠️ Pagination tracking engine execution halted: {pagination_err}")
            break

    print(f"\n🎉 ALL RUN EXECUTION METRICS COMPLETE!")
    driver.quit()

if __name__ == "__main__":
    main()