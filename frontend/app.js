// Colores oficiales reales de cada equipo (dato público, no un logo).
// [color primario, color secundario] en hex.
const TEAM_COLORS = {
  ATL: ["#E03A3E", "#26282A"], BOS: ["#007A33", "#BA9653"], BKN: ["#000000", "#FFFFFF"],
  CHA: ["#1D1160", "#00788C"], CHI: ["#CE1141", "#000000"], CLE: ["#860038", "#FDBB30"],
  DAL: ["#00538C", "#002B5E"], DEN: ["#0E2240", "#FEC524"], DET: ["#C8102E", "#1D42BA"],
  GSW: ["#1D428A", "#FFC72C"], HOU: ["#CE1141", "#000000"], IND: ["#002D62", "#FDBB30"],
  LAC: ["#C8102E", "#1D428A"], LAL: ["#552583", "#FDB927"], MEM: ["#5D76A9", "#12173F"],
  MIA: ["#98002E", "#F9A01B"], MIL: ["#00471B", "#EEE1C6"], MIN: ["#0C2340", "#236192"],
  NOP: ["#0C2340", "#C8102E"], NYK: ["#006BB6", "#F58426"], OKC: ["#007AC1", "#EF3B24"],
  ORL: ["#0077C0", "#C4CED4"], PHI: ["#006BB6", "#ED174C"], PHX: ["#1D1160", "#E56020"],
  POR: ["#E03A3E", "#000000"], SAC: ["#5A2D81", "#63727A"], SAS: ["#C4CED4", "#000000"],
  TOR: ["#CE1141", "#000000"], UTA: ["#002B5C", "#F9A01B"], WAS: ["#002B5C", "#E31837"],
};

function colorsFor(abbr) {
  return TEAM_COLORS[abbr] || ["#f0a500", "#1a1a1a"];
}

let currentTeam = null;
let nextBefore = null;
let hasMore = true;
let loadingPage = false;

const teamGridView = document.getElementById("team-grid-view");
const teamGamesView = document.getElementById("team-games-view");
const teamGrid = document.getElementById("team-grid");
const gamesList = document.getElementById("games-list");
const teamTitle = document.getElementById("team-title");
const loadingEl = document.getElementById("loading");
const noMoreEl = document.getElementById("no-more");
const syncStatusEl = document.getElementById("sync-status");

async function init() {
  await loadSyncStatus();
  await loadTeams();
  window.addEventListener("scroll", onScroll);
}

async function loadSyncStatus() {
  try {
    const res = await fetch("/api/sync-status");
    const data = await res.json();
    if (data.last_update_date) {
      syncStatusEl.textContent = `Datos actualizados hasta: ${data.last_update_date}`;
    } else {
      syncStatusEl.textContent = "Sin datos aún — corre sync.py";
    }
  } catch (e) {
    syncStatusEl.textContent = "";
  }
}

async function loadTeams() {
  const res = await fetch("/api/teams");
  const teams = await res.json();
  if (!teams.length) {
    teamGrid.innerHTML = `<p>No hay equipos guardados todavía. Corre <code>python sync.py teams</code> primero.</p>`;
    return;
  }
  teamGrid.innerHTML = "";
  teams.forEach((t) => {
    const [primary, secondary] = colorsFor(t.abbreviation);
    const card = document.createElement("div");
    card.className = "team-card";
    card.style.setProperty("--team-primary", primary);
    card.style.setProperty("--team-secondary", secondary);
    card.onclick = () => openTeam(t);
    card.innerHTML = `
      <div class="team-badge">
        <span class="team-badge-abbr">${t.abbreviation}</span>
      </div>
      <div class="team-name">${t.full_name}</div>
      <div class="team-conf">${t.conference ?? ""} ${t.division ? "· " + t.division : ""}</div>
    `;
    teamGrid.appendChild(card);
  });
}

function showTeamGrid() {
  teamGamesView.classList.add("hidden");
  teamGridView.classList.remove("hidden");
  currentTeam = null;
}

async function openTeam(team) {
  currentTeam = team;
  nextBefore = null;
  hasMore = true;
  gamesList.innerHTML = "";
  noMoreEl.classList.add("hidden");
  teamTitle.textContent = team.full_name;
  const [primary, secondary] = colorsFor(team.abbreviation);
  teamGamesView.style.setProperty("--team-primary", primary);
  teamGamesView.style.setProperty("--team-secondary", secondary);
  teamGridView.classList.add("hidden");
  teamGamesView.classList.remove("hidden");
  window.scrollTo(0, 0);
  await loadMoreGames();
}

function renderGame(g) {
  const row = document.createElement("div");
  row.className = "game-row";
  const vs = g.is_home ? "vs" : "@";
  const resultClass = g.result === "W" ? "badge-win" : g.result === "L" ? "badge-loss" : "";
  row.innerHTML = `
    <div class="game-left">
      <span class="game-date">${g.date}${g.postseason ? " · Playoffs" : ""}</span>
      <span class="game-opp">${vs} ${g.opponent_abbr} — ${g.opponent_name}</span>
    </div>
    <div class="game-right">
      <span class="game-score">${g.team_score ?? "-"} : ${g.opponent_score ?? "-"}</span>
      ${g.result ? `<span class="badge-result ${resultClass}">${g.result}</span>` : ""}
    </div>
  `;
  gamesList.appendChild(row);
}

async function loadMoreGames() {
  if (!currentTeam || loadingPage || !hasMore) return;
  loadingPage = true;
  loadingEl.classList.remove("hidden");

  const params = new URLSearchParams({ limit: 15 });
  if (nextBefore) params.set("before", nextBefore);

  const res = await fetch(`/api/teams/${currentTeam.id}/games?${params}`);
  const data = await res.json();

  data.games.forEach(renderGame);
  nextBefore = data.next_before;
  hasMore = data.has_more;

  loadingEl.classList.add("hidden");
  if (!hasMore) noMoreEl.classList.remove("hidden");
  loadingPage = false;
}

function onScroll() {
  if (teamGamesView.classList.contains("hidden")) return;
  const scrolledToBottom =
    window.innerHeight + window.scrollY >= document.body.offsetHeight - 300;
  if (scrolledToBottom) loadMoreGames();
}

init();
