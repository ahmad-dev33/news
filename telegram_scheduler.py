
import schedule
import time
import threading
from main import NewsBot
import os
from datetime import datetime

class TelegramScheduler:
    def __init__(self):
        self.bot = NewsBot()
        self.is_running = False
        
    def run_news_job(self):
        """تشغيل مهمة جلب وإرسال الأخبار"""
        try:
            self.bot.log("بدء مهمة جلب الأخبار السورية المجدولة")
            
            # التحقق من وجود التوكنات المطلوبة
            if not os.getenv('TELEGRAM_TOKEN'):
                self.bot.log("خطأ: TELEGRAM_TOKEN غير موجود")
                return
                
            if not os.getenv('CHAT_ID'):
                self.bot.log("خطأ: CHAT_ID غير موجود")
                return
            
            # تشغيل البوت
            result = self.bot.send_news_to_telegram()
            
            if result:
                self.bot.log("✅ تم إرسال الأخبار السورية بنجاح")
            else:
                self.bot.log("⚠️ لم يتم العثور على أخبار سورية جديدة")
                
        except Exception as e:
            self.bot.log(f"❌ خطأ في المهمة المجدولة: {str(e)}")
    
    def start_scheduler(self):
        """بدء المجدول"""
        self.is_running = True
        
        # جدولة المهام
        schedule.every(30).minutes.do(self.run_news_job)  # كل 30 دقيقة
        schedule.every().hour.at(":00").do(self.run_news_job)  # كل ساعة
        schedule.every().day.at("08:00").do(self.run_news_job)  # الساعة 8 صباحاً
        schedule.every().day.at("12:00").do(self.run_news_job)  # الساعة 12 ظهراً
        schedule.every().day.at("18:00").do(self.run_news_job)  # الساعة 6 مساءً
        
        self.bot.log("🚀 تم بدء مجدول الأخبار السورية")
        self.bot.log("📅 المواعيد: كل 30 دقيقة + 8:00، 12:00، 18:00")
        
        # تشغيل مهمة فورية عند البدء
        self.run_news_job()
        
        # حلقة التشغيل المستمر
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # فحص كل دقيقة
    
    def stop_scheduler(self):
        """إيقاف المجدول"""
        self.is_running = False
        schedule.clear()
        self.bot.log("⏹️ تم إيقاف مجدول الأخبار")
    
    def run_in_background(self):
        """تشغيل المجدول في خيط منفصل"""
        scheduler_thread = threading.Thread(target=self.start_scheduler, daemon=True)
        scheduler_thread.start()
        return scheduler_thread

def manual_send():
    """إرسال يدوي للأخبار"""
    bot = NewsBot()
    print("🔄 بدء الإرسال اليدوي للأخبار السورية...")
    result = bot.send_news_to_telegram()
    
    if result:
        print("✅ تم إرسال الأخبار بنجاح!")
    else:
        print("⚠️ لم يتم العثور على أخبار جديدة")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        # تشغيل يدوي
        manual_send()
    else:
        # تشغيل المجدول
        scheduler = TelegramScheduler()
        try:
            scheduler.start_scheduler()
        except KeyboardInterrupt:
            print("\n🛑 تم إيقاف المجدول بواسطة المستخدم")
            scheduler.stop_scheduler()
