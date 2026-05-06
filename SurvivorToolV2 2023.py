import pandas as pd
import numpy as np
import csv
import espn_api
import espnsecrets
from espn_api.football import League

##SETUP set these values for the seasons survivor pool

#Number of weeks it will take to get to 1 winner, same as number of participants
weekneed = 13

#empty sets for the cycle to add to. add any non-participants to the elims set
elims = np.array([11])

#League settings mainly the year
league = League(league_id=espnsecrets.league, year=2023, espn_s2=espnsecrets.espn_s2, swid=espnsecrets.swid)

######

standings = league.standings_weekly(1)

standings = pd.DataFrame(standings)

teamlist = league.teams

#loop through teams
x = range(1,15)

#loop through weeks for each team
y = range(1,14)

#set final matrix column names
df = pd.DataFrame(columns=['Team ID','Out','Owner','1','2','3','4','5','6','7','8','9','10','11','12','13','14'])

#import owner name list
owners = espnsecrets.owners
onrs = pd.DataFrame([owners])

count = 0

for i in x:
        count = count + 1
        teamname =  str(league.get_team_data(i))
        teamnum = str(league.get_team_data(i).team_id)
        o = (int(teamnum)-1)
       

        teamscores = league.get_team_data(i).scores
        #print(teamscores)
        ownername = (str(owners[o]))
        

        teamrow = [{'Team ID':[teamnum],
                    'Out': '',
                    'Owner':[ownername],
                    '1':teamscores[0],
                    '2':teamscores[1],
                    '3':teamscores[2],
                    '4':teamscores[3],
                    '5':teamscores[4],
                    '6':teamscores[5],
                    '7':teamscores[6],
                    '8':teamscores[7],
                    '9':teamscores[8],
                    '10':teamscores[9],
                    '11':teamscores[10],
                    '12':teamscores[11],
                    '13':teamscores[12],
                    '14':teamscores[13]}]
        newrow = pd.DataFrame(teamrow)
        

        df = pd.concat([df, newrow], axis=0, ignore_index=True)


w = range(1,weekneed)
for l in elims:
        df.at[(int(l-1)), 'Out'] = 'inelig'

outs = pd.DataFrame()
cycles = 0

#cycle each weeks results
for v in w:
        vtext = str(v)
        vnum = int(v)
        cwk = df[vtext]
        lowz = 0
        tally=0
        lowposs = max(cwk)
        found=0

        #check each score against the previous except check the first against max

        for z in cwk:
                tally = int(tally+1)

                if (float(z) < lowposs) and (tally not in elims):
                
                        #make the current z the new lowest to check against
                        lowposs = z
                        found = tally                      
                        
                        continue                               
                else:
                        continue

        #add the lowest score for the current week to the list of eliminated owners
        elims = np.append(elims, found)

        #write the out week note to the owners row in the table and on the last week declare winner
        if (cycles+2) == weekneed and (found>0):
                df.at[(int(found-1)), 'Out'] = 'WINNER'
        else:
                df.at[(int(found-1)), 'Out'] = 'OUT ' + 'wk' + vtext
        
        
        cycles = cycles + 1
        
#exportname = str('season' + str(season) + 'scores.csv')
df.to_csv('season2024scores.csv', index=True)
print(df)
        



        








