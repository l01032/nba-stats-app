"""
Servidor local. Corre con: python app.py
Abre en el navegador: http://localhost:5000

Sirve dos cosas:
  1. El frontend estático (carpeta ../frontend)
  2. Una API JSON local que lee de la base SQLite (nunca llama a internet
     directamente; los datos ya fueron bajados antes con sync.py)
"""
import os
import sys

from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import db  # noqa: E402

load_dotenv()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
db.init_db()


def row_to_game_dict(g, team_id):
    is_home = g["home_team_id"] == team_id
    team_score = g["home_team_score"] if is_home else g["visitor_team_score"]
    opp_score = g["visitor_team_score"] if is_home else g["home_team_score"]
    opp_name = g["visitor_full_name"] if is_home else g["home_full_name"]
    opp_abbr = g["visitor_abbr"] if is_home else g["home_abbr"]
    result = None
    if team_score is not None and opp_score is not None:
        result = "W" if team_score > opp_score else ("L" if team_score < opp_score else "T")
    return {
        "id": g["id"],
        "date": g["date"],
        "season": g["season"],
        "postseason": bool(g["postseason"]),
        "is_home": is_home,
        "opponent_name": opp_name,
        "opponent_abbr": opp_abbr,
        "team_score": team_score,
        "opponent_score": opp_score,
        "result": result,
    }


@app.get("/api/teams")
def api_teams():
    with db.get_conn() as conn:
        teams = db.list_teams(conn)
    return jsonify([dict(t) for t in teams])


@app.get("/api/teams/<int:team_id>/games")
def api_team_games(team_id):
    before_date = request.args.get("before")
    limit = min(int(request.args.get("limit", 15)), 50)
    with db.get_conn() as conn:
        games = db.list_team_games(conn, team_id, before_date=before_date, limit=limit)
    items = [row_to_game_dict(g, team_id) for g in games]
    next_before = items[-1]["date"] if items else None
    return jsonify({"games": items, "next_before": next_before, "has_more": len(items) == limit})


@app.get("/api/sync-status")
def api_sync_status():
    with db.get_conn() as conn:
        last_update = db.get_meta(conn, "last_update_date")
        last_run = db.get_meta(conn, "last_update_run_at")
        last_season = db.get_meta(conn, "last_full_season_synced")
    return jsonify(
        {
            "last_update_date": last_update,
            "last_update_run_at": last_run,
            "last_full_season_synced": last_season,
            "note": "Los datos se actualizan corriendo 'python sync.py update', no en tiempo real.",
        }
    )


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    print(f"Abre http://localhost:{PORT} en tu navegador")
    app.run(port=PORT, debug=True)
