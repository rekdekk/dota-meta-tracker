import json
import os
from datetime import datetime
import google.generativeai as genai

# Резервная база (если вдруг серверы Google упадут)
FALLBACK_DATA = {
    "last_updated": "Ошибка ИИ. Демо-режим",
    "meta_heroes": [
        {
            "name": "Shadow Fiend", "role": "Mid", "winrate_d2pt": "54.2%", "winrate_4k": "51.8%", 
            "tier": "S", "innate_ability": "Necromastery (души дают урон)", 
            "core_items": ["black_king_bar", "blink", "ultimate_scepter", "silver_edge"],
            "best_with": ["magnataur", "enigma"], "counters": ["templar_assassin", "viper"],
            "laning_winrate": "53.5%", "power_spike": "Мидгейм (15-25 мин)"
        },
        {
            "name": "Tiny", "role": "Mid", "winrate_d2pt": "55.4%", "winrate_4k": "52.1%", 
            "tier": "S", "innate_ability": "Craggy Exterior", 
            "core_items": ["blink", "power_treads", "black_king_bar", "echo_sabre"],
            "best_with": ["wisp", "rubick"], "counters": ["lifestealer", "necrolyte"],
            "laning_winrate": "55.0%", "power_spike": "Ранняя агрессия (10-20 мин)"
        }
    ],
    "teams": [
        {
            "name": "Team Falcons", "power_index": 95, "recent_results": "W-W-W-W-L",
            "status": "Тир-1 Фаворит", "playstyle": "Быстрый темп",
            "coach_strategy": "Сильный упор на контр-инициацию",
            "key_heroes": ["Razor", "Timbersaw"], "last_opponents": ["Spirit: W"]
        }
    ],
    "tournament": {
        "name": "Riyadh Masters / The International",
        "matches": [
            {"time": "Сегодня", "team_a": "Falcons", "team_b": "Spirit", "prediction": "Победа Falcons", "odds_a": "1.45", "odds_b": "2.80", "ai_reasoning": "Демо данные."}
        ]
    }
}

def fetch_data():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("ВНИМАНИЕ: Секрет GEMINI_API_KEY не найден!")
        FALLBACK_DATA["last_updated"] = f"{now} (Нет API ключа)"
        return FALLBACK_DATA

    try:
        genai.configure(api_key=api_key)
        
        # КРИТИЧЕСКИ ВАЖНО: Выкручиваем лимиты, чтобы ИИ не обрезал массив!
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=8192,  # Максимальная длина ответа
            temperature=0.2          # Минимум галлюцинаций, строгий сбор данных
        )
        
        model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            generation_config=generation_config
        )
        
        prompt = """
        Ты — Data Scientist и киберспортивный аналитик Dota 2. Собери самую свежую статистику для текущего патча 7.41+ (Без Аспектов, только Врожденные способности).
        
        КРИТИЧЕСКОЕ ПРАВИЛО (ЗАПРЕТ НА СОКРАЩЕНИЯ):
        Ты ОБЯЗАН сгенерировать ровно 20 разных героев в массиве meta_heroes. НЕ МЕНЬШЕ 20! Не используй фразы "и так далее" или "остальные герои". Выведи полный массив от начала до конца.
        
        Массив "teams" должен содержать РОВНО 5 лучших мировых команд.
        В объекте "tournament" в массиве "matches" должно быть РОВНО 4 предстоящих матча.

        Требуемая структура JSON:
        {
          "meta_heroes": [
            {
              "name": "Shadow Fiend", "role": "Mid/Carry/Offlane/Support", 
              "winrate_d2pt": "54.2%", "winrate_4k": "51.8%", "pickrate_d2pt": "15%", "banrate_pro": "42%", 
              "tier": "S", "innate_ability": "Опиши способность подробно", 
              "core_items": ["black_king_bar", "blink"], // 4 предмета
              "best_with": ["magnataur", "enigma"], // 2-3 героя
              "counters": ["templar_assassin"], // 2-3 героя
              "laning_winrate": "53.5%", "versatility": "4.2", 
              "damage_ratio": { "phys": 55, "mag": 45, "pure": 0 }, 
              "power_spike": "Мидгейм (15-25 мин)"
            }
            // СГЕНЕРИРУЙ 20 ТАКИХ ОБЪЕКТОВ
          ],
          "teams": [
            {
              "name": "Team Falcons", "power_index": 95, "recent_results": "W-W-W-W-L",
              "status": "Тир-1 Фаворит", "playstyle": "Быстрый темп",
              "average_match_length": "34:12", "win_rate_10m": "84%",
              "coach_strategy": "Контр-инициация", "key_heroes": ["Razor"], "last_opponents": ["Spirit: W"]
            }
            // СГЕНЕРИРУЙ 5 ТАКИХ ОБЪЕКТОВ
          ],
          "tournament": {
            "name": "Название Турнира",
            "matches": [
               { "time": "18:00", "team_a": "Falcons", "team_b": "Spirit", "prediction": "Победа Falcons 2:1", "odds_a": "1.45", "odds_b": "2.80", "ai_reasoning": "Анализ формы" }
               // СГЕНЕРИРУЙ 4 МАТЧА
            ]
          }
        }
        """
        
        # Безопасный вызов (в некоторых версиях SDK tools="google_search" вызывает ошибку, поэтому используем try-except)
        try:
            response = model.generate_content(prompt, tools='google_search')
        except:
            response = model.generate_content(prompt)
            
        data = json.loads(response.text)
        data["last_updated"] = f"{now} (Live API)"
        print(f"Успех! Сгенерировано героев: {len(data.get('meta_heroes', []))}")
        return data
        
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА ИИ: {e}")
        FALLBACK_DATA["last_updated"] = f"{now} (Fallback: Error)"
        return FALLBACK_DATA

if __name__ == "__main__":
    print("Запуск парсинга меты...")
    final_data = fetch_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    print("Файл data.json успешно перезаписан огромным массивом!")
