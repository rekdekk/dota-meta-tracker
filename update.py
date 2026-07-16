import json
import os
import requests
from datetime import datetime

# Настройки ELO
STARTING_ELO = 1200
K_FACTOR = 40 

def calculate_expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def update_elo(rating_a, rating_b, score_a):
    expected_a = calculate_expected_score(rating_a, rating_b)
    expected_b = calculate_expected_score(rating_b, rating_a)
    new_rating_a = rating_a + K_FACTOR * (score_a - expected_a)
    new_rating_b = rating_b + K_FACTOR * ((1 - score_a) - expected_b)
    return round(new_rating_a, 1), round(new_rating_b, 1)

def run_tracker_engine():
    print("Запуск 3-Tier Meta Engine...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    db_path = 'data.json'
    db = {}
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            try: db = json.load(f)
            except: pass

    elo_history = db.get("team_elo", {})
    processed_matches = set(db.get("processed_matches", []))

    # ==========================================
    # 1. ПРО-СЦЕНА (Tier 1 - Tier 3 Турниры)
    # ==========================================
    print("Сбор результатов Pro-матчей...")
    try:
        # Получаем последние официальные турнирные матчи (Valve учитывает Tier 1-3)
        matches = requests.get("https://api.opendota.com/api/proMatches", headers=headers, timeout=10).json()
    except:
        matches = []

    playoffs = []
    
    for m in reversed(matches[:200]): # Берем 200 последних матчей для объективности
        match_id = m.get('match_id')
        if not match_id: continue
        
        r_name = m.get('radiant_name', 'Radiant')
        d_name = m.get('dire_name', 'Dire')
        r_win = m.get('radiant_win', True)
        
        if r_name not in elo_history: elo_history[r_name] = STARTING_ELO
        if d_name not in elo_history: elo_history[d_name] = STARTING_ELO
        
        if match_id not in processed_matches:
            score_r = 1 if r_win else 0
            new_r, new_d = update_elo(elo_history[r_name], elo_history[d_name], score_r)
            elo_history[r_name] = new_r
            elo_history[d_name] = new_d
            processed_matches.add(match_id)

            # Сохраняем свежие матчи для сетки (последние 10)
            if len(playoffs) < 10:
                playoffs.insert(0, {
                    "match_id": match_id,
                    "league": m.get('league_name', 'Pro Circuit'),
                    "team_a": r_name,
                    "team_b": d_name,
                    "score": "1 - 0" if r_win else "0 - 1",
                    "winner": r_name if r_win else d_name,
                    "time": datetime.utcfromtimestamp(m.get('start_time', 0)).strftime('%d.%m %H:%M')
                })

    # ==========================================
    # 2. АБСОЛЮТНАЯ МЕТА (3 Уровня)
    # ==========================================
    print("Сбор статистики героев (3-5k, 8k+, Pro)...")
    try:
        heroes_data = requests.get("https://api.opendota.com/api/heroStats", headers=headers, timeout=10).json()
    except:
        heroes_data = []

    meta_heroes = []
    total_pro_matches = sum(h.get('pro_pick', 0) for h in heroes_data) / 10 # Примерное кол-во матчей
    
    for h in heroes_data:
        # Уровень 1: Паблики 3000-5000 MMR (Legend & Ancient - OpenDota Ranks 5-6)
        pick_4k = h.get('5_pick', 0) + h.get('6_pick', 0)
        win_4k = h.get('5_win', 0) + h.get('6_win', 0)
        wr_4k = (win_4k / pick_4k * 100) if pick_4k > 0 else 50.0

        # Уровень 2: Паблики 8000+ MMR (Immortal - OpenDota Rank 8)
        pick_8k = h.get('8_pick', 0)
        win_8k = h.get('8_win', 0)
        wr_8k = (win_8k / pick_8k * 100) if pick_8k > 0 else 50.0

        # Уровень 3: Профессиональная сцена (Официальные матчи Tier 1-3)
        pro_pick = h.get('pro_pick', 0)
        pro_win = h.get('pro_win', 0)
        pro_ban = h.get('pro_ban', 0)
        wr_pro = (pro_win / pro_pick * 100) if pro_pick > 0 else 50.0
        pb_rate_pro = ((pro_pick + pro_ban) / total_pro_matches * 100) if total_pro_matches > 0 else 0
        
        # Расчет общего Тира на основе 3 показателей
        tier = "B"
        if wr_8k >= 52.0 and pb_rate_pro > 30: tier = "S"
        elif wr_8k >= 50.5 or wr_pro >= 51.0: tier = "A"
        elif wr_4k < 48.0 and wr_8k < 48.0: tier = "C"

        meta_heroes.append({
            "name": h.get('localized_name', 'Unknown'),
            "role": h.get('roles', ['Flex'])[0],
            "tier": tier,
            "stats_4k": { "winrate": f"{wr_4k:.1f}%" },
            "stats_8k": { "winrate": f"{wr_8k:.1f}%", "pickrate": pick_8k },
            "stats_pro": { "winrate": f"{wr_pro:.1f}%", "pb_rate": f"{pb_rate_pro:.1f}%", "bans": pro_ban },
            "core_items": ["black_king_bar", "blink"], # Заглушка, можно расширить через Stratz API
            "innate_ability": "Анализ патча активен",
            "best_with": [], "counters": []
        })
    
    # Сортируем по силе на 8к + Про-сцене
    meta_heroes.sort(key=lambda x: float(x['stats_8k']['winrate'].strip('%')) + float(x['stats_pro']['pb_rate'].strip('%')), reverse=True)

    # ==========================================
    # 3. ИИ-Предикты и Команды
    # ==========================================
    upcoming_predictions = []
    sorted_teams = sorted(elo_history.items(), key=lambda x: x[1], reverse=True)
    top_teams = [{"name": k, "power_index": int((v/2000)*100), "status": "Tier-1" if v > 1350 else ("Tier-2" if v > 1250 else "Tier-3")} for k, v in sorted_teams[:20]]

    # Предикты для последних турнирных стычек
    for m in playoffs[:6]:
        r_rating = elo_history.get(m['team_a'], STARTING_ELO)
        d_rating = elo_history.get(m['team_b'], STARTING_ELO)
        exp_a = calculate_expected_score(r_rating, d_rating)
        
        odds_a = round(1 / exp_a, 2) if exp_a > 0 else 1.01
        odds_b = round(1 / (1 - exp_a), 2) if exp_a < 1 else 1.01

        upcoming_predictions.append({
            "league": m['league'],
            "time": m['time'],
            "team_a": m['team_a'],
            "team_b": m['team_b'],
            "prediction": f"Шанс {m['team_a']}: {int(exp_a*100)}%",
            "odds_a": str(odds_a),
            "odds_b": str(odds_b),
            "ai_reasoning": f"ELO {m['team_a']} ({int(r_rating)}) vs ELO {m['team_b']} ({int(d_rating)})."
        })

    final_data = {
        "last_updated": datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC'),
        "processed_matches": list(processed_matches)[-1500:], 
        "team_elo": elo_history,
        "meta_heroes": meta_heroes[:120],
        "teams": top_teams,
        "tournament": {
            "name": "Global Pro Circuit (Tier 1-3)",
            "playoffs": playoffs[:10],
            "predictions": upcoming_predictions
        }
    }

    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("Успех! База данных (3-Tier) обновлена.")

if __name__ == "__main__":
    run_tracker_engine()
