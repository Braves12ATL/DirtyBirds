#! /home/scott/scripts/DirtyBirdsApp/dbvenv/bin/python3

# Write to file
##output_file = "/Users/scott/Library/Mobile Documents/com~apple~CloudDocs/Documents/Python_Fantasy/all_scores.txt"

#! /home/scott/scripts/DirtyBirdsApp/dbvenv/bin/python3

import pandas as pd
from espn_api.football import League
import espnsecrets

LEAGUE_ID = espnsecrets.league
S2 = espnsecrets.espn_s2
SWID = espnsecrets.swid
OWNERS = espnsecrets.owners

YEARS = range(2012, 2026)  # 2012 through 2025

def year_scores_df(year: int) -> pd.DataFrame:
    league = League(league_id=LEAGUE_ID, year=year, espn_s2=S2, swid=SWID)
    rows = []

    for team in league.teams:
        team_id = int(team.team_id)

        # Owner fallback logic
        if 0 <= team_id - 1 < len(OWNERS):
            owner_name = OWNERS[team_id - 1]
        else:
            owner_name = getattr(team, "owner", getattr(team, "team_name", f"Team {team_id}"))

        team_name = getattr(team, "team_name", f"Team {team_id}")

        # 🟩 Ownership name adjustments for historical seasons
        owner_lower = owner_name.strip().lower()

        # Brad → Nick for any season ≤ 2020
        if year <= 2020 and owner_lower == "brad":
            owner_name = "Nick"

        # Thai → Mullins for any season ≤ 2021
        if year <= 2021 and owner_lower == "thai":
            owner_name = "Mullins"

        for week_idx, score in enumerate(team.scores, start=1):
            rows.append({
                "Year": year,
                "Team ID": team_id,
                "Owner": owner_name,
                "Team Name": team_name,
                "Week": week_idx,
                "Score": float(score)
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Trim trailing all-zero future weeks
    nonzero_by_week = df.groupby("Week")["Score"].max()
    nonzero_weeks = nonzero_by_week[nonzero_by_week > 0]
    if not nonzero_weeks.empty:
        last_played_week = int(nonzero_weeks.index.max())
        df = df[df["Week"] <= last_played_week]
    else:
        df = df.iloc[0:0]

    return df

# Build combined DataFrame for all years
all_years = [year_scores_df(y) for y in YEARS]
combined = pd.concat(all_years, ignore_index=True) if all_years else pd.DataFrame()

# Write to file
output_file = "/Users/scott/Library/Mobile Documents/com~apple~CloudDocs/Documents/Python_Fantasy/all_scores.txt"
with open(output_file, "w", encoding="utf-8") as f:
    if combined.empty:
        f.write("No data found.\n")
    else:
        for year, dfy in combined.groupby("Year"):
            f.write(f"\n===== {year} =====\n")
            wide = dfy.pivot_table(
                index=["Team ID", "Owner", "Team Name"],
                columns="Week",
                values="Score",
                fill_value=0
            ).sort_index()
            wide.columns = [str(c) for c in wide.columns]
            f.write(wide.to_string())
            f.write("\n")

print(f"All scores with team names written to {output_file}")
# --- Regular-season records only (ignore playoffs & zero scores) ---

if not combined.empty:
    def reg_weeks(year: int) -> int:
        return 13 if year <= 2020 else 14

    # last played (non-zero) week per year
    last_played_by_year = (
        combined[combined["Score"] > 0.0]
        .groupby("Year")["Week"]
        .max()
        .astype(int)
        .to_dict()
    )

    # Cutoff per year = min(configured reg-season, last played so far)
    cutoff_by_year = {
        y: max(1, min(reg_weeks(int(y)), int(last_played_by_year.get(y, 0))))
        for y in combined["Year"].unique()
    }

    # Keep only regular-season, non-zero scores
    reg_mask = combined["Week"] <= combined["Year"].map(cutoff_by_year)
    valid_scores = combined[reg_mask & (combined["Score"] > 0.0)]

    if valid_scores.empty:
        print("\nNo valid regular-season scores found (after filtering).")
    else:
        # ---- (A) All-time single-week records ----
        min_idx = valid_scores["Score"].idxmin()
        max_idx = valid_scores["Score"].idxmax()
        min_row = valid_scores.loc[min_idx]
        max_row = valid_scores.loc[max_idx]

        print("\n🏈 All-Time LOWEST Regular-Season Score (non-zero):")
        print(f"  {min_row['Score']} pts — {min_row['Team Name']} ({min_row['Owner']})")
        print(f"  Week {int(min_row['Week'])}, {int(min_row['Year'])}")

        print("\n🔥 All-Time HIGHEST Regular-Season Score:")
        print(f"  {max_row['Score']} pts — {max_row['Team Name']} ({max_row['Owner']})")
        print(f"  Week {int(max_row['Week'])}, {int(max_row['Year'])}")

        # ---- (B) Lowest average team score by year (regular season only) ----
        grp = (valid_scores
               .groupby(["Year", "Team ID", "Owner", "Team Name"], as_index=False)
               .agg(Weeks=("Score", "count"), AvgScore=("Score", "mean")))

        # Tiebreaker: lowest avg, then most weeks (prefer full slates), then name
        lowest_avg_by_year = (grp.sort_values(["Year", "AvgScore", "Weeks", "Team Name"])
                                 .groupby("Year", as_index=False)
                                 .first())

        print("\n📉 Lowest Average Regular-Season Score by Year (non-zero weeks only)")
        for _, r in lowest_avg_by_year.iterrows():
            y, nm, ow = int(r["Year"]), r["Team Name"], r["Owner"]
            w, avg = int(r["Weeks"]), round(float(r["AvgScore"]), 2)
            print(f"  {y}: {avg} pts avg over {w} wks — {nm} ({ow})")
        # ---- (C) Highest average team score by year (regular season only) ----
        # Tiebreaker: highest avg, then most weeks, then name
        highest_avg_by_year = (grp.sort_values(["Year", "AvgScore", "Weeks", "Team Name"],
                                               ascending=[True, False, False, True])
                                  .groupby("Year", as_index=False)
                                  .first())

        print("\n📈 Highest Average Regular-Season Score by Year (non-zero weeks only)")
        for _, r in highest_avg_by_year.iterrows():
            y  = int(r["Year"])
            nm = r["Team Name"]
            ow = r["Owner"]
            w  = int(r["Weeks"])
            avg = round(float(r["AvgScore"]), 2)
            print(f"  {y}: {avg} pts avg over {w} wks — {nm} ({ow})")
