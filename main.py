import os
import csv
import time
import random
import logging
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pickle

# Setup logging
BASE_URL = "https://www.gsmarena.com/"

# List of user-agent strings
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15",
]

def setup_logging(manufacturer):
    if not os.path.exists(manufacturer):
        os.makedirs(manufacturer)
    log_file = os.path.join(manufacturer, 'scraping.log')
    logging.basicConfig(level=logging.INFO, filename=log_file, filemode='a',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

def setup_playwright():
    """Setup Playwright with Firefox."""
    playwright = sync_playwright().start()
    browser = playwright.firefox.launch(headless=True)  # Headless mode can sometimes be detected
    return playwright, browser

def extract_links(page):
    """Extract links from the current page."""
    page.wait_for_selector("div.makers ul li a")
    mobile_links = page.query_selector_all("div.makers ul li a")
    links = [BASE_URL + link.get_attribute("href") for link in mobile_links]
    return links

def get_all_links(page, start_url, end_page=None):
    """Get all phone links by navigating through pages using the 'Next' button."""
    all_links = []
    page.goto(start_url)
    page_number = 1

    while True:
        if end_page and page_number > end_page:
            break
        logging.info(f"Extracting links from page {page_number}")
        
        links = extract_links(page)
        if not links:
            break
        
        all_links.extend(links)

        # Click the "Next" button
        next_button = page.query_selector("a.prevnextbutton[title='Next page']")
        if next_button:
            next_url = BASE_URL + next_button.get_attribute("href")
            logging.info(f"Navigating to next page: {next_url}")
            page.goto(next_url)
            page_number += 1
        else:
            break

        time.sleep(random.uniform(1, 3))  # Introduce a random delay
    return all_links

def scrape_phone_data(page, url, retries=3):
    """Scrape phone data from a given URL with retries and measure the time taken."""
    start_time = time.time()
    attempt = 0
    while attempt < retries:
        try:
            logging.info(f"Navigating to {url}")
            page.goto(url)
            page.wait_for_selector('body')
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            title = soup.select_one('h1.specs-phone-name-title').text if soup.select_one('h1.specs-phone-name-title') else 'N/A'
            end_time = time.time()
            scraping_duration = end_time - start_time
            logging.info(f'Scraped {title} in {scraping_duration:.2f} seconds.')
            return title, soup, scraping_duration
        except Exception as e:
            logging.error(f'Failed to scrape {url} on attempt {attempt + 1}: {e}')
            attempt += 1
            time.sleep(random.uniform(2, 5))  # Wait a bit before retrying
    logging.error(f'All retry attempts failed for {url}')
    return None, None, None

def parse_os_details(value, specs_template):
    if "upgradable to" in value:
        released_info, upgrade_info = value.split("upgradable to")
        released_parts = released_info.split(',')
        upgrade_parts = upgrade_info.split(',')
        specs_template["AOSP version code (released)"] = released_parts[0].strip()
        specs_template["OEMOS version code (released)"] = upgrade_parts[1].strip() if len(upgrade_parts) > 1 else ""
        specs_template["AOSP version code (latest)"] = upgrade_parts[0].strip()
        specs_template["OEMOS version code (latest)"] = ""
    else:
        parts = value.split(',')
        specs_template["AOSP version code (released)"] = parts[0].strip()
        specs_template["OEMOS version code (released)"] = parts[1].strip() if len(parts) > 1 else ""
        specs_template["AOSP version code (latest)"] = ""
        specs_template["OEMOS version code (latest)"] = ""

def clean_text(text):
    pattern = r'[^\x20-\x7E]'  # This pattern matches any character that is not in the range of ASCII printable characters (space to ~)
    cleaned_text = re.sub(pattern, '', text).strip()
    return cleaned_text

def format_date(date_string):
    """Format the date to DD/MM/YYYY."""
    try:
        date_obj = datetime.strptime(date_string, "%Y, %B %d")
        return date_obj.strftime("%d/%m/%Y")
    except ValueError as e:
        logging.error(f'Date format error: {e}')
        return date_string

def parse_html_file(soup, manufacturer):
    model_name = soup.select_one('h1.specs-phone-name-title').text if soup.select_one('h1.specs-phone-name-title') else 'N/A'
    if 'watch' in model_name.lower() or 'pad' in model_name.lower() or 'band' in model_name.lower() or 'tablet' in model_name.lower():
        logging.info(f'Skipping model: {model_name}')
        return []
    
    specs_template = {
        "Manufacturer": manufacturer,
        "Model Name": model_name.replace(f'{manufacturer} ', ''),
        "Model No": "",
        "Device release date": "",
        "Model EOL Date": "",
        "AOSP version code (released)": "",
        "AOSP version code (latest)": "",
        "OEMOS version code (released)": "",
        "OEMOS version code (latest)": "",
        "Latest Security Update Dt": "",
        "LatestSecUpdateReleasedDt": "",
        "CPU Make & Model": "",
        "GPU Make & Model": "",
        "NCCS Approved": "True",
        "Google Certified": "True"
    }

    # Extract and format the release date
    announce_element = soup.select_one('td.nfo[data-spec="year"]')
    release_date_element = soup.select_one('td.nfo[data-spec="status"]')

    if announce_element and 'Released' in announce_element.text:
        release_date_text = announce_element.text.replace('Released ', '').strip()
    elif release_date_element:
        release_date_text = release_date_element.text.replace('Available. Released ', '').strip()
    else:
        release_date_text = None

    if release_date_text:
        specs_template["Device release date"] = format_date(release_date_text)

    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            title = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if title == "OS":
                parse_os_details(value, specs_template)
            elif title == "Chipset":
                specs_template["CPU Make & Model"] = value
            elif title == "GPU":
                specs_template["GPU Make & Model"] = value
    model_numbers = soup.select_one('td.nfo[data-spec="models"]')
    all_specs = []
    if model_numbers:
        model_numbers = clean_text(model_numbers.get_text()).split(',')
        for model_no in model_numbers:
            model_specs = specs_template.copy()
            model_specs['Model No'] = model_no.strip()
            all_specs.append(model_specs)
    else:
        all_specs.append(specs_template)
    logging.info(f'Parsed HTML data.')
    return all_specs

def save_to_csv(specs_list, manufacturer):
    csv_file = os.path.join(manufacturer, f'{manufacturer}.csv')
    if specs_list:
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=specs_list[0].keys())
                file.seek(0, os.SEEK_END)
                if file.tell() == 0:
                    writer.writeheader()
                for specs in specs_list:
                    writer.writerow(specs)
            logging.info(f'Saved {len(specs_list)} specs to {csv_file}.')
        except Exception as e:
            logging.error(f'Failed to save specs to CSV {csv_file}: {e}')
    else:
        logging.info('No data to write for this file.')

def scrape_and_save(url, manufacturer, completed_urls_file):
    playwright, browser = setup_playwright()
    page = browser.new_page(user_agent=random.choice(user_agents))  # Randomize user-agent
    page.set_extra_http_headers({"Referer": BASE_URL})  # Add referer header
    title, soup, duration = scrape_phone_data(page, url)
    if soup:
        specs_list = parse_html_file(soup, manufacturer)
        save_to_csv(specs_list, manufacturer)
        with open(completed_urls_file, 'a') as file:
            file.write(url + '\n')
    browser.close()
    playwright.stop()
    return title

def load_progress(manufacturer):
    links_file = os.path.join(manufacturer, f'{manufacturer}_links.pkl')
    completed_file = os.path.join(manufacturer, f'{manufacturer}_completed.pkl')

    if os.path.exists(links_file):
        with open(links_file, 'rb') as f:
            all_links = pickle.load(f)
    else:
        all_links = []

    if os.path.exists(completed_file):
        with open(completed_file, 'rb') as f:
            completed_links = pickle.load(f)
    else:
        completed_links = []

    return all_links, completed_links

def save_progress(all_links, completed_links, manufacturer):
    links_file = os.path.join(manufacturer, f'{manufacturer}_links.pkl')
    completed_file = os.path.join(manufacturer, f'{manufacturer}_completed.pkl')

    with open(links_file, 'wb') as f:
        pickle.dump(all_links, f)

    with open(completed_file, 'wb') as f:
        pickle.dump(completed_links, f)

def main(manufacturer, start_url, end_page=None):
    setup_logging(manufacturer)

    # Load progress
    all_links, completed_links = load_progress(manufacturer)

    if not all_links:
        # Setup Playwright and browser
        playwright, browser = setup_playwright()
        page = browser.new_page(user_agent=random.choice(user_agents))  # Randomize user-agent
        page.set_extra_http_headers({"Referer": BASE_URL})  # Add referer header

        # Get all phone links
        all_links = get_all_links(page, start_url, end_page)

        # Close the initial browser instance
        browser.close()
        playwright.stop()

        save_progress(all_links, completed_links, manufacturer)
        logging.info(f"Found {len(all_links)} phone links to scrape.")

    remaining_links = [url for url in all_links if url not in completed_links]

    logging.info(f"Resuming scraping. {len(remaining_links)} links left to scrape.")

    # Use ThreadPoolExecutor for concurrent scraping
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_and_save, url, manufacturer, f'{manufacturer}_completed.txt') for url in remaining_links]
        for future in as_completed(futures):
            try:
                future.result()  # This will raise any exceptions caught during scraping
            except Exception as e:
                logging.error(f'Error during scraping: {e}')

    # Save progress
    completed_links.extend(remaining_links)
    save_progress(all_links, completed_links, manufacturer)

    logging.info('Scraping process completed.')

if __name__ == "__main__":
    manufacturer = "Nokia"  # Replace with the desired manufacturer
    start_url = "https://www.gsmarena.com/nokia-phones-1.php"
    end_page = 5  # Change this to set an end page or set to None to scrape all pages
    main(manufacturer, start_url, end_page)
