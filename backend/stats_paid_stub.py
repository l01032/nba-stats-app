"""
LIMITACIÓN ACTUAL (presupuesto $0): esta función NO está activa.

El endpoint "Game Player Stats" de balldontlie (estadísticas de cada jugador
por partido: puntos, rebotes, asistencias, etc.) requiere el plan pagado
ALL-STAR (9.99 USD/mes por liga) o superior. El plan Free solo da acceso a
teams, players y games (calendario y marcador final), que es lo que ya usa
esta app.

Esta función queda escrita y lista, pero deshabilitada, para que si en el
futuro se decide pagar ese plan, conectar las estadísticas de jugador sea
cuestión de:
  1. Poner ENABLE_PAID_STATS=true en el .env
  2. Quitar el "raise" de abajo
No se simulan ni se inventan datos de estadísticas en ningún punto de la app.
"""
import os

ENABLE_PAID_STATS = os.environ.get("ENABLE_PAID_STATS", "false").lower() == "true"


def fetch_player_stats_for_game(game_id, _get, db, conn):
    """
    Estructura lista para el endpoint GET /v1/stats?game_ids[]=<game_id>
    (requiere plan ALL-STAR o superior). Deshabilitada por defecto.
    """
    if not ENABLE_PAID_STATS:
        raise RuntimeError(
            "Estadísticas de jugador deshabilitadas: requieren el plan pagado "
            "ALL-STAR de balldontlie. Activa ENABLE_PAID_STATS=true en .env "
            "solo si decides contratar ese plan."
        )

    data = _get("/stats", params={"game_ids[]": game_id, "per_page": 100})
    for s in data["data"]:
        # Aquí se insertaría en una tabla `player_game_stats` (a crear en db.py
        # cuando se active esta función) con: player, team, pts, reb, ast,
        # stl, blk, fg_pct, etc. Se deja sin implementar para no mantener
        # código muerto mientras el plan free siga siendo la única fuente.
        pass
