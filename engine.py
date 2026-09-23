import os
import json
import random
from datetime import datetime, timezone
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"
IDEAS_FILE = "ideas.json"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def should_trigger(days_passed):
    # Menos de 3 días de descanso: no dispara
    if days_passed < 3:
        return False
    # A partir del día 8: disparo forzado para no enfriar la rutina
    if days_passed >= 8:
        return True
    
    # Probabilidad gradual según días transcurridos
    probabilidades = {3: 0.20, 4: 0.35, 5: 0.55, 6: 0.75, 7: 0.90}
    return random.random() < probabilidades.get(days_passed, 0.40)

def send_telegram(idea):
    mensaje = (
        f"✨ *Misión Cupido de Hoy*\n\n"
        f"{idea['texto']}\n\n"
        f"⏱ *Tiempo:* {idea.get('tiempo', 'Rápido')}\n"
        f"🏷 *Tipo:* `#{idea.get('tipo', 'detalle')}`\n"
        f"🪙 *Gasto estimado:* ${idea.get('costo', 0)} MXN"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload, timeout=10)
    return res.status_code == 200

def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise ValueError("Faltan variables TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")

    state = load_json(STATE_FILE, {"last_sent": None, "used_ids": []})
    ideas = load_json(IDEAS_FILE, [])

    today = datetime.now(timezone.utc).date()

    if state.get("last_sent"):
        last_date = datetime.strptime(state["last_sent"], "%Y-%m-%d").date()
        days_passed = (today - last_date).days
    else:
        days_passed = 10  # Para que se ejecute la primera vez como prueba

    if not should_trigger(days_passed):
        print(f"Hoy no toca disparo. Días desde el último: {days_passed}")
        return

    # Evitar repetir ideas hasta agotar el ciclo
    available_ideas = [i for i in ideas if i["id"] not in state.get("used_ids", [])]
    if not available_ideas:
        state["used_ids"] = []
        available_ideas = ideas

    selected = random.choice(available_ideas)
    
    if send_telegram(selected):
        state["last_sent"] = str(today)
        state.setdefault("used_ids", []).append(selected["id"])
        save_json(STATE_FILE, state)
        print(f"Notificación enviada con éxito (ID {selected['id']}).")
    else:
        print("Error al enviar mensaje a Telegram.")

if __name__ == "__main__":
    main()
