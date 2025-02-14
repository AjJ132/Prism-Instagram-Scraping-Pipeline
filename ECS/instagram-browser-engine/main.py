import json
import sys
import logging
import random
import time
from dotenv import load_dotenv
import os
from pathlib import Path
from seleniumbase import SB, BaseCase
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import colorama
from colorama import Fore, Style
import mycdp
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
import re

# Initialize colorama
colorama.init(autoreset=True)

# Custom logging formatter to add colors
class CustomFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        if levelname == "DEBUG":
            record.msg = f"{Fore.BLUE}{record.msg}{Style.RESET_ALL}"
        elif levelname == "INFO":
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"
        elif levelname == "WARNING":
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        elif levelname == "ERROR":
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        elif levelname == "CRITICAL":
            record.msg = f"{Fore.RED}{Style.BRIGHT}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Apply custom formatter
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)

# Get the directory containing the script
SCRIPT_DIR = Path(__file__).resolve().parent
data_dir = SCRIPT_DIR / "data"
data_dir.mkdir(exist_ok=True)

# Load .env from the same directory as the script
load_dotenv(SCRIPT_DIR / '.env')

# You can verify the environment variables are loaded
if not os.getenv("INSTAGRAM_USERNAME") or not os.getenv("INSTAGRAM_PASSWORD"):
    logger.error(f"Could not load environment variables from {SCRIPT_DIR / '.env'}")
    sys.exit(1)

#global constant for current users follower count
CURRENT_FOLLOWER_COUNT = 0


def random_scroll(sb, max_time):
    """
    Scrolls the page at random intervals for a total duration of max_time seconds.
    Always starts with a downward scroll, then randomly scrolls up (small intervals)
    or down.
    
    Parameters:
    - sb: SeleniumBase instance.
    - max_time: Total time (in seconds) to spend scrolling.
    """
    start_time = time.time()
    
    # Always start by scrolling down
    initial_down = random.randint(300, 800)
    sb.execute_script(f"window.scrollBy(0, {initial_down});")
    
    while (time.time() - start_time) < max_time:
        # Wait a random short duration between scrolls
        time.sleep(random.uniform(0.5, 2))
        
        # Randomly decide whether to scroll down or up
        if random.random() < 0.5:
            # Scroll down by a random amount
            scroll_amount = random.randint(100, 500)
        else:
            # Scroll up by a smaller random amount
            scroll_amount = -random.randint(20, 100)
        
        sb.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
def scroll_reels(sb, max_time):
    """
    Scrolls the reels page at random intervals for a total duration of max_time seconds.
    Always starts with a downward scroll, no scrolling up. Scroll distance is always 1000.
    
    Parameters:
    - sb: SeleniumBase instance.
    - max_time: Total time (in seconds) to spend scrolling.
    """
    start_time = time.time()
    
    # Always start by scrolling down
    initial_down = 5000
    sb.execute_script(f"window.scrollBy(0, {initial_down});")
    
    while (time.time() - start_time) < max_time:
        # Wait a random short duration between scrolls
        time.sleep(random.uniform(0.5, 2))
        
        # Scroll down by a fixed amount
        sb.execute_script(f"window.scrollBy(0, 5000);")
   
def extract_users_from_html(html_file: str):
    logger.info(f"Extracting and converting users to JSON \n")

    soup = BeautifulSoup(open(html_file, "r", encoding="utf-8"), "html.parser")
    
    users = []
    # Get the container holding all user divs
    master_div = soup.find("div", style="display: flex; flex-direction: column; padding-bottom: 0px; padding-top: 0px; position: relative;")
    user_divs = master_div.find_all("div", recursive=False)
    print(f"Found {len(user_divs)} users")
    
    for user_div in user_divs:
        # Find the profile image using the alt text filter.
        img_tag = user_div.find("img", alt=lambda alt: alt and "profile picture" in alt)
        if not img_tag or not img_tag.get("src"):
            continue
        image = img_tag["src"]
        
        # Find the <a> tag that contains the username and profile link.
        a_tag = user_div.find("a", href=True)
        if not a_tag:
            continue
        link = a_tag["href"]
        username_span = a_tag.find("span", dir="auto")
        username = username_span.get_text(strip=True) if username_span else ""
        
        # Find the full name.
        # In this HTML snippet, the full name appears in a <span> outside the <a> tag.
        # Here we look for a span with a known class fragment (e.g., "x193iq5w")
        full_name_span = user_div.find("span", class_=lambda cls: cls and "x193iq5w" in cls)
        full_name = full_name_span.get_text(strip=True) if full_name_span else ""
        
        users.append({
            "image": image,
            "username": link.strip("/"),
            "full_name": full_name
        })
    
    return users   

def throw_off_scents(sb, base_url):
    # if base_url contains reels/ then scroll reels
        if "reels" in base_url:
            logger.info("Scrolling reels")
            scroll_reels(sb, 10)
        else:
            logger.info("Scrolling explore page")
            random_scroll(sb, 10)

def locate_modal(sb):
    return sb.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]")
     
def get_followers_from_api(sb, user_id, target_account):
    users = []
    next_max_id = None
    while True:
        time.sleep(1)
        print("Getting followers at next_max_id:", next_max_id)
        # Extract cookies from Selenium session
        cookies = {cookie["name"]: cookie["value"] for cookie in sb.get_cookies()}
        csrf_token = cookies.get("csrftoken", "")

        headers = {
            "sec-ch-ua-full-version-list": '"Not(A:Brand";v="99.0.0.0", "Google Chrome";v="133.0.6943.54", "Chromium";v="133.0.6943.54"',
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "sec-ch-ua-model": '""',
            "sec-ch-ua-mobile": "?0",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "X-CSRFToken": csrf_token,
            "X-Web-Session-ID": "wcfm36:dt9dcn:ib5aos",  # May need to update dynamically
            "Referer": f"https://www.instagram.com/{target_account}/followers/",
            "X-ASBD-ID": "129477",
            "sec-ch-prefers-color-scheme": "dark",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "X-IG-WWW-Claim": "hmac.AR3KwkFLVueyIUz-AWqejkSqx6M86xUZNmPCAKexOlwHAvi0",
            "sec-ch-ua-platform-version": '"15.1.0"',
        }

        params = {"count": 12, "search_surface": "follow_list_page"}
        if next_max_id:
            params["max_id"] = next_max_id

        url = f"https://www.instagram.com/api/v1/friendships/{user_id}/followers/"
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        data = response.json()
        users.extend(data.get("users", []))
        next_max_id = data.get("next_max_id")
        if not next_max_id:
            break
        
    return users
     
def get_user_information(sb, target_account: str):
    logger.info(f"Getting user information for {target_account} \n")
    try:
        obj = {
            "username": target_account,
            "scrape_date": time.strftime("%Y-%m-%d"),
            "scrape_start_time": time.time(),
            "scrape_end_time": None,
            "followers_count": None,
            "following_count": None,
            "is_verified": None,
            "scraped_name": None,
            "number_of_posts": None,
            "bio": None,
        }
        
        #navigate to the target account
        sb.open(f"https://www.instagram.com/{target_account}")
        
        #wait for page to load
        time.sleep(10)
        
        logger.info("Getting user's information")
        
        try:
            # Get the number of followers
            followers = sb.get_text("ul li:nth-child(2) a span")
            followers_count = int(followers.replace(",", ""))
            
            logger.info(f"User has {followers_count} followers")
            
            #update obj
            obj["followers_count"] = followers_count
        except Exception as e:
            logger.warning(f"Could not get followers count: {e}")
            obj["followers_count"] = None
        
        try:
            logger.info("Getting user's followers")
            #click on followers
            sb.click("ul li:nth-child(2) a")
            
            #wait for modal to load
            time.sleep(5)
            
            user_id = None
            
            # print(sb.driver.get_log("performance"))
            performance_logs = sb.driver.get_log("performance")
            # url: https://www.instagram.com/api/v1/friendships/8569400103/followers/?count=12&max_id=12&search_surface=follow_list_page
            #search performance logs for user_id buried in the request url
            for entry in performance_logs:
                try:
                    log_entry = json.loads(entry["message"])
                except Exception:
                    continue

                method = log_entry.get("message", {}).get("method")
                url = ""
                if method == "Network.requestWillBeSent":
                    url = log_entry["message"]["params"]["request"].get("url", "")
                elif method == "Network.responseReceived":
                    url = log_entry["message"]["params"]["response"].get("url", "")

                if "https://www.instagram.com/api/v1/friendships" in url and "show_many" not in url:
                    print("Found target url containing user_id")
                    match = re.search(r'friendships/(\d+)/', url)
                    if match:
                        user_id = match.group(1)
                        print("User ID:", user_id)

            if not user_id:
                logger.warning("Could not find user ID. Returning without gettng followers")
                return obj
            
            print("Attempting to get data for user: ", user_id)
            #make request to server
            
            users = get_followers_from_api(sb=sb, user_id=user_id, target_account=target_account)
            logger.info("FOLLOWERS DATA")
            logger.info(users)
            
            # Save followers data to JSON file
            followers_file_path = data_dir / f"{target_account}_followers.json"
            with open(followers_file_path, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=4)
            
            # base_scroll_amount = 1000
            # while True:
            #     logger.info("scrolling")
            #     current_scroll = sb.driver.execute_script("return arguments[0].scrollTop", locate_modal(sb))
                
            #     # Add randomization to scroll amount (base_scroll_amount ± 50)
            #     random_scroll = base_scroll_amount + random.randint(-50, 50)
            #     sb.driver.execute_script(f"arguments[0].scrollTop += {random_scroll}", locate_modal(sb))
                
            #     time.sleep(3)
            #     new_scroll = sb.driver.execute_script("return arguments[0].scrollTop", locate_modal(sb))
            #     if new_scroll == current_scroll:
            #         break
                
            # #get modals children parent
            # users_parent_container = sb.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]/div[1]/div")
            
            # #wait for load
            # time.sleep(5)
            
            # #save to HTML file
            # logger.info("Saving users HTML to file")
            # file_path = data_dir / f"{target_account}_followers.html"
            # with open(file_path, "w", encoding="utf-8") as f:
            #     f.write(users_parent_container.get_attribute("outerHTML"))
                
            # # extract users
            # users = extract_users_from_html(file_path)
            
            #update OBJ
            obj["followers"] = users
            logger.info(f"Extracted {len(users)} followers")
        except Exception as e:
            logger.warning(f"Could not get followers list: {e}")
            obj["followers"] = []
            
        obj["scrape_end_time"] = time.time()
        logger.info(f"Finished scraping user information for {target_account}")
        return obj
            
    except Exception as e:
        logger.error(f"Error getting user information for {target_account}: {e}")
        return None

def cookie_to_dict(cookie):
    return {
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain,
        "path": cookie.path,
        "expires": cookie.expires,
        "size": cookie.size,
        "httpOnly": cookie.http_only,
        "secure": cookie.secure,
        "session": cookie.session,
        "sameSite": str(cookie.same_site) if cookie.same_site is not None else None,
        "priority": cookie.priority.name if hasattr(cookie.priority, "name") else cookie.priority,
        "sameParty": cookie.same_party,
        "sourceScheme": cookie.source_scheme.name if hasattr(cookie.source_scheme, "name") else cookie.source_scheme,
        "sourcePort": cookie.source_port,
        "partitionKey": cookie.partition_key,
        "partitionKeyOpaque": cookie.partition_key_opaque,
    }

def load_and_set_cookies(file_path, sb):
    import json
    with open(file_path, "r") as f:
        cookies = json.load(f)

    cookie_params = []
    for cookie in cookies:
        # If no URL is provided, build one from the domain and path.
        if not cookie.get("url"):
            domain = cookie.get("domain", "").lstrip(".")
            path = cookie.get("path", "/")
            cookie["url"] = f"https://{domain}{path}"

        # Optional: clean up sameSite value if needed (e.g. "CookieSameSite.NONE" -> "NONE")
        if cookie.get("sameSite") and "." in cookie["sameSite"]:
            cookie["sameSite"] = cookie["sameSite"].split(".")[-1]

        # Remove keys not needed by CDP (if any) or adjust names if required.
        cookie_params.append(cookie)

    # Use SeleniumBase's set_all_cookies to apply them
    sb.cdp.set_all_cookies(cookie_params)


def navigate_instagram(
    target_accounts: list,
    account_username = os.getenv("INSTAGRAM_USERNAME"),
    account_password = os.getenv("INSTAGRAM_PASSWORD"),
):
    # ensure account_username and account_password are set
    if not account_username or not account_password:
        logger.error("Instagram username or password not set")
        sys.exit(1)
    
    start_url = "https://about.instagram.com/"
    base_url = "https://www.instagram.com/"
    
    #random chance to add reels/ or explore/ to base_url
    # if random.random() < 0.5:
    #     base_url += "reels/"
    # else:
    #     base_url += "explore/"
    
    login_url = "https://www.instagram.com/accounts/login/"
    cookie_file = "cookies.json"
    
    with SB(uc=True, test=True, locale_code="en", pls="none", log_cdp=True) as sb:
        sb: BaseCase 
        # sb.activate_cdp_mode("about:blank")
        # activte CDP
        # sb.cdp.driver.set_window_size(1200, 1000)   
        if os.path.exists(cookie_file): #this is for local development only. ECS will not maintain state
            # Open base page to establish domain context
            sb.open(start_url)
            
            
            time.sleep(5)
            # Load and add cookies
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            for cookie in cookies:
                try:
                    sb.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Error adding cookie {cookie}: {e}")
                    
                    
            sb.open(base_url)
            time.sleep(5)
            
        else:
            #on initialization the browser will open, navigate to the login page, and login
            sb.open(login_url)
            time.sleep(5)
            # sb.press_keys('input[name="username"]', account_username)
            sb.press_keys('input[name="username"]', account_username)
            time.sleep(2)
            sb.press_keys('input[name="password"]', account_password)
            time.sleep(1)
            sb.click('button[type="submit"]')
            time.sleep(10)  # Wait for login to complete
            
            # Save cookies
            cookies = sb.get_cookies()
            with open("cookies.json", "w") as f:
                    json.dump(cookies, f)
        
            
                
        # throw off the scent
        # throw_off_scents(sb, base_url=base_url)
        
        #begin targetting accounts
        for target_account in target_accounts:
            user_info = get_user_information(sb, target_account)
            if user_info:
                #write to json
                file_path = data_dir / f"{target_account}_followers.json"
                with open(file_path, "w") as f:
                    json.dump(user_info, f, indent=4)
        
        

def main(usernames: list):
    logger.info(f"Beginning processing of {len(usernames)} usernames")
    
    navigate_instagram(usernames)
    
    
if __name__ == "__main__":
    start_time = time.time()
    usernames = sys.argv[1:]  # All arguments after the script name
    
    #make sure there is at least one username, if not exit
    if not usernames:
        logger.error("No usernames provided")
        sys.exit(1)
        
    main(usernames)
    
    execution_time = time.time() - start_time
    minutes, seconds = divmod(execution_time, 60)
    logger.info(f"Execution time: {int(minutes)}:{seconds:.2f} minutes")