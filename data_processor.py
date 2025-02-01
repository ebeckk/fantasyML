import pandas as pd
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import joblib

def get_and_process_data():
    # Fetch data from FPL API
    base_url = "https://fantasy.premierleague.com/api/"
    response = requests.get(f"{base_url}bootstrap-static/").json()
    
    # Create DataFrames
    players_df = pd.DataFrame(response['elements'])
    teams_df = pd.DataFrame(response['teams'])
    
    # Fetch fixture data
    fixtures_response = requests.get(f"{base_url}fixtures/").json()
    fixtures_df = pd.DataFrame(fixtures_response)
    
    # Process fixture data to calculate average FDR for each team
    team_fdr = {}
    for team_id in teams_df['id']:
        home_fdr = fixtures_df[fixtures_df['team_h'] == team_id]['team_h_difficulty'].mean()
        away_fdr = fixtures_df[fixtures_df['team_a'] == team_id]['team_a_difficulty'].mean()
        avg_fdr = (home_fdr + away_fdr) / 2 if (home_fdr + away_fdr) > 0 else 5  # Default FDR
        team_fdr[team_id] = avg_fdr
    
    # Map FDR to players based on their team
    players_df['FDR'] = players_df['team'].map(team_fdr)
    
    # Add rolling averages for recent performance
    def add_rolling_features(df, window_sizes=[3, 5, 10]):
        for window in window_sizes:
            df[f'Goals_Rolling_{window}'] = df.groupby('second_name')['goals_scored'].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean()
            )
            df[f'Assists_Rolling_{window}'] = df.groupby('second_name')['assists'].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean()
            )
            df[f'Points_Rolling_{window}'] = df.groupby('second_name')['total_points'].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean()
            )
        return df
    
    players_df = add_rolling_features(players_df)
    
    # Add upcoming FDR for next 3 fixtures
    def get_upcoming_fdr(team_id, fixtures_df, num_fixtures=3):
        team_fixtures = fixtures_df[
            (fixtures_df['team_h'] == team_id) | (fixtures_df['team_a'] == team_id)
        ].head(num_fixtures)
        avg_fdr = team_fixtures[['team_h_difficulty', 'team_a_difficulty']].values.mean()
        return avg_fdr
    
    players_df['Upcoming_FDR'] = players_df['team'].apply(lambda team_id: get_upcoming_fdr(team_id, fixtures_df))
    
    # Add next opponent and difficulty rating
    def get_next_fixture(team_id, fixtures_df):
        team_fixtures = fixtures_df[
            ((fixtures_df['team_h'] == team_id) | (fixtures_df['team_a'] == team_id)) &
            (fixtures_df['finished'] == False)  # Only upcoming fixtures
        ].sort_values('event').head(1)  # Get the next fixture
        
        if not team_fixtures.empty:
            fixture = team_fixtures.iloc[0]
            if fixture['team_h'] == team_id:
                opponent_team_id = fixture['team_a']
                is_home = True
            else:
                opponent_team_id = fixture['team_h']
                is_home = False
            
            opponent_name = teams_df.loc[teams_df['id'] == opponent_team_id, 'name'].values[0]
            fdr = fixture['team_h_difficulty'] if is_home else fixture['team_a_difficulty']
            return opponent_name, fdr
        return None, None
    
    players_df['Next_Opponent'], players_df['Next_FDR'] = zip(*players_df['team'].apply(
        lambda team_id: get_next_fixture(team_id, fixtures_df)
    ))
    
    # Add team-level metrics
    team_stats = players_df.groupby('team').agg({
        'goals_scored': 'mean',
        'clean_sheets': 'mean',
        'total_points': 'mean'
    }).reset_index().rename(columns={
        'goals_scored': 'Team_Goals',
        'clean_sheets': 'Team_Clean_Sheets',
        'total_points': 'Team_Points'
    })
    
    players_df = players_df.merge(team_stats, on='team')
    
    # Add consistency metric
    players_df['Points_Consistency'] = players_df.groupby('second_name')['total_points'].transform('std').fillna(0)
    
    # Process player data
    processed_df = pd.DataFrame({
        'Name': players_df['first_name'] + ' ' + players_df['second_name'],
        'Team': players_df['team'].map(teams_df.set_index('id')['name']),
        'Position': players_df['element_type'].map({
            1: 'Goalkeeper',
            2: 'Defender',
            3: 'Midfielder',
            4: 'Forward'
        }),
        'Price': players_df['now_cost'] / 10.0,
        'Total_Points': players_df['total_points'],
        'Minutes': players_df['minutes'],
        'Goals': players_df['goals_scored'],
        'Assists': players_df['assists'],
        'Clean_Sheets': players_df['clean_sheets'],
        'Form': players_df['form'].astype(float),
        'Points_Per_Game': players_df['points_per_game'].astype(float),
        'Selected_By_Percent': players_df['selected_by_percent'].astype(float),
        'FDR': players_df['FDR'],  # Fixture Difficulty Rating
        'Goals_Rolling_3': players_df['Goals_Rolling_3'],
        'Goals_Rolling_5': players_df['Goals_Rolling_5'],
        'Assists_Rolling_3': players_df['Assists_Rolling_3'],
        'Assists_Rolling_5': players_df['Assists_Rolling_5'],
        'Points_Rolling_3': players_df['Points_Rolling_3'],
        'Points_Rolling_5': players_df['Points_Rolling_5'],
        'Upcoming_FDR': players_df['Upcoming_FDR'],
        'Team_Goals': players_df['Team_Goals'],
        'Team_Clean_Sheets': players_df['Team_Clean_Sheets'],
        'Team_Points': players_df['Team_Points'],
        'Points_Consistency': players_df['Points_Consistency'],
        'Next_Opponent': players_df['Next_Opponent'],  # Next opponent name
        'Next_FDR': players_df['Next_FDR'],  # Next opponent difficulty
        'Image_URL': "https://resources.premierleague.com/premierleague/photos/players/110x140/p" + players_df['code'].astype(str) + ".png"
    })
    
    # Save processed data
    processed_df.to_csv('player_data_latest.csv', index=False)
    
    # Normalize features
    features = [
        'Minutes', 'Goals', 'Assists', 'Clean_Sheets', 
        'Form', 'Points_Per_Game', 'Selected_By_Percent', 
        'FDR', 'Goals_Rolling_3', 'Goals_Rolling_5', 
        'Assists_Rolling_3', 'Assists_Rolling_5', 
        'Points_Rolling_3', 'Points_Rolling_5', 
        'Upcoming_FDR', 'Team_Goals', 'Team_Clean_Sheets', 
        'Team_Points', 'Points_Consistency'
    ]
    
    X = processed_df[features]
    y = processed_df['Total_Points']
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train and save the model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    joblib.dump(model, 'fpl_model_latest.joblib')
    
    # Save feature names for later use
    joblib.dump(features, 'model_features.joblib')
    
    # Evaluate model using cross-validation
    scores = cross_val_score(model, X_scaled, y, cv=5, scoring='neg_mean_squared_error')
    print(f"Cross-Validation MSE: {-scores.mean()}")
    
    return "Data processing and model training complete!"

if __name__ == "__main__":
    get_and_process_data()