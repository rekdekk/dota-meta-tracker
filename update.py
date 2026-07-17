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

def get_pro_ai_analysis(meta_data, team_ratings, real_matches, player_data):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY отсутствует в GitHub Secrets. Анализ невозможен."
    
    try:
        genai.configure(api_key=api_key)
        # Подключаем флагманский Pro-мозг для глубокой аналитики
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""
        Ты — главный дата-сайентист и шеф-аналитик тир-1 киберспортивной организации в Dota 2. 
        Твоя цель — выжать абсолютную ценность из терабайта сырых данных для максимального винрейта.
        
        ВХОДНЫЕ ДАННЫЕ ДЛЯ АНАЛИЗА:
        1. Срез глобальной меты (Топ героев на 6k+ MMR, винрейты по брекетам): {json.dumps(meta_data[:25], ensure_ascii=False)}
        2. Официальный мировой рейтинг про-команд (ELO, статистика): {json.dumps(team_ratings[:20], ensure_ascii=False)}
        3. Расписание ближайших матчей с Liquipedia: {json.dumps(real_matches, ensure_ascii=False)}
        4. Личный профиль игрока (Steam ID 872107609, винрейты на героях): {json.dumps(player_data, ensure_ascii=False)}
        
        ВЫДАЙ ЖЕСТКИЙ И ОТКРОВЕННЫЙ ОТЧЕТ В ТРЕХ МЕГА-БЛОКАХ (используй дотерский профессиональный сленг, пиши без цензуры, прямо и цинично):
        
        АНАЛИЗ МЕТЫ И СКРЫТЫЕ ИМБЫ:
        Разбери, какие герои сейчас реально ломают винрейты на Divine/Immortal, а какие — переоцененный мусор. Объясни логику их сборок (почему именно эти лейт-предметы дают автовин). Ткни пальцем в скрытые синергии.
        
        РАСКЛАД ПО ПРО-СЦЕНЕ И ПРЕДИКТЫ:
        Если есть предстоящие матчи из списка — сопоставь ELO-рейтинг команд, их текущую форму и мета-пул. Сделай математически обоснованный предикт на результат серии и ключевых героев в драфтах. Если матчей прямо сейчас нет — детально разбери топ-3 сильнейших команд мира на основе их ELO, в чем их аппаратное превосходство над остальной сценой и кто сейчас в тир-2 зоне готовится выстрелить.
        
        ПЕРСОНАЛЬНАЯ СТРАТЕГИЯ ДЛЯ 872107609:
        Проанализируй его пул. Сравни его комфортных героев с текущей метой 3k-6k MMR. Выдай 3 железных героя для немедленного обуза ПТС и жестко запрети пикать тех мета-героев, на которых он руинит из-за нехватки винрейта или игр. Дай совет по макро-игре в текущем патче.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Критический сбой ИИ-анализатора: {e}"

def main():
    print("Запуск ультимативного аналитического хаба [DeepThink Mode]...")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'AbsoluteAnalyticsEngine/3.0 (github.com/rekdekk; pro-bot)',
        'Accept-Encoding': 'gzip, deflate'
    })
    
    data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "player_id": "872107609",
        "meta_heroes": [],
        "pro_teams_ranking": [],
        "upcoming_matches": [],
        "absolute_ai_verdict": ""
    }

    try:
        # 1. DotaConstants
        print("Сканирование базы предметов...")
        items_req = session.get("https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json").json()
        id_to_item = {str(v.get('id')): k for k, v in items_req.items() if 'id' in v}

        # 2. Личная статистика (Steam ID 872107609)
        print("Выкачивание личной Big Data...")
        player_profile = {}
        p_res = session.get("https://api.opendota.com/api/players/872107609/heroes", timeout=10)
        if p_res.status_code == 200:
            for h in p_res.json():
                if h['games'] > 0:
                    player_profile[str(h['hero_id'])] = {
                        "games": h['games'],
                        "winrate": f"{round((h['win']/h['games']*100), 1)}%"
                    }

        # 3. Мировой рейтинг про-команд (Чистый ELO без фейков)
        print("Выгрузка официального рейтинга команд Valve/OpenDota...")
        teams_res = session.get("https://api.opendota.com/api/teams").json()
        # Сортируем по ELO рейтингу
        teams_res.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        for t in teams_res[:30]: # Топ-30 команд планеты
            if t.get('name'):
                data["pro_teams_ranking"].append({
                    "team_id": t.get('id'),
                    "name": t.get('name'),
                    "elo_rating": t.get('rating'),
                    "total_wins": t.get('wins'),
                    "total_losses": t.get('losses')
                })

        # 4. Многоуровневый парсинг мета-героев
        print("Глубокий анализ MMR-сегментов (От Legend до Immortal)...")
        hero_stats = session.get("https://api.opendota.com/api/heroStats").json()
        
        for index, h in enumerate(hero_stats):
            hero_id = h['id']
            name = h['localized_name']
            
            def get_wr(p, w):
                return f"{round((h.get(w,0)/h.get(p,1)*100), 1)}%" if h.get(p,0) > 0 else "0.0%"

            # Вытаскиваем лейт-билды (с задержкой от банов)
            late_build = []
            try:
                time.sleep(1.2) # Жесткий тайм-аут, обманываем защиту Valve
                item_res = session.get(f"https://api.opendota.com/api/heroes/{hero_id}/itemPopularity", timeout=10)
                if item_res.status_code == 200:
                    pop = item_res.json().get('late_game_items', {})
                    top_items = sorted(pop.items(), key=lambda x: x[1], reverse=True)[:4]
                    for i_id, _ in top_items:
                        i_name = id_to_item.get(str(i_id))
                        if i_name and "recipe" not in i_name:
                            late_build.append(i_name)
            except Exception:
                pass

            role = "Support"
            if "Carry" in h.get('roles', []): role = "Carry"
            if h.get('primary_attr') == 'int' or "Midlane" in h.get('roles', []): role = "Mid"
            if name in ["Axe", "Centaur Warrunner", "Tidehunter", "Slardar", "Magnus", "Bristleback", "Doom", "Primal Beast", "Timbersaw"]: role = "Offlane"

            data["meta_heroes"].append({
                "id": hero_id,
                "name": name,
                "role": role,
                "brackets": {
                    "3k_legend": get_wr('5_pick', '5_win'),
                    "4k_ancient": get_wr('6_pick', '6_win'),
                    "5k_divine": get_wr('7_pick', '7_win'),
                    "6k_immortal": get_wr('8_pick', '8_win')
                },
                "pro_stats": {
                    "picks": h.get('pro_pick', 0),
                    "bans": h.get('pro_ban', 0),
                    "winrate": f"{round((h.get('pro_win',0)/h.get('pro_pick',1)*100), 1)}%" if h.get('pro_pick',0) > 0 else "0.0%"
                },
                "personal_stats": player_profile.get(str(hero_id), {"games": 0, "winrate": "0.0%"}),
                "meta_late_items": late_build or ["black_king_bar", "blink"]
            })
            
            if index % 30 == 0 and index > 0:
                print(f"Обработано {index}/124 героев...")

        # 5. Белый парсинг Liquipedia через API
        print("Сбор расписания матчей Liquipedia...")
        real_matches = []
        try:
            liq_res = session.get("https://liquipedia.net/dota2/api.php", params={
                "action": "parse", "page": "Liquipedia:Upcoming_and_ongoing_matches", "format": "json"
            }, timeout=15)
            if liq_res.status_code == 200:
                html = liq_res.json().get('parse', {}).get('text', {}).get('*', '')
                soup = BeautifulSoup(html, 'html.parser')
                for table in soup.find_all('table', class_='infobox_matches_content')[:8]:
                    t1 = table.find('td', class_='team-left')
                    t2 = table.find('td', class_='team-right')
                    if t1 and t2:
                        team1 = t1.get_text(strip=True)
                        team2 = t2.get_text(strip=True)
                        if team1 and team2:
                            real_matches.append({"match": f"{team1} vs {team2}"})
                            data["upcoming_matches"].append({"match": f"{team1} vs {team2}"})
        except Exception as e:
            print(f"Liquipedia Bypass Log: {e}")

        # Сортируем массив героев по винрейту на Имморталах для ИИ
        data["meta_heroes"].sort(key=lambda x: float(x['brackets']['6_immortal'].replace('%', '')), reverse=True)

        # 6. Запуск ультимативного ИИ-анализа на Gemini 2.5 Pro
        print("Активация нейромодуля Gemini 2.5 Pro...")
        data["absolute_ai_verdict"] = get_pro_ai_analysis(
            data["meta_heroes"], 
            data["pro_teams_ranking"], 
            real_matches, 
            player_profile
        )
        
        # Финальное сохранение базы
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Абсолютный аналитический хаб полностью обновлен и упакован!")

    except Exception as e:
        print(f"Глобальный сбой ядра: {e}")
    sys.exit(0)

if __name__ == "__main__":
    main()
