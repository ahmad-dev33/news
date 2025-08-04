
import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot, ParseMode
import json
from datetime import datetime
import time
import random
import re

# تهيئة الملفات
if not os.path.exists('data'):
    os.makedirs('data')

CONFIG = {
    'sent_links_file': 'data/sent_links.json',
    'log_file': 'data/bot_log.txt',
    'sources': {
        'aljazeera': {
            'name': 'الجزيرة نت',
            'url': 'https://www.aljazeera.net',
            'selectors': {
                'container': 'article, .featured-news-item, .news-card, .gc__content',
                'title': 'h1, h2, h3, .title, .gc__title a',
                'link': 'a'
            },
            'enabled': True
        },
        'bbc_arabic': {
            'name': 'بي بي سي عربي',
            'url': 'https://www.bbc.com/arabic',
            'selectors': {
                'container': 'article, .media-list__item, .block-link',
                'title': 'h3, .media__title, .block-link__overlay-text',
                'link': 'a'
            },
            'enabled': True
        },
        'rt_arabic': {
            'name': 'روسيا اليوم',
            'url': 'https://arabic.rt.com',
            'selectors': {
                'container': 'article, .card, .list-item',
                'title': 'h2, h3, .card__heading, .list-item__title',
                'link': 'a'
            },
            'enabled': True
        }
    }
}

class NewsBot:
    def __init__(self):
        try:
            self.bot = Bot(token=os.getenv('TELEGRAM_TOKEN')) if os.getenv('TELEGRAM_TOKEN') else None
            self.chat_id = os.getenv('CHAT_ID')
            self.hf_token = os.getenv('HUGGING_FACE_TOKEN')
        except:
            self.bot = None
            self.chat_id = None
            self.hf_token = None
        self.load_sent_links()

    def log(self, message):
        """تسجيل الأحداث في ملف log"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        try:
            with open(CONFIG['log_file'], 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except:
            pass
        print(log_entry.strip())

    def load_sent_links(self):
        """تحميل الروابط المرسلة مسبقاً"""
        try:
            with open(CONFIG['sent_links_file'], 'r', encoding='utf-8') as f:
                self.sent_links = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.sent_links = []
            self.log("تم إنشاء ملف الروابط الجديد")

    def save_links(self):
        """حفظ الروابط المرسلة"""
        try:
            with open(CONFIG['sent_links_file'], 'w', encoding='utf-8') as f:
                json.dump(self.sent_links[-1000:], f)  # الاحتفاظ بآخر 1000 رابط فقط
        except:
            pass

    def is_syria_related(self, title):
        """التحقق من ارتباط الخبر بسوريا"""
        syria_keywords = [
            'سوريا', 'سورية', 'دمشق', 'حلب', 'حمص', 'حماة', 'اللاذقية', 'طرطوس',
            'درعا', 'السويداء', 'القامشلي', 'الحسكة', 'إدلب', 'الرقة', 'دير الزور',
            'بشار الأسد', 'الأسد', 'نظام دمشق', 'المعارضة السورية', 'الثورة السورية',
            'اللاجئين السوريين', 'النازحين السوريين', 'هيئة تحرير الشام', 'الجيش الحر',
            'قوات سوريا الديمقراطية', 'كردستان سوريا', 'شمال شرق سوريا'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in syria_keywords)

    def get_random_headers(self):
        """الحصول على headers عشوائية لتجنب الحظر"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

    def generate_summary(self, title, content):
        """إنشاء موجز للخبر باستخدام Hugging Face"""
        if not self.hf_token:
            return "موجز غير متوفر - يتطلب توكن Hugging Face"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/json"
            }
            
            # استخدام نموذج تلخيص عربي
            api_url = "https://api-inference.huggingface.co/models/aubmindlab/bert-base-arabertv02"
            
            # تجهيز النص للتلخيص
            text_to_summarize = f"{title}. {content[:500]}"  # أول 500 حرف من المحتوى
            
            payload = {
                "inputs": text_to_summarize,
                "parameters": {
                    "max_length": 100,
                    "min_length": 30,
                    "do_sample": False
                }
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('summary_text', title[:100] + "...")
                else:
                    return title[:100] + "..."
            else:
                self.log(f"خطأ في Hugging Face API: {response.status_code}")
                return title[:100] + "..."
                
        except Exception as e:
            self.log(f"خطأ في إنشاء الموجز: {str(e)}")
            return title[:100] + "..."

    def get_article_content(self, url):
        """جلب محتوى المقال لإنشاء الموجز"""
        try:
            headers = self.get_random_headers()
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # البحث عن المحتوى في العناصر الشائعة
            content_selectors = [
                'article p', '.article-content p', '.content p', 
                '.story-body p', '.post-content p', 'main p'
            ]
            
            content = ""
            for selector in content_selectors:
                paragraphs = soup.select(selector)
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs[:3]])
                    if len(content) > 100:
                        break
            
            return content[:800] if content else ""
            
        except Exception as e:
            self.log(f"خطأ في جلب محتوى المقال: {str(e)}")
            return ""

    def fetch_news(self, source_key):
        """استخراج الأخبار من مصدر معين مع التركيز على سوريا"""
        if source_key not in CONFIG['sources'] or not CONFIG['sources'][source_key]['enabled']:
            return []

        config = CONFIG['sources'][source_key]
        headers = self.get_random_headers()
        headers['Referer'] = config['url']

        try:
            time.sleep(random.uniform(0.5, 2.0))
            
            session = requests.Session()
            response = session.get(config['url'], headers=headers, timeout=15, verify=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = []
            containers = soup.select(config['selectors']['container'])
            
            self.log(f"تم العثور على {len(containers)} عنصر من {config['name']}")
            
            for article in containers[:100]:  # فحص المزيد من العناصر للعثور على أخبار سوريا
                try:
                    title_element = article.select_one(config['selectors']['title'])
                    link_element = article.select_one(config['selectors']['link']) or article
                    
                    if not title_element:
                        continue
                        
                    title = title_element.get_text(strip=True)
                    link = link_element.get('href') if link_element else None
                    
                    if not title or not link or len(title) < 15:
                        continue

                    # تصحيح الروابط النسبية
                    if link.startswith('/'):
                        link = config['url'].rstrip('/') + link
                    elif not link.startswith('http'):
                        link = config['url'].rstrip('/') + '/' + link.lstrip('/')

                    # تصفية الروابط غير المناسبة
                    if any(exclude in link.lower() for exclude in ['javascript:', 'mailto:', '#']):
                        continue

                    # التحقق من ارتباط الخبر بسوريا
                    if self.is_syria_related(title) and link not in self.sent_links:
                        # جلب محتوى المقال لإنشاء الموجز
                        content = self.get_article_content(link)
                        summary = self.generate_summary(title, content)
                        
                        news_items.append({
                            'title': title[:200],
                            'link': link,
                            'source': config['name'],
                            'summary': summary,
                            'content_preview': content[:200] if content else ""
                        })
                        
                        self.sent_links.append(link)
                        self.log(f"تم العثور على خبر سوري: {title[:50]}...")
                        
                        if len(news_items) >= 5:  # الحد الأقصى للأخبار السورية
                            break

                except Exception as e:
                    continue

            self.log(f"تم جلب {len(news_items)} خبر سوري من {config['name']}")
            return news_items

        except requests.exceptions.RequestException as e:
            self.log(f"خطأ في الاتصال بـ {config['name']}: {str(e)}")
            return []
        except Exception as e:
            self.log(f"خطأ في جلب الأخبار من {config['name']}: {str(e)}")
            return []

    def get_all_news(self):
        """جلب الأخبار من جميع المصادر مع التركيز على سوريا"""
        all_news = {}
        
        for source_key, source_config in CONFIG['sources'].items():
            if source_config['enabled']:
                news = self.fetch_news(source_key)
                if news:
                    all_news[source_config['name']] = news
                
        return all_news

    def send_news_to_telegram(self):
        """جمع الأخبار وإرسالها إلى تيليجرام"""
        if not self.bot or not self.chat_id:
            self.log("لم يتم تكوين بوت التليجرام بشكل صحيح")
            return False

        all_news = self.get_all_news()
        sent_count = 0

        # إرسال رسالة ترحيبية
        welcome_message = "🇸🇾 <b>آخر الأخبار السورية</b>\n\n"
        welcome_message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        welcome_message += "━━━━━━━━━━━━━━━━━━━━━━━━━"

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=welcome_message,
                parse_mode=ParseMode.HTML
            )
            time.sleep(2)
        except Exception as e:
            self.log(f"خطأ في إرسال الرسالة الترحيبية: {str(e)}")

        for source, news in all_news.items():
            if news:
                for item in news:
                    try:
                        message = f"📰 <b>{item['title']}</b>\n\n"
                        message += f"📝 <b>الموجز:</b>\n{item['summary']}\n\n"
                        message += f"🔗 <a href='{item['link']}'>اقرأ المزيد</a>\n\n"
                        message += f"📡 المصدر: {source}"

                        self.bot.send_message(
                            chat_id=self.chat_id,
                            text=message,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=False
                        )
                        
                        sent_count += 1
                        self.log(f"تم إرسال خبر سوري من {source}")
                        time.sleep(3)  # تأخير أطول بين الرسائل
                        
                    except Exception as e:
                        self.log(f"خطأ في إرسال خبر من {source}: {str(e)}")
                        continue

        # إرسال رسالة ختامية
        if sent_count > 0:
            summary_message = f"✅ <b>تم إرسال {sent_count} خبر سوري</b>\n\n"
            summary_message += "📱 للمزيد من الأخبار، تابع القناة\n"
            summary_message += f"🕐 التحديث التالي خلال ساعة"
            
            try:
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=summary_message,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                self.log(f"خطأ في إرسال الرسالة الختامية: {str(e)}")

        self.save_links()
        return sent_count > 0

if __name__ == "__main__":
    bot = NewsBot()
    bot.log("بدء تشغيل بوت الأخبار السورية")
    result = bot.send_news_to_telegram()
    if result:
        bot.log("تم إرسال الأخبار بنجاح")
    else:
        bot.log("لم يتم العثور على أخبار جديدة أو حدث خطأ")
