"""
Risk Manager
============
Position sizing and risk management calculations.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradeSetup:
    """Complete trade setup with risk parameters."""
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float]
    position_size: float
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "position_size": self.position_size,
            "risk_amount": self.risk_amount,
            "reward_amount": self.reward_amount,
            "risk_reward_ratio": self.risk_reward_ratio,
        }


class RiskManager:
    """
    Position sizing and risk management.
    
    Implements:
    - Fixed percentage risk per trade
    - ATR-based stop loss calculation
    - Multiple take profit targets
    - Position size calculation
    - Portfolio heat management
    """
    
    def __init__(
        self,
        default_risk_percent: float = 2.0,
        default_rr_ratio: float = 2.0,
        max_position_size_percent: float = 10.0,
        max_portfolio_heat: float = 10.0
    ):
        """
        Initialize risk manager.
        
        Args:
            default_risk_percent: Default risk per trade (% of capital)
            default_rr_ratio: Default risk/reward ratio target
            max_position_size_percent: Maximum position size (% of capital)
            max_portfolio_heat: Maximum total portfolio risk (% of capital)
        """
        self.default_risk_percent = default_risk_percent
        self.default_rr_ratio = default_rr_ratio
        self.max_position_size_percent = max_position_size_percent
        self.max_portfolio_heat = max_portfolio_heat
    
    def calculate_position_size(
        self,
        capital: float,
        risk_percent: Optional[float],
        entry_price: float,
        stop_loss: float
    ) -> float:
        """
        Calculate position size based on risk.
        
        Uses the formula: Position Size = (Capital × Risk%) / (Entry - Stop)
        
        Args:
            capital: Total trading capital
            risk_percent: Percentage of capital to risk (or use default)
            entry_price: Planned entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size (number of shares/units)
        """
        risk_pct = risk_percent or self.default_risk_percent
        
        # Risk amount in currency
        risk_amount = capital * (risk_pct / 100)
        
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            logger.warning("Stop loss equals entry price, using 1% of price")
            risk_per_share = entry_price * 0.01
        
        # Position size
        position_size = risk_amount / risk_per_share
        
        # Check maximum position size
        max_shares = (capital * self.max_position_size_percent / 100) / entry_price
        position_size = min(position_size, max_shares)
        
        return round(position_size, 4)
    
    def calculate_position_value(
        self,
        capital: float,
        risk_percent: Optional[float],
        entry_price: float,
        stop_loss: float
    ) -> float:
        """
        Calculate position value (in currency).
        
        Args:
            capital: Total trading capital
            risk_percent: Percentage of capital to risk
            entry_price: Planned entry price
            stop_loss: Stop loss price
            
        Returns:
            Position value in currency
        """
        shares = self.calculate_position_size(capital, risk_percent, entry_price, stop_loss)
        return round(shares * entry_price, 2)
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str = "long",
        atr_multiplier: float = 2.0
    ) -> float:
        """
        Calculate ATR-based stop loss.
        
        Args:
            entry_price: Entry price
            atr: Average True Range value
            direction: 'long' or 'short'
            atr_multiplier: ATR multiplier for stop distance
            
        Returns:
            Stop loss price
        """
        stop_distance = atr * atr_multiplier
        
        if direction == "long":
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        return round(stop_loss, 4)
    
    def calculate_stop_loss_percent(
        self,
        entry_price: float,
        stop_percent: float,
        direction: str = "long"
    ) -> float:
        """
        Calculate percentage-based stop loss.
        
        Args:
            entry_price: Entry price
            stop_percent: Stop loss percentage
            direction: 'long' or 'short'
            
        Returns:
            Stop loss price
        """
        if direction == "long":
            return round(entry_price * (1 - stop_percent / 100), 4)
        else:
            return round(entry_price * (1 + stop_percent / 100), 4)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        rr_ratio: Optional[float] = None,
        direction: str = "long"
    ) -> float:
        """
        Calculate take profit based on risk/reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            rr_ratio: Risk/reward ratio (or use default)
            direction: 'long' or 'short'
            
        Returns:
            Take profit price
        """
        rr = rr_ratio or self.default_rr_ratio
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = risk_distance * rr
        
        if direction == "long":
            take_profit = entry_price + reward_distance
        else:
            take_profit = entry_price - reward_distance
        
        return round(take_profit, 4)
    
    def calculate_multiple_targets(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str = "long",
        targets: list = [1.5, 2.5, 4.0]
    ) -> list:
        """
        Calculate multiple take profit targets.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'long' or 'short'
            targets: List of R:R ratios for each target
            
        Returns:
            List of take profit prices
        """
        return [
            self.calculate_take_profit(entry_price, stop_loss, rr, direction)
            for rr in targets
        ]
    
    def calculate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> float:
        """
        Calculate risk/reward ratio for a trade.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Risk/reward ratio
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return 0.0
        
        return round(reward / risk, 2)
    
    def create_trade_setup(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        rr_ratio: Optional[float] = None,
        risk_percent: Optional[float] = None,
        direction: str = "long"
    ) -> TradeSetup:
        """
        Create complete trade setup with all risk parameters.
        
        Args:
            capital: Trading capital
            entry_price: Entry price
            stop_loss: Stop loss price
            rr_ratio: Risk/reward ratio target
            risk_percent: Risk percentage per trade
            direction: 'long' or 'short'
            
        Returns:
            TradeSetup object with all parameters
        """
        rr = rr_ratio or self.default_rr_ratio
        risk_pct = risk_percent or self.default_risk_percent
        
        # Calculate position size
        position_size = self.calculate_position_size(
            capital, risk_pct, entry_price, stop_loss
        )
        
        # Calculate take profits
        tp1 = self.calculate_take_profit(entry_price, stop_loss, rr, direction)
        tp2 = self.calculate_take_profit(entry_price, stop_loss, rr * 1.5, direction)
        
        # Calculate risk and reward amounts
        risk_amount = position_size * abs(entry_price - stop_loss)
        reward_amount = position_size * abs(tp1 - entry_price)
        
        return TradeSetup(
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            position_size=position_size,
            risk_amount=round(risk_amount, 2),
            reward_amount=round(reward_amount, 2),
            risk_reward_ratio=self.calculate_risk_reward(entry_price, stop_loss, tp1),
        )
    
    def validate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        min_rr_ratio: float = 1.5
    ) -> Tuple[bool, str]:
        """
        Validate if a trade setup meets minimum criteria.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            min_rr_ratio: Minimum acceptable R:R ratio
            
        Returns:
            Tuple of (is_valid, reason)
        """
        rr = self.calculate_risk_reward(entry_price, stop_loss, take_profit)
        
        if rr < min_rr_ratio:
            return False, f"R:R ratio ({rr}) below minimum ({min_rr_ratio})"
        
        # Check stop is in right direction
        if stop_loss >= entry_price and take_profit > entry_price:
            return False, "Stop loss should be below entry for long trades"
        
        if stop_loss <= entry_price and take_profit < entry_price:
            return False, "Stop loss should be above entry for short trades"
        
        return True, "Trade setup is valid"
    
    def calculate_portfolio_heat(
        self,
        open_positions: list
    ) -> Dict[str, float]:
        """
        Calculate total portfolio risk from open positions.
        
        Args:
            open_positions: List of dicts with 'risk_amount' and 'capital'
            
        Returns:
            Portfolio risk metrics
        """
        if not open_positions:
            return {
                "total_risk": 0.0,
                "heat_percent": 0.0,
                "can_add_risk": True,
            }
        
        total_risk = sum(p.get("risk_amount", 0) for p in open_positions)
        total_capital = open_positions[0].get("capital", 10000)  # Assume same capital
        
        heat_percent = (total_risk / total_capital) * 100
        can_add = heat_percent < self.max_portfolio_heat
        
        return {
            "total_risk": round(total_risk, 2),
            "heat_percent": round(heat_percent, 2),
            "max_heat": self.max_portfolio_heat,
            "remaining_capacity": round(self.max_portfolio_heat - heat_percent, 2),
            "can_add_risk": can_add,
        }
    
    def adjust_for_volatility(
        self,
        base_risk_percent: float,
        current_atr_percent: float,
        avg_atr_percent: float
    ) -> float:
        """
        Adjust risk based on volatility.
        
        Reduce risk in high volatility, increase in low volatility.
        
        Args:
            base_risk_percent: Base risk percentage
            current_atr_percent: Current ATR as percentage of price
            avg_atr_percent: Average ATR as percentage
            
        Returns:
            Adjusted risk percentage
        """
        if avg_atr_percent == 0:
            return base_risk_percent
        
        volatility_ratio = current_atr_percent / avg_atr_percent
        
        # Reduce risk if volatility is high, increase if low
        if volatility_ratio > 1.5:
            adjusted = base_risk_percent * 0.7  # Reduce by 30%
        elif volatility_ratio > 1.2:
            adjusted = base_risk_percent * 0.85  # Reduce by 15%
        elif volatility_ratio < 0.7:
            adjusted = base_risk_percent * 1.2  # Increase by 20%
        else:
            adjusted = base_risk_percent
        
        # Cap at reasonable limits
        return round(max(0.5, min(adjusted, 4.0)), 2)


if __name__ == "__main__":
    # Test risk manager
    print("Testing Risk Manager...")
    
    rm = RiskManager(
        default_risk_percent=2.0,
        default_rr_ratio=2.0,
        max_position_size_percent=10.0
    )
    
    # Example trade setup
    capital = 10000
    entry = 150.00
    
    # ATR-based stop
    atr = 3.5
    stop_loss = rm.calculate_stop_loss(entry, atr, "long", atr_multiplier=2.0)
    
    print(f"\n=== Trade Setup ===")
    print(f"Capital: ${capital}")
    print(f"Entry: ${entry}")
    print(f"ATR: ${atr}")
    print(f"Stop Loss: ${stop_loss}")
    
    # Position size
    position_size = rm.calculate_position_size(capital, 2.0, entry, stop_loss)
    position_value = rm.calculate_position_value(capital, 2.0, entry, stop_loss)
    
    print(f"\nPosition Size: {position_size} shares")
    print(f"Position Value: ${position_value}")
    
    # Take profit targets
    targets = rm.calculate_multiple_targets(entry, stop_loss, "long", [1.5, 2.5, 4.0])
    print(f"\nTake Profit Targets:")
    for i, tp in enumerate(targets, 1):
        rr = rm.calculate_risk_reward(entry, stop_loss, tp)
        print(f"  TP{i}: ${tp} (R:R = {rr})")
    
    # Complete setup
    print(f"\n=== Complete Trade Setup ===")
    setup = rm.create_trade_setup(capital, entry, stop_loss, rr_ratio=2.0)
    print(f"Entry: ${setup.entry_price}")
    print(f"Stop Loss: ${setup.stop_loss}")
    print(f"TP1: ${setup.take_profit_1}")
    print(f"TP2: ${setup.take_profit_2}")
    print(f"Position Size: {setup.position_size} shares")
    print(f"Risk Amount: ${setup.risk_amount}")
    print(f"Reward Amount: ${setup.reward_amount}")
    print(f"R:R Ratio: {setup.risk_reward_ratio}")
    
    # Validate
    is_valid, reason = rm.validate_trade(entry, stop_loss, setup.take_profit_1)
    print(f"\nValidation: {'✓ ' + reason if is_valid else '✗ ' + reason}")
