import json
import sys
import logging
import random
import time
from dotenv import load_dotenv
import os
from pathlib import Path
from seleniumbase import SB
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

#setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get the directory containing the script
SCRIPT_DIR = Path(__file__).resolve().parent

# Load .env from the same directory as the script
load_dotenv(SCRIPT_DIR / '.env')

# You can verify the environment variables are loaded
if not os.getenv("INSTAGRAM_USERNAME") or not os.getenv("INSTAGRAM_PASSWORD"):
    logger.error(f"Could not load environment variables from {SCRIPT_DIR / '.env'}")
    sys.exit(1)


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
    logger.info(f"Extracting users from {html_file}")

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
     
def get_user_information(sb, target_account: str):
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
        
        try:
            # Get the number of followers
            followers = sb.get_text("ul li:nth-child(2) a span")
            followers_count = int(followers.replace(",", ""))
            #update obj
            obj["followers_count"] = followers_count
        except Exception as e:
            logger.warning(f"Could not get followers count: {e}")
            obj["followers_count"] = None
        
        try:
            #click on followers
            sb.click("ul li:nth-child(2) a")
            
            # Wait for the followers modal to appear and find its scrollable container
            modal = sb.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]")
            base_scroll_amount = 1000
            
            while True:
                current_scroll = sb.driver.execute_script("return arguments[0].scrollTop", modal)
                
                # Add randomization to scroll amount (base_scroll_amount ± 50)
                random_scroll = base_scroll_amount + random.randint(-50, 50)
                sb.driver.execute_script(f"arguments[0].scrollTop += {random_scroll}", modal)
                
                time.sleep(3)
                new_scroll = sb.driver.execute_script("return arguments[0].scrollTop", modal)
                if new_scroll == current_scroll:
                    break
                
            #get modals children parent
            users_parent_container = sb.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]/div[1]/div")
            
            #wait for load
            time.sleep(5)
            
            #save to HTML file
            with open(f"/data/{target_account}_followers.html", "w", encoding="utf-8") as f:
                f.write(users_parent_container.get_attribute("outerHTML"))
                
            #extract users
            users = extract_users_from_html(f"/data/{target_account}_followers.html")
            
            #update OBJ
            obj["followers"] = users
        except Exception as e:
            logger.warning(f"Could not get followers list: {e}")
            obj["followers"] = []
            
        obj["scrape_end_time"] = time.time()
        return obj
            
    except Exception as e:
        logger.error(f"Error getting user information for {target_account}: {e}")
        return None
    
        
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
    if random.random() < 0.5:
        base_url += "reels/"
    else:
        base_url += "explore/"
    
    login_url = "https://www.instagram.com/accounts/login/"
    cookie_file = "cookies.json"
    
    with SB(uc=True, test=True, locale_code="en", ad_block=False) as sb:
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
            # Refresh to apply cookies and load authenticated session
            sb.open(base_url)
            time.sleep(5)
        else:
            #on initialization the browser will open, navigate to the login page, and login
            sb.open(login_url)
            time.sleep(5)
            sb.press_keys('input[name="username"]', account_username)
            time.sleep(2)
            sb.press_keys('input[name="password"]', account_password)
            time.sleep(1)
            sb.click('button[type="submit"]')
            time.sleep(10)  # Wait for login to complete
        
            cookies = sb.get_cookies()
            with open("cookies.json", "w") as f:
                    json.dump(cookies, f)
                
        # throw off the scent
        # if base_url contains reels/ then scroll reels
        if "reels" in base_url:
            logger.info("Scrolling reels")
            scroll_reels(sb, 10)
        else:
            logger.info("Scrolling explore page")
            random_scroll(sb, 10)
            
        #begin targetting accounts
        for target_account in target_accounts:
            user_info = get_user_information(sb, target_account)
            if user_info:
                with open(f"/data/{target_account}_followers.json", "w") as f:
                    json.dump(user_info, f, indent=4)
        
        

def main(usernames: list):
    logger.info(f"Beginning processing of {len(usernames)} usernames")
    
    #ensure data directory exists
    if not os.path.exists("/data"):
        os.makedirs("/data")
    
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