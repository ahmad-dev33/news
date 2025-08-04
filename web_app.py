
from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime
from main import NewsBot, CONFIG
from telegram_scheduler import TelegramScheduler, manual_send
import threading
import time

app = Flask(__name__)

# متغيرات عامة لتخزين البيانات
latest_news = {}
last_update = None
update_lock = threading.Lock()
telegram_scheduler = None
scheduler_thread = None

def update_news_background():
    """تحديث الأخبار في الخلفية"""
    global latest_news, last_update
    
    while True:
        try:
            with update_lock:
                bot = NewsBot()
                latest_news = bot.get_all_news()
                last_update = datetime.now()
                bot.log("تم تحديث الأخبار في الخلفية")
        except Exception as e:
            print(f"خطأ في تحديث الأخبار: {e}")
        
        # تحديث كل 10 دقائق
        time.sleep(600)

# بدء خيط التحديث في الخلفية
background_thread = threading.Thread(target=update_news_background, daemon=True)
background_thread.start()

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')

@app.route('/api/news')
def get_news():
    """API لجلب الأخبار"""
    global latest_news, last_update
    
    # إذا لم تكن هناك أخبار محفوظة، جلبها الآن
    if not latest_news:
        with update_lock:
            bot = NewsBot()
            latest_news = bot.get_all_news()
            last_update = datetime.now()
    
    # إحصائيات سريعة
    total_articles = sum(len(articles) for articles in latest_news.values())
    active_sources = len([s for s in latest_news.keys() if latest_news[s]])
    
    return jsonify({
        'status': 'success',
        'timestamp': last_update.isoformat() if last_update else datetime.now().isoformat(),
        'news': latest_news,
        'stats': {
            'total_articles': total_articles,
            'active_sources': active_sources,
            'total_sources': len(CONFIG['sources'])
        }
    })

@app.route('/api/news/refresh')
def refresh_news():
    """API لتحديث الأخبار فوراً"""
    global latest_news, last_update
    
    try:
        with update_lock:
            bot = NewsBot()
            latest_news = bot.get_all_news()
            last_update = datetime.now()
            bot.log("تم تحديث الأخبار يدوياً")
        
        total_articles = sum(len(articles) for articles in latest_news.values())
        
        return jsonify({
            'status': 'success',
            'message': 'تم تحديث الأخبار بنجاح',
            'timestamp': last_update.isoformat(),
            'news': latest_news,
            'stats': {
                'total_articles': total_articles,
                'active_sources': len([s for s in latest_news.keys() if latest_news[s]]),
                'total_sources': len(CONFIG['sources'])
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ في تحديث الأخبار: {str(e)}'
        })

@app.route('/api/logs')
def get_logs():
    """API لجلب السجلات"""
    try:
        with open(CONFIG['log_file'], 'r', encoding='utf-8') as f:
            logs = f.readlines()
        return jsonify({
            'status': 'success',
            'logs': logs[-100:]  # آخر 100 سجل
        })
    except FileNotFoundError:
        return jsonify({
            'status': 'error',
            'message': 'ملف السجلات غير موجود',
            'logs': []
        })

@app.route('/api/sources')
def get_sources():
    """API لجلب معلومات المصادر"""
    sources_info = []
    for key, config in CONFIG['sources'].items():
        sources_info.append({
            'key': key,
            'name': config['name'],
            'url': config['url'],
            'enabled': config['enabled'],
            'status': 'نشط' if config['enabled'] else 'معطل'
        })
    
    return jsonify({
        'status': 'success',
        'sources': sources_info
    })

@app.route('/api/status')
def get_status():
    """حالة البوت والنظام"""
    global telegram_scheduler
    
    telegram_status = "معطل"
    if telegram_scheduler and telegram_scheduler.is_running:
        telegram_status = "نشط"
    elif os.getenv('TELEGRAM_TOKEN') and os.getenv('CHAT_ID'):
        telegram_status = "جاهز"
    
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'bot_name': 'بوت الأخبار السورية المطور',
        'version': '3.0',
        'last_update': last_update.isoformat() if last_update else None,
        'sources_count': len(CONFIG['sources']),
        'active_sources': len([s for s in CONFIG['sources'].values() if s['enabled']]),
        'telegram_status': telegram_status,
        'telegram_configured': bool(os.getenv('TELEGRAM_TOKEN') and os.getenv('CHAT_ID')),
        'huggingface_configured': bool(os.getenv('HUGGING_FACE_TOKEN'))
    })

@app.route('/api/telegram/send', methods=['POST'])
def send_to_telegram():
    """إرسال يدوي للأخبار إلى تيليجرام"""
    try:
        result = manual_send()
        return jsonify({
            'status': 'success' if result else 'warning',
            'message': 'تم إرسال الأخبار بنجاح' if result else 'لم يتم العثور على أخبار جديدة'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ في الإرسال: {str(e)}'
        })

@app.route('/api/telegram/scheduler/start', methods=['POST'])
def start_telegram_scheduler():
    """بدء مجدول التليجرام"""
    global telegram_scheduler, scheduler_thread
    
    try:
        if not os.getenv('TELEGRAM_TOKEN') or not os.getenv('CHAT_ID'):
            return jsonify({
                'status': 'error',
                'message': 'يجب إعداد TELEGRAM_TOKEN و CHAT_ID أولاً'
            })
        
        if telegram_scheduler and telegram_scheduler.is_running:
            return jsonify({
                'status': 'warning',
                'message': 'المجدول يعمل بالفعل'
            })
        
        telegram_scheduler = TelegramScheduler()
        scheduler_thread = telegram_scheduler.run_in_background()
        
        return jsonify({
            'status': 'success',
            'message': 'تم بدء مجدول التليجرام بنجاح'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ في بدء المجدول: {str(e)}'
        })

@app.route('/api/telegram/scheduler/stop', methods=['POST'])
def stop_telegram_scheduler():
    """إيقاف مجدول التليجرام"""
    global telegram_scheduler
    
    try:
        if telegram_scheduler:
            telegram_scheduler.stop_scheduler()
            telegram_scheduler = None
        
        return jsonify({
            'status': 'success',
            'message': 'تم إيقاف مجدول التليجرام'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ في إيقاف المجدول: {str(e)}'
        })

@app.route('/api/config')
def get_config():
    """الحصول على إعدادات البوت"""
    return jsonify({
        'status': 'success',
        'config': {
            'telegram_token_set': bool(os.getenv('TELEGRAM_TOKEN')),
            'chat_id_set': bool(os.getenv('CHAT_ID')),
            'huggingface_token_set': bool(os.getenv('HUGGING_FACE_TOKEN')),
            'syria_focus': True,
            'auto_summary': True,
            'sources': CONFIG['sources']
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'الصفحة غير موجودة'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'خطأ داخلي في الخادم'}), 500

if __name__ == '__main__':
    # إنشاء مجلد templates إذا لم يكن موجوداً
    os.makedirs('templates', exist_ok=True)
    
    # تحديث أولي للأخبار
    try:
        bot = NewsBot()
        latest_news = bot.get_all_news()
        last_update = datetime.now()
        print("تم تحديث الأخبار عند بدء التطبيق")
    except Exception as e:
        print(f"خطأ في التحديث الأولي: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
