

import pandas as pd
import numpy as np
import csv
import espn_api
import espnsecrets
from espn_api.football import League
import datetime

import warnings
with warnings.catch_warnings():
        warnings.simplefilter(action='ignore', category=FutureWarning)

now = datetime.datetime.now()
now.isoformat(sep=" ", timespec="seconds")
#print(now)


##SETUP set these values for the seasons survivor pool

season = (input("What year to run?"))

if season.isdigit():
        pass
else:
        season = 2024



#Number of weeks it will take to get to 1 winner, same as number of participants

playnum = (input('How many players?'))



#empty sets for the cycle to add to. add any non-participants to the elims set
if (playnum.isdigit()) and (int(playnum) < 14):
        haters = (input('Who is inligible?'))
        haters = int(haters)
        elims = np.array([haters])
        #print('cond 1')
elif (playnum.isdigit()):
        playnum = 14
        elims = np.array([])
else:
        elims = np.array([])
        playnum = int(14)

weekneed = int(playnum) + int(1)

#League settings mainly the year
league = League(league_id=espnsecrets.league, year=int(season), espn_s2=espnsecrets.espn_s2, swid=espnsecrets.swid)

######

standings = league.standings_weekly(1)

standings = pd.DataFrame(standings)

teamlist = league.teams

#loop through teams
x = range(1,15)

#loop through weeks for each team
y = range(1,14)

#set final matrix column names
df = pd.DataFrame(columns=['Team ID','Owner','Out','1','2','3','4','5','6','7','8','9','10','11','12','13','14'])

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
        

        df = pd.concat([df, newrow.astype(df.dtypes)], axis=0, ignore_index=True)

        #print(df.dtypes)


w = range(1,weekneed)
for l in elims:
        df.at[(int(l)-1), 'Out'] = 'inelig'

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
        elif (found>0):
                df.at[(int(found-1)), 'Out'] = 'OUT ' + 'wk' + vtext
        
        cycles = cycles + 1


print(df)
#df.to_csv('/Users/Scott/Documents/Python_Fantasy/season' + str(season) + 'scores.csv', index=True)

makecsv = input('Export a CSV?') or 'n'

if makecsv  in {'y', 'Y', 'yes', 'YES', 'Yes'}:

        #filename = input('What do you want to name it?')
        filename = '/Users/Scott/Documents/Python_Fantasy/season' + str(season) + 'scores.csv'
        df.to_csv(filename, index=True)

        pd.read_csv(filename).iloc[:, 1:].apply(lambda x: x.replace(r'[^\w\s.]','',regex=True)).to_csv(filename)

        #df.to_csv('season.csv', index=True)



