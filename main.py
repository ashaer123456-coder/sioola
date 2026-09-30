import requests
import time
from datetime import datetime

# بيانات بوت التليجرام الخاص بك
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID_HERE'

# قائمة لتتبع العملات التي تم تنبيهها منعاً للتكرار المزعج
alerted_coins = {}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

def check_liquidity():
    # الاتصال المباشر بـ Binance API (يعمل بدون حظر على Render)
    url = "https://api.binance.com/api/v3/ticker/24hr"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"تنبيه API: حالة الاستجابة {response.status_code}")
            return

        data = response.json()
        if not isinstance(data, list):
            return

        # تصفية أزواج USDT فقط
        usdt_pairs = [
            item for item in data 
            if isinstance(item, dict) and item.get('symbol', '').endswith('USDT') 
            and not any(x in item['symbol'] for x in ['UP', 'DOWN'])
        ]
        
        # ترتيب حسب حجم التداول وأخذ أعلى 1000 عملة
        usdt_pairs = sorted(usdt_pairs, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)[:1000]

        now_str = datetime.now().strftime('%H:%M:%S')

        for item in usdt_pairs:
            symbol = item['symbol'].replace('USDT', '')
            price = float(item['lastPrice'])
            price_change = float(item['priceChangePercent'])
            trades_count = int(item['count'])
            high = float(item['highPrice'])
            low = float(item['lowPrice'])

            price_range = high - low
            position_in_range = ((price - low) / price_range) * 100 if price_range > 0 else 50
            rsi = min(max((position_in_range * 0.55) + (price_change * 1.4) + 32, 18), 92)
            vol_ratio = trades_count / 100000.0

            is_smart_money = (vol_ratio >= 1.3 and abs(price_change) <= 3.8)
            
            # حساب قوة الانفجار
            score = 0
            if 50 <= rsi <= 66: score += 30
            if vol_ratio >= 1.4: score += 30
            if is_smart_money: score += 25
            if 1.0 <= price_change <= 8.0: score += 15

            # تحديد نوع الحركة
            status_tag = ""
            if is_smart_money:
                status_tag = "🐋 تجميع حيتان خفي"
            elif vol_ratio >= 1.7 and price_change > 3:
                status_tag = "💧 تدفق سيولة ضخم"
            elif score >= 75:
                status_tag = "🚀 بداية انفجار وشيك"

            # إرسال تنبيه في حال اكتشاف بداية سيولة جديدة
            if status_tag != "":
                last_alert_time = alerted_coins.get(symbol, 0)
                if time.time() - last_alert_time > 3600:  # تنبيه كل ساعة كحد أقصى للعملة الواحدة
                    alerted_coins[symbol] = time.time()
                    
                    msg = (
                        f"🚨 *رصد جديد لتدفق السيولة!*\n\n"
                        f"🪙 *العملة:* #{symbol}\n"
                        f"⏱️ *توقيت البداية:* `{now_str}`\n"
                        f"📊 *الحالة:* {status_tag}\n"
                        f"💵 *السعر:* `${price}` ({price_change:+.2f}%)\n"
                        f"🔥 *قوة الانفجار:* `{score}%` | *RSI:* `{rsi:.1f}`\n\n"
                        f"📈 [تداول الآن على Binance](https://www.binance.com/ar/trade/{symbol}_USDT?type=spot)"
                    )
                    send_telegram_message(msg)
                    print(f"[{now_str}] تم إرسال تنبيه للعملة: {symbol}")

    except Exception as e:
        print(f"خطأ أثناء معالجة البيانات: {e}")

# التشغيل المستمر
if __name__ == "__main__":
    send_telegram_message("🤖 *تم تشغيل رادار السيولة السحابي بنجاح على Render!*")
    while True:
        check_liquidity()
        time.sleep(10)  # فحص كل 10 ثوانٍ