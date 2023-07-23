from datetime import datetime
import pandas as pd
import time
import random

YEAR = str(datetime.now().year)

# Given a team name, look at how the team has done in its last ten games and
# its current winning/losing streak. Based on that, calculate a number for
# which every batter's OBP on that team will be multiplied by.
def recent_team_performance_factor(team_name):
    standings_url = "https://www.foxsports.com/mlb/standings"
    division_standings = pd.read_html(standings_url)
    time.sleep(random.uniform(0.5, 1))

    streak_multiplier, last_ten_multiplier = 0, 0
    for division in division_standings:
        curr_division = division.columns[1] # has format DIVISION.1
        team_row = division[division[curr_division] == team_name]
        if not team_row.empty:
            team_row = team_row.reset_index(drop=True)
            streak_type = team_row.loc[0, "STRK"][0] # checks if team is on winning or losing streak
            streak = int(team_row.loc[0, "STRK"][1:])
            # Calculate impact of streak on team batting's OBP.
            if streak_type == "W":
                streak_multiplier = round(pow(1.01, streak), 5)
            elif streak_type == "L":
                streak_multiplier = round(pow(0.99, streak), 5)

            last_ten_wins = int(team_row.loc[0, "L10"][0]) # check number of wins in last ten games
            if last_ten_wins > 5:
                last_ten_multiplier = round(pow(1.01, last_ten_wins - 5), 5)
            else:
                last_ten_multiplier = round(pow(0.99, 5 - last_ten_wins), 5)

            return round(streak_multiplier + last_ten_multiplier - 1, 5)

# Given a team name, determine how much better or worse the pitching staff does
# compared to the league average. Number greater than 1 indicates worse than average.
def team_pitching_performance(team_name):
    # Gets the URL and table for team pitching statistics for the season.
    standard_pitching_url = "https://www.baseball-reference.com/leagues/majors/" + YEAR + "-batting-pitching.shtml"
    team_pitching_stats_table = pd.read_html(standard_pitching_url)[0][:-2]
    for col in team_pitching_stats_table.columns[1:]: # convert numerical quantities to float types
        team_pitching_stats_table[col] = team_pitching_stats_table[col].astype("float")
    time.sleep(random.uniform(3, 4))

    league_avg = team_pitching_stats_table[team_pitching_stats_table["Tm"] == "League Average"]
    team_stats = team_pitching_stats_table[team_pitching_stats_table["Tm"].str.contains(team_name)]
    league_avg = league_avg.reset_index(drop=True)
    team_stats = team_stats.reset_index(drop=True)
    return round(team_stats.loc[0, "OBP"] / league_avg.loc[0, "OBP"], 5)

# Given a team name, find the corresponding stadium and weather. Return the factor
# by which the pitching will be affected (i.e. multiply BAA by this number).
def get_stadium_weather(team):
    table = pd.read_csv("~/Documents/mlb_project/names_stadiums.csv")
    row = table.loc[table["Name"] == team]
    row = row.reset_index(drop=True)
    temperature = row.loc[0, "Temperature"]
    if row.loc[0, "Retractable Roof"] == "Yes" or (temperature >= 72 and temperature <= 78):
        return 1
    difference = min(abs(temperature - 78), abs(temperature - 72)) # establish ideal range of 72-78
    return round(pow(1.01, difference), 5)

# Given a team name, find the corresponding park factors, which will be returned in
# the form of a pandas Series
def get_stadium_factor(team):
    table = pd.read_csv("~/Documents/mlb_project/park_factors.csv")
    row = table.loc[table["Team"] == team]
    row = row.reset_index(drop=True)
    return row

# Given a list of Pitcher objects in the bullpen, sort them based on their statistics.
def rank_bullpen(bullpen):
    rankings = []
    for pitcher in bullpen:
        totals_table = pitcher.totals_table_game_level
        if totals_table.empty:
            rankings += [(pitcher.name, 0)]
        else:
            totals_row = totals_table.loc[totals_table["Split"] == YEAR + " Totals"]
            era = totals_row.loc[0, "ERA"]
            if era == 0:
                era = 4.3 # Set to league average if ERA is 0
            ip = totals_row.loc[0, "IP"]
            whip = totals_row.loc[0, "WHIP"]
            score = 4.3 / era * ip / whip
            rankings += [(pitcher.name, score)]

    rankings = sorted(rankings, key=lambda x: x[1], reverse=True)
    print(rankings)
    for i in range(len(rankings)):
        for pitcher in bullpen:
            if rankings[i][0] == pitcher.name:
                rankings[i] = pitcher
                break
    return rankings