import os
import sys
import json
import html
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_COSTO = os.environ.get("MAX_COSTO")  # opcional, ej. "300"
FORCE = os.environ.get("FORCE") == "1"   # para probar sin esperar

STATE_FILE = "state.json"
IDEAS_FILE = "ideas.json"
TZ = ZoneInfo("America/Mexico_City")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # escritura segura


def should_trigger(days_passed):
    if days_passed < 3:
        return False
    if days_passed >= 8:
        return True
    probabilidades = {3: 0.20, 4: 0.35, 5: 0.55, 6: 0.75, 7: 0.90}
    return random.random() < probabilidades[days_passed]


def send_telegram(idea):
    mensaje = (
        "✨ <b>Misión Cupido de Hoy</b>\n\n"
        f"{html.escape(idea['texto'])}\n\n"
        f"⏱ <b>Tiempo:</b> {html.escape(str(idea.get('tiempo', 'Rápido')))}\n"
        f"🏷 <b>Tipo:</b> #{html.escape(str(idea.get('tipo', 'detalle')))}\n"
        f"🪙 <b>Gasto estimado:</b> ${idea.get('costo', 0)} MXN"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        print(f"Error de red: {e}")
        return False
    if not res.ok:
        print(f"Telegram respondió {res.status_code}: {res.text}")
        return False
    return True


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise ValueError("Faltan variables TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")

    state = load_json(STATE_FILE, {"last_sent": None, "used_ids": [], "last_tipo": None})
    ideas = load_json(IDEAS_FILE, [])
    if not ideas:
        print("ideas.json está vacío o no existe.")
        sys.exit(1)

    today = datetime.now(TZ).date()

    if state.get("last_sent"):
        last_date = datetime.strptime(state["last_sent"], "%Y-%m-%d").date()
        days_passed = (today - last_date).days
    else:
        days_passed = 10  # primera ejecución: dispara

    if not FORCE and not should_trigger(days_passed):
        print(f"Hoy no toca disparo. Días desde el último: {days_passed}")
        return

    # Filtro opcional por presupuesto
    pool = ideas
    if MAX_COSTO:
        pool = [i for i in ideas if i.get("costo", 0) <= float(MAX_COSTO)] or ideas

    # Evitar repetir ideas hasta agotar el ciclo
    used = state.get("used_ids", [])
    available = [i for i in pool if i["id"] not in used]
    if not available:
        state["used_ids"] = []
        available = pool

    # Evitar dos del mismo tipo seguidas
    distinto_tipo = [i for i in available if i.get("tipo") != state.get("last_tipo")]
    selected = random.choice(distinto_tipo or available)

    if send_telegram(selected):
        state["last_sent"] = str(today)
        state["last_tipo"] = selected.get("tipo")
        state.setdefault("used_ids", []).append(selected["id"])
        save_json(STATE_FILE, state)
        print(f"Notificación enviada con éxito (ID {selected['id']}).")
    else:
        print("Error al enviar mensaje a Telegram.")
        sys.exit(1)  # que el workflow marque fallo


if __name__ == "__main__":
    main()
