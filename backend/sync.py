"""
Sincroniza datos desde la API gratuita de balldontlie hacia la base local.

USO:
    python sync.py teams                    -> descarga los 30 equipos (una sola vez)
    python sync.py games --season 2025      -> descarga el historial completo de una temporada
    python sync.py update                   -> descarga solo los partidos nuevos desde
                                                la última sincronización (para correr seguido,
                                                ej. una vez al día, con cron / Tareas Programadas)

LÍMITE DEL PLAN FREE: 5 solicitudes por minuto. Este script respeta ese límite
de forma conservadora (1 solicitud cada 13 segundos) y reintenta con espera si
la API responde 429 (demasiadas solicitudes).

IMPORTANTE (documentado por transparencia, sin inventar datos):
El plan Free de balldontlie incluye los endpoints "teams", "players" y "games"
(calendario, marcador final, fecha). NO incluye estadísticas por jugador
("Game Player Stats"), que requieren el plan pagado ALL-STAR (9.99 USD/mes).
Por eso esta app solo construye el historial de PARTIDOS (resultado, rival,
fecha, local/visitante), no líneas de estadísticas individuales de jugadores.
Ver stats_paid_stub.py para la estructura ya preparada para cuando se decida
pagar ese plan.
"""
import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import db  # noqa: E402

load_dotenv()

API_BASE = "https://api.balldontlie.io/v1"
API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")
SECONDS_BETWEEN_REQUESTS = 13  # 60s / 5 req = 12s; dejamos 13s de margen


def _headers():
    if not API_KEY or API_KEY == "pon_aqui_tu_api_key_gratis":
        raise SystemExit(
            "Falta configurar BALLDONTLIE_API_KEY en tu archivo .env.\n"
            "Crea una cuenta gratis (sin tarjeta) en https://app.balldontlie.io "
            "y copia tu API key ahí."
        )
    return {"Authorization": API_KEY}


def _get(path, params=None):
    """GET con reintento respetuoso del rate limit (429)."""
    url = f"{API_BASE}{path}"
    while True:
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 60))
            print(f"  Rate limit alcanzado, esperando {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()


def sync_teams():
    """
    El endpoint /teams de balldontlie no solo devuelve los 30 equipos actuales:
    también incluye franquicias históricas desaparecidas (ej. Chicago Stags de
    los años 40) y equipos internacionales con los que la NBA ha jugado partidos
    de exhibición (ej. Real Madrid, Adelaide 36ers). Esos registros vienen con
    el campo "conference" vacío, mientras que los 30 equipos actuales siempre
    tienen "East" o "West". Filtramos por eso para quedarnos solo con los 30
    equipos reales de la NBA actual.
    """
    print("Descargando equipos...")
    data = _get("/teams")
    current_teams = [t for t in data["data"] if (t.get("conference") or "").strip() in ("East", "West")]
    print(f"  {len(data['data'])} registros recibidos, {len(current_teams)} son equipos actuales de la NBA.")
    with db.get_conn() as conn:
        for t in current_teams:
            db.upsert_team(
                conn,
                {
                    "id": t["id"],
                    "full_name": t["full_name"],
                    "abbreviation": t["abbreviation"],
                    "city": t["city"],
                    "name": t["name"],
                    "conference": t["conference"],
                    "division": t["division"],
                },
            )
    print("Listo: equipos guardados localmente.")


def _save_games_page(conn, games):
    saved = 0
    for g in games:
        if g.get("home_team_score") is None and g.get("status_state") != "final":
            # Guardamos igual (puede servir para calendario futuro), pero el
            # listado de "últimos partidos" en el frontend solo muestra finales.
            pass
        db.upsert_game(
            conn,
            {
                "id": g["id"],
                "date": g["date"],
                "datetime": g.get("datetime"),
                "season": g.get("season"),
                "status": g.get("status"),
                "status_state": g.get("status_state"),
                "postseason": 1 if g.get("postseason") else 0,
                "home_team_id": g["home_team"]["id"],
                "visitor_team_id": g["visitor_team"]["id"],
                "home_team_score": g.get("home_team_score"),
                "visitor_team_score": g.get("visitor_team_score"),
            },
        )
        saved += 1
    return saved


def sync_games_for_season(season):
    print(f"Descargando partidos de la temporada {season} (esto puede tardar por el límite de 5 req/min)...")
    cursor = None
    total = 0
    page = 1
    while True:
        params = {"seasons[]": season, "per_page": 100}
        if cursor is not None:
            params["cursor"] = cursor
        data = _get("/games", params=params)
        with db.get_conn() as conn:
            total += _save_games_page(conn, data["data"])
            db.set_meta(conn, f"last_full_season_synced", str(season))
        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")
        print(f"  página {page}: {len(data['data'])} partidos (total acumulado: {total})")
        page += 1
        if not cursor:
            break
        time.sleep(SECONDS_BETWEEN_REQUESTS)
    print(f"Listo: {total} partidos de la temporada {season} guardados localmente.")


def sync_update():
    """Descarga solo los partidos desde la última fecha sincronizada hasta hoy."""
    with db.get_conn() as conn:
        last_date = db.get_meta(conn, "last_update_date")

    if not last_date:
        print(
            "No hay sincronización previa registrada. Corre primero:\n"
            "  python sync.py teams\n"
            "  python sync.py games --season <temporada, ej. 2025>\n"
        )
        return

    start_date = (datetime.strptime(last_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
    end_date = date.today().isoformat()
    print(f"Actualizando partidos entre {start_date} y {end_date}...")

    cursor = None
    total = 0
    while True:
        params = {"start_date": start_date, "end_date": end_date, "per_page": 100}
        if cursor is not None:
            params["cursor"] = cursor
        data = _get("/games", params=params)
        with db.get_conn() as conn:
            total += _save_games_page(conn, data["data"])
        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")
        if not cursor:
            break
        time.sleep(SECONDS_BETWEEN_REQUESTS)

    with db.get_conn() as conn:
        db.set_meta(conn, "last_update_date", end_date)
        db.set_meta(conn, "last_update_run_at", datetime.now().isoformat(timespec="seconds"))

    print(f"Listo: {total} partidos actualizados. Próxima vez partirá desde {end_date}.")


def main():
    parser = argparse.ArgumentParser(description="Sincroniza datos NBA locales desde balldontlie (plan free).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("teams", help="Descarga los 30 equipos")

    p_games = sub.add_parser("games", help="Descarga el historial completo de una temporada")
    p_games.add_argument("--season", type=int, required=True, help="Año de inicio de temporada, ej. 2025 para 2025-26")

    sub.add_parser("update", help="Descarga solo los partidos nuevos desde la última sincronización")

    args = parser.parse_args()
    db.init_db()

    if args.command == "teams":
        sync_teams()
    elif args.command == "games":
        sync_games_for_season(args.season)
        with db.get_conn() as conn:
            db.set_meta(conn, "last_update_date", date.today().isoformat())
    elif args.command == "update":
        sync_update()


if __name__ == "__main__":
    main()
