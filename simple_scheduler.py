#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Daily Rules Scheduler
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from telegram import Bot
from simple_daily import SimpleDailyRules

class SimpleScheduler:
    def __init__(self, bot: Bot, daily_time: time = time(10, 0)):
        """Initialize simple scheduler"""
        self.bot = bot
        self.daily_time = daily_time
        self.daily_rules = SimpleDailyRules()
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        self.logger.info("🚀 Simple Daily Rules Scheduler started (10:00 daily)")
        
        while self.running:
            try:
                # Ждем до следующего времени отправки
                await self.wait_until_next_run()
                
                if self.running:
                    # Отправляем правила дня во все группы
                    await self.send_daily_rules_to_all_groups()
                    
                    # Ждем 1 час перед следующей проверкой
                    await asyncio.sleep(3600)
                    
            except Exception as e:
                self.logger.error(f"Error in scheduler: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.logger.info("🛑 Simple Daily Rules Scheduler stopped")
    
    async def wait_until_next_run(self):
        """Wait until next scheduled time"""
        now = datetime.now()
        next_run = datetime.combine(now.date(), self.daily_time)
        
        # Если время уже прошло сегодня, планируем на завтра
        if now.time() >= self.daily_time:
            next_run += timedelta(days=1)
        
        # Вычисляем время ожидания
        wait_seconds = (next_run - now).total_seconds()
        
        if wait_seconds > 0:
            self.logger.info(f"⏰ Next daily rule at {next_run.strftime('%Y-%m-%d %H:%M')}")
            await asyncio.sleep(wait_seconds)
    
    async def send_daily_rules_to_all_groups(self):
        """Send daily rules to all registered groups"""
        try:
            groups = self.daily_rules.groups
            
            if not groups:
                self.logger.info("📝 No groups registered for daily rules")
                return
            
            self.logger.info(f"📤 Sending daily rules to {len(groups)} groups")
            
            for group_id_str in groups:
                try:
                    group_id = int(group_id_str)
                    await self.send_daily_rule_to_group(group_id)
                    await asyncio.sleep(1)  # Небольшая задержка между отправками
                    
                except Exception as e:
                    self.logger.error(f"Error sending to group {group_id_str}: {e}")
                    # Просто пропускаем группу и продолжаем
                    continue
            
            self.logger.info("✅ Daily rules sent to all groups")
            
        except Exception as e:
            self.logger.error(f"Error in send_daily_rules_to_all_groups: {e}")
    
    async def send_daily_rule_to_group(self, group_id: int):
        """Send daily rule to specific group"""
        try:
            self.logger.info(f"🔍 Getting daily rule for group {group_id}")
            
            # Получаем правило дня
            rule_data = self.daily_rules.get_daily_rule(group_id)
            
            if not rule_data:
                self.logger.warning(f"⚠️ No daily rule for group {group_id}")
                return
            
            self.logger.info(f"✅ Got rule #{rule_data['rule_number']} for group {group_id}")
            
            # Форматируем сообщение
            message = self.daily_rules.format_daily_rule_message(rule_data)
            
            self.logger.info(f"📤 Sending message to group {group_id}")
            
            # Отправляем в группу
            await self.bot.send_message(
                chat_id=group_id,
                text=message,
                parse_mode='Markdown'
            )
            
            self.logger.info(f"✅ Daily rule #{rule_data['rule_number']} sent to group {group_id}")
            
        except Exception as e:
            # Если ошибка доступа или другая проблема - просто логируем и продолжаем
            self.logger.warning(f"⚠️ Could not send to group {group_id}: {e}")
            # Не останавливаем процесс, продолжаем с другими группами


async def test_scheduler():
    """Test the simple scheduler"""
    import os
    
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        return
    
    print("🧪 Тестирование Simple Scheduler")
    print("=" * 40)
    
    # Создаем бота
    bot = Bot(token=token)
    
    # Создаем планировщик в тестовом режиме
    scheduler = SimpleScheduler(bot)
    
    # Тестируем отправку правила дня в тестовую группу
    test_group_id = 4841035709
    
    print(f"📤 Тестируем отправку в группу {test_group_id}...")
    
    try:
        await scheduler.send_daily_rule_to_group(test_group_id)
        print("✅ Тестовая отправка завершена")
    except Exception as e:
        print(f"❌ Ошибка тестовой отправки: {e}")
    
    print("\n📝 Планировщик готов к работе!")
    print("   🚀 Время отправки: 10:00 каждый день")
    print("   Группы: автоматически из groups.json")


if __name__ == "__main__":
    asyncio.run(test_scheduler())
