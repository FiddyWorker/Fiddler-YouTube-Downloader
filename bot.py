import os
import zipfile
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pytube import YouTube, Playlist
import logging

# إعداد التسجيل لتصحيح الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# القائمة البيضاء: قائمة بمعرفات المستخدمين المسموح لهم
WHITELIST = {608907196}  # معرفك مضاف هنا

# وظيفة الأمر /start
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in WHITELIST:
        update.message.reply_text('عذرًا، أنت غير مصرح لك باستخدام هذا البوت.')
        return
    update.message.reply_text('مرحبًا! أرسل رابط فيديو يوتيوب أو قائمة تشغيل لتحميلها.')

# وظيفة لإضافة مستخدم إلى القائمة البيضاء
def add_to_whitelist(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id != 608907196:  # معرفك كمدير
        update.message.reply_text('عذرًا، هذا الأمر متاح للمدير فقط.')
        return
    
    try:
        new_user_id = int(context.args[0])
        WHITELIST.add(new_user_id)
        update.message.reply_text(f'تم إضافة المستخدم {new_user_id} إلى القائمة البيضاء.')
    except (IndexError, ValueError):
        update.message.reply_text('يرجى إرسال معرف المستخدم (رقم) بشكل صحيح. مثال: /add 123456789')

# وظيفة لتحميل الفيديو
def download_video(url: str, chat_id: int, context: CallbackContext) -> str:
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            return "لا يمكن العثور على فيديو بجودة مناسبة."
        
        output_path = f"downloads/{chat_id}"
        os.makedirs(output_path, exist_ok=True)
        file_path = stream.download(output_path=output_path)
        return file_path
    except Exception as e:
        logger.error(f"خطأ في تحميل الفيديو: {e}")
        return None

# وظيفة لتحميل قائمة تشغيل
def download_playlist(url: str, chat_id: int, context: CallbackContext) -> list:
    try:
        playlist = Playlist(url)
        output_path = f"downloads/{chat_id}"
        os.makedirs(output_path, exist_ok=True)
        file_paths = []
        
        for video_url in playlist.video_urls:
            file_path = download_video(video_url, chat_id, context)
            if file_path:
                file_paths.append(file_path)
        return file_paths
    except Exception as e:
        logger.error(f"خطأ في تحميل قائمة التشغيل: {e}")
        return []

# وظيفة لضغط الملفات
def create_zip(file_paths: list, chat_id: int) -> str:
    zip_path = f"downloads/{chat_id}/videos_{chat_id}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))
    return zip_path

# وظيفة التعامل مع الروابط
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in WHITELIST:
        update.message.reply_text('عذرًا، أنت غير مصرح لك باستخدام هذا البوت.')
        return

    chat_id = update.message.chat_id
    url = update.message.text

    update.message.reply_text('جاري معالجة الرابط...')
    
    if 'playlist' in url.lower():
        file_paths = download_playlist(url, chat_id, context)
    else:
        file_path = download_video(url, chat_id, context)
        file_paths = [file_path] if file_path else []

    if not file_paths:
        update.message.reply_text('فشل تحميل المحتوى. تأكد من الرابط وحاول مجددًا.')
        return

    if len(file_paths) > 1:
        zip_path = create_zip(file_paths, chat_id)
        with open(zip_path, 'rb') as zip_file:
            context.bot.send_document(chat_id=chat_id, document=zip_file)
        os.remove(zip_path)  # حذف ملف ZIP بعد الإرسال
    else:
        with open(file_paths[0], 'rb') as video_file:
            context.bot.send_document(chat_id=chat_id, document=video_file)

    # حذف الملفات المؤقتة من السيرفر
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)

# الوظيفة الرئيسية
def main() -> None:
    updater = Updater("8165591903:AAGYGR_K5vie-NsTBlr26OVqyMbsR5Zr2bQ", use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add", add_to_whitelist))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
