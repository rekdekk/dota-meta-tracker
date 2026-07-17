import json
import time
import sys
import os
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
        Действуй как старший аналитик Dota 2 уровня The International.
        Вот свежие данные по героям на Immortal ранге (топ-3 по винрейту): {meta_data[:3]}
        Вот последние результаты про-сцены: {pro_matches[:2]}
        
        Напиши краткий, жесткий и точный абзац (до 4 предложений) с анализом текущей меты и сделай предикт: на что стоит обращать внимание в драфтах в ближайшие дни. Пиши на русском языке, без воды, профессиональным сленгом.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Сбой ИИ-модуля: {e}"

def main():
    print("Инициализация Absolute Meta Parser + AI Engine...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AbsoluteMetaTracker/1.0'}
    
    data = {"meta_heroes": [], "teams": [], "tournament": {}, "ai_insight": ""}

    try:
        print("1. Получение Immortal статистики (Аналог D2PT)...")
        hero_stats = requests.get("https://api.opendota.com/api/heroStats", headers=headers).json()
        hero_stats.sort(key=lambda x: x.get('8_pick', 0), reverse=True)

        meta_summary_for_ai = []

        for h in hero_stats:
            hero_id = h['id']
            name = h['localized_name']
            
            immortal_picks = h.get('8_pick', 0)
            immortal_wins = h.get('8_win', 0)
            winrate = round((immortal_wins / immortal_picks * 100), 1) if immortal_picks > 0 else 0
            
            # Для промпта ИИ собираем только лучших
            if immortal_picks > 2000 and winrate > 52:
                meta_summary_for_ai.append(f"{name} ({winrate}%)")

            # Жесткое исправление ролей
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
                "core_items": ["black_king_bar", "blink"] # Базовый билд для скорости
            })

        print("2. Получение данных Pro-сцены...")
        pro_matches = requests.get("https://api.opendota.com/api/proMatches", headers=headers).json()
        
        live_matches = []
        matches_for_ai = []
        for pm in pro_matches[:5]:
            team_a = pm.get("radiant_name", "Radiant")
            team_b = pm.get("dire_name", "Dire")
            winner = team_a if pm.get("radiant_win") else team_b
            
            matches_for_ai.append(f"{team_a} vs {team_b} (Winner: {winner})")
            live_matches.append({
                "time": "Завершен",
                "team_a": team_a,
                "team_b": team_b,
                "prediction": f"Победитель: {winner}",
            })
        
        data["tournament"] = {
            "name": "Live Pro Tracker",
            "matches": live_matches
        }

        print("3. Запуск ИИ-Аналитика...")
        data["ai_insight"] = get_ai_analysis(meta_summary_for_ai, matches_for_ai)
        print(f"ИИ выдал вердикт: {data['ai_insight']}")

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Сбор РЕАЛЬНЫХ данных и ИИ-анализа завершен!")

    except Exception as e:
        print(f"Критическая ошибка парсинга: {e}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
