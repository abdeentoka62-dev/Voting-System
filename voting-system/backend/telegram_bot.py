import os
from telethon.sync import TelegramClient

# الإعدادات الأساسية
API_ID = 38234906
API_HASH = '25e2ae3696e6583aad60a3136058a188'
session_path = os.path.join(os.path.dirname(__file__), 'gateway_auth_session')

def send_telegram_code(phone_number):
    """إرسال الكود مع فتح وقفل الاتصال في كل مرة"""
    # بنعرف الـ client هنا جوه عشان كل طلب يكون مستقل (بيمنع الـ Event loop error)
    client = TelegramClient(session_path, API_ID, API_HASH)
    try:
        client.connect()
        target = str(phone_number).strip()
        if not target.startswith('+'): target = '+' + target
            
        result = client.send_code_request(target)
        print(f"✅ [Telegram] Code sent to: {target}")
        return {"success": True, "phoneCodeHash": result.phone_code_hash}
    except Exception as e:
        print(f"❌ [Telegram Error]: {e}")
        return {"success": False, "error": str(e)}
    finally:
        client.disconnect() # بنقفل الاتصال فوراً بعد الإرسال

def verify_telegram_code(phone_number, code, phone_code_hash):
    """التحقق من الكود مع فتح وقفل الاتصال"""
    client = TelegramClient(session_path, API_ID, API_HASH)
    try:
        client.connect()
        target = str(phone_number).strip()
        if not target.startswith('+'): target = '+' + target

        client.sign_in(phone=target, code=code, phone_code_hash=phone_code_hash)
        print(f"✅ [Telegram] User Verified!")
        return {"success": True}
    except Exception as e:
        print(f"❌ [Verification Error]: {e}")
        return {"success": False, "error": str(e)}
    finally:
        client.disconnect() # بنقفل الاتصال عشان ميعملش تعارض