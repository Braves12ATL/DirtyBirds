import streamlit as st
import pandas as pd
from espn_api.football import League

LEAGUE_ID = st.secrets["league"]
S2 = st.secrets["espn_s2"]
SWID = st.secrets["swid"]
OWNERS = list(st.secrets["owners"])

YEARS = range(2012, 2026)
NAME_ALIASES = {k: dict(v) for k, v in st.secrets.get("name_aliases", {}).items()}


def apply_name_aliases(owner_name: str, year: int) -> str:
    lower = owner_name.strip().lower()
    for key, info in NAME_ALIASES.items():
        if lower == key and year <= info["until_year"]:
            return info["display"]
    return owner_name

st.set_page_config(page_title="Fantasy Football Stats", page_icon="🏈", layout="wide")
st.title("🏈 Fantasy Football League Stats")


def reg_weeks(year: int) -> int:
    return 13 if year <= 2020 else 14


@st.cache_data(show_spinner="Loading scores from ESPN...")
def load_all_scores() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        try:
            league = League(league_id=LEAGUE_ID, year=year, espn_s2=S2, swid=SWID)
        except Exception:
            continue

        rows = []
        for team in league.teams:
            team_id = int(team.team_id)

            if 0 <= team_id - 1 < len(OWNERS):
                owner_name = OWNERS[team_id - 1]
            else:
                owner_name = getattr(team, "owner", getattr(team, "team_name", f"Team {team_id}"))

            team_name = getattr(team, "team_name", f"Team {team_id}")

            owner_name = apply_name_aliases(owner_name, year)

            for week_idx, score in enumerate(team.scores, start=1):
                rows.append({
                    "Year": year,
                    "Team ID": team_id,
                    "Owner": owner_name,
                    "Team Name": team_name,
                    "Week": week_idx,
                    "Score": float(score),
                })

        df = pd.DataFrame(rows)
        if df.empty:
            continue

        nonzero_by_week = df.groupby("Week")["Score"].max()
        nonzero_weeks = nonzero_by_week[nonzero_by_week > 0]
        if not nonzero_weeks.empty:
            last_played_week = int(nonzero_weeks.index.max())
            df = df[df["Week"] <= last_played_week]
        else:
            continue

        frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


@st.cache_data(show_spinner="Loading Hall of Fame data...")
def load_hof_data() -> pd.DataFrame:
    rows = []
    for year in YEARS:
        try:
            league = League(league_id=LEAGUE_ID, year=year, espn_s2=S2, swid=SWID)
        except Exception:
            continue
        for team in league.teams:
            team_id = int(team.team_id)
            if 0 <= team_id - 1 < len(OWNERS):
                owner_name = OWNERS[team_id - 1]
            else:
                owner_name = getattr(team, "owner", getattr(team, "team_name", f"Team {team_id}"))
            team_name = getattr(team, "team_name", f"Team {team_id}")
            owner_name = apply_name_aliases(owner_name, year)
            rows.append({
                "Year": year,
                "Owner": owner_name,
                "Team Name": team_name,
                "Final Standing": getattr(team, "final_standing", None),
                "Wins": int(getattr(team, "wins", 0)),
                "Losses": int(getattr(team, "losses", 0)),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def run_survivor(year_df: pd.DataFrame) -> pd.DataFrame:
    pivot = year_df.pivot_table(
        index="Owner", columns="Week", values="Score", fill_value=0
    )
    pivot.columns = [int(c) for c in pivot.columns]
    pivot = pivot.sort_index()

    result = pivot.copy()
    result["Status"] = "Active"
    eliminated = set()

    for week in sorted(pivot.columns):
        active_scores = result.loc[~result.index.isin(eliminated), week]
        nonzero = active_scores[active_scores > 0]
        if nonzero.empty:
            break
        loser = nonzero.idxmin()
        eliminated.add(loser)
        result.at[loser, "Status"] = f"OUT wk{week}"

    result.columns = [f"Wk {c}" if isinstance(c, int) else c for c in result.columns]
    result = result.reset_index()

    def sort_key(status):
        return 999 if status == "Active" else int(status.replace("OUT wk", ""))

    result["_sort"] = result["Status"].apply(sort_key)
    result = result.sort_values("_sort", ascending=False).drop(columns="_sort")
    return result


combined = load_all_scores()

if combined.empty:
    st.error("No data loaded. Check your ESPN credentials in espnsecrets.")
    st.stop()

# --- Regular-season only ---
last_played_by_year = (
    combined[combined["Score"] > 0]
    .groupby("Year")["Week"]
    .max()
    .astype(int)
    .to_dict()
)
cutoff_by_year = {
    y: max(1, min(reg_weeks(int(y)), int(last_played_by_year.get(y, 0))))
    for y in combined["Year"].unique()
}
reg_mask = combined["Week"] <= combined["Year"].map(cutoff_by_year)
valid_scores = combined[reg_mask & (combined["Score"] > 0)].copy()

# --- Sidebar filters (apply to Records and Charts tabs) ---
st.sidebar.header("Filters")
st.sidebar.caption("Applies to Records & Charts tabs")
all_years = sorted(combined["Year"].unique())
selected_years = st.sidebar.multiselect("Years", all_years, default=all_years)

all_owners = sorted(valid_scores["Owner"].unique())
selected_owners = st.sidebar.multiselect("Owners", all_owners, default=all_owners)

filtered = valid_scores[
    valid_scores["Year"].isin(selected_years) & valid_scores["Owner"].isin(selected_owners)
]

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Records & Averages", "All Scores", "Survivor Game", "Charts", "Hall of Fame"])

# ── Tab 1: Records & Averages ─────────────────────────────────────────────────
with tab1:
    st.header("All-Time Records (Regular Season)")

    if not filtered.empty:
        max_row = filtered.loc[filtered["Score"].idxmax()]
        min_row = filtered.loc[filtered["Score"].idxmin()]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🔥 Highest Single-Week Score", f"{max_row['Score']:.2f} pts")
            st.caption(f"{max_row['Team Name']} ({max_row['Owner']}) — Week {int(max_row['Week'])}, {int(max_row['Year'])}")
        with col2:
            st.metric("📉 Lowest Single-Week Score", f"{min_row['Score']:.2f} pts")
            st.caption(f"{min_row['Team Name']} ({min_row['Owner']}) — Week {int(min_row['Week'])}, {int(min_row['Year'])}")

    st.header("Per-Year Averages (Regular Season)")

    grp = (
        filtered
        .groupby(["Year", "Team ID", "Owner", "Team Name"], as_index=False)
        .agg(Weeks=("Score", "count"), AvgScore=("Score", "mean"))
    )
    lowest_avg = (
        grp.sort_values(["Year", "AvgScore", "Weeks", "Team Name"])
        .groupby("Year", as_index=False).first()
        .rename(columns={"AvgScore": "Avg Score", "Team Name": "Team"})
    )
    highest_avg = (
        grp.sort_values(["Year", "AvgScore", "Weeks", "Team Name"], ascending=[True, False, False, True])
        .groupby("Year", as_index=False).first()
        .rename(columns={"AvgScore": "Avg Score", "Team Name": "Team"})
    )

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("📉 Lowest Avg Score by Year")
        display_low = lowest_avg[["Year", "Owner", "Team", "Avg Score", "Weeks"]].copy()
        display_low["Avg Score"] = display_low["Avg Score"].round(2)
        st.dataframe(display_low, use_container_width=True, hide_index=True)
    with col4:
        st.subheader("📈 Highest Avg Score by Year")
        display_high = highest_avg[["Year", "Owner", "Team", "Avg Score", "Weeks"]].copy()
        display_high["Avg Score"] = display_high["Avg Score"].round(2)
        st.dataframe(display_high, use_container_width=True, hide_index=True)

# ── Tab 2: All Scores ─────────────────────────────────────────────────────────
with tab2:
    st.header("All Weekly Scores by Year")

    year_select = st.selectbox("Select Year", sorted(combined["Year"].unique(), reverse=True), key="scores_year")
    year_data = combined[combined["Year"] == year_select].copy()

    if not year_data.empty:
        wide = year_data.pivot_table(
            index=["Owner", "Team Name"],
            columns="Week",
            values="Score",
            fill_value=0,
        ).reset_index()
        wide.columns = ["Owner", "Team Name"] + [f"Wk {int(c)}" for c in wide.columns[2:]]

        week_cols = [c for c in wide.columns if c.startswith("Wk")]
        wide["Season Avg"] = wide[week_cols].replace(0, float("nan")).mean(axis=1).round(2)
        wide = wide.sort_values("Season Avg", ascending=False)

        st.dataframe(wide, use_container_width=True, hide_index=True)

        csv = year_data.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            file_name=f"fantasy_scores_{year_select}.csv",
            mime="text/csv",
        )

# ── Tab 3: Survivor Game ──────────────────────────────────────────────────────
with tab3:
    st.header("Survivor Game")
    st.caption("Each week, the owner with the lowest score (among those still active) is eliminated.")

    survivor_year = st.selectbox(
        "Select Year", sorted(combined["Year"].unique(), reverse=True), key="survivor_year"
    )

    year_data_s = combined[combined["Year"] == survivor_year].copy()

    if not year_data_s.empty:
        result = run_survivor(year_data_s)

        active = result[result["Status"] == "Active"]["Owner"].tolist()
        if active:
            st.success(f"Still active: {', '.join(active)}")
        else:
            winner = result.iloc[0]["Owner"]
            st.success(f"🏆 Survivor winner: {winner}")

        def highlight_survivor(row):
            if row["Status"] == "Active":
                return ["background-color: #1a472a; color: white"] * len(row)
            return ["color: #888888"] * len(row)

        st.dataframe(
            result.style.apply(highlight_survivor, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        # Elimination order summary
        eliminated = result[result["Status"] != "Active"][["Owner", "Status"]].copy()
        eliminated = eliminated.sort_values(
            "Status", key=lambda s: s.str.replace("OUT wk", "").astype(int)
        )
        if not eliminated.empty:
            with st.expander("Elimination order"):
                st.dataframe(eliminated, use_container_width=True, hide_index=True)

# ── Tab 4: Charts ─────────────────────────────────────────────────────────────
with tab4:
    st.header("Owner Career Averages")

    owner_avg = (
        filtered
        .groupby("Owner")["Score"]
        .mean()
        .reset_index()
        .rename(columns={"Score": "Career Avg Score"})
        .sort_values("Career Avg Score", ascending=False)
    )
    owner_avg["Career Avg Score"] = owner_avg["Career Avg Score"].round(2)
    st.bar_chart(owner_avg.set_index("Owner")["Career Avg Score"])

    st.header("Weekly Scores Over Time")

    if not filtered.empty:
        owner_for_chart = st.selectbox("Select owner", sorted(filtered["Owner"].unique()))
        owner_data = filtered[filtered["Owner"] == owner_for_chart].copy()
        owner_data["Season-Week"] = (
            owner_data["Year"].astype(str) + " W" + owner_data["Week"].astype(str).str.zfill(2)
        )
        owner_data = owner_data.sort_values(["Year", "Week"])
        st.line_chart(owner_data.set_index("Season-Week")["Score"])

    with st.expander("Raw Data Explorer"):
        st.dataframe(
            filtered.sort_values(["Year", "Week", "Owner"]).reset_index(drop=True),
            use_container_width=True,
        )

# ── Tab 5: Hall of Fame ───────────────────────────────────────────────────────
with tab5:
    st.header("🏆 Hall of Fame")

    hof_data = load_hof_data()

    if hof_data.empty:
        st.warning("No Hall of Fame data available.")
    else:
        champions = hof_data[hof_data["Final Standing"] == 1].sort_values("Year", ascending=False)

        # ── Champions by year ──
        st.subheader("League Champions")
        st.dataframe(
            champions[["Year", "Owner", "Team Name"]].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        col1, col2 = st.columns(2)

        # ── Most championships ──
        with col1:
            st.subheader("Most Championships")
            champ_count = (
                champions.groupby("Owner")
                .size()
                .reset_index(name="Championships")
                .sort_values("Championships", ascending=False)
            )
            if not champ_count.empty:
                top = champ_count.iloc[0]
                st.metric("Most Rings", top["Owner"], f"{top['Championships']} title(s)")
            st.dataframe(champ_count, use_container_width=True, hide_index=True)

        # ── Most career regular-season wins ──
        with col2:
            st.subheader("Most Career Wins")
            career_wins = (
                hof_data.groupby("Owner")["Wins"]
                .sum()
                .reset_index()
                .sort_values("Wins", ascending=False)
            )
            if not career_wins.empty:
                top_wins = career_wins.iloc[0]
                st.metric("Most Career Wins", top_wins["Owner"], f"{int(top_wins['Wins'])} wins")
            st.dataframe(career_wins, use_container_width=True, hide_index=True)

        st.divider()

        # ── Never won ──
        st.subheader("Never Won a Championship")
        never_won = sorted(set(hof_data["Owner"].unique()) - set(champions["Owner"].unique()))
        if never_won:
            st.dataframe(
                pd.DataFrame({"Owner": never_won}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Every owner has won at least one championship!")
