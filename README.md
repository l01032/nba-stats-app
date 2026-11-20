# NBA Stats Local (presupuesto $0)

Web local para explorar los últimos partidos de los 30 equipos de la NBA,
con scroll infinito hacia partidos más antiguos. Corre 100% en tu computadora,
sin pagar nada.

## Cómo funciona (arquitectura)

```
balldontlie API (gratis)  -->  sync.py  -->  SQLite local (nba_local.db)  -->  Flask (app.py)  -->  tu navegador
     [1 vez / diario]        [script]        [base de datos local]         [API + frontend]
```

- **Fuente de datos:** [balldontlie.io](https://www.balldontlie.io) — API gratuita, legal
  y oficial (no es scraping). Da acceso gratis a equipos, calendario y resultados finales
  desde 1946. **Requiere crear una cuenta gratis (solo email + contraseña, sin tarjeta)**
  para obtener una API key.
- **Base de datos:** SQLite. Un solo archivo (`nba_local.db`), no necesita servidor ni cuenta.
  Es tu copia local de los datos — la app nunca llama a internet en vivo mientras la usas,
  solo cuando corres `sync.py`.
- **Backend:** Flask (Python), sirve una API JSON local y el frontend.
- **Frontend:** HTML/CSS/JS simple, sin frameworks pagos ni dependencias externas.

## Instalación

Requisitos: Python 3.10 o más nuevo.

```bash
cd nba-stats-app
python -m venv venv
source venv/bin/activate       # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y pon tu API key:
1. Crea una cuenta gratis en https://app.balldontlie.io (sin tarjeta para el plan Free).
2. Copia tu API key y pégala en `BALLDONTLIE_API_KEY` dentro de `.env`.

## Primera carga de datos

```bash
cd backend
python sync.py teams
python sync.py games --season 2025   # temporada 2025-26
python sync.py games --season 2024   # temporada 2024-25 (repite por cada temporada que quieras)
```

⚠️ El plan gratuito permite **5 solicitudes por minuto**, así que descargar varias
temporadas completas puede tardar varios minutos. El script respeta ese límite
automáticamente (no te van a bloquear la cuenta).

## Correr la app

```bash
python app.py
```

Abre **http://localhost:5000** en tu navegador. Elige un equipo (ej. Warriors) y
verás sus partidos más recientes; al bajar en la página se van cargando los más
antiguos (scroll infinito), equipo por equipo, para los 30 equipos.

## Mantener los datos actualizados

Los partidos **no se actualizan en vivo** (eso requeriría un plan pagado con
websockets/datos en tiempo real, fuera de presupuesto). En vez de eso, corre
esto cada vez que quieras traer los resultados de los partidos que ya se jugaron:

```bash
cd backend
python sync.py update
```

Puedes programarlo para que corra solo una vez al día:
- **Windows:** Programador de tareas → nueva tarea → ejecutar `python sync.py update` diario.
- **Mac/Linux:** `crontab -e` y agregar una línea tipo `0 9 * * * cd /ruta/al/proyecto/backend && venv/bin/python sync.py update`.

## Limitaciones actuales (por el presupuesto $0, documentadas sin inventar nada)

| Funcionalidad | Estado | Por qué |
|---|---|---|
| Equipos, calendario, marcador final, local/visitante | ✅ Funciona | Incluido en el plan Free de balldontlie |
| Historial desde 1946 | ✅ Funciona | Incluido en el plan Free |
| Scroll infinito de partidos antiguos | ✅ Funciona | Paginación local sobre SQLite |
| Actualización tras cada jornada | ✅ Funciona (manual/programada) | `sync.py update`, no en tiempo real |
| Estadísticas de jugador por partido (puntos, rebotes, asistencias...) | ❌ Deshabilitado | Requiere plan pagado ALL-STAR (9.99 USD/mes). Ver `backend/stats_paid_stub.py`, ya está la estructura lista pero apagada. |
| Partidos en vivo segundo a segundo | ❌ No implementado | El endpoint live existe en el plan Free pero decidimos no complicar la primera versión con esto; se puede agregar después sin costo si se necesita (polling cada cierto tiempo al endpoint `/v1/box_scores/live`, que sí es gratis). |
| PostgreSQL / Supabase | ❌ No usado todavía | SQLite es suficiente para este tamaño de datos; se deja como posible paso futuro, no como requisito. |

## Siguiente paso: publicarla en internet (gratis)

Esto lo dejamos para después, como pediste. Algunas pistas para cuando llegue ese momento,
todas con plan gratuito:
- Backend: Render o Railway (free tier) o Fly.io (free allowance).
- Base de datos: si se migra de SQLite, Supabase (Postgres) tiene un plan free que alcanza
  para este tamaño de datos.
- Frontend: se puede servir desde el mismo backend (como ahora) o separarlo a GitHub Pages.

No se requiere ninguna tarjeta para empezar a investigar estas opciones en sus planes free.
