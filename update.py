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

def get_absolute_ai_report(meta_summary, pro_matches, player_meta, real_matches):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"global_analysis": "API ключ не найден.", "personal_strategy": "Добавьте GEMINI_API_KEY в Secrets."}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Ты — главный аналитик киберспортивной организации уровня TI и дата-сайентист. 
        Перед тобой полная выгрузка сырой аналитики из Absolute Meta Tracker. Твоя задача — провести глубокий анализ.
        
        1. ГЛОБАЛЬНАЯ МЕТА (Immortal & High MMR): {meta_summary[:20]}
        2. ТЕКУЩИЕ ПРО-МАТЧИ (Последние результаты): {pro_matches[:5]}
        3. ЛИЧНАЯ СТАТИСТИКА ИГРОКА (Steam ID 872107609): {player_meta}
        4. ПРЕДСТОЯЩИЕ МАТЧИ LIQUIDEPEDIA: {real_matches if real_matches else "Ближайших матчей в расписании нет."}
        
        Выдай развернутый, жесткий аналитический отчёт, разделенный строго на два блока:
        
        БЛОК 1: Глобальный разбор патча и предикты. Какие скрытые имбы сейчас душат хай-ММР паблики, какие тренды забирают про-игроки, какие связки героев сейчас не контрятся. Если есть предстоящие матчи — дай по ним железный предикт с обоснованием. Если матчей в расписании нет — проанализируй форму про-команд на основе последних результатов.
        
        БЛОК 2: Персональная стратегия для игрока. Сопоставь глобальную мету с его личным винрейтом и пулом. Назови 3 идеальных героя из текущего S-тира, на которых он обязан поднимать ПТС прямо сейчас, и ткни носом в героев, которых ему категорически запрещено пикать, даже если они в тренде, потому что у него на них плохая статистика или не хватает комфорта.
        
        Пиши профессиональным дотерским сленгом, без цензуры, максимально откровенно, прямо и по делу.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Разделяем ответ на блоки для удобного вывода на фронтенд
        parts = text.split("БЛОК 2:")
        analysis = parts[0].replace("БЛОК 1:", "").strip()
        strategy = parts[1].strip() if len(parts) > 1 else "Анализ личного пула временно недоступен."
        
        return {
            "global_analysis": analysis,
            "personal_strategy": strategy
        }
    except Exception as e:
        return {"global_analysis": f"Ошибка генерации отчёта: {e}", "personal_strategy": ""}

def main():
    print("Запуск Absolute Telemetry Hub...")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'AbsoluteMetaTracker/2.0 (github.com/rekdekk; analytical bot)',
        'Accept-Encoding': 'gzip, deflate'
    })
    
    data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "player_id": "872107609",
        "player_perfomance": {},
        "meta_heroes": [],
        "ai_report": {}
    }

    try:
        # 1. Загрузка DotaConstants (Словарь предметов)
        print("Загрузка базы DotaConstants...")
        items_req = session.get("https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json").json()
        id_to_item = {str(v.get('id')): k for k, v in items_req.items() if 'id' in v}

        # 2. Выгрузка личной Big Data игрока
        print("Сбор расширенной телеметрии по Steam ID 872107609...")
        player_heroes = {}
        p_heroes_res = session.get("https://api.opendota.com/api/players/872107609/heroes", timeout=10)
        if p_heroes_res.status_code == 200:
            for h in p_heroes_res.json():
                player_heroes[str(h['hero_id'])] = h
                
        p_matches_res = session.get("https://api.opendota.com/api/players/872107609/matches?limit=100", timeout=10)
        if p_matches_res.status_code == 200:
            recent = p_matches_res.json()
            wins = sum(1 for m in recent if (m['player_slot'] < 128 and m['radiant_win']) or (m['player_slot'] >= 128 and not m['radiant_win']))
            data["player_perfomance"] = {
                "recent_winrate_last_100_games": f"{wins}%",
                "total_monitored_matches": len(recent)
            }

        # 3. Выгрузка глобальной статистики героев по всем брекетам
        print("Сбор многоуровневых массивов мета-героев...")
        hero_stats = session.get("https://api.opendota.com/api/heroStats").json()
        meta_summary_for_ai = []
        
        for index, h in enumerate(hero_stats):
            hero_id = h['id']
            name = h['localized_name']
            
            # Посегментный подсчет винрейтов
            def calc_bracket(p_key, w_key):
                picks = h.get(p_key, 0)
                wins = h.get(w_key, 0)
                return f"{round((wins / picks * 100), 1)}%" if picks > 0 else "0.0%"

            legend_wr = calc_bracket('5_pick', '5_win')
            ancient_wr = calc_bracket('6_pick', '6_win')
            divine_wr = calc_bracket('7_pick', '7_win')
            immortal_wr = calc_bracket('8_pick', '8_win')
            
            # Про-сцена телеметрия
            pro_picks = h.get('pro_pick', 0)
            pro_wins = h.get('pro_win', 0)
            pro_wr = f"{round((pro_wins / pro_picks * 100), 1)}%" if pro_picks > 0 else "0.0%"
            
            # Личные маркеры комфорта
            my_h_stats = player_heroes.get(str(hero_id), {})
            my_g = my_h_stats.get("games", 0)
            my_w = my_h_stats.get("win", 0)
            my_wr = round((my_w / my_g * 100), 1) if my_g > 0 else 0
            
            meta_summary_for_ai.append({
                "hero": name, "immortal_wr": immortal_wr, "pro_picks": pro_picks
            })

            # Постадийный сбор предметов (Безопасный асинхронный симулятор с задержкой)
            items_stages = {"starting": [], "early": [], "mid": [], "late": []}
            try:
                time.sleep(1.2) # ЖЕСТКИЙ ТАЙМ-АУТ ДЛЯ СНЯТИЯ БЛОКИРОВОК С СЕРВЕРА
                item_resp = session.get(f"https://api.opendota.com/api/heroes/{hero_id}/itemPopularity", timeout=10)
                if item_resp.status_code == 200:
                    pop = item_resp.json()
                    for api_key, stage_key in [('start_game_items', 'starting'), ('early_game_items', 'early'), ('mid_game_items', 'mid'), ('late_game_items', 'late')]:
                        sorted_ids = sorted(pop.get(api_key, {}).items(), key=lambda x: x[1], reverse=True)[:4]
                        for i_id, _ in sorted_ids:
                            i_name = id_to_item.get(str(i_id))
                            if i_name and "recipe" not in i_name:
                                items_stages[stage_key].append(i_name)
            except Exception:
                pass

            # Исправление ролей на основе жестких мета-паттернов
            role = "Support"
            if "Carry" in h.get('roles', []): role = "Carry"
            if h.get('primary_attr') == 'int' or "Midlane" in h.get('roles', []): role = "Mid"
            if name in ["Axe", "Centaur Warrunner", "Tidehunter", "Slardar", "Magnus", "Bristleback", "Doom", "Primal Beast"]: role = "Offlane"

            data["meta_heroes"].append({
                "id": hero_id,
                "name": name,
                "internal_name": h['name'].replace("npc_dota_hero_", ""),
                "role": role,
                "analytics": {
                    "winrate_3k_legend": legend_wr,
                    "winrate_4k_ancient": ancient_wr,
                    "winrate_5k_divine": divine_wr,
                    "winrate_6k_immortal": immortal_wr,
                    "pro_scene_winrate": pro_wr,
                    "pro_scene_bans": h.get('pro_ban', 0)
                },
                "personal_comfort": {
                    "matches_played": my_g,
                    "winrate": f"{my_wr}%",
                    "priority": "META_PICK" if my_wr >= 53.0 and my_g > 15 else "SITUATIONAL"
                },
                "builds": items_stages
            })
            
            if index % 20 == 0 and index > 0:
                print(f"Парсинг Big Data: Скомпилировано {index} / 124 героев...")

        # 4. Сбор турнирных данных (OpenDota Pro Matches)
        print("Сбор логов турнирных матчей...")
        pro_matches_res = session.get("https://api.opendota.com/api/proMatches").json()
        pro_summary = [f"{m.get('radiant_name')} vs {m.get('dire_name')} (Winner: {'Radiant' if m.get('radiant_win') else 'Dire'})" for m in pro_matches_res[:5]]

        # 5. Сбор расписания Liquipedia через MediaWiki API
        print("Сбор расписания Liquipedia...")
        real_matches = []
        try:
            liq_res = session.get("https://liquipedia.net/dota2/api.php", params={
                "action": "parse", "page": "Liquipedia:Upcoming_and_ongoing_matches", "format": "json"
            }, timeout=15)
            if liq_res.status_code == 200:
                html = liq_res.json().get('parse', {}).get('text', {}).get('*', '')
                soup = BeautifulSoup(html, 'html.parser')
                for table in soup.find_all('table', class_='infobox_matches_content')[:5]:
                    t1 = table.find('td', class_='team-left')
                    t2 = table.find('td', class_='team-right')
                    if t1 and t2:
                        real_matches.append(f"{t1.get_text(strip=True)} vs {t2.get_text(strip=True)}")
        except Exception as e:
            print(f"Liquipedia API Limit: {e}")

        # 6. Запуск ИИ-Машины
        print("Запуск ИИ-Анализатора...")
        player_meta_summary = f"Recent WR: {data['player_perfomance'].get('recent_winrate_last_100_games')}. Топ сыгранных героев в базе."
        data["ai_report"] = get_absolute_ai_report(meta_summary_for_ai, pro_summary, player_meta_summary, "\n".join(real_matches))

        # Сортировка по винрейту на Имморталах
        data["meta_heroes"].sort(key=lambda x: float(x['analytics']['winrate_6k_immortal'].replace('%', '')), reverse=True)

        # Сохранение
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Компиляция Absolute Analytical Hub завершена! Файл data.json полностью обновлен.")

    except Exception as e:
        print(f"Критическая ошибка ядра: {e}")
    sys.exit(0)

if __name__ == "__main__":
    main()
