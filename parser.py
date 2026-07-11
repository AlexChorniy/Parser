import os
import time
import re
import csv
from multiprocessing import Pool, Manager
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
    if not vessels_text or vessels_text == "N/A":
        return "N/A"
    amount_match = re.search(r'(?:拥有|规模约|约有|有|拥有约|船队有|共|大约有)\s*(\d+)\s*艘', vessels_text)
    if amount_match:
        return amount_match.group(1).strip()
    fallback_match = re.search(r'(\d+)\s*艘', vessels_text)
    if fallback_match:
        return fallback_match.group(1).strip()
    return "N/A"

def remove_chinese_symbols(text_string):
    if not text_string:
        return "N/A"
    cleaned = re.sub(r'[\u4e00-\u9fff]+', '', text_string)
    cleaned = re.sub(r'\s*,\s*,', ',', cleaned)
    cleaned = cleaned.strip().rstrip(',').rstrip(';').strip()
    return cleaned if cleaned else "N/A"

def extract_clean_profile_data(driver):
    data = {
        "address": "N/A", 
        "tel": "N/A", 
        "email": "N/A", 
        "website": "N/A",
        "vessels": "N/A",
        "vessel_amount": "N/A"
    }
    try:
        try:
            web_element = driver.find_element(By.XPATH, "//tr[@id='content_row_company_website']//a")
            data["website"] = web_element.get_attribute("href").strip()
        except NoSuchElementException:
            pass

        text_cell = driver.find_element(By.ID, "content_cel_text")
        cell_html = text_cell.get_attribute("innerHTML")
        raw_lines = [line.strip() for line in re.split(r'<br\s*/?>', cell_html, flags=re.IGNORECASE)]
        
        address_lines = []
        vessel_lines = []
        extracted_emails = []
        
        for line_raw in raw_lines:
            line = re.sub(r'<[^>]+>', '', line_raw).strip()
            if not line:
                continue
            if re.search(r'\b(tel|telephone|phone|fax)[:\s]*', line, re.IGNORECASE):
                if "tel" in line.lower() or "phone" in line.lower() or data["tel"] == "N/A":
                    data["tel"] = re.sub(r'^(tel|telephone|phone|fax)[:\s]*', '', line, flags=re.IGNORECASE).strip()
                continue
            line_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
            if line_emails:
                extracted_emails.extend(line_emails)
                continue
            if re.search(r'[\u4e00-\u9fff]', line):
                calculated_amt = parse_vessel_amount(line)
                if calculated_amt != "N/A":
                    data["vessel_amount"] = calculated_amt
                english_only_vessel_note = remove_chinese_symbols(line)
                if english_only_vessel_note != "N/A":
                    vessel_lines.append(english_only_vessel_note)
            else:
                if not any(kwd in line.lower() for kwd in ["isletmeciligi", "inc.", "co ltd", "pty ltd"]):
                    address_lines.append(line)

        if address_lines:
            data["address"] = remove_chinese_symbols(", ".join(address_lines))
        if extracted_emails:
            data["email"] = "; ".join(list(set(extracted_emails)))
        if vessel_lines:
            data["vessels"] = " ".join(vessel_lines).strip()
    except Exception:
        pass
    return data

def scrape_single_page(args):
    page_number, shared_saved_dict = args
    print(f"Worker Thread: Launching parallel Chrome instance for Page {page_number}...")
    driver = setup_driver()
    
    output_dir = "/app/output"
    txt_output_path = os.path.join(output_dir, "company_directory.txt")
    excel_output_path = os.path.join(output_dir, "company_directory.xls")
    
    if page_number == 2:
        page_url = "https://www.chinashipbuild.com/companys.aspx?nmkhTk8Pl4ENaoklppLwi94XgaclppkLL0p4JXapoljjlSLPHH4c"
    else:
        page_url = f"https://www.chinashipbuild.com/companys.aspx?page={page_number}"
        
    try:
        driver.get(page_url)
        time.sleep(4)
        
        info_table_id = None
        for potential_id in ["content_tb_companys", "content_tb_info"]:
            try:
                driver.find_element(By.ID, potential_id)
                info_table_id = potential_id
                break
            except NoSuchElementException:
                continue
                
        if not info_table_id:
            driver.quit()
            return
            
        info_table = driver.find_element(By.ID, info_table_id)
        rows = info_table.find_elements(By.XPATH, ".//tr[td/a[contains(@href, 'company.aspx')]]")
        
        profile_links = []
        for row in rows:
            try:
                link = row.find_element(By.XPATH, ".//td/a[contains(@href, 'company.aspx')]")
                profile_links.append((link.get_attribute("href"), link.text.strip()))
            except:
                continue
                
        for url, name in profile_links:
            try:
                clean_name = remove_chinese_symbols(name)
                
                # Check shared memory keys safely
                if clean_name in shared_saved_dict:
                    continue

                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "content_tb_company")))
                
                profile = extract_clean_profile_data(driver)
                
                if clean_name in shared_saved_dict:
                    continue
                    
                # Store entry name in the synchronized shared dict keys
                shared_saved_dict[clean_name] = True

                with open(txt_output_path, "a", encoding="utf-8") as file:
                    file.write(f"Company name: {clean_name};\n")
                    file.write(f"Website (URL): {profile['website']};\n")
                    file.write(f"Company address: {profile['address']};\n")
                    file.write(f"Tel: {profile['tel']};\n")
                    file.write(f"Email: {profile['email']};\n")
                    file.write(f"Vessels amount: {profile['vessel_amount']};\n")
                    file.write(f"Vessels/Description: {profile['vessels']}\n")
                    file.write("-" * 50 + "\n")
                    file.flush()

                with open(excel_output_path, "a", encoding="utf-8-sig", newline="") as xl_file:
                    xl_writer = csv.writer(xl_file, delimiter="\t")
                    xl_writer.writerow([
                        clean_name, 
                        profile["website"], 
                        profile["address"], 
                        profile["tel"], 
                        profile["email"], 
                        profile["vessel_amount"], 
                        profile["vessels"]
                    ])
                    xl_file.flush()
                    
                print(f"✅ Page {page_number}: Saved {clean_name}")
            except Exception:
                continue
                
    except Exception:
        pass
    finally:
        driver.quit()

def main():
    print("🚀 Initializing 6-Core Parallel English-Only Parser Engine...")
    
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    excel_output_path = os.path.join(output_dir, "company_directory.xls")
    
    if not os.path.exists(excel_output_path):
        with open(excel_output_path, "w", encoding="utf-8-sig", newline="") as xl_file:
            xl_writer = csv.writer(xl_file, delimiter="\t")
            xl_writer.writerow(["Company Name", "Website (URL)", "Company Address", "Tel", "Email", "Vessels Amount", "Vessels/Description"])
    
    with Manager() as manager:
        # Utilizing manager.dict() to reliably keep an exact unique record set across all processes
        shared_saved_dict = manager.dict()
        
        BLACKLISTED_PAGES = {}
        pages_pool = [page for page in range(2, 96) if page not in BLACKLISTED_PAGES]
        
        worker_tasks = [(page, shared_saved_dict) for page in pages_pool]
        
        NUMBER_OF_PROCESSORS = 8
        print(f"🔥 Spawning {NUMBER_OF_PROCESSORS} independent English-only web worker tasks concurrently...")
        print(f"📋 Total pages queued for parallel parsing: {len(worker_tasks)} (Pages 2-95)")
        
        with Pool(processes=NUMBER_OF_PROCESSORS) as pool:
            pool.map(scrape_single_page, worker_tasks)
        
    print(f"\n🎉 ALL MULTI-CORE RUN SEGMENTS COMPLETE! Files saved without duplicates.")

if __name__ == "__main__":
    main()