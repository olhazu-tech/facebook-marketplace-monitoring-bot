from playwright.sync_api import sync_playwright
import urllib.parse
import time
import requests
import re

BOT_TOKEN = "8710371922:AAE8px8TKa48mnFT3a2pSBuCPyeRMCdfkzw"

CHAT_IDS = [
    "689223350",
    "8989208055"
]

MAX_PRICE = 3000
SCROLLS = 6

SEARCH_KEYWORDS = [
    "mower",
    "walk behind mower",
    "lawn mower",
    "generator",
    "scag",
    "exmark",
    "wright",
    "bobcat",
    "toro",
    "john deere",
    "honda mower",
    "honda generator"
]


def build_url(keyword):
    q = urllib.parse.quote(keyword)
    return f"https://www.facebook.com/marketplace/search/?query={q}"


def extract_item_id(url):
    match = re.search(r"/marketplace/item/(\d+)", url)
    if match:
        return match.group(1)
    return None


def extract_price(text):
    match = re.search(r"\$([\d,]+)", text)
    if not match:
        return None

    try:
        return int(match.group(1).replace(",", ""))
    except:
        return None


def send_telegram(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        data = {
            "chat_id": chat_id,
            "text": message
        }

        try:
            requests.post(url, data=data)
        except Exception as e:
            print(f"Telegram error for {chat_id}:", e)


def scroll_marketplace(page):
    previous_count = 0

    for scroll_number in range(SCROLLS):
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(2000)

        current_count = page.locator('a[href*="/marketplace/item/"]').count()
        print(f"Scroll {scroll_number + 1}/{SCROLLS}: {current_count} listing links loaded")

        if current_count == previous_count:
            print("No new listings loaded after scroll.")
            break

        previous_count = current_count


def run():
    try:
        with open("seen.txt", "r") as f:
            seen = set(f.read().splitlines())
    except:
        seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="fb_profile",
            headless=False
        )

        page = browser.pages[0]

        print("\nOpening Facebook...")
        page.goto("https://www.facebook.com", wait_until="domcontentloaded")

        print("\nMake sure Facebook is logged in.")
        input("Press ENTER to continue...\n")

        print("\nOpening Marketplace...")
        page.goto("https://www.facebook.com/marketplace", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        print("\nLIVE MODE ON: only Just Listed items will be sent.\n")

        while True:
            for keyword in SEARCH_KEYWORDS:
                print(f"\nSearching: {keyword}")

                try:
                    page.goto(build_url(keyword), wait_until="domcontentloaded")
                    page.wait_for_timeout(5000)

                    scroll_marketplace(page)

                    listing_links = page.locator('a[href*="/marketplace/item/"]')
                    count = listing_links.count()

                    print(f"Total listing links after scroll: {count}")

                    for i in range(count):
                        try:
                            link = listing_links.nth(i)
                            href = link.get_attribute("href")

                            if not href:
                                continue

                            item_id = extract_item_id(href)

                            if not item_id:
                                continue

                            if item_id in seen:
                                continue

                            text = link.inner_text()

                            if len(text.strip()) < 5:
                                continue

                            if "just listed" not in text.lower():
                                continue

                            price = extract_price(text)

                            if price is not None and price > MAX_PRICE:
                                print(f"Skipped expensive listing: ${price}")
                                continue

                            seen.add(item_id)

                            with open("seen.txt", "a") as f:
                                f.write(item_id + "\n")

                            full_link = f"https://www.facebook.com/marketplace/item/{item_id}/"

                            message = (
                                f"JUST LISTED MARKETPLACE ITEM\n\n"
                                f"Keyword: {keyword}\n"
                                f"Item ID: {item_id}\n"
                                f"Price: ${price if price is not None else 'unknown'}\n\n"
                                f"{text[:500]}\n\n"
                                f"{full_link}"
                            )

                            print("\n==============================")
                            print(message)
                            print("==============================")

                            send_telegram(message)

                        except Exception as item_error:
                            print("Item error:", item_error)

                except Exception as e:
                    print("Search error:", e)

                time.sleep(3)

            print("\nWaiting 2 minutes before next scan...\n")
            time.sleep(120)


if __name__ == "__main__":
    run()