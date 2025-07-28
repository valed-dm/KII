import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv('BASE_URL')
PMA_PATH = os.getenv("PMA_PATH")
LOGIN_URL = urljoin(BASE_URL, PMA_PATH)
PMA_USERNAME = os.getenv("PMA_USERNAME")
PMA_PASSWORD = os.getenv("PMA_PASSWORD")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def login(session: requests.Session) -> bool:
    """
    Performs login to phpMyAdmin.
    Returns True on success, raises Exception on failure.
    """
    print("[1] Getting login token...")
    try:
        response = session.get(LOGIN_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        token_input = soup.find('input', {'name': 'token'})
        if not token_input or not token_input.get('value'):
            raise ValueError("Login token not found on the page.")
        token = token_input['value']
        print(f"[2] Extracted token: {token}")

    except (requests.RequestException, ValueError) as e:
        raise Exception(f"Failed to get login page or token: {e}")

    login_data = {
        'pma_username': PMA_USERNAME,
        'pma_password': PMA_PASSWORD,
        'server': '1',
        'target': 'index.php',
        'token': token,
    }

    print("[3] Submitting login form...")
    try:
        response = session.post(LOGIN_URL, data=login_data, allow_redirects=True)
        response.raise_for_status()

        if 'pma_password' in response.text:
            # We are still on the login page, so it failed.
            soup = BeautifulSoup(response.text, 'html.parser')
            error_div = soup.find('div', class_='error')
            error_message = error_div.get_text(strip=True) if error_div else "Incorrect username/password."
            raise PermissionError(f"Authentication failed. Server message: {error_message}")

        print("[4] Login successful!")
        return True

    except (requests.RequestException, PermissionError) as e:
        raise Exception(f"Login process failed: {e}")


def fetch_table_data(session: requests.Session, base_url: str, db_name: str, table_name: str):
    """
    Fetches and displays data from a specific table.
    """
    data_url = urljoin(base_url, f"index.php?route=/sql&db={db_name}&table={table_name}&pos=0")
    print(f"\n[5] Fetching data from: {data_url}")

    try:
        response = session.get(data_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        results_table = soup.find('table', class_='table_results')
        if not results_table:
            with open('debug_data_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            raise ValueError("Could not find the results table. See 'debug_data_page.html'.")

        print("\n--- Users Table Data ---")
        print(f"{'ID':<4} | Name")
        print("-----|------")

        rows = results_table.find_all('tr')
        for row in rows:
            # Skip header rows explicitly
            if row.find('th'):
                continue

            cells = row.find_all('td')
            if len(cells) > 2:
                user_id = cells[-2].get_text(strip=True)
                user_name = cells[-1].get_text(strip=True)
                if user_id and user_name:
                    print(f"{user_id:<4} | {user_name}")

    except (requests.RequestException, ValueError, IndexError) as e:
        print(f"\n[ERROR] Failed to fetch or parse data: {e}")


def main():
    """Main execution function."""
    if not PMA_USERNAME or not PMA_PASSWORD:
        print("Error: PMA_USERNAME or PMA_PASSWORD not set in .env file or environment.", file=sys.stderr)
        sys.exit(1)

    with requests.Session() as session:
        session.headers.update(HEADERS)
        try:
            if login(session):
                fetch_table_data(session, LOGIN_URL, db_name="testDB", table_name="users")
        except Exception as e:
            print(f"\nAn unrecoverable error occurred: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
