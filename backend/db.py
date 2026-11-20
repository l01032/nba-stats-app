"""
Capa de base de datos local (SQLite).

Por restricción de presupuesto ($0) usamos SQLite en vez de PostgreSQL/Supabase:
no requiere servidor, no requiere cuenta, no requiere tarjeta, y es más que
suficiente para el volumen de datos de la NBA (equipos + partidos).

Si en el futuro se decide migrar a Supabase (su plan free es suficiente para
este tamaño de datos), solo hay que reescribir esta capa: el resto de la app
(sync.py, app.py) solo llama a las funciones de aquí, no usa SQL directamente.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "nba_local.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    abbreviation TEXT NOT NULL,
    city TEXT,
    name TEXT,
    conference TEXT,
    division TEXT
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,            -- YYYY-MM-DD
    datetime TEXT,
    season INTEGER,
    status TEXT,
    status_state TEXT,
    postseason INTEGER DEFAULT 0,
    home_team_id INTEGER NOT NULL,
    visitor_team_id INTEGER NOT NULL,
    home_team_score INTEGER,
    visitor_team_score INTEGER,
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (visitor_team_id) REFERENCES teams(id)
);

CREATE INDEX IF NOT EXISTS idx_games_home ON games(home_team_id, date);
CREATE INDEX IF NOT EXISTS idx_games_visitor ON games(visitor_team_id, date);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date);

-- Guarda metadatos de sincronización: hasta qué fecha/temporada ya se descargó,
-- para poder actualizar de forma incremental sin repetir todo el historial.
CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_team(conn, t):
    conn.execute(
        """
        INSERT INTO teams (id, full_name, abbreviation, city, name, conference, division)
        VALUES (:id, :full_name, :abbreviation, :city, :name, :conference, :division)
        ON CONFLICT(id) DO UPDATE SET
            full_name=excluded.full_name,
            abbreviation=excluded.abbreviation,
            city=excluded.city,
            name=excluded.name,
            conference=excluded.conference,
            division=excluded.division
        """,
        t,
    )


def upsert_game(conn, g):
    conn.execute(
        """
        INSERT INTO games (
            id, date, datetime, season, status, status_state, postseason,
            home_team_id, visitor_team_id, home_team_score, visitor_team_score
        ) VALUES (
            :id, :date, :datetime, :season, :status, :status_state, :postseason,
            :home_team_id, :visitor_team_id, :home_team_score, :visitor_team_score
        )
        ON CONFLICT(id) DO UPDATE SET
            date=excluded.date,
            datetime=excluded.datetime,
            season=excluded.season,
            status=excluded.status,
            status_state=excluded.status_state,
            postseason=excluded.postseason,
            home_team_score=excluded.home_team_score,
            visitor_team_score=excluded.visitor_team_score
        """,
        g,
    )


def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO sync_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM sync_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def list_teams(conn):
    return conn.execute("SELECT * FROM teams ORDER BY full_name").fetchall()


def list_team_games(conn, team_id, before_date=None, limit=15):
    """
    Devuelve los partidos de un equipo, del más reciente al más antiguo.
    `before_date` permite paginar hacia atrás en el tiempo (scroll infinito):
    se le pasa la fecha del último partido ya cargado y trae los siguientes
    más antiguos que esa fecha.
    """
    params = {"team_id": team_id, "limit": limit}
    date_filter = ""
    if before_date:
        date_filter = "AND g.date < :before_date"
        params["before_date"] = before_date

    query = f"""
        SELECT
            g.id, g.date, g.season, g.status, g.status_state, g.postseason,
            g.home_team_id, g.visitor_team_id, g.home_team_score, g.visitor_team_score,
            ht.full_name AS home_full_name, ht.abbreviation AS home_abbr,
            vt.full_name AS visitor_full_name, vt.abbreviation AS visitor_abbr
        FROM games g
        JOIN teams ht ON ht.id = g.home_team_id
        JOIN teams vt ON vt.id = g.visitor_team_id
        WHERE (g.home_team_id = :team_id OR g.visitor_team_id = :team_id)
          AND g.status_state = 'final'
          {date_filter}
        ORDER BY g.date DESC, g.id DESC
        LIMIT :limit
    """
    return conn.execute(query, params).fetchall()
