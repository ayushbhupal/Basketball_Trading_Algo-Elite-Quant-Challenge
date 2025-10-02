# This strategy implements probability arbitrage by comparing real-time basketball game probabilities against 
# market-implied prices. Starting with a 55% home team advantage, the model continuously updates win probabilities 
# based on score differentials, momentum shifts and subsequent decay, and game events. When our model identifies a significant mispricing
# (3%+ probability difference), it executes trades: buying home team contracts when the market underestimates their 
# chances, and selling when overvalued. The algorithm uses Kelly criterion position sizing with conservative risk 
# limits, leveraging superior bayesian modelling to capture edges before the market fully adjusts to new information.

"""
Basketball Trading Algorithmic Strategy
"""

from enum import Enum
from typing import Optional
import math

class Side(Enum):
    BUY = 0
    SELL = 1

class Ticker(Enum):
    # TEAM_A (home team)
    TEAM_A = 0

def place_market_order(side: Side, ticker: Ticker, quantity: float) -> None:
    """Place a market order."""
    return

def place_limit_order(side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> int:
    """Place a limit order."""
    return 0

def cancel_order(ticker: Ticker, order_id: int) -> bool:
    """Cancel an order."""
    return 0

class Strategy:
    """Basketball Probability Arbitrage Strategy"""

    def reset_state(self) -> None:
        """Reset the state of the strategy to the start of game position."""
        self.home_score = 0
        self.away_score = 0
        self.time_remaining = 2880.0
        self.position = 0
        self.capital = 100000.0
        self.cash = 100000.0
        self.portfolio_value = 100000.0
        
        # RISK MANAGEMENT PARAMETERS
        self.max_position_size = 20000.0  # Max $20,000 per position
        self.max_portfolio_risk = 0.1     # Max 10% of capital at risk
        self.kelly_fraction = 1.0         # Full Kelly (aggressive)
        self.min_trade_size = 100.0       # Minimum trade size in dollars
        
        # Trading parameters - FIXED: Now using proper price scale
        self.model_prob = 0.55  # Your model probability (0-1 scale)
        self.market_price = 55.0  # Market price in dollars (not probability!)
        
        # Game state tracking
        self.home_momentum = 0
        self.away_momentum = 0
        self.recent_events = []
        self.active_orders = []
        self.last_event_time = None   # store previous time_remaining
        self.momentum_tau = 180.0     # decay time constant in seconds (2 minutes)

    def __init__(self) -> None:
        """Initialization code goes here."""
        self.reset_state()

    def market_price_to_probability(self, price: float) -> float:
        """Convert market price to implied probability."""
        # Assuming price range: ~50 (5% prob) to ~150 (95% prob)
        # Linear conversion: price 50 = 0.05, price 150 = 0.95
        return (price - 50.0) / 100.0

    def probability_to_price(self, probability: float) -> float:
        """Convert probability to expected market price."""
        return 50.0 + (probability * 100.0)

    def calculate_true_probability(self) -> float:
        """Calculate real probability of home team winning based on game state."""
        if self.time_remaining <= 0:
            return 1.0 if self.home_score > self.away_score else 0.0 if self.home_score < self.away_score else 0.5
        
        # Start with 55% home advantage
        base_prob = 0.55
        
        # Score differential impact
        score_diff = self.home_score - self.away_score
        time_factor = 1.0 - (self.time_remaining / 2880.0)
        score_impact = score_diff * 0.02 * (1.0 + time_factor * 2.0)
        
        # Momentum impact
        momentum_impact = (self.home_momentum - self.away_momentum) * 0.005
        
        true_prob = base_prob + score_impact + momentum_impact
        return max(0.05, min(0.95, true_prob))

    def get_event_impact(self, event_type: str, home_away: str, shot_type: Optional[str]) -> float:
        """Calculate the impact of a game event on team momentum."""
        impact = 0.0
        
        if event_type == "SCORE":
            impact = 3.0
            if shot_type == "THREE_POINT":
                impact = 4.0
            elif shot_type == "DUNK":
                impact = 5.0
        elif event_type == "MISSED":
            impact = -1.0
        elif event_type == "TURNOVER":
            impact = -2.0
        elif event_type == "STEAL":
            impact = 2.0
        elif event_type == "BLOCK":
            impact = 1.5
        elif event_type == "FOUL":
            impact = -1.0
            
        if home_away == "away":
            impact = -impact
            
        return impact
    
    def check_risk_management(self) -> None:
        """Check for take profit, stop loss, and late-game exits."""
        # Current PnL relative to starting capital
        pnl = self.portfolio_value - 100000.0
        
        # 1. Take Profit / Stop Loss
        tp_level = self.kelly_fraction * 80000.0
        sl_level = -self.kelly_fraction * 50000.0
        
        if pnl >= tp_level:
            print(f"TAKE PROFIT triggered! PnL = ${pnl:.2f} (TP Level: {tp_level:.2f})")
            if self.position > 0:
                place_market_order(Side.SELL, Ticker.TEAM_A, abs(self.position))
            elif self.position < 0:
                place_market_order(Side.BUY, Ticker.TEAM_A, abs(self.position))
            self.reset_state()
            return
        
        if pnl <= sl_level:
            print(f"STOP LOSS triggered! PnL = ${pnl:.2f} (SL Level: {sl_level:.2f})")
            if self.position > 0:
                place_market_order(Side.SELL, Ticker.TEAM_A, abs(self.position))
            elif self.position < 0:
                place_market_order(Side.BUY, Ticker.TEAM_A, abs(self.position))
            self.reset_state()
            return
        
        # 2. Late-game safety exit
        score_diff = abs(self.home_score - self.away_score)
        if self.time_remaining < 600 and score_diff < 5 and pnl > 55000:
            print(f"LATE-GAME SAFETY EXIT triggered! Score diff={score_diff}, "
                  f"Time remaining={self.time_remaining:.1f}s, PnL=${pnl:.2f}")
            if self.position > 0:
                place_market_order(Side.SELL, Ticker.TEAM_A, abs(self.position))
            elif self.position < 0:
                place_market_order(Side.BUY, Ticker.TEAM_A, abs(self.position))
            self.reset_state()


    def should_trade(self, model_prob: float, market_price: float) -> tuple:
        """Trade when model probability differs significantly from market price."""
        # Convert market price to probability for comparison
        market_prob = self.market_price_to_probability(market_price)
        
        confidence_threshold = 0.03  # 3% probability difference
        
        if model_prob > market_prob + confidence_threshold:
            # Market UNDERvalues home team - BUY
            return True, Side.BUY, model_prob - market_prob
        elif model_prob < market_prob - confidence_threshold:
            # Market OVERvalues home team - SELL
            return True, Side.SELL, market_prob - model_prob
        else:
            return False, None, 0.0

    def calculate_position_size(self, probability_edge: float, side: Side, market_price: float) -> float:
        """Calculate position size using Kelly Criterion with risk management."""
        
        # Convert to probabilities for Kelly calculation
        market_prob = self.market_price_to_probability(market_price)
        
        if side == Side.BUY:
            # If we BUY, upside if price goes to max (150 = 95% prob)
            # downside if price goes to min (50 = 5% prob)
            upside = 150.0 - market_price  # Potential gain per share
            downside = market_price - 50.0  # Potential loss per share
        else:  # SELL
            # If we SELL, upside if price goes to min (50 = 5% prob)
            # downside if price goes to max (150 = 95% prob)
            upside = market_price - 50.0
            downside = 150.0 - market_price
        
        if upside <= 0 or downside <= 0:
            return 0.0
            
        # Win probability based on our edge
        win_prob = 0.5 + (probability_edge * 2)
        win_prob = max(0.51, min(0.95, win_prob))
        lose_prob = 1.0 - win_prob
        
        # Kelly fraction
        b = upside / downside  # Odds
        kelly_fraction = (win_prob * b - lose_prob) / b if b > 0 else 0.0
        
        # Apply Kelly fraction
        kelly_fraction = max(0.0, kelly_fraction) * self.kelly_fraction
        
        # Position size in dollars
        position_dollars = min(
            self.capital * kelly_fraction,
            self.max_position_size,
            self.cash if side == Side.BUY else abs(self.position) * market_price
        )
        
        # Ensure minimum trade size
        position_dollars = max(self.min_trade_size, position_dollars)
        
        # Convert to shares
        shares = position_dollars / market_price
        return max(1.0, shares)  # Minimum 1 share

    # def can_afford_trade(self, side: Side, quantity: float, price: float) -> bool:
    #     """Check if we can afford the trade."""
    #     trade_value = quantity * price
        
    #     if side == Side.BUY:
    #         return trade_value <= self.cash and trade_value <= self.max_position_size
    #     else:  # SELL
    #         return quantity <= abs(self.position) if self.position < 0 else quantity <= self.position

    def can_afford_trade(self, side: Side, quantity: float, price: float) -> bool:
        if side == Side.BUY:
            return quantity * price <= self.cash and quantity <= self.max_position_size
        else:  # SELL
            return quantity <= self.max_position_size  # max short size allowed

    def update_portfolio_value(self) -> None:
        """Update portfolio value with current market prices."""
        position_value = self.position * self.market_price
        self.portfolio_value = self.cash + position_value

    def on_trade_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        """Called whenever two orders match."""
        print(f"Trade: {ticker} {side} {quantity} shares @ ${price:.3f}")

    def on_orderbook_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        """Market price update."""
        self.market_price = price
        self.update_portfolio_value()

    def on_account_update(self, ticker: Ticker, side: Side, price: float, 
                         quantity: float, capital_remaining: float) -> None:
        """Called whenever one of my orders is filled."""
        trade_value = quantity * price
        
        if side == Side.BUY:
            self.position += quantity
            self.cash -= trade_value
        else:
            self.position -= quantity
            self.cash += trade_value
            
        self.capital = capital_remaining
        self.update_portfolio_value()
        
        print(f"Filled: {side} {quantity} shares @ ${price:.3f}")
        print(f"Position: {self.position}, Cash: ${self.cash:.2f}, Portfolio: ${self.portfolio_value:.2f}")

    def on_game_event_update(self, event_type: str, home_away: str, home_score: int, 
                           away_score: int, player_name: Optional[str],
                           substituted_player_name: Optional[str], shot_type: Optional[str],
                           assist_player: Optional[str], rebound_type: Optional[str],
                           coordinate_x: Optional[float], coordinate_y: Optional[float],
                           time_seconds: Optional[float]) -> None:
        """Main trading logic."""
        
        if time_seconds is not None:
            if self.last_event_time is None:
                self.last_event_time = time_seconds
            dt = max(0.0, self.last_event_time - time_seconds)  # seconds elapsed
            decay = math.exp(-dt / self.momentum_tau)
            self.home_momentum *= decay
            self.away_momentum *= decay
            self.last_event_time = time_seconds


        # Update game state
        self.home_score = home_score
        self.away_score = away_score
        if time_seconds is not None:
            self.time_remaining = time_seconds

        # Update model probability
        impact = self.get_event_impact(event_type, home_away, shot_type)
        if home_away == "home":
            self.home_momentum += impact
        else:
            self.away_momentum += impact
            
        self.model_prob = self.calculate_true_probability()
        
        # Convert model probability to expected price for comparison
        model_price = self.probability_to_price(self.model_prob)
        market_prob = self.market_price_to_probability(self.market_price)
        
        # Trading decision
        should_trade, side, probability_edge = self.should_trade(self.model_prob, self.market_price)
        
        if should_trade:
            # Cancel existing orders
            for order_id in self.active_orders:
                cancel_order(Ticker.TEAM_A, order_id)
            self.active_orders = []
            
            # Calculate position size
            quantity = self.calculate_position_size(probability_edge, side, self.market_price)
            
            # Risk management check
            if self.can_afford_trade(side, quantity, self.market_price) and quantity > 0:
                # Trade at MARKET PRICE
                target_price = self.market_price
                
                # Place order at market price
                order_id = place_limit_order(side, Ticker.TEAM_A, quantity, target_price)
                if order_id:
                    self.active_orders.append(order_id)
                
                if side == Side.BUY:
                    print(f"BUY: Market undervalues home team")
                    print(f"Model: {self.model_prob:.3f} ({model_price:.1f}) > Market: {market_prob:.3f} ({self.market_price:.1f})")
                else:
                    print(f"SELL: Market overvalues home team")  
                    print(f"Model: {self.model_prob:.3f} ({model_price:.1f}) < Market: {market_prob:.3f} ({self.market_price:.1f})")
                print(f"Trading {quantity:.1f} shares @ ${target_price:.1f} (Edge: {probability_edge:.3f})")
            else:
                print(f"Trade skipped: Risk limits or zero quantity")
                print(f"Available: ${self.cash:.2f}, Calculated Qty: {quantity:.1f}")

        # Update portfolio
        self.update_portfolio_value()

        # Check risk management rules
        self.check_risk_management()

        
        print(f"Score: {home_score}-{away_score}, Time: {time_seconds}s")
        print(f"Model: {self.model_prob:.3f} (${model_price:.1f}), Market: {market_prob:.3f} (${self.market_price:.1f})")
        print(f"Position: {self.position}, Portfolio: ${self.portfolio_value:.2f}")

        if event_type == "END_GAME" or self.time_remaining < 3:
            # Close position at market
            if self.position > 0:
                place_market_order(Side.SELL, Ticker.TEAM_A, abs(self.position))
            elif self.position < 0:
                place_market_order(Side.BUY, Ticker.TEAM_A, abs(self.position))
                
            final_pnl = self.portfolio_value - 100000.0
            print(f"FINAL PnL: ${final_pnl:+.2f} ({final_pnl/1000:.2f}%)")
            self.reset_state()