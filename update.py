import json
import os
import re
from datetime import datetime
import google.generativeai as genai

# Резервная база на случай, если сервера Google временно недоступны
FALLBACK_DATA = {
    "last_updated": "Ошибка API. Показаны резервные данные",
    "meta_heroes": [
        {
            "name": "Shadow Fiend", "role": "Mid", "winrate_d2pt": "54.2%", "winrate_4k": "51.8%", 
            "pickrate_d2pt": "15%", "banrate_pro": "42%", "tier": "S", 
            "innate_ability": "Necromastery (души дают урон)", 
            "core_items": ["black_king_bar", "blink", "ultimate_scepter", "silver_edge"],
            "best_with": ["magnataur", "enigma"], "counters": ["templar_assassin", "viper"],
            "laning_winrate": "53.5%", "versatility": "4.2", "damage_ratio": { "phys": 55, "mag": 45, "pure": 0 },
            "power_spike": "Мидгейм (15-25 мин)"
        }
    ],
    "teams": [
        {
            "name": "Team Falcons", "power_index": 95, "recent_results": "W-W-W-W-L", "status": "Тир-1 Фаворит",
            "playstyle": "Быстрый темп", "average_match_length": "34:12", "win_rate_10m": "84%",
            "coach_strategy": "Сильный упор на контр-инициацию",
            "key_heroes": ["Razor", "Timbersaw"], "last_opponents": ["Gaimin: W", "Xtreme: L"]
        }
    ],
    "tournament": {
        "name": "Live Tournament Offline", "stage": "TBA", "prize_pool": "TBA", "location": "TBA",
        "upcoming_matches": []
    }
}

def fetch_data_from_ai():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("ВНИМАНИЕ: Секрет GEMINI_API_KEY не найден в GitHub Actions! Используем резервные данные.")
        FALLBACK_DATA["last_updated"] = now
        return FALLBACK_DATA

    try:
        # Настройка и подключение к ИИ
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro') # Используем Pro версию для глубокой аналитики
        
        prompt = """
        Ты — киберспортивный дата-аналитик Dota 2. Используй поиск по интернету.
        Собери самую свежую статистику для патча 7.41+:
        1. Топ-10 актуальных героев меты (соедини данные 8k+ D2PT и 4k MMR). Укажи Innate Abilities (без аспектов).
        2. Топ-3 тир-1 команды и их текущую форму (Power Index).
        3. Информацию о текущем или ближайшем крупном турнире и расписание 3 матчей.
        
        Выведи результат СТРОГО в формате JSON, без приветствий, без Markdown-блоков (```json). Только сырой объект!
        Структура должна строго соответствовать ключам: "meta_heroes", "teams", "tournament".
        В "tournament" должны быть поля "name", "stage", "prize_pool", "location" и массив "upcoming_matches" (с полями team1, team2, date, time, bo, favorite, win_probability).
        """
        
        print("Отправка запроса в Google Gemini AI...")
        response = model.generate_content(prompt)
        
        # Броня от ошибок: Очищаем ответ от лишнего мусора и Markdown-разметки
        raw_text = response.text.strip()
        raw_text = re.sub(r"^```(?:json)?", "", raw_text).strip()
        raw_text = re.sub(r"```$", "", raw_text).strip()
        
        # Пробуем распарсить JSON
        data = json.loads(raw_text)
        data["last_updated"] = now
        print("Успех! Свежие данные от ИИ получены и расшифрованы.")
        return data
        
    except json.JSONDecodeError as e:
        print(f"ОШИБКА: ИИ вернул невалидный формат JSON. Подробности: {e}")
        print(f"Сырой ответ был:\n{raw_text}")
        FALLBACK_DATA["last_updated"] = now
        return FALLBACK_DATA
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")
        FALLBACK_DATA["last_updated"] = now
        return FALLBACK_DATA

if __name__ == "__main__":
    final_data = fetch_data_from_ai()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    print("Процесс обновления завершен. Файл data.json успешно перезаписан!")
