import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Function to scrape a single URL

def scrape_url(url):
    try:
        response = requests.get(url)
        return url, response.status_code, response.text[:100]  # Return status code and first 100 chars
    except Exception as e:
        return url, None, str(e)

# Function to scrape multiple URLs concurrently

def scrape_urls_concurrently(urls):
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append((url, None, str(e)))
    return results

# Example usage
if __name__ == '__main__':
    urls = ['https://example.com', 'https://example2.com', 'https://example3.com']
    results = scrape_urls_concurrently(urls)
    for url, status, content in results:
        print(f'URL: {url}, Status: {status}, Content: {content}')