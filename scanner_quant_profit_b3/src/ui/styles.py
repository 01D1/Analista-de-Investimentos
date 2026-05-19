"""
Premium CSS for Plataforma Quant B3.

All existing palette colors are preserved.
New additions: glow effects, gradients, keyframe animations,
premium component classes.
"""

PREMIUM_CSS: str = """
<style>
/* ════════════════════════════════════════════════════════════════════
   RESETS & PAGE
   ════════════════════════════════════════════════════════════════════ */
section.main > div { padding-top: 0.2rem; }
[data-testid="stDecoration"] { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* ════════════════════════════════════════════════════════════════════
   NAV  (page_link)
   ════════════════════════════════════════════════════════════════════ */
[data-testid="stPageLink"] a {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: transparent !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #64748B !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.3px !important;
    padding: 6px 10px !important;
    text-decoration: none !important;
    transition: all 0.18s ease !important;
    width: 100% !important;
}
[data-testid="stPageLink"] a:hover {
    background: #1E2D42 !important;
    color: #93C5FD !important;
    border-color: #2563EB !important;
    box-shadow: 0 0 10px rgba(59,130,246,0.18) !important;
}
[data-testid="stPageLink"][aria-current="page"] a,
[data-testid="stPageLink"] a[aria-current="page"] {
    background: #0D1F38 !important;
    color: #93C5FD !important;
    border-color: #2563EB !important;
    box-shadow: 0 0 12px rgba(59,130,246,0.22) !important;
}

/* ════════════════════════════════════════════════════════════════════
   GLOBAL WIDGETS (dark)
   ════════════════════════════════════════════════════════════════════ */
div[data-baseweb="select"] > div {
    background-color: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
div[data-baseweb="input"] > div {
    background-color: #111827 !important;
    border-color: #1E2D42 !important;
}
input { color: #E2E8F0 !important; }
.stTextInput input, .stNumberInput input {
    background: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
.stMultiSelect span[data-baseweb="tag"] { background: #1E3A5F !important; }
.stDateInput input {
    background: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
.stSlider [data-testid="stTickBarMin"],
.stSlider [data-testid="stTickBarMax"] { color: #475569 !important; }

/* ════════════════════════════════════════════════════════════════════
   EXPANDERS
   ════════════════════════════════════════════════════════════════════ */
details summary {
    background: #111827 !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    padding: 8px 14px !important;
}
details[open] summary { border-radius: 8px 8px 0 0 !important; }
details > div {
    background: #0D1421 !important;
    border: 1px solid #1E2D42 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 12px 14px !important;
}

/* ════════════════════════════════════════════════════════════════════
   TABS
   ════════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px !important;
    border-bottom: 1px solid #1E2D42 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #475569 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 14px !important;
    border: none !important;
    transition: all 0.15s ease !important;
}
.stTabs [aria-selected="true"] {
    color: #93C5FD !important;
    border-bottom: 2px solid #3B82F6 !important;
    background: #0D1F38 !important;
}

/* ════════════════════════════════════════════════════════════════════
   st.metric
   ════════════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    padding: 12px 14px;
    transition: border-color 0.2s;
}
[data-testid="stMetric"]:hover { border-color: #3B82F6; }
[data-testid="stMetricLabel"] { color: #475569 !important; font-size: 0.68rem !important; }
[data-testid="stMetricValue"] { color: #F1F5F9 !important; font-size: 1.3rem !important; }

/* ════════════════════════════════════════════════════════════════════
   SCROLLBAR
   ════════════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb {
    background: #1E2D42;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: #3B82F6; }

/* ════════════════════════════════════════════════════════════════════
   ANIMATIONS
   ════════════════════════════════════════════════════════════════════ */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); }
    50%       { box-shadow: 0 0 0 4px rgba(59,130,246,0.18); }
}
@keyframes fill-bar {
    from { width: 0%; }
}
@keyframes glow-green {
    0%, 100% { text-shadow: 0 0 6px rgba(34,197,94,0.4); }
    50%       { text-shadow: 0 0 14px rgba(34,197,94,0.8); }
}
@keyframes glow-red {
    0%, 100% { text-shadow: 0 0 6px rgba(239,68,68,0.4); }
    50%       { text-shadow: 0 0 14px rgba(239,68,68,0.8); }
}

/* ════════════════════════════════════════════════════════════════════
   HERO SECTION
   ════════════════════════════════════════════════════════════════════ */
.hero-section {
    background: linear-gradient(135deg, #0D1421 0%, #111827 60%, #0F1E35 100%);
    border: 1px solid #1E2D42;
    border-radius: 16px;
    padding: 28px 32px 24px 32px;
    margin-bottom: 20px;
    animation: fadeInUp 0.4s ease;
    position: relative;
    overflow: hidden;
}
.hero-section::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #3B82F6, #60A5FA, #3B82F6);
}
.hero-ticker {
    font-size: 2.4rem;
    font-weight: 900;
    color: #F1F5F9;
    letter-spacing: -1px;
    line-height: 1;
    margin-bottom: 4px;
}
.hero-company {
    font-size: 1.05rem;
    color: #94A3B8;
    font-weight: 500;
    margin-bottom: 10px;
}
.hero-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    margin-top: 14px;
}
.hero-metric {
    background: rgba(30,45,66,0.6);
    border: 1px solid #1E2D42;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.78rem;
    color: #94A3B8;
}
.hero-metric span {
    display: block;
    font-size: 1.05rem;
    font-weight: 800;
    color: #E2E8F0;
    margin-top: 2px;
}

/* ════════════════════════════════════════════════════════════════════
   KPI STRIP
   ════════════════════════════════════════════════════════════════════ */
.kpi-strip {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.kpi-card {
    flex: 1;
    min-width: 130px;
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 12px;
    padding: 14px 16px;
    transition: all 0.2s ease;
    animation: fadeInUp 0.4s ease;
}
.kpi-card:hover {
    border-color: #3B82F6;
    box-shadow: 0 4px 20px rgba(59,130,246,0.12);
    transform: translateY(-2px);
}
.kpi-card.blue  { border-top: 2px solid #3B82F6; }
.kpi-card.green { border-top: 2px solid #22C55E; }
.kpi-card.red   { border-top: 2px solid #EF4444; }
.kpi-card.amber { border-top: 2px solid #F59E0B; }
.kpi-card.gray  { border-top: 2px solid #64748B; }
.kpi-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #475569;
    font-weight: 700;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 1.35rem;
    font-weight: 800;
    color: #F1F5F9;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 0.7rem;
    color: #64748B;
    margin-top: 3px;
}
.kpi-delta-pos { font-size: 0.72rem; color: #22C55E; font-weight: 700; }
.kpi-delta-neg { font-size: 0.72rem; color: #EF4444; font-weight: 700; }

/* ════════════════════════════════════════════════════════════════════
   METRIC CARD (general)
   ════════════════════════════════════════════════════════════════════ */
.metric-card {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: border-color 0.15s;
}
.metric-card:hover { border-color: #2563EB; }
.metric-card-label { font-size: 0.78rem; color: #64748B; }
.metric-card-value { font-size: 0.9rem; font-weight: 700; color: #E2E8F0; }

/* ════════════════════════════════════════════════════════════════════
   SCORE GAUGE CONTAINER
   ════════════════════════════════════════════════════════════════════ */
.score-gauge-wrap {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 14px;
    padding: 16px 12px 8px 12px;
    text-align: center;
    animation: fadeInUp 0.5s ease;
}

/* ════════════════════════════════════════════════════════════════════
   SCORE BREAKDOWN BARS
   ════════════════════════════════════════════════════════════════════ */
.score-bar-row {
    margin-bottom: 10px;
    animation: fadeInUp 0.4s ease;
}
.score-bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: #94A3B8;
    margin-bottom: 4px;
    font-weight: 600;
}
.score-bar-track {
    background: #1E2D42;
    border-radius: 99px;
    height: 7px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 99px;
    animation: fill-bar 0.9s ease-out;
}
.score-bar-blue   { background: linear-gradient(90deg, #2563EB, #60A5FA); }
.score-bar-green  { background: linear-gradient(90deg, #16A34A, #22C55E); }
.score-bar-amber  { background: linear-gradient(90deg, #B45309, #F59E0B); }
.score-bar-red    { background: linear-gradient(90deg, #B91C1C, #EF4444); }
.score-bar-purple { background: linear-gradient(90deg, #7C3AED, #A78BFA); }

/* ════════════════════════════════════════════════════════════════════
   THESIS CARD
   ════════════════════════════════════════════════════════════════════ */
.thesis-card {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 14px;
    animation: fadeInUp 0.4s ease;
}
.thesis-section-title {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 800;
    margin-bottom: 8px;
}
.thesis-section-title.bull { color: #22C55E; }
.thesis-section-title.bear { color: #EF4444; }
.thesis-text {
    font-size: 0.88rem;
    color: #CBD5E1;
    line-height: 1.65;
}
.thesis-divider {
    border: none;
    border-top: 1px solid #1E2D42;
    margin: 16px 0;
}

/* ════════════════════════════════════════════════════════════════════
   DRIVER / RISK ITEMS
   ════════════════════════════════════════════════════════════════════ */
.driver-item {
    background: #0D1421;
    border: 1px solid #1E2D42;
    border-left: 3px solid #3B82F6;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin-bottom: 8px;
    transition: border-left-color 0.2s;
}
.driver-item:hover { border-left-color: #60A5FA; }
.risk-item {
    background: #0D1421;
    border: 1px solid #1E2D42;
    border-left: 3px solid #EF4444;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.driver-title, .risk-title {
    font-size: 0.82rem;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 4px;
}
.driver-desc, .risk-desc {
    font-size: 0.78rem;
    color: #94A3B8;
    line-height: 1.5;
}

/* ════════════════════════════════════════════════════════════════════
   BADGES
   ════════════════════════════════════════════════════════════════════ */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}
.badge-buy     { background: rgba(34,197,94,0.15);  color: #22C55E; border: 1px solid rgba(34,197,94,0.35); }
.badge-hold    { background: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.35); }
.badge-sell    { background: rgba(239,68,68,0.15);  color: #EF4444; border: 1px solid rgba(239,68,68,0.35); }
.badge-high    { background: rgba(239,68,68,0.15);  color: #EF4444; border: 1px solid rgba(239,68,68,0.35); }
.badge-medium  { background: rgba(245,158,11,0.12); color: #F59E0B; border: 1px solid rgba(245,158,11,0.35); }
.badge-low     { background: rgba(34,197,94,0.12);  color: #22C55E; border: 1px solid rgba(34,197,94,0.35); }
.badge-neutral { background: rgba(100,116,139,0.15);color: #94A3B8; border: 1px solid rgba(100,116,139,0.35); }
.badge-blue    { background: rgba(59,130,246,0.15); color: #60A5FA; border: 1px solid rgba(59,130,246,0.35); }

/* ════════════════════════════════════════════════════════════════════
   WATCHLIST CARDS GRID
   ════════════════════════════════════════════════════════════════════ */
.watchlist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
}
.watchlist-row {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 12px;
    padding: 16px 18px;
    transition: all 0.2s ease;
    animation: fadeInUp 0.35s ease;
    position: relative;
    overflow: hidden;
}
.watchlist-row::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    border-radius: 4px 0 0 4px;
}
.watchlist-row.buy::before   { background: #22C55E; }
.watchlist-row.hold::before  { background: #F59E0B; }
.watchlist-row.sell::before  { background: #EF4444; }
.watchlist-row:hover {
    border-color: #2563EB;
    box-shadow: 0 4px 24px rgba(59,130,246,0.12);
    transform: translateY(-2px);
}
.watchlist-ticker {
    font-size: 1.4rem;
    font-weight: 900;
    color: #F1F5F9;
    letter-spacing: -0.5px;
    margin-bottom: 2px;
}
.watchlist-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 12px;
    margin-top: 10px;
}
.watchlist-detail-item {
    font-size: 0.68rem;
    color: #64748B;
}
.watchlist-detail-item span {
    display: block;
    font-size: 0.82rem;
    font-weight: 700;
    color: #CBD5E1;
}

/* ════════════════════════════════════════════════════════════════════
   OPPORTUNITY CARDS
   ════════════════════════════════════════════════════════════════════ */
.opp-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
}
.opportunity-card {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 12px;
    padding: 18px 20px;
    transition: all 0.2s ease;
    animation: fadeInUp 0.4s ease;
    position: relative;
    overflow: hidden;
}
.opportunity-card::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
}
.opportunity-card.dcf::before      { background: #3B82F6; }
.opportunity-card.momentum::before { background: #F59E0B; }
.opportunity-card.ipe::before      { background: #A78BFA; }
.opportunity-card.default::before  { background: #64748B; }
.opportunity-card:hover {
    border-color: #2563EB;
    box-shadow: 0 4px 20px rgba(59,130,246,0.12);
    transform: translateY(-2px);
}
.opp-ticker {
    font-size: 1.5rem;
    font-weight: 900;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
}
.opp-ticker.dcf      { color: #60A5FA; }
.opp-ticker.momentum { color: #F59E0B; }
.opp-ticker.ipe      { color: #A78BFA; }
.opp-ticker.default  { color: #E2E8F0; }
.opp-description {
    font-size: 0.82rem;
    color: #94A3B8;
    line-height: 1.55;
    margin: 8px 0 12px 0;
}
.opp-score-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    color: #64748B;
    margin-bottom: 5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.opp-score-num {
    font-size: 1.1rem;
    font-weight: 800;
    color: #E2E8F0;
}
.opp-score-track {
    background: #1E2D42;
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
}
.opp-score-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #2563EB, #60A5FA);
    animation: fill-bar 1s ease-out;
}

/* ════════════════════════════════════════════════════════════════════
   SECTION TITLE
   ════════════════════════════════════════════════════════════════════ */
.section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 800;
    color: #475569;
    margin: 18px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1E2D42;
}
.section-title-icon { font-size: 1rem; }

/* ════════════════════════════════════════════════════════════════════
   EMPTY STATE
   ════════════════════════════════════════════════════════════════════ */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #475569;
    animation: fadeInUp 0.4s ease;
}
.empty-state-icon { font-size: 2.8rem; margin-bottom: 12px; }
.empty-state-text { font-size: 0.9rem; line-height: 1.6; }

/* ════════════════════════════════════════════════════════════════════
   FILTER BAR
   ════════════════════════════════════════════════════════════════════ */
.filter-bar {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 16px;
    display: flex;
    gap: 12px;
    align-items: center;
}

/* ════════════════════════════════════════════════════════════════════
   SUMMARY KPI HEADER
   ════════════════════════════════════════════════════════════════════ */
.summary-header {
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D42;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 18px;
    display: flex;
    gap: 32px;
    flex-wrap: wrap;
    align-items: center;
}
.summary-kpi { text-align: center; }
.summary-kpi-num {
    font-size: 2rem;
    font-weight: 900;
    color: #F1F5F9;
    line-height: 1;
}
.summary-kpi-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #475569;
    font-weight: 700;
    margin-top: 4px;
}
.summary-kpi-num.green { color: #22C55E; }
.summary-kpi-num.amber { color: #F59E0B; }
.summary-kpi-num.red   { color: #EF4444; }
.summary-kpi-num.blue  { color: #60A5FA; }

/* ════════════════════════════════════════════════════════════════════
   RADAR CHART CONTAINER
   ════════════════════════════════════════════════════════════════════ */
.radar-wrap {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 14px;
    padding: 12px;
    animation: fadeInUp 0.5s ease;
}

/* ════════════════════════════════════════════════════════════════════
   PAGE HEADER
   ════════════════════════════════════════════════════════════════════ */
.page-header {
    margin-bottom: 22px;
    animation: fadeInUp 0.3s ease;
}
.page-header-title {
    font-size: 1.5rem;
    font-weight: 900;
    color: #F1F5F9;
    letter-spacing: -0.5px;
    margin-bottom: 2px;
}
.page-header-sub {
    font-size: 0.8rem;
    color: #64748B;
}
</style>
"""
