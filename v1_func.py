import requests
from bs4 import BeautifulSoup
from bs4 import Comment
from websearch import WebSearch as web
import pandas as pd
import time
import random
from v1_mini_func import *

AVERAGE_RUNS_PER_INNING = 0.444
NUM_INNINGS = 9

def get_lineup(team):
    url = web(team + " starting lineups").pages[0]
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    data = soup.find_all('div', class_="starting-lineups__teams starting-lineups__teams--xs starting-lineups__teams--md starting-lineups__teams--lg")

    lineup = data[0].text # Gets today's lineup only when index is 0
    lineup = lineup.split("\n")

    # Delete empty string elements and remove excess whitespace
    lineup = [item for item in lineup if item]
    lineup.pop(3)
    lineup.pop(1)
    lineup = [item.strip(' ') for item in lineup]

    # Establish away team and home team lineup
    awayTeam = [lineup[0][:3]]
    homeTeam = [lineup[1][:3]]
    lineup = lineup[2:]

    # Add players to respsective teams, delete info on position and handedness
    for i in range(len(lineup)):
        if i < 9:
            awayTeam.append(lineup[i][:-6].rstrip())
        else:
            homeTeam.append(lineup[i][:-6].rstrip())
    
    return awayTeam, homeTeam

def get_starting_pitching(team, year):
    url = web(team + " starting lineups").pages[0]
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    name_tags = soup.find_all('div', class_="starting-lineups__pitcher-name")

    away_starter = name_tags[0].text
    home_starter = name_tags[1].text
    starters = [away_starter.strip('\n'), home_starter.strip('\n')]
    starters_run_per_inn = []

    for pitcher in starters:
        print(pitcher + " bref stats, height, weight, position")
        possible_url = web(pitcher + " bref stats, height, weight, position").pages
        url = ''
        index = 0
        while not url:
            #print(possible_url[index])
            #print("baseball-reference" in possible_url[index])
            if "baseball-reference" in possible_url[index]:
                url = possible_url[index]
            index += 1
        #url = web(pitcher + " bref stats, height, weight, position").pages[0]
        print(url)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        if pitcher == "Shohei Ohtani":
            recent_starts_html = soup.find_all('table', id="last5_p")
        else:
            recent_starts_html = soup.find_all('table', id='last5')
        
        # Get pitcher data for last five starts
        try:
            recent_starts_table = pd.read_html(str(recent_starts_html))[0]

            recent_innings = string_to_int_sum(recent_starts_table["IP"], float)
            recent_runs_allowed = string_to_int_sum(recent_starts_table["R"], int)
            recent_avg_start_length = round(recent_innings / 5.0, 3)
            recent_runs_per_inning = round(recent_runs_allowed / recent_innings, 3)
        except: # In case no pitcher data is found
            recent_avg_start_length = 5
            recent_runs_per_inning = 0.6

        season_starts_table = []
        try:
            season_starts_html = soup.find_all('table', id='pitching_standard')
            season_starts_table = pd.read_html(str(season_starts_html))[0]
        except:
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            tables = []
            for each in comments:
                if 'table' in each:
                    try:
                        tables.append(pd.read_html(each)[0])
                    except:
                        continue
            
            some_tables = []
            for tab in tables:
                if 'W' in tab.columns:
                        some_tables += [tab]
            season_starts_table = some_tables[0]
        
        current_season_stats = season_starts_table.loc[season_starts_table['Year'] == year]
        current_season_stats = current_season_stats.loc[~current_season_stats['Tm'].str.contains("min")]    
        
        try:
            season_innings = float(current_season_stats.iloc[0]["IP"])
            season_runs = int(current_season_stats.iloc[0]["R"])
            num_games = int(current_season_stats.iloc[0]["G"])

            avg_start_length = round(season_innings / num_games, 3)
            avg_runs_per_inning = round(season_runs / season_innings, 3)
        except: # In case no pitcher data is found
            avg_start_length = 5
            avg_runs_per_inning = 0.6

        starters_run_per_inn += [starting_pitcher_calculation(recent_avg_start_length,
                recent_runs_per_inning, avg_start_length, avg_runs_per_inning)]
    
    return starters_run_per_inn

# Returns teams' bullpens' ERA in form [Away ERA, Home ERA]
def get_bullpen(away, home, year):
    url = web("mlb bullpen stats covers " + year).pages[0]
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    html = soup.find('table', id="MLB_RegularSeason")
    table = pd.read_html(str(html))[0]

    # Get bullpen information
    away_index, home_index = -1, -1
    for i in range(len(table)):
        curr_name = table.loc[i]['Team']
        if curr_name in away:
            away_index = i
        elif curr_name in home:
            home_index = i
        
        if away_index > 0 and home_index > 0:
            break

    away_era = table.iloc[away_index]['ERA']
    home_era = table.iloc[home_index]['ERA']

    return away_era, home_era

# Given a player name and the player's team, extract batting information for current season
# All arguments are strings
def extract_player_data_batting(player, team, year):
    # Find part of page that contains batting data
    print(player + " " + team + " bref stats, height, weight, position " + year)
    possible_url = web(player + " " + team + " bref stats, height, weight, position").pages
    url = ''
    index = 0
    while not url:
        if "baseball-reference" in possible_url[index]:
            url = possible_url[index]
        index += 1
    print(url)
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    html = soup.find('table', id="batting_standard")
    try:
        table = pd.read_html(str(html))[0]
        return table
    except: # In case no batter data is found
        columns = ["PA", "OBP", "H", "2B", "3B", "HR", "BB", "HBP", "GDP", "SH", "SF"]
        data = [[3783, .319, 839, 171, 14, 116, 325, 42, 71, 9, 26]]
        table = pd.DataFrame(data, columns=columns)
        return table

# Convert a lineup to stats
def player_to_stats(team, year):
    stats = []
    for player in team[1:]:
        stats += [extract_player_data_batting(player, team[0], year)]
        time.sleep(3)
    return stats

# Determines result of a single batter.
# TEAM is either home or away, BOP is batter order position (0-8), BASEPATHS shows occupied bases.
def batter(team, bop, basepaths):
    player = team[bop]
    obp = float(player["OBP"][0])
    times_on_base = int(player["H"][0]) + int(player["BB"][0]) + int(player["HBP"][0])
    if obp < round(random.uniform(0, 1), 3):
        times_out = int(player["PA"][0]) - times_on_base
        out_result = round(random.uniform(1, times_out)) # Generates GDP, SH, SF, or regular out

        if out_result <= int(player["GDP"][0]) and basepaths[0] == "*":
            return "GDP"
        elif out_result <= int(player["GDP"][0]) + int(player["SH"][0]) and basepaths.count("*") > 0:
            return "SH"
        elif out_result <= int(player["GDP"][0]) + int(player["SH"][0]) + int(player["SF"][0]) and basepaths[2] == "*":
            return "SF"
        else:
            return "Out"
    else:
        base_result = round(random.uniform(1, times_on_base)) # Generates hit, walk, HBP

        if base_result <= int(player["H"][0]):
            if base_result <= int(player["H"][0]) - int(player["2B"][0]) - int(player["3B"][0]) - int(player["HR"][0]):
                return "Single"
            elif base_result <= int(player["H"][0]) - int(player["3B"][0]) - int(player["HR"][0]):
                return "Double"
            elif base_result <= int(player["H"][0]) - int(player["HR"][0]):
                return "Triple"
            else:
                return "Home Run"
        elif base_result <= int(player["H"][0]) + int(player["BB"][0]):
            return "Walk"
        else:
            return "HBP"
        
# Simulates an inning and returns the number of runs batting team has and the next BOP
def inning(runs, bop, stats):
    outs_left = 3
    runners_position = "---"

    while outs_left > 0:
        result = batter(stats, bop, runners_position)
        if result == "Out":
            outs_left -= 1
        elif result == "GDP":
            outs_left -= 2
            if outs_left > 0 and runners_position[2] == "*":
                runs += 1
            runners_position = "--" + runners_position[1]
        elif result == "SH":
            outs_left -= 1
            if outs_left > 0 and runners_position[2] == "*":
                runs += 1
            runners_position = "-" + runners_position[0:2]
        elif result == "SF":
            outs_left -= 1
            if outs_left > 0 and runners_position[2] == "*":
                runs += 1
            runners_position = runners_position[0:2] + "-"
        elif result == "Double":
            runs += runners_position[1:].count("*")
            runners_position = "-*" + runners_position[0]
        elif result == "Triple":
            runs += runners_position.count("*")
            runners_position = "--*"
        elif result == "Home Run":
            runs = runs + runners_position.count("*") + 1
            runners_position = "---"
        else:
            runs += runners_position[2:].count("*")
            runners_position = "*" + runners_position[:2]

        if bop == 8: # i.e. if at end of lineup, go back to top of order
            bop = 0
        else:
            bop += 1

    return runs, bop

# Simulates a game
def game(away_stats, home_stats, away_runs, home_runs, away_bop, home_bop, starters, bullpen):
    num_half_innings = 18
    for half_inning in range(num_half_innings):
        if half_inning % 2 == 0: # i.e. away team is batting
            away_runs, away_bop = inning(away_runs, away_bop, away_stats)
        else:
            home_runs, home_bop = inning(home_runs, home_bop, home_stats)
    
    # Factor impact of starting pitcher
    away_starting_pitcher_difference = (AVERAGE_RUNS_PER_INNING - starters[0][0]) * starters[0][1]
    home_starting_pitcher_difference = (AVERAGE_RUNS_PER_INNING - starters[1][0]) * starters[1][1]
    away_runs -= home_starting_pitcher_difference
    home_runs -= away_starting_pitcher_difference

    # Factor impact of bullpen
    away_bullpen_runs_per_inning = round(bullpen[0] / NUM_INNINGS, 3)
    away_bullpen_innings = NUM_INNINGS - starters[0][1]
    away_bullpen_difference = (AVERAGE_RUNS_PER_INNING - away_bullpen_runs_per_inning) * away_bullpen_innings
    home_bullpen_runs_per_inning = round(bullpen[1] / NUM_INNINGS, 3)
    home_bullpen_innings = NUM_INNINGS - starters[1][1]
    home_bullpen_difference = (AVERAGE_RUNS_PER_INNING - home_bullpen_runs_per_inning) * home_bullpen_innings
    away_runs -= home_bullpen_difference
    home_runs -= away_bullpen_difference

    while away_runs == home_runs:
        away_runs, away_bop = inning(away_runs, away_bop, away_stats)
        home_runs, home_bop = inning(home_runs, home_bop, home_stats)
    
    return away_runs, home_runs
