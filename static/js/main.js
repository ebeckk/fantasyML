// main.js

class TeamOptimizer {
    constructor() {
        this.initializeEventListeners();
        this.initializeUpdateButton(); 
    }

    initializeEventListeners() {
        document.getElementById('teamForm').addEventListener('submit', (e) => this.handleFormSubmit(e));
    }

    initializeUpdateButton() {  
        const updateBtn = document.getElementById('updateDataBtn');  
        const updateStatus = document.getElementById('updateStatus');  
        
       updateBtn.addEventListener('click', async () => {  
       try {  
        updateBtn.disabled = true;  
                    updateStatus.textContent = 'Updating data...';  
        
                    const response = await fetch('/update_data', {  
                        method: 'POST'  
                    });  
        
                    const data = await response.json();  
        
                    if (data.status === 'success') {  
                        updateStatus.textContent = 'Data updated successfully!';  
                        updateStatus.style.color = 'green';  
                        // Optionally refresh the team display  
                        const formEvent = new Event('submit');  
                        document.getElementById('teamForm').dispatchEvent(formEvent);  
                    } else {  
                        throw new Error(data.message);  
                    }  
                } catch (error) {  
                    console.error('Error:', error);  
                    updateStatus.textContent = 'Error updating data';  
                    updateStatus.style.color = 'red';  
                } finally {  
                    updateBtn.disabled = false;  
                    setTimeout(() => {  
                        updateStatus.textContent = '';  
                    }, 3000);  
                }  
            });  
        }  

    async handleFormSubmit(e) {
        e.preventDefault();
        const formData = new FormData(e.target);

        try {
            const response = await fetch('/get_team', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.error) {
                this.showError(data.error);
                return;
            }

            this.updateTeamDisplay(data, formData.get('formation'));
            this.updateTeamStats(data);
        } catch (error) {
            console.error('Error:', error);
            this.showError('An error occurred while getting the team');
        }
    }

    updateTeamDisplay(data, formation) {
        this.displayTeam(data.team, formation);
        this.displaySubstitutes(data.substitutes || []);
    }

    updateTeamStats(data) {
        document.getElementById('totalCost').textContent = data.total_cost;
        document.getElementById('predictedPoints').textContent = data.predicted_points;
        document.getElementById('remainingBudget').textContent = data.remaining_budget;
    }

    displayTeam(team, formation) {
        if (!team || team.length === 0) {
            this.showError('No team data available for rendering.');
            return;
        }

        const pitch = document.getElementById('pitch');
        pitch.innerHTML = '';

        const [def, mid, fwd] = formation.split('-').map(Number);
        const positions = this.calculatePositions(def, mid, fwd);

        team.slice(0, 11).forEach((player, index) => {
            const pos = positions[index];
            const playerElement = this.createPlayerIcon(player, pos.left, pos.top);
            pitch.appendChild(playerElement);
        });
    }

    displaySubstitutes(substitutes) {
        const substitutesDiv = document.getElementById('substitutes');
        substitutesDiv.innerHTML = '';
        substitutes.forEach(player => {
            const subElement = this.createSubIcon(player);
            substitutesDiv.appendChild(subElement);
        });
    }

    createPlayerIcon(player, left, top) {
        const div = document.createElement('div');
        div.className = `player-icon pitch-player ${player.Position.toLowerCase()}`;
        div.style.left = `${left}%`;
        div.style.top = `${top}%`;
        div.innerHTML = `
            <img src="${player.Image_URL}" alt="${player.Name}" class="player-img">
            <div class="player-name">${player.Name.split(' ').pop()}</div>
            <div class="player-stats">
                £${player.Price}m <span class="stat-divider">•</span> ${Math.round(player.Predicted_Points)} pts
            </div>
        `;
        div.addEventListener('click', () => this.showPlayerStats(player));
        return div;
    }

    createSubIcon(player) {
        const div = document.createElement('div');
        div.className = `player-icon substitute ${player.Position.toLowerCase()}`;
        div.innerHTML = `
            <img src="${player.Image_URL}" alt="${player.Name}" class="player-img">
            <div class="player-name">${player.Name.split(' ').pop()}</div>
            <div class="player-stats">
                Price: £${player.Price}m, Pts: ${Math.round(player.Predicted_Points)}
            </div>
        `;
        div.addEventListener('click', () => this.showPlayerStats(player));
        return div;
    }

    showPlayerStats(player) {
        const modalFields = {
            'modalPlayerName': player.Name,
            'modalPlayerTeam': player.Team,
            'modalPlayerPosition': player.Position,
            'modalPlayerPrice': player.Price.toFixed(1),
            'modalPlayerTotalPoints': player.Total_Points,
            'modalPlayerMinutes': player.Minutes,
            'modalPlayerGoals': player.Goals,
            'modalPlayerAssists': player.Assists,
            'modalPlayerCleanSheets': player.Clean_Sheets,
            'modalPlayerForm': player.Form,
            'modalPlayerPointsPerGame': player.Points_Per_Game,
            'modalPlayerSelectedBy': player.Selected_By_Percent,
            'modalPlayerNextOpponent': player.Next_Opponent || 'N/A',
            'modalPlayerNextFDR': player.Next_FDR || 'N/A'
        };

        Object.entries(modalFields).forEach(([id, value]) => {
            document.getElementById(id).textContent = value;
        });

        // Set player image
         const playerImageElement = document.getElementById('modalPlayerImage');
        if (player.Image_URL) {
            playerImageElement.src = player.Image_URL;
            playerImageElement.alt = player.Name;
        } else {
             // Fallback image if Image_URL is missing
             playerImageElement.src = 'https://via.placeholder.com/100'; // Placeholder image
             playerImageElement.alt = 'No Image Available';
        }

        const modal = new bootstrap.Modal(document.getElementById('playerStatsModal'));
        modal.show();
    }

    calculatePositions(def, mid, fwd) {
        const positions = [];
        const pitchWidth = 100;
        const pitchHeight = 100;

        // Goalkeeper position
        positions.push({ left: pitchWidth / 2, top: pitchHeight * 0.1 });

        // Defenders positions
        const defSpacing = pitchWidth / (def + 1);
        for (let i = 1; i <= def; i++) {
            positions.push({ left: i * defSpacing, top: pitchHeight * 0.3 });
        }

        // Midfielders positions
        const midSpacing = pitchWidth / (mid + 1);
        for (let i = 1; i <= mid; i++) {
            positions.push({ left: i * midSpacing, top: pitchHeight * 0.5 });
        }

        // Forwards positions
        const fwdSpacing = pitchWidth / (fwd + 1);
        for (let i = 1; i <= fwd; i++) {
            positions.push({ left: i * fwdSpacing, top: pitchHeight * 0.7 });
        }

        return positions;
    }

    showError(message) {
        alert(message);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TeamOptimizer();

    
});