#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for Cycling Rules Search
"""

import os
import logging
import random
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes
from search_rules import RulesSearcher
from daily_rules import SimpleDailyRules
from daily_scheduler import SimpleScheduler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CyclingRulesBot:
    def __init__(self, token: str):
        """Initialize the bot with token and rules searcher"""
        self.token = token
        self.searcher = RulesSearcher()
        self.daily_rules = SimpleDailyRules()
        self.scheduler = None
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup bot command and message handlers"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("rule", self.rule_command))
        self.application.add_handler(CommandHandler("random", self.random_command))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработка callback queries (для inline кнопок)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Inline режим - поиск в любом чате
        self.application.add_handler(InlineQueryHandler(self.handle_inline_query))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = (
            "🚴‍♂️ Добро пожаловать в бот Правил Велосипедистов!\n\n"
            "Я помогу тебе найти нужные правила из знаменитого свода Веломинати.\n\n"
            "🔍 Как использовать:\n"
            "• Просто напиши слово или фразу для поиска\n"
            "• Или напиши номер правила (например: 5)\n"
            "• Используй /search для поиска\n"
            "• Используй /rule для поиска по номеру\n"
            "• Используй /random для случайного правила\n"
            "• Используй /help для справки\n\n"
            "💡 Inline режим: Напиши @имя_бота + запрос в любом чате!\n"
            "🎲 Случайное правило: Напиши 'случайное' или 'random' в inline режиме\n\n"
            "Поиск работает на русском и английском языках!"
        )
        
        await update.message.reply_text(
            welcome_text
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "📚 Справка по использованию бота:\n\n"
            "🔍 Поиск:\n"
            "• Напиши любое слово или фразу\n"
            "• Бот найдет релевантные правила\n"
            "• Поиск работает на двух языках\n\n"
            "🔢 Поиск по номеру:\n"
            "• Просто напиши номер (например: 5)\n"
            "• Или используй команду /rule 5\n\n"
            "💡 Inline режим:\n"
            "• Напиши @имя_бота + запрос в любом чате\n"
            "• Например: @cycling_rules_bot шлем\n"
            "• Или: @cycling_rules_bot 42\n\n"
            "📝 Команды:\n"
            "/start - Начать работу\n"
            "/help - Показать справку\n"
            "/search <запрос> - Поиск по запросу\n"
            "/rule <номер> - Найти правило по номеру\n"
            "/random - Показать случайное правило\n\n"
            "💡 Примеры запросов:\n"
            "• шлем\n"
            "• bike\n"
            "• training\n"
            "• над головой\n"
            "• 42\n"
            "• случайное (или random, 🎲)\n\n"
            "🎯 Правила дня автоматически отправляются в группы каждый день в 10:00"
        )
        
        await update.message.reply_text(
            help_text
        )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if not context.args:
            await update.message.reply_text(
                "🔍 Использование: /search <запрос>\n\n"
                "Например:\n"
                "/search шлем\n"
                "/search bike\n"
                "/search training"
            )
            return
        
        query = " ".join(context.args)
        await self.perform_search(update, context, query)
    
    async def rule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rule command"""
        if not context.args:
            await update.message.reply_text(
                "🔢 Использование: /rule <номер>\n\n"
                "Например:\n"
                "/rule 5\n"
                "/rule 42"
            )
            return
        
        try:
            rule_number = int(context.args[0])
            await self.show_rule(update, context, rule_number)
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректный номер правила (например: /rule 5)"
            )
    
    async def random_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /random command"""
        try:
            rule_number = random.randint(1, 95)
            await self.show_rule(update, context, rule_number)
        except Exception as e:
            logger.error(f"Error showing random rule: {e}")
            await update.message.reply_text(
                "❌ Ошибка при показе случайного правила."
            )
    

    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        text = update.message.text.strip()
        
        if not text:
            return
        
        # Проверяем, является ли сообщение просто числом
        if text.isdigit():
            rule_number = int(text)
            await self.show_rule(update, context, rule_number)
        else:
            # Обычный поиск
            await self.perform_search(update, context, text)
    
    async def perform_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Perform search and show results"""
        try:
            # Показываем "печатает" индикатор
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Выполняем поиск
            results = self.searcher.fuzzy_search(query, threshold=0.5, max_results=5)
            
            if not results:
                await update.message.reply_text(
                    f"🔍 Поиск: {query}\n\n"
                    "❌ Ничего не найдено.\n\n"
                    "💡 Попробуйте:\n"
                    "• Другие ключевые слова\n"
                    "• Более простые запросы\n"
                    "• Поиск на другом языке"
                )
                return
            
            # Если найден только один результат и это прямое правило, показываем его
            if len(results) == 1 and results[0].get('is_direct_rule', False):
                await self.show_rule(update, context, results[0]['rule_number'])
                return
            
            # Показываем результаты поиска
            await self.show_search_results(update, context, query, results)
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при поиске. Попробуйте позже."
            )
    
    async def show_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, results: list):
        """Show search results with inline buttons"""
        # Создаем inline кнопки для каждого результата
        keyboard = []
        for result in results:
            button_text = f"Правило {result['rule_number']}"
            callback_data = f"rule_{result['rule_number']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Показываем краткие результаты
        results_text = f"🔍 Поиск: {query}\n\n"
        results_text += f"📋 Найдено {len(results)} результат(ов):\n\n"
        
        for i, result in enumerate(results, 1):
            # Обрезаем текст для краткости
            eng_preview = result['text_eng'][:100] + "..." if len(result['text_eng']) > 100 else result['text_eng']
            rus_preview = result['text_rus'][:100] + "..." if len(result['text_rus']) > 100 else result['text_rus']
            
            results_text += f"{i}. Правило {result['rule_number']}\n"
            results_text += f"   {eng_preview}\n"
            results_text += f"   {rus_preview}\n\n"
        
        results_text += "💡 Нажмите на кнопку, чтобы увидеть полное правило"
        
        await update.message.reply_text(
            results_text,
            reply_markup=reply_markup
        )
    
    async def show_rule(self, update: Update, context: ContextTypes.DEFAULT_TYPE, rule_number: int):
        """Show a specific rule by number"""
        try:
            rule = self.searcher.search_by_rule_number(rule_number)
            
            if not rule:
                await update.message.reply_text(
                    f"❌ Правило #{rule_number} не найдено.\n\n"
                    "💡 Всего правил: 95 (от 1 до 95)"
                )
                return
            
            # Форматируем правило в нужном формате
            rule_text = f"Правило {rule['rule_number']}\n\n"
            rule_text += f"{rule['text_eng']}\n\n"
            rule_text += f"{rule['text_rus']}"
            
            await update.message.reply_text(
                rule_text
            )
            
        except Exception as e:
            logger.error(f"Error showing rule {rule_number}: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при показе правила #{rule_number}"
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("rule_"):
            try:
                rule_number = int(query.data.split("_")[1])
                await self.show_rule(update, context, rule_number)
            except (ValueError, IndexError):
                await query.edit_message_text("❌ Ошибка при обработке запроса")
    
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline queries for searching rules in any chat"""
        query = update.inline_query.query.strip()
        
        if not query:
            # Показываем подсказки при пустом запросе
            results = [
                InlineQueryResultArticle(
                    id="help_1",
                    title="🔍 Поиск правил",
                    description="Начните вводить слово или фразу для поиска",
                    input_message_content=InputTextMessageContent(
                        message_text="🔍 Поиск правил велосипедистов\n\nНачните вводить слово или фразу для поиска правил."
                    )
                ),
                InlineQueryResultArticle(
                    id="help_2",
                    title="🔢 Поиск по номеру",
                    description="Введите номер правила (например: 5, 42)",
                    input_message_content=InputTextMessageContent(
                        message_text="🔢 Поиск по номеру\n\nВведите номер правила от 1 до 95."
                    )
                ),
                InlineQueryResultArticle(
                    id="help_3",
                    title="💡 Примеры запросов",
                    description="шлем, bike, training, над головой",
                    input_message_content=InputTextMessageContent(
                        message_text="💡 Примеры запросов:\n\n• шлем\n• bike\n• training\n• над головой\n• 42"
                    )
                ),
                InlineQueryResultArticle(
                    id="random_rule",
                    title="🎲 Случайное правило",
                    description="Напиши random чтобы получить случайное правило",
                    input_message_content=InputTextMessageContent(
                        message_text="🎲 Случайное правило\n\nНапишите @имя_бота + случайное слово для получения случайного правила."
                    )
                )
            ]
            await update.inline_query.answer(results)
            return
        
        try:
            # Проверяем, не запрашивает ли пользователь случайное правило
            random_keywords = ['случайное', 'random', 'случайно', 'любое', 'любое правило', 'random rule', '🎲', 'dice']
            is_random_request = any(keyword in query.lower() for keyword in random_keywords)
            
            if is_random_request:
                # Показываем случайное правило
                random_rule_number = random.randint(1, 95)
                random_rule = self.searcher.search_by_rule_number(random_rule_number)
                
                if random_rule:
                    message_text = f"🎲 Случайное правило {random_rule['rule_number']}\n\n"
                    message_text += f"{random_rule['text_eng']}\n\n"
                    message_text += f"{random_rule['text_rus']}"
                    
                    random_result = InlineQueryResultArticle(
                        id=f"random_{random_rule_number}",
                        title=f"🎲 Случайное правило {random_rule_number}",
                        description=f"Случайно выбранное правило: {random_rule['text_rus'][:100]}...",
                        input_message_content=InputTextMessageContent(
                            message_text=message_text
                        )
                    )
                    
                    await update.inline_query.answer([random_result])
                    return
            
            # Выполняем обычный поиск
            search_results = self.searcher.fuzzy_search(query, threshold=0.4, max_results=10)
            
            if not search_results:
                # Если ничего не найдено, показываем подсказку
                results = [
                    InlineQueryResultArticle(
                        id="no_results",
                        title="❌ Ничего не найдено",
                        description=f"Запрос: {query}",
                        input_message_content=InputTextMessageContent(
                            message_text=f"🔍 Поиск: {query}\n\n❌ Ничего не найдено.\n\n💡 Попробуйте другие ключевые слова или более простые запросы."
                        )
                    )
                ]
            else:
                # Формируем результаты для inline режима
                results = []
                
                for i, result in enumerate(search_results):
                    # Создаем краткое описание только на русском
                    rus_preview = result['text_rus'][:120] + "..." if len(result['text_rus']) > 120 else result['text_rus']
                    
                    # Формируем текст для отправки (полный текст на двух языках)
                    message_text = f"Правило {result['rule_number']}\n\n"
                    message_text += f"{result['text_eng']}\n\n"
                    message_text += f"{result['text_rus']}"
                    
                    # Создаем inline результат с русским описанием
                    inline_result = InlineQueryResultArticle(
                        id=f"rule_{result['rule_number']}",
                        title=f"Правило {result['rule_number']}",
                        description=rus_preview,
                        input_message_content=InputTextMessageContent(
                            message_text=message_text
                        )
                    )
                    results.append(inline_result)
            
            await update.inline_query.answer(results)
            
        except Exception as e:
            logger.error(f"Error in inline query: {e}")
            # В случае ошибки показываем сообщение об ошибке
            error_result = [
                InlineQueryResultArticle(
                    id="error",
                    title="❌ Ошибка поиска",
                    description="Произошла ошибка при поиске",
                    input_message_content=InputTextMessageContent(
                        message_text="❌ Произошла ошибка при поиске. Попробуйте позже."
                    )
                )
            ]
            await update.inline_query.answer(error_result)
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Cycling Rules Bot...")
        
        # Запускаем бота
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def run_with_scheduler(self):
        """Run bot with scheduler in async context"""
        logger.info("Starting Cycling Rules Bot with scheduler...")
        
        # Запускаем планировщик в отдельной задаче
        scheduler_task = asyncio.create_task(self.start_scheduler())
        
        # Запускаем бота
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        try:
            # Ждем завершения планировщика
            await scheduler_task
        except asyncio.CancelledError:
            pass
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
    
    async def start_scheduler(self):
        """Start the daily rules scheduler"""
        try:
            from telegram import Bot
            bot = Bot(self.token)
            self.scheduler = SimpleScheduler(bot)
            await self.scheduler.start()
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")


def main():
    """Main function to run the bot"""
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен!")
        print("💡 Установите токен: export TELEGRAM_BOT_TOKEN='your_token_here'")
        return
    
    # Создаем и запускаем бота
    bot = CyclingRulesBot(token)
    
    try:
        # Запускаем бота с планировщиком
        asyncio.run(bot.run_with_scheduler())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        logging.error(f"Bot startup error: {e}")


if __name__ == "__main__":
    main()
