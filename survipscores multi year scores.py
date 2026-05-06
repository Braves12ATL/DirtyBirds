#!/usr/bin/env python3

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
output_file = "all_scores.txt"
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
    # Decide the regular-season cutoff per year based on total weeks in that year
    cutoff_by_year = {}
    for year, dfy in combined.groupby("Year"):
        total_weeks = int(dfy["Week"].max()) if not dfy.empty else 0
        if total_weeks == 16:
            cutoff = 13
        elif total_weeks == 17:
            cutoff = 14
        else:
            cutoff = max(total_weeks - 3, 1)  # safe fallback
        cutoff_by_year[year] = cutoff

    # Keep only regular-season, non-zero scores
    reg_mask = combined["Week"] <= combined["Year"].map(cutoff_by_year)
    valid_scores = combined[reg_mask & (combined["Score"] > 0.0)]

    if not valid_scores.empty:
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
    else:
        print("\nNo valid regular-season scores found (after filtering).")
