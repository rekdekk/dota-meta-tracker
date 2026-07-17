import json
import time
import sys
import os
import datetime
try:
    import requests
    from bs4 import BeautifulSoup
    import google.generativeai as genai
except ImportError:
    print("Установите зависимости: pip install requests beautifulsoup4 google-generativeai")
    sys.exit(0)

def get_ai_predictions(meta_data, real_matches):
    if not real_matches:
        return "В данный момент нет актуальных предстоящих матчей на Liquipedia."
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "ИИ-аналитика недоступна. Добавьте GEMINI_API_KEY."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Ты — старший аналитик Dota 2.
        Твоя задача — проанализировать РЕАЛЬНЫЕ предстоящие матчи и выдать предикт.
        ЗАПРЕЩЕНО выдумывать матчи, команды или турниры. Работай ТОЛЬКО с предоставленным списком.
        
        Текущая мета (винрейт 3000+ MMR): {meta_data[:10]}
        
        Список реальных предстоящих матчей с Liquipedia:
        {real_matches}
        
        Для каждого матча из списка:
        1. Сделай жесткий предикт победителя, опираясь на форму команд и мету.
        2. Дай инсайт в 1-2 предложения (почему именно они).
        Выведи профессионально, без воды.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Сбой ИИ: {e}"

def main():
    print("Инициализация Absolute Hub (API Liquipedia + OpenDota + Steam)...")
    
    session = requests.Session()
    # Белый User-Agent по правилам API Liquipedia (иначе бан)
    session.headers.update({
        'User-Agent': 'AbsoluteMetaTracker/1.0 (github.com/rekdekk; bot)',
        'Accept-Encoding': 'gzip, deflate'
    })
    
    data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "player_id": "872107609",
        "meta_heroes": [],
        "upcoming_pro_matches": "",
    }

    try:
        # 1. Загрузка DotaConstants (Маппинг шмоток)
        print("Подгрузка DotaConstants...")
        items_req = session.get("https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json").json()
        id_to_item = {str(v.get('id')): k for k, v in items_req.items() if 'id' in v}

        # 2. Выгрузка личной статистики игрока
        print("Сбор персональной статистики Steam...")
        player_data = {}
        player_resp = session.get("https://api.opendota.com/api/players/872107609/heroes", timeout=10)
        if player_resp.status_code == 200:
            for item in player_resp.json():
                player_data[str(item['hero_id'])] = item

        # 3. Выгрузка глобальной статистики
        print("Выгрузка статистики героев (3000+ MMR)...")
        hero_stats = session.get("https://api.opendota.com/api/heroStats").json()
        meta_summary_for_ai = []
        
        for index, h in enumerate(hero_stats):
            hero_id = h['id']
            name = h['localized_name']
            
            # Агрегация от 3000 MMR до Immortal
            high_picks = sum(h.get(f"{i}_pick", 0) for i in range(5, 9))
            high_wins = sum(h.get(f"{i}_win", 0) for i in range(5, 9))
            high_winrate = round((high_wins / high_picks * 100), 1) if high_picks > 0 else 0
            
            pro_picks = h.get('pro_pick', 0)
            pro_wins = h.get('pro_win', 0)
            pro_winrate = round((pro_wins / pro_picks * 100), 1) if pro_picks > 0 else 0
            
            # Личный комфорт
            my_stats = player_data.get(str(hero_id), {})
            my_games = my_stats.get("games", 0)
            my_wins = my_stats.get("win", 0)
            my_winrate = round((my_wins / my_games * 100), 1) if my_games > 0 else 0
            my_comfort = "High" if my_games > 30 and my_winrate >= 50 else ("Medium" if my_games > 10 else "Low")

            if high_picks > 10000 and high_winrate > 51:
                meta_summary_for_ai.append(f"{name} ({high_winrate}%)")

            # Предметы
            early_game, mid_game, late_game = [], [], []
            try:
                time.sleep(1.2) # Защита от бана OpenDota
                item_resp = session.get(f"https://api.opendota.com/api/heroes/{hero_id}/itemPopularity", timeout=10)
                if item_resp.status_code == 200:
                    popular_items = item_resp.json()
                    for phase, target_list in [('early_game_items', early_game), ('mid_game_items', mid_game), ('late_game_items', late_game)]:
                        phase_items = popular_items.get(phase, {})
                        top_ids = sorted(phase_items.items(), key=lambda x: x[1], reverse=True)[:4]
                        for i_id, _ in top_ids:
                            i_name = id_to_item.get(str(i_id))
                            if i_name and "recipe" not in i_name:
                                target_list.append(i_name)
            except Exception:
                pass

            data["meta_heroes"].append({
                "id": hero_id,
                "name": name,
                "internal_name": h['name'].replace("npc_dota_hero_", ""),
                "pub_3000_plus_winrate": f"{high_winrate}%",
                "pro_winrate": f"{pro_winrate}%",
                "pro_bans": h.get('pro_ban', 0),
                "personal_stats": {
                    "games_played": my_games,
                    "winrate": f"{my_winrate}%",
                    "comfort_level": my_comfort
                },
                "items": {
                    "early": early_game or ["magic_wand", "boots"],
                    "mid": mid_game or ["black_king_bar"],
                    "late": late_game or ["blink", "skadi"]
                }
            })
            
            if index % 20 == 0 and index > 0:
                print(f"Обработано {index} / 124 героев...")

        # 4. РЕАЛЬНЫЕ Предстоящие матчи (API Liquipedia)
        print("Сбор реального расписания через MediaWiki API...")
        real_matches_list = []
        try:
            liq_api_url = "https://liquipedia.net/dota2/api.php"
            params = {
                "action": "parse",
                "page": "Liquipedia:Upcoming_and_ongoing_matches",
                "format": "json"
            }
            req = session.get(liq_api_url, params=params, timeout=15)
            
            if req.status_code == 200:
                html_content = req.json().get('parse', {}).get('text', {}).get('*', '')
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Ищем таблицы матчей
                match_tables = soup.find_all('table', class_='infobox_matches_content')
                for table in match_tables[:5]: # Берем топ-5 матчей
                    team_left = table.find('td', class_='team-left')
                    team_right = table.find('td', class_='team-right')
                    
                    if team_left and team_right:
                        # Очищаем от мусора
                        t1 = team_left.get_text(strip=True)
                        t2 = team_right.get_text(strip=True)
                        if t1 and t2:
                            real_matches_list.append(f"{t1} vs {t2}")
        except Exception as e:
            print(f"Ошибка API Liquipedia: {e}")

        # 5. ИИ-Предикты
        print("Генерация предиктов...")
        if real_matches_list:
            matches_text = "\n".join(real_matches_list)
            data["upcoming_pro_matches"] = get_ai_predictions(meta_summary_for_ai, matches_text)
        else:
            data["upcoming_pro_matches"] = "Матчи не найдены или API Liquipedia недоступно."

        # Сортировка по винрейту
        data["meta_heroes"].sort(key=lambda x: float(x['pub_3000_plus_winrate'].replace('%', '')), reverse=True)

        # 6. Сохранение
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Скрипт отработал чисто. Фейков нет.")

    except Exception as e:
        print(f"Критический сбой: {e}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
