from flask import Flask, render_template, request, jsonify
import pandas as pd
import joblib

app = Flask(__name__)

def load_data():
    # Load the processed player data, trained model, and feature names
    df = pd.read_csv('player_data_latest.csv')
    model = joblib.load('fpl_model_latest.joblib')
    features = joblib.load('model_features.joblib')
    return df, model, features

def get_best_team(df, model, features, formation='3-4-3', budget=100.0):
    # Parse the formation string into defender, midfielder, and forward counts
    def_num, mid_num, fwd_num = map(int, formation.split('-'))
    
    # Predict points for each player using the model
    X = df[features]  # Ensure the correct features are used
    df['Predicted_Points'] = model.predict(X)
    
    # Select the best players for each position
    gks = df[df['Position'] == 'Goalkeeper'].nlargest(2, 'Predicted_Points')
    defs = df[df['Position'] == 'Defender'].nlargest(def_num + 1, 'Predicted_Points')
    mids = df[df['Position'] == 'Midfielder'].nlargest(mid_num + 1, 'Predicted_Points')
    fwds = df[df['Position'] == 'Forward'].nlargest(fwd_num + 1, 'Predicted_Points')
    
    # Finalize starting XI
    gks = gks.nlargest(1, 'Predicted_Points')  # Only 1 goalkeeper in starting XI
    starting_xi = pd.concat([gks, defs[:def_num], mids[:mid_num], fwds[:fwd_num]])
    starting_xi_ids = starting_xi['Name']
    
    # Select substitutes
    available_subs = df[~df['Name'].isin(starting_xi_ids)]
    subs_gk = available_subs[available_subs['Position'] == 'Goalkeeper'].nlargest(1, 'Predicted_Points')
    subs_outfield = available_subs[available_subs['Position'] != 'Goalkeeper'].nlargest(3, 'Predicted_Points')
    subs = pd.concat([subs_gk, subs_outfield]).nlargest(4, 'Predicted_Points')
    
    # Combine starting XI and substitutes
    team = pd.concat([starting_xi, subs])
    
    # Build the final team within the budget
    selected_team = []
    total_cost = 0.0
    
    for _, player in team.iterrows():
        if total_cost + player['Price'] <= budget:
            selected_team.append(player.to_dict())
            total_cost += player['Price']
            if len(selected_team) == (1 + def_num + mid_num + fwd_num + 4):  # Total players in squad
                break
    
    return pd.DataFrame(selected_team), subs

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/update_data', methods=['POST'])
def update_data():
    try:
        # Call the data processor to fetch and process the latest data
        from data_processor import get_and_process_data
        result = get_and_process_data()
        return jsonify({'status': 'success', 'message': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_team', methods=['POST'])
def get_team():
    # Load the latest data, model, and feature names
    df, model, features = load_data()
    
    # Get user inputs for formation and budget
    formation = request.form.get('formation', '3-4-3')
    budget = float(request.form.get('budget', 100.0))
    
    # Ensure the dataset contains all required features
    if not all(feature in df.columns for feature in features):
        missing_features = [feature for feature in features if feature not in df.columns]
        return jsonify({'status': 'error', 'message': f'Missing features: {missing_features}'}), 500
    
    # Generate the best team based on the inputs
    best_team, substitutes = get_best_team(df, model, features, formation, budget)
    
    # Return the results as JSON
    return jsonify({
        'team': best_team.to_dict('records'),
        'substitutes': substitutes.to_dict('records'),
        'total_cost': round(best_team['Price'].sum(), 1),
        'predicted_points': round(best_team['Predicted_Points'].sum(), 1),
        'remaining_budget': round(budget - best_team['Price'].sum(), 1)
    })

if __name__ == '__main__':
    app.run(debug=True)