#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Daily Rules Manager
"""

import json
import random
import os
from typing import Dict, Optional
from search_rules import RulesSearcher

class SimpleDailyRules:
    def __init__(self, groups_file: str = "data/groups.json"):
        """Initialize simple daily rules manager"""
        self.groups_file = groups_file
        self.searcher = RulesSearcher()
        
        # Создаем папку data если её нет
        data_dir = os.path.dirname(groups_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        
        self.groups = self.load_groups()
    
    def load_groups(self) -> Dict:
        """Load groups from JSON file"""
        try:
            if os.path.exists(self.groups_file):
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем пустой файл если не существует
                empty_groups = {}
                self.save_groups(empty_groups)
                return empty_groups
        except Exception as e:
            print(f"Error loading groups: {e}")
            return {}
    
    def save_groups(self, groups: Dict) -> bool:
        """Save groups to JSON file"""
        try:
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(groups, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving groups: {e}")
            return False
    
    def add_group(self, group_id: int) -> bool:
        """Add new group if not exists"""
        group_id_str = str(group_id)
        
        if group_id_str not in self.groups:
            self.groups[group_id_str] = {
                "id": group_id,
                "used": [],
                "unused": list(range(1, 96))  # 1-95
            }
            return self.save_groups(self.groups)
        return True
    
    def get_daily_rule(self, group_id: int) -> Optional[Dict]:
        """Get daily rule for group"""
        try:
            group_id_str = str(group_id)
            
            # Проверяем, есть ли группа в файле
            if group_id_str not in self.groups:
                # Группы нет = не нужны правила дня
                return None
            
            group = self.groups[group_id_str]
            unused = group.get("unused", [])
            
            # Если unused пустой, перезаполняем из used
            if not unused:
                used = group.get("used", [])
                if used:
                    group["unused"] = used.copy()
                    group["used"] = []
                    unused = group["unused"]
                else:
                    # Если и used пустой, создаем заново
                    group["unused"] = list(range(1, 96))
                    unused = group["unused"]
            
            # Выбираем случайное правило
            if unused:
                rule_number = random.choice(unused)
                
                # Перемещаем правило из unused в used
                group["unused"].remove(rule_number)
                group["used"].append(rule_number)
                
                # Сохраняем изменения
                self.save_groups(self.groups)
                
                # Получаем текст правила
                rule = self.searcher.search_by_rule_number(rule_number)
                if rule:
                    return {
                        "rule_number": rule_number,
                        "text_eng": rule["text_eng"],
                        "text_rus": rule["text_rus"],
                        "used_count": len(group["used"]),
                        "unused_count": len(group["unused"])
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting daily rule for group {group_id}: {e}")
            return None
    
    def format_daily_rule_message(self, rule_data: Dict) -> str:
        """Format daily rule message"""
        message = f"🎯 *Правило дня #{rule_data['rule_number']}*\n\n"
        message += f"{rule_data['text_eng']}\n\n"
        message += f"{rule_data['text_rus']}"
        
        return message


def main():
    """Test the simple daily rules"""
    daily = SimpleDailyRules()
    
    print("🧪 Тестирование Simple Daily Rules")
    print("=" * 40)
    
    # Тестируем с существующей группой
    test_group_id = 4841035709
    
    # Получаем правило дня
    rule = daily.get_daily_rule(test_group_id)
    if rule:
        print(f"🎯 Правило дня #{rule['rule_number']}:")
        print(f"   Английский: {rule['text_eng'][:50]}...")
        print(f"   Русский: {rule['text_rus'][:50]}...")
        print(f"   Использовано: {rule['used_count']}/95")
        print(f"   Осталось: {rule['unused_count']}")
    else:
        print("❌ Ошибка получения правила дня")
    
    # Показываем содержимое файла
    print(f"\n📁 Файл {daily.groups_file}:")
    with open(daily.groups_file, 'r', encoding='utf-8') as f:
        content = json.load(f)
        print(json.dumps(content, ensure_ascii=False, indent=2))
    
    print("\n🎉 Тестирование завершено!")


if __name__ == "__main__":
    main()
