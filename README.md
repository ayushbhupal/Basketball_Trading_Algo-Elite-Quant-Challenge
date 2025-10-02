Idea - A Bayesian-inspired, momentum-adjusted probability model identifies inefficiencies between true win probabilities and market odds. Trades are executed only on significant edges, sized by Kelly, and strictly risk-managed to capture value from market adjustment lags.
This strategy exploits mispricings between a real-time win probability model and market-implied probabilities in a simulated basketball betting market.
1.	Baseline & Setup
  Start with a 55% home team advantage and an initial bankroll of $100,000.

2.	Dynamic Win Probability Model
      Incorporates score differential (increasing weight as game progresses).
    	Tracks momentum from game events (scores, fouls, turnovers, dunks, etc.), with exponential decay (half-life ~180s).
    	Continuously updates the home team win probability.

3.	Trading Logic
    	Compare model probability with market probability.
    	Enter trades only if the mispricing is ≥ 3%:
      	BUY if the home team is undervalued.
    	  SELL if the home team is overvalued.
  	
4.	Position Sizing & Risk Controls
    	Trade size determined using a modified Kelly Criterion, scaled by bankroll.
    	Risk constraints:
      	Max $20,000 per position.
        Max 10% of capital at risk.
        Minimum trade size of $100.
  	
5.	Risk Management & Exits
    	Take Profit: Lock in gains at ≥ $80,000 (scaled by Kelly).
    	Stop Loss: Exit if losses reach $50,000.
    	Late-Game Safety Exit: In the last 10 minutes, if score diff < 5 and profit > $55,000, exit.
    	Close all positions at the end of the game.
<img width="468" height="582" alt="image" src="https://github.com/user-attachments/assets/1857c645-af39-4b2a-b50a-10807432ae2e" />
