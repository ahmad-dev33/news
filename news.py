import requests
from bs4 import BeautifulSoup

def get_aljazeera_news():
    url = "https://www.aljazeera.net"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        # اختيار العناصر بدقة (تحديث حسب هيكل الموقع الحالي)
        for article in soup.select('article.card'):
            title = article.find('h3').get_text(strip=True) if article.find('h3') else "No title"
            link = article.find('a')['href'] if article.find('a') else "#"
            if not link.startswith('http'):
                link = url + link
            links.append(f"{title}: {link}")
        
        return links[:5]  # أول 5 أخبار
    except Exception as e:
        print(f"Error fetching Al Jazeera: {e}")
        return []
def get_alarabiya_news():
    url = "https://www.alarabiya.net"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        for article in soup.select('div.item-inner'):
            title = article.find('h2').get_text(strip=True) if article.find('h2') else "No title"
            link = article.find('a')['href'] if article.find('a') else "#"
            if not link.startswith('http'):
                link = url + link
            links.append(f"{title}: {link}")
        
        return links[:5]
    except Exception as e:
        print(f"Error fetching Al Arabiya: {e}")
        return []
from telegram import Bot
import time

TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
bot = Bot(token=TELEGRAM_TOKEN)

def main():
    aljazeera = get_aljazeera_news()
    alarabiya = get_alarabiya_news()
    
    message = "📢 **أخبار الجزيرة**\n" + "\n".join(aljazeera) + \
              "\n\n📢 **أخبار العربية**\n" + "\n".join(alarabiya)
    
    bot.send_message(chat_id=CHAT_ID, text=message)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(3600)  # انتظر ساعة
