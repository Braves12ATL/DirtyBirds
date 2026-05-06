#! /home/scott/scripts/DirtyBirdsApp/dbvenv/bin/python3

#import sys
#sys.path.append('/home/scott/scripts')

import pandas as pd
import numpy as np
#from openpyxl import load_workbook
from espn_api.football import League
import espnsecrets
import datetime
import subprocess

##print(executable)


# ESPN League settings
league = League(league_id=espnsecrets.league, year=2021, espn_s2=espnsecrets.espn_s2, swid=espnsecrets.swid)
owners = espnsecrets.owners

# Get current date and week of the season
today = datetime.datetime.now()
#day_of_week = today.weekday()
day_of_week = 1
wk = league.currentMatchupPeriod
wkout = wk - 1 if (day_of_week < 1) else wk
print('It is week', wkout)

# Get box scores and team list
box_scores = np.array(league.box_scores(wk))
teamlist = league.teams

# Initialize DataFrame
df = pd.DataFrame(columns=['Team ID', 'Owner', 'Out'] + [str(i) for i in range(1, wk + 1)])
rows = []

# Populate DataFrame with season records
for i in range(1, 15):
    team_data = league.get_team_data(i)
    team_id = str(team_data.team_id)
    owner_name = owners[int(team_id) - 1]
    team_scores = team_data.scores
    
    team_row = {
        'Team ID': team_id,
        'Owner': owner_name,
        'Out': '',
        **{str(idx + 1): score for idx, score in enumerate(team_scores)}
    }
    rows.append(team_row)

# Assign row one to empty frame, concat the rest to avoid conacting to empty table
for i, row in enumerate(rows):
    new_row = pd.DataFrame([row])
    
    if df.empty and i == 0:
        # Directly assign the first row if the DataFrame is empty
        df = new_row
    else:
        # Concatenate subsequent rows
        df = pd.concat([df, new_row], ignore_index=True)


#df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)


# Identify eliminated owners
eliminated_players = set()

# Iterate through each week to find the player with the lowest score who is not eliminated
for week in range(1, wkout):
    # Filter out scores of eliminated players
    week_scores = df[~df['Owner'].isin(eliminated_players)][['Owner', str(week)]].sort_values(by=str(week))
    
    # Iterate through sorted scores to find the first eligible player
    for _, row in week_scores.iterrows():
        if row['Owner'] not in eliminated_players:
            eliminated_owner = row['Owner']
            lowest_score = row[str(week)]
            break

    # Mark player as eliminated
    eliminated_players.add(eliminated_owner)

    df.loc[df['Owner'] == eliminated_owner, 'Out'] = f'OUT wk{week}'

    elims = eliminated_players

    ##print(elims)
   
                

# Fill in current week live scores
for box in box_scores:
    home_team_id = int(box.home_team.team_id)
    away_team_id = int(box.away_team.team_id)
    home_score = float(box.home_score)
    away_score = float(box.away_score)
    
    df.at[home_team_id - 1, str(wk)] = home_score
    df.at[away_team_id - 1, str(wk)] = away_score

# Clean up DataFrame
df_cleaned = df.loc[:, (df != 0.0).any(axis=0)]

print(df_cleaned)
