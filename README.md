# GSM Arena Phone Scraper

This repository contains a Python-based web scraper for extracting detailed specifications of mobile phones from [GSMArena](https://www.gsmarena.com/). It utilizes Playwright and BeautifulSoup for robust data extraction and supports multi-threaded execution for efficient scraping.

## Features

- **Progress Saving**: Ensures data is not lost and scraping can resume from the last saved point in case of interruptions.
- **Concurrent Scraping**: Uses `ThreadPoolExecutor` to scrape multiple pages concurrently.
- **Comprehensive Data Extraction**: Extracts various phone specifications including model name, release date, OS details, CPU/GPU information, and more.
- **Custom Logging**: Provides detailed logs of the scraping process for monitoring and debugging.

## Requirements

- Python 3.7+
- Playwright
- BeautifulSoup4
- Requests
- Logging
- Pickle

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/ahthserhsluk/GSMARENA-Mobile-Data-Scapper.git
    cd gsmarena-phone-scraper
    ```

2. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Install Playwright browsers:
    ```bash
    playwright install
    ```

## Usage

1. Update the `main` function in `scraper.py` with the desired manufacturer and start URL:
    ```python
    if __name__ == "__main__":
        manufacturer = "Nokia"  # Replace with the desired manufacturer
        start_url = "https://www.gsmarena.com/nokia-phones-1.php"
        end_page = 5  # Change this to set an end page or set to None to scrape all pages
        main(manufacturer, start_url, end_page)
    ```

2. Run the scraper:
    ```bash
    python scraper.py
    ```

3. The scraped data will be saved to a CSV file in the manufacturer's directory.

## Code Structure

- `scraper.py`: The main script containing the scraping logic.
- `requirements.txt`: The dependencies required to run the scraper.
- `logs/`: Directory where logs are saved.
- `data/`: Directory where the scraped CSV files are saved.

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

## License

This project is licensed under the MIT License 

