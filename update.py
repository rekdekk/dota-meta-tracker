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

def get_ai_predictions(meta_data, raw_schedule_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "ИИ-аналитика недоступна. Добавьте GEMINI_API_KEY."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Ты — старший аналитик Dota 2.
        Вот список актуальных мета-героев (винрейт 3000+ MMR): {meta_data[:10]}
        
        А вот сырой текст со страницы расписания предстоящих матчей Liquipedia:
        {raw_schedule_text[:3000]}
        
        Твоя задача:
        1. Найди в этом тексте 3-4 ближайших ПРЕДСТОЯЩИХ матча (Team A vs Team B).
        2. Опираясь на текущую мету, сделай жесткий и точный предикт победителя для каждого матча.
        3. Напиши краткий инсайт, почему именно эта команда заберет серию.
        Выведи результат в структурированном виде, без воды.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Сбой ИИ: {e}"

def main():
    print("Инициализация Absolute Hub (3000+ MMR, Pro Scene, Personal Comfort)...")
    
    session = requests.Session()
    # Жесткая маскировка под реального пользователя для обхода блокировок
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    })
    
    data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "player_id": "872107609",
        "meta_heroes": [],
        "upcoming_pro_matches": "",
    }

    try:
        # 1. Загрузка базы предметов
        print("Подгрузка DotaConstants...")
        items_req = session.get("https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json").json()
        id_to_item = {str(v.get('id')): k for k, v in items_req.items() if 'id' in v}

        # 2. Выгрузка личной статистики игрока (Зона комфорта)
        print("Сбор персональной статистики (Steam ID 872107609)...")
        player_data = {}
        player_resp = session.get("https://api.opendota.com/api/players/872107609/heroes", timeout=10)
        if player_resp.status_code == 200:
            for item in player_resp.json():
                player_data[str(item['hero_id'])] = item
        else:
            print("Не удалось получить стату профиля. Идем дальше.")

        # 3. Выгрузка глобальной статистики
        print("Выгрузка статистики героев (3000+ MMR и Pro Scene)...")
        hero_stats = session.get("https://api.opendota.com/api/heroStats").json()
        
        meta_summary_for_ai = []
        
        for index, h in enumerate(hero_stats):
            hero_id = h['id']
            name = h['localized_name']
            
            # Агрегация пабликов от 3000 MMR (Legend) до Immortal
            # OpenDota brackets: 5=Legend, 6=Ancient, 7=Divine, 8=Immortal
            high_picks = sum(h.get(f"{i}_pick", 0) for i in range(5, 9))
            high_wins = sum(h.get(f"{i}_win", 0) for i in range(5, 9))
            high_winrate = round((high_wins / high_picks * 100), 1) if high_picks > 0 else 0
            
            # Про-сцена
            pro_picks = h.get('pro_pick', 0)
            pro_wins = h.get('pro_win', 0)
            pro_bans = h.get('pro_ban', 0)
            pro_winrate = round((pro_wins / pro_picks * 100), 1) if pro_picks > 0 else 0
            
            # Интеграция личного комфорта
            my_stats = player_data.get(str(hero_id), {})
            my_games = my_stats.get("games", 0)
            my_wins = my_stats.get("win", 0)
            my_winrate = round((my_wins / my_games * 100), 1) if my_games > 0 else 0
            my_comfort = "High" if my_games > 30 and my_winrate >= 50 else ("Medium" if my_games > 10 else "Low")

            if high_picks > 10000 and high_winrate > 51:
                meta_summary_for_ai.append(f"{name} ({high_winrate}%)")

            # Предметы (с паузой для защиты от бана)
            early_game, mid_game, late_game = [], [], []
            try:
                time.sleep(1.2) # ЖЕСТКО НЕ ТРОГАТЬ. ЭТО ЗАЩИТА ОТ БАНА OPENDOTA.
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
                "pro_bans": pro_bans,
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

        # 4. Предстоящие матчи (Парсинг Liquipedia)
        print("Сбор расписания предстоящих матчей...")
        try:
            # Парсим открытый хаб матчей
            liq_url = "https://liquipedia.net/dota2/Liquipedia:Upcoming_and_ongoing_matches"
            req = session.get(liq_url, timeout=15)
            if req.status_code == 200:
                soup = BeautifulSoup(req.text, 'html.parser')
                # Вытягиваем весь текст из таблиц с матчами
                matches_text = " ".join([t.get_text(separator=' ') for t in soup.find_all('table', class_='infobox_matches_content')[:10]])
            else:
                matches_text = "Не удалось пробить Cloudflare Liquipedia. Анализируй текущие тренды турниров."
        except Exception:
            matches_text = "Ошибка соединения с турнирными хабами."

        # 5. ИИ-Предикты на основе расписания
        print("Генерация предиктов предстоящих игр...")
        data["upcoming_pro_matches"] = get_ai_predictions(meta_summary_for_ai, matches_text)
        print(f"ИИ выдал расписание и предикты:\n{data['upcoming_pro_matches']}")

        # Сортируем героев по винрейту на 3000+ MMR перед сохранением (чтобы топ был в начале)
        data["meta_heroes"].sort(key=lambda x: float(x['pub_3000_plus_winrate'].replace('%', '')), reverse=True)

        # 6. Сохранение
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Абсолютный хаб успешно скомпилирован! Объем данных колоссальный.")

    except Exception as e:
        print(f"Критический сбой: {e}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
