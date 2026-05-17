import time
import re
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    PLAYWRIGHT_AVAILABLE = True
    logger.info("Playwright available — will use browser-based scraping")
except ImportError:
    logger.warning("Playwright not available — using cloudscraper fallback")

try:
    import cloudscraper
    from bs4 import BeautifulSoup
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

from utils import extract_otp_from_text, clean_phone_number, clean_service_name


class IVASMSPlaywrightScraper:
    """Playwright-based scraper that bypasses Cloudflare Managed Challenge"""

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.base_url = "https://www.ivasms.com"
        self.is_logged_in = False
        self._cookies = []

    def _parse_messages_from_html(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        messages = []

        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')[1:]
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    msg = _extract_from_row(cells)
                    if msg:
                        messages.append(msg)

        if not messages:
            divs = soup.find_all('div', class_=re.compile(r'message|sms|otp|item|card', re.I))
            for div in divs:
                msg = _extract_from_div(div)
                if msg:
                    messages.append(msg)

        return messages

    def login(self):
        if not PLAYWRIGHT_AVAILABLE:
            return False
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                    ]
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 720},
                    locale='en-US',
                )
                page = context.new_page()
                stealth_sync(page)

                logger.info("Navigating to IVASMS login page...")
                page.goto(f"{self.base_url}/login", wait_until='networkidle', timeout=30000)

                # Wait for Cloudflare challenge to resolve
                page.wait_for_timeout(3000)

                # Check if we got past Cloudflare
                title = page.title()
                logger.info(f"Page title: {title}")

                if 'just a moment' in title.lower() or 'cloudflare' in title.lower():
                    logger.warning("Still on Cloudflare challenge page — waiting longer...")
                    page.wait_for_timeout(5000)
                    title = page.title()
                    logger.info(f"Page title after wait: {title}")

                # Fill login form
                try:
                    page.fill('input[name="email"], input[type="email"]', self.email)
                    page.fill('input[name="password"], input[type="password"]', self.password)
                    page.click('button[type="submit"], input[type="submit"]')
                    page.wait_for_load_state('networkidle', timeout=15000)
                except Exception as e:
                    logger.error(f"Could not fill login form: {e}")
                    browser.close()
                    return False

                final_url = page.url.lower()
                page_text = page.content().lower()

                if any(x in final_url for x in ['dashboard', 'account', 'home', 'inbox']):
                    self.is_logged_in = True
                    self._cookies = context.cookies()
                    logger.info("Playwright login successful (URL check)")
                elif any(x in page_text for x in ['logout', 'dashboard', 'sign out', 'my account']):
                    self.is_logged_in = True
                    self._cookies = context.cookies()
                    logger.info("Playwright login successful (content check)")
                else:
                    logger.warning(f"Login may have failed — URL: {page.url}")

                browser.close()
                return self.is_logged_in

        except Exception as e:
            logger.error(f"Playwright login error: {e}")
            return False

    def fetch_messages(self):
        if not PLAYWRIGHT_AVAILABLE:
            return []
        if not self.is_logged_in:
            if not self.login():
                return []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox',
                          '--disable-dev-shm-usage', '--disable-gpu']
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 720},
                )
                if self._cookies:
                    context.add_cookies(self._cookies)

                page = context.new_page()
                stealth_sync(page)

                paths = ['/sms', '/messages', '/inbox', '/history', '/dashboard']
                messages = []

                for path in paths:
                    try:
                        page.goto(f"{self.base_url}{path}", wait_until='networkidle', timeout=20000)
                        page.wait_for_timeout(2000)
                        html = page.content()
                        msgs = self._parse_messages_from_html(html)
                        if msgs:
                            logger.info(f"Found {len(msgs)} messages at {path}")
                            messages.extend(msgs)
                            break
                    except Exception as e:
                        logger.debug(f"Error at {path}: {e}")
                        continue

                browser.close()
                return messages

        except Exception as e:
            logger.error(f"Playwright fetch error: {e}")
            return []

    def test_connection(self):
        if not PLAYWRIGHT_AVAILABLE:
            return False
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])
                page = browser.new_page()
                stealth_sync(page)
                page.goto(self.base_url, wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(3000)
                title = page.title()
                browser.close()
                reachable = 'just a moment' not in title.lower()
                logger.info(f"Playwright connection test — title: {title!r} — reachable: {reachable}")
                return reachable
        except Exception as e:
            logger.error(f"Playwright connection test failed: {e}")
            return False


class IVASMSScraper:
    """Cloudscraper-based fallback scraper"""

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.base_url = "https://www.ivasms.com"
        self.is_logged_in = False
        if CLOUDSCRAPER_AVAILABLE:
            self.session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
        else:
            import requests
            self.session = requests.Session()
        self.session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        })

    def login(self):
        try:
            logger.info(f"Cloudscraper login attempt: {self.email}")
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url, timeout=30)

            if response.status_code != 200:
                logger.error(f"Login page status: {response.status_code}")
                return False

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            csrf_input = soup.find('input', {'name': '_token'})
            csrf_token = csrf_input.get('value') if csrf_input else None

            login_data = {'email': self.email, 'password': self.password}
            if csrf_token:
                login_data['_token'] = csrf_token

            self.session.headers.update({
                'Referer': login_url, 'Origin': self.base_url,
            })

            login_response = self.session.post(login_url, data=login_data, timeout=30)
            final_url = login_response.url.lower()

            if any(x in final_url for x in ['dashboard', 'account', 'home', 'inbox']):
                self.is_logged_in = True
                logger.info("Cloudscraper login successful")
                return True

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_response.content, 'html.parser')
            page_text = soup.get_text().lower()
            if any(x in page_text for x in ['logout', 'dashboard', 'sign out']):
                self.is_logged_in = True
                logger.info("Cloudscraper login successful (content check)")
                return True

            logger.warning("Cloudscraper login failed")
            return False

        except Exception as e:
            logger.error(f"Cloudscraper login error: {e}")
            return False

    def fetch_messages(self):
        if not self.is_logged_in:
            if not self.login():
                return []
        try:
            from bs4 import BeautifulSoup
            messages = []
            for path in ['/sms', '/messages', '/inbox', '/history', '/dashboard']:
                try:
                    r = self.session.get(f"{self.base_url}{path}", timeout=30)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.content, 'html.parser')
                        msgs = _extract_messages_from_page(soup)
                        if msgs:
                            messages.extend(msgs)
                            break
                except Exception:
                    continue
            return messages
        except Exception as e:
            logger.error(f"Cloudscraper fetch error: {e}")
            return []

    def test_connection(self):
        try:
            r = self.session.get(self.base_url, timeout=15)
            return r.status_code in [200, 302, 301]
        except Exception:
            return False


def _extract_messages_from_page(soup):
    messages = []
    tables = soup.find_all('table')
    for table in tables:
        for row in table.find_all('tr')[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                msg = _extract_from_row(cells)
                if msg:
                    messages.append(msg)
    if not messages:
        for div in soup.find_all('div', class_=re.compile(r'message|sms|otp|item|card', re.I)):
            msg = _extract_from_div(div)
            if msg:
                messages.append(msg)
    return messages


def _extract_from_row(cells):
    try:
        phone = service = message = ""
        timestamp = datetime.now().strftime('%H:%M:%S')
        for cell in cells:
            text = cell.get_text(strip=True)
            if re.search(r'\+?\d{10,15}', text):
                m = re.search(r'\+?\d{10,15}', text)
                phone = clean_phone_number(m.group())
            elif re.search(r'\d{1,2}:\d{2}', text) and len(text) < 30:
                timestamp = text
            elif len(text) > 10:
                message = text
        otp = extract_otp_from_text(message)
        if otp:
            return {
                'otp': otp,
                'phone': phone or 'N/A',
                'service': service or _guess_service(message),
                'timestamp': timestamp,
                'raw_message': message
            }
    except Exception:
        pass
    return None


def _extract_from_div(div):
    try:
        text = div.get_text(strip=True)
        otp = extract_otp_from_text(text)
        if not otp:
            return None
        m = re.search(r'\+?\d{10,15}', text)
        phone = clean_phone_number(m.group()) if m else 'N/A'
        return {
            'otp': otp,
            'phone': phone,
            'service': _guess_service(text),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'raw_message': text
        }
    except Exception:
        pass
    return None


def _guess_service(text):
    if not text:
        return 'Unknown'
    t = text.lower()
    for key, val in {
        'facebook': 'Facebook', 'fb': 'Facebook',
        'google': 'Google', 'gmail': 'Google',
        'instagram': 'Instagram',
        'twitter': 'Twitter', 'x.com': 'Twitter',
        'whatsapp': 'WhatsApp',
        'telegram': 'Telegram',
        'discord': 'Discord',
        'tiktok': 'TikTok',
        'snapchat': 'Snapchat',
        'netflix': 'Netflix',
        'amazon': 'Amazon',
        'paypal': 'PayPal',
        'uber': 'Uber',
        'binance': 'Binance',
        'coinbase': 'Coinbase',
    }.items():
        if key in t:
            return val
    return 'Unknown'


def create_scraper(email, password):
    if not email or not password:
        logger.error("IVASMS credentials missing")
        return None

    if PLAYWRIGHT_AVAILABLE:
        logger.info("Using Playwright scraper (Cloudflare-resistant)")
        scraper = IVASMSPlaywrightScraper(email, password)
        if scraper.test_connection():
            logger.info("Playwright can reach IVASMS — attempting login...")
            if scraper.login():
                logger.info("IVASMS login SUCCESSFUL via Playwright")
            else:
                logger.warning("Playwright login failed — will retry on first fetch")
        else:
            logger.warning("IVASMS not reachable via Playwright — will retry on first fetch")
        return scraper
    else:
        logger.info("Using cloudscraper fallback (may fail on cloud IPs)")
        scraper = IVASMSScraper(email, password)
        if scraper.test_connection():
            scraper.login()
        else:
            logger.warning("IVASMS not reachable (Cloudflare blocking this IP). Deploy on Railway to fix.")
        return scraper
