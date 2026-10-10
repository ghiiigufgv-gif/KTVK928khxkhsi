import asyncio
import logging
import random
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# បញ្ជី Bot Tokens
BOT_TOKENS = [
    "8885307855:AAGm6-_3fErVd9S6INHRHw1yJhY5lapmFd0",
    "8897978749:AAFMBMr4KZ5WWmbFXjgCVmLmfc29keHYDys",
    "8374550112:AAHP9raRVUAXszGGs3i1KgybbBqrjqDMwg4",
    "8621496558:AAEKAcAixTCVUTQHyf7X9ERITzYFqL012PI",
    "8990183023:AAFxihioYiC8nhizP6KWShItGmuRD8YI9Ho",
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# -------------------------------------------------------------
# បញ្ជីពាក្យ និង Emoji សម្រាប់ Detect
# -------------------------------------------------------------

SAD_KEYWORDS = [
    "sad", "depressed", "cry", "lonely", "hurt", "pain", "broken", "sorry", "miss",
    "សេដ", "ពិបាកចិត្ត", "ឈឺចាប់", "ខូចចិត្ត", "នឹក", "សោកស្ដាយ", "យំ", "អន់ចិត្ត", 
    "ឯកោ", "បាក់ទឹកចិត្ត", "ហត់", "ស្នេហា", "បែកគ្នា", "ខកបំណង", "បាក់", "ស្វិត"
]

SAD_EMOJIS = ["🥺", "💔", "😭", "😿", "🥀", "🖤", "☹️", "🙁", "😥", "😓"]

# Telegram Standard Reaction Emojis
ALLOWED_REACTIONS_MAP = {
    # ពេលសេត៖ React Emojis បែកបាក់/សេត
    "SAD": ["💔", "🥺", "😢", "😭"],
    
    # ពេលសប្បាយ/ធម្មតា៖ រាប់បញ្ចូលទាំង បេះដូងចេញភ្លើង ❤️‍🔥
    "HAPPY": ["❤️‍🔥", "😂", "🔥", "🥰", "🎉", "❤️"],
    
    # ករណីទូទៅ៖ មាន បេះដូងចេញភ្លើង ❤️‍🔥 ជាចម្បង
    "DEFAULT": ["❤️‍🔥", "❤️", "🔥", "🥰"]
}

def analyze_sentiment(target_msg) -> str:
    """ ពិនិត្យមើល Sentiment ពី Text, Caption និង រូបភាព/Media """
    text = target_msg.text or target_msg.caption or ""
    
    # ប្រសិនបើជាសារដែលផ្ញើរូបភាព ឬវីដេអូ ដោយគ្មាន Text
    # តែបើមាន Caption សេត/Emoji សេត វានឹង Detect តាម Caption នោះ
    text_lower = text.lower()
    
    # ពិនិត្យមើលថាមានពាក្យ សេត ឬ Emoji សេត ដែរឬទេ
    has_sad_word = any(kw in text_lower for kw in SAD_KEYWORDS)
    has_sad_emoji = any(emoji in text for emoji in SAD_EMOJIS)
    
    if has_sad_word or has_sad_emoji:
        return "SAD"
    
    # ប្រសិនបើជាអត្ថបទ ឬរូបភាពធម្មតា/សប្បាយ
    return "HAPPY"


async def reaction_worker(queue: asyncio.Queue, context: ContextTypes.DEFAULT_TYPE, bot_index: int):
    """ Worker Process សម្រាប់ចាត់ចែង Reaction តាម Queue """
    while True:
        target_msg = await queue.get()
        try:
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # វិភាគសារ (អត្ថបទ, 캡션, ឬរូបភាព)
            sentiment = analyze_sentiment(target_msg)
            
            # ជ្រើសរើស Emoji តាម Sentiment នោះ
            possible_emojis = ALLOWED_REACTIONS_MAP.get(sentiment, ALLOWED_REACTIONS_MAP["DEFAULT"])
            chosen_emoji = random.choice(possible_emojis)
            
            reaction_obj = ReactionTypeEmoji(emoji=chosen_emoji)
            await target_msg.set_reaction(reaction=[reaction_obj])
            
            print(f"⚡ [Bot {bot_index + 1}: {context.bot.first_name}] [{sentiment}] React: {chosen_emoji} លើ Msg ID: {target_msg.message_id}")
            
        except Exception as e:
            print(f"❌ [Bot {bot_index + 1}: {context.bot.first_name}] មិនអាច React បានទេ: {e}")
        finally:
            queue.task_done()

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Handler ពេលមាន Message ចូលមក (រូបភាព/អត្ថបទ/វីដេអូ...) """
    target_msg = update.message or update.channel_post
    if target_msg:
        queue: asyncio.Queue = context.bot_data["reaction_queue"]
        await queue.put(target_msg)

async def start_bot(token: str, index: int):
    """ Setup និង Start Bot """
    try:
        app = ApplicationBuilder().token(token).build()
        
        queue = asyncio.Queue()
        app.bot_data["reaction_queue"] = queue
        app.bot_data["bot_index"] = index
        
        # filters.ALL អនុញ្ញាតឱ្យ Catch គ្រប់ Message ទាំងអស់ (រូបភាព, អត្ថបទ, Sticker...)
        app.add_handler(MessageHandler(filters.ALL, auto_react))
        
        await app.initialize()
        await app.start()
        
        asyncio.create_task(reaction_worker(queue, app.context_types.context(app), index))
        
        await app.updater.start_polling(drop_pending_updates=True)
        print(f"✅ Botទី{index+1} (...{token[-8:]}) ដំណើរការជោគជ័យ!")
    except Exception as e:
        print(f"⚠️ Botទី{index+1} (...{token[-8:]}) មានបញ្ហា: {e}")

async def main():
    tasks = [start_bot(token, i) for i, token in enumerate(BOT_TOKENS)]
    await asyncio.gather(*tasks)
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 បានបិទ Bot ទាំងអស់!")
