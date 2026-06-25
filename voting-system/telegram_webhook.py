"""
Telegram Bot Webhook - لربط حسابات المستخدمين تلقائياً
شغّل هذا الملف في terminal منفصل بجانب السيرفر الرئيسي
"""
import os
import sys

# Check if python-telegram-bot is installed
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:
    print("❌ مكتبة python-telegram-bot غير مثبتة")
    print("قم بتثبيتها باستخدام: pip install python-telegram-bot")
    sys.exit(1)

# Import database models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models import db, User
from flask import Flask

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ لم يتم تعيين TELEGRAM_BOT_TOKEN")
    print("استخدم: export TELEGRAM_BOT_TOKEN='your_token_here'")
    sys.exit(1)

# Initialize Flask app for database access
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///backend/voting.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    # Check if user provided phone number in deep link
    phone = context.args[0] if context.args else None
    
    if phone:
        # Link chat_id to user account
        with app.app_context():
            user = User.query.filter_by(phone_number=phone).first()
            if user:
                user.telegram_chat_id = str(chat_id)
                db.session.commit()
                await update.message.reply_text(
                    f"✅ مرحباً {user_name}!\n\n"
                    f"تم ربط حسابك بنجاح مع نظام التصويت.\n"
                    f"سوف تستقبل رموز التحقق (OTP) هنا عند تسجيل الدخول.\n\n"
                    f"🔒 حسابك: {user.name}\n"
                    f"📱 رقم الموبايل: {phone}"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ لم يتم العثور على حساب مرتبط برقم {phone}\n"
                    f"تأكد من التسجيل أولاً في نظام التصويت."
                )
    else:
        await update.message.reply_text(
            f"👋 مرحباً {user_name}!\n\n"
            f"أنا بوت نظام التصويت الإلكتروني.\n\n"
            f"📝 للربط مع حسابك:\n"
            f"1. سجّل في نظام التصويت\n"
            f"2. استخدم الرابط الذي سيظهر بعد التسجيل\n"
            f"3. سوف تستقبل رموز التحقق هنا تلقائياً\n\n"
            f"🔐 Chat ID الخاص بك: <code>{chat_id}</code>",
            parse_mode="HTML"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📖 <b>مساعدة - بوت نظام التصويت</b>\n\n"
        "<b>الأوامر المتاحة:</b>\n"
        "/start - بدء البوت وربط الحساب\n"
        "/help - عرض هذه المساعدة\n"
        "/chatid - عرض Chat ID الخاص بك\n\n"
        "<b>كيفية الاستخدام:</b>\n"
        "1. سجّل حساب في نظام التصويت\n"
        "2. افتح الرابط المرسل بعد التسجيل\n"
        "3. سوف تستقبل رموز OTP هنا عند تسجيل الدخول",
        parse_mode="HTML"
    )


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chatid command"""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 <b>Chat ID الخاص بك:</b>\n"
        f"<code>{chat_id}</code>\n\n"
        f"يمكنك استخدام هذا الرقم لربط حسابك يدوياً.",
        parse_mode="HTML"
    )


def main():
    """Start the bot"""
    print("🤖 جاري تشغيل بوت التليجرام...")
    print(f"📱 Bot Token: {TOKEN[:10]}...{TOKEN[-5:]}")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chatid", chatid_command))
    
    print("✅ البوت يعمل الآن!")
    print("📩 في انتظار الرسائل...")
    print("⏹️  اضغط Ctrl+C للإيقاف")
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
