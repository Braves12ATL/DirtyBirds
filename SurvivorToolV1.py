import pandas as pd
import csv
import espn_api
import espnsecrets
from espn_api.football import League

league = League(league_id=68054, year=2024, espn_s2=espnsecrets.espn_s2, swid=espnsecrets.swid)



x = range(0,7)

wk = 1
weekcol = 'Week ' + str(wk) + ' Score'
df = pd.DataFrame(columns=['Team ID','Owner','Team',str(weekcol)])
count = 0

owners = espnsecrets.owners

onrs = pd.Series([owners])

for i in x:
        count = count + 1
        box_scores = league.box_scores(wk)
        ht = (str(box_scores[i].home_team)).replace('Team', '')
        htid = (int(box_scores[i].home_team.team_id))
        hownid = htid - 1
        honr = (str(owners[hownid]))
        hs = float(box_scores[i].home_score)
        wt = (str(box_scores[i].away_team)).replace('Team', '')
        atid = (int(box_scores[i].away_team.team_id))
        aownid = atid - 1
        aonr = (str(owners[aownid]))
        ws = float(box_scores[i].away_score)
        hdata = [{'Team ID':[htid],'Owner':[honr],'Team':[ht], str(weekcol):[hs]}]
        adata = [{'Team ID':[atid],'Owner':[aonr],'Team':[wt], str(weekcol):[ws]}]
        df_new_rowh = pd.DataFrame(hdata)
        df_new_rowa = pd.DataFrame(adata)
        df = pd.concat([df, df_new_rowh, df_new_rowa], axis=0, ignore_index=False)

#pd.set_option('display.max_colwidth', 130)
#df['Team'] = df['Team'].apply(str)
#df['Score'] = df['Score'].apply(str)
#df['Score'].astype(str)
                                     
dff = df.sort_values('Team ID')
dff.to_csv('this_weeks_scores.csv', index=True)


pd.read_csv('this_weeks_scores.csv').iloc[:, 1:].apply(lambda x: x.replace(r'[^\w\s.]','',regex=True)).to_csv('this_weeks_scores.csv')

print(dff)