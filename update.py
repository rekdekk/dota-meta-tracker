import json
import time
import sys
import os
import datetime
try:
    import requests
    import google.generativeai as genai
except ImportError:
    print("Установите зависимости: pip install requests google-generativeai")
    sys.exit(0)

def get_ai_analysis(meta_data, pro_matches):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "ИИ-аналитика недоступна: добавьте GEMINI_API_KEY в GitHub Secrets."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Ты — старший драфтер и аналитик Dota 2. 
        Текущие тир-S герои на Immortal (с винрейтом): {meta_data[:5]}
        Последние про-матчи: {pro_matches[:3]}
        
        Напиши жесткий, профессиональный инсайт на 3-4 предложения. 
        Проанализируй мету, какие тенденции сейчас на хай-ММР и про-сцене. 
        Пиши без воды, используй дотерский сленг, выдай реальную ценность для предиктов.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Сбой ИИ: {e}"

def main():
    print("Инициализация Absolute Meta Parser (Real Dota Constants + AI)...")
    
    # Session позволяет переиспользовать TCP-соединение (работает быстрее и стабильнее)
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AbsoluteTracker/1.0'})
    
    # Добавлен таймстамп! Теперь файл всегда уникальный, Git не отменит пуш.
    data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta_heroes": [],
        "teams": [],
        "tournament": {},
        "ai_insight": ""
    }

    try:
        # 1. Тянем базу шмоток от Valve, чтобы переводить ID в нормальные названия
        print("Подгрузка DotaConstants (Маппинг предметов)...")
        items_req = session.get("https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json").json()
        id_to_item = {str(v.get('id')): k for k, v in items_req.items() if 'id' in v}

        # 2. Берем Immortal стату
        print("Выгрузка статистики Immortal-брекета...")
        hero_stats = session.get("https://api.opendota.com/api/heroStats").json()
        hero_stats.sort(key=lambda x: x.get('8_pick', 0), reverse=True)

        meta_summary_for_ai = []
        
        print("Начинаю глубокий скан предметов по каждому герою (Это займет ~3 минуты из-за анти-досс защиты)...")
        
        for index, h in enumerate(hero_stats):
            hero_id = h['id']
            name = h['localized_name']
            
            # Настоящий Immortal винрейт
            immortal_picks = h.get('8_pick', 0)
            immortal_wins = h.get('8_win', 0)
            winrate = round((immortal_wins / immortal_picks * 100), 1) if immortal_picks > 0 else 0
            
            if immortal_picks > 2000 and winrate > 52:
                meta_summary_for_ai.append(f"{name} ({winrate}%)")

            # Вытаскиваем РЕАЛЬНУЮ сборку с OpenDota
            core_items = []
            try:
                # Пауза 1.2 сек, чтобы GitHub не улетел в бан от Valve
                time.sleep(1.2)
                item_resp = session.get(f"https://api.opendota.com/api/heroes/{hero_id}/itemPopularity", timeout=10)
                
                if item_resp.status_code == 200:
                    popular_items = item_resp.json()
                    # Берем лейт-артефакты (то, с чем реально побеждают, а не промежуточный мусор)
                    late_items = popular_items.get('late_game_items', {})
                    
                    # Сортируем шмотки по популярности и берем топ-4
                    top_items_ids = sorted(late_items.items(), key=lambda x: x[1], reverse=True)[:4]
                    for item_id, count in top_items_ids:
                        item_name = id_to_item.get(str(item_id))
                        # Отсеиваем рецепты
                        if item_name and "recipe" not in item_name:
                            core_items.append(item_name)
            except Exception as e:
                print(f"Не удалось вытянуть шмотки для {name}: {e}")
            
            # Фоллбэк, если герой пустой или API залагало
            if not core_items:
                core_items = ["black_king_bar", "blink"]

            # Жесткий фактчекинг ролей (Игнорируем кривые теги Valve)
            actual_role = "Support"
            if "Carry" in h.get('roles', []): actual_role = "Carry"
            if h.get('primary_attr') == 'int' or "Midlane" in h.get('roles', []): actual_role = "Mid/Offlane"
            if name in ["Axe", "Centaur Warrunner", "Tidehunter", "Slardar", "Magnus", "Bristleback", "Doom"]: actual_role = "Offlane"

            data["meta_heroes"].append({
                "id": hero_id,
                "name": name,
                "internal_name": h['name'].replace("npc_dota_hero_", ""),
                "role": actual_role,
                "tier": "S" if winrate >= 52.0 and immortal_picks > 5000 else ("A" if winrate >= 50.0 else "B"),
                "winrate_d2pt": f"{winrate}%",
                "core_items": core_items
            })
            
            if index % 20 == 0 and index > 0:
                print(f"Обработано {index} / 124 героев...")

        # 3. Выгружаем Pro-сцену для предиктов
        print("Сканирование профессиональных матчей...")
        pro_matches = session.get("https://api.opendota.com/api/proMatches").json()
        
        live_matches = []
        matches_for_ai = []
        for pm in pro_matches[:5]:
            team_a = pm.get("radiant_name", "Radiant")
            team_b = pm.get("dire_name", "Dire")
            winner = team_a if pm.get("radiant_win") else team_b
            
            matches_for_ai.append(f"{team_a} vs {team_b} (Победитель: {winner})")
            live_matches.append({
                "time": "Завершен",
                "team_a": team_a,
                "team_b": team_b,
                "prediction": f"Победил {winner}",
            })
            
            # Добавляем команды в список команд турнира
            if not any(t.get("name") == team_a for t in data["teams"]) and team_a != "Radiant":
                data["teams"].append({"name": team_a, "power_index": 90, "status": "Pro"})
            if not any(t.get("name") == team_b for t in data["teams"]) and team_b != "Dire":
                data["teams"].append({"name": team_b, "power_index": 90, "status": "Pro"})
        
        data["tournament"] = {
            "name": "OpenDota Pro Tracker",
            "matches": live_matches
        }

        # 4. Анализ ИИ
        print("Генерация аналитики нейросетью...")
        data["ai_insight"] = get_ai_analysis(meta_summary_for_ai, matches_for_ai)
        print(f"Вердикт ИИ: {data['ai_insight']}")

        # 5. Сохранение
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Все данные успешно собраны и записаны в data.json!")

    except Exception as e:
        print(f"Критический сбой: {e}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
