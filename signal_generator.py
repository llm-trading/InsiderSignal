"""
Signal Generator - Three Layer Hybrid Factor Aggregation
Generates buy signals from enriched insider trading data.
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any


class SignalGenerator:
    """Generates trading signals from enriched insider data."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # -------------------------
    # Utility Functions
    # -------------------------
    
    @staticmethod
    def sigmoid(x: float) -> float:
        """Sigmoid activation function."""
        try:
            return 1 / (1 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0
    
    @staticmethod
    def safe_log(x: float) -> float:
        """Safe logarithm that handles negative values."""
        return math.log(1 + max(x, 0))
    
    @staticmethod
    def normalize_weights(scores: List[Optional[float]], 
                         weights: List[float]) -> Tuple[List[float], List[float]]:
        """Filter out None scores and normalize weights."""
        filtered = [(s, w) for s, w in zip(scores, weights) if s is not None]
        if not filtered:
            return [], []
        s_vals, w_vals = zip(*filtered)
        total_w = sum(w_vals)
        return list(s_vals), [w / total_w for w in w_vals]
    
    @staticmethod
    def power_mean(scores: List[float], weights: List[float], p: int = 2) -> float:
        """Compute weighted power mean."""
        if not scores:
            return 0.0
        return (sum(w * (s ** p) for s, w in zip(scores, weights))) ** (1 / p)
    
    # -------------------------
    # Factor Computation
    # -------------------------
    
    def compute_conviction(self, tx: Dict, position_ctx: Dict) -> Optional[float]:
        """
        Compute conviction factor (C) based on transaction size and ownership change.
        
        Args:
            tx: Transaction data
            position_ctx: Position sizing context
            
        Returns:
            Conviction score [0, 1] or None
        """
        val = tx.get("Value", "")
        own = tx.get("ΔOwn", "")
        
        # Parse value
        val_num = None
        if val:
            try:
                val_num = float(val.replace("$", "").replace(",", "").replace("+", ""))
            except (ValueError, AttributeError):
                pass
        
        # Parse ownership change
        own_num = None
        if own and own != "New":
            try:
                own_num = float(own.replace("%", "").replace("+", "").replace(">999", "999"))
            except (ValueError, AttributeError):
                pass
        
        ratio = position_ctx.get("insider_value_to_mcap")
        
        signals = []
        
        if val_num:
            signals.append(self.sigmoid(self.safe_log(val_num) - 10))
        
        if own_num:
            signals.append(self.sigmoid(own_num / 10))
        
        if ratio:
            signals.append(self.sigmoid(ratio * 50))
        
        if not signals:
            return None
        
        return sum(signals) / len(signals)
    
    def compute_credibility(self, tx: Dict, history_ctx: Dict) -> float:
        """
        Compute credibility factor (Q) based on insider role and history.
        
        Args:
            tx: Transaction data
            history_ctx: Insider history context
            
        Returns:
            Credibility score [0, 1]
        """
        role = tx.get("Title", "")
        
        role_map = {
            "CEO": 1.0,
            "CFO": 0.85,
            "COO": 0.8,
            "Dir": 0.6,
            "Pres": 0.9
        }
        
        # Check for role keywords
        base = 0.5
        for key, score in role_map.items():
            if key in role:
                base = score
                break
        
        # Adjust based on history
        if history_ctx.get("has_history_data"):
            if history_ctx.get("repeat_insider_count", 0) > 0:
                base -= 0.1
        
        return max(min(base, 1.0), 0.0)
    
    def compute_timing(self, earnings_ctx: Dict) -> Optional[float]:
        """
        Compute timing factor (T) based on earnings reactions.
        
        Args:
            earnings_ctx: Earnings context
            
        Returns:
            Timing score [0, 1] or None
        """
        if not earnings_ctx.get("has_earnings_8k"):
            return None
        
        p1 = earnings_ctx.get("price_change_1d_post_earnings")
        p3 = earnings_ctx.get("price_change_3d_post_earnings")
        
        # If BOTH missing → no timing signal
        if p1 is None and p3 is None:
            return None
        
        signal = 0.0
        weight_sum = 0
        
        # 1D reaction
        if p1 is not None:
            weight_sum += 1
            if p1 < 0:
                signal += 1.5
            elif p1 > 0.05:
                signal -= 1.0
        
        # 3D reaction
        if p3 is not None:
            weight_sum += 1
            if p3 < 0:
                signal += 1.2
            elif p3 > 0.08:
                signal -= 0.8
        
        # Normalize signal if partial data
        if weight_sum > 0:
            signal = signal / weight_sum
        
        return self.sigmoid(signal)
    
    def compute_coordination(self, behavior_ctx: Dict) -> Optional[float]:
        """
        Compute coordination factor (K) based on multiple insiders.
        
        Args:
            behavior_ctx: Insider behavior context
            
        Returns:
            Coordination score [0, 1] or None
        """
        if not behavior_ctx.get("has_behavior_data"):
            return None
        
        count = behavior_ctx.get("unique_insider_count", 0)
        repeat = behavior_ctx.get("has_repeated_buys", False)
        
        score = self.sigmoid(count - 1)
        
        if repeat:
            score += 0.2
        
        return min(score, 1.0)
    
    def compute_positioning(self, price_ctx: Dict, sector_ctx: Dict, 
                          insider_price_ctx: Dict) -> Optional[float]:
        """
        Compute positioning factor (P) based on price levels and sector context.
        
        Args:
            price_ctx: Price context
            sector_ctx: Sector context
            insider_price_ctx: Insider price context
            
        Returns:
            Positioning score [0, 1] or None
        """
        signals = []
        
        # Drawdown / entry
        drawdown = price_ctx.get("stock_drawdown_30d")
        if drawdown is not None:
            signals.append(drawdown * 2)
        
        dist_low = price_ctx.get("distance_from_52w_low")
        if dist_low is not None:
            signals.append(1 / (1 + dist_low))
        
        # Sector contrarian
        sector_ret = sector_ctx.get("sector_return_30d")
        if sector_ret is not None:
            signals.append(-sector_ret)
        
        # Insider price edge
        diff = insider_price_ctx.get("price_diff_pct")
        if diff is not None:
            signals.append(-diff)
        
        if not signals:
            return None
        
        return self.sigmoid(sum(signals))
    
    # -------------------------
    # Interaction & Classification
    # -------------------------
    
    @staticmethod
    def interaction_boost(C: Optional[float], Q: Optional[float], 
                         T: Optional[float], K: Optional[float], 
                         P: Optional[float]) -> float:
        """Compute interaction boost based on factor combinations."""
        boost = 1.0
        
        if C and T and C > 0.7 and T > 0.7:
            boost += 0.15
        
        if K and Q and K > 0.6 and Q > 0.8:
            boost += 0.10
        
        if P and P < 0.3:
            boost -= 0.10
        
        return boost
    
    @staticmethod
    def classify(score: float) -> str:
        """Classify signal strength."""
        if score >= 0.75:
            return "STRONG_BUY_SIGNAL"
        elif score >= 0.60:
            return "BUY_SIGNAL"
        elif score >= 0.45:
            return "WEAK_SIGNAL"
        else:
            return "NOISE"
    
    # -------------------------
    # Main Scoring Logic
    # -------------------------
    
    def score_transaction(self, tx: Dict, ticker_data: Dict) -> Dict:
        """
        Score a single transaction.
        
        Args:
            tx: Transaction data
            ticker_data: Full ticker data with all contexts
            
        Returns:
            Transaction score with factors
        """
        # Extract contexts
        earnings_ctx = ticker_data.get("earnings_context", {})
        price_ctx = ticker_data.get("price_context", {})
        sector_ctx = ticker_data.get("sector_context", {})
        history_ctx = ticker_data.get("insider_history_context", {})
        insider_price_ctx = ticker_data.get("insider_price_context", {})
        position_ctx = ticker_data.get("position_sizing_context", {})
        behavior_ctx = ticker_data.get("insider_behavior_context", {})
        
        # Compute factors
        C = self.compute_conviction(tx, position_ctx)
        Q = self.compute_credibility(tx, history_ctx)
        T = self.compute_timing(earnings_ctx)
        K = self.compute_coordination(behavior_ctx)
        P = self.compute_positioning(price_ctx, sector_ctx, insider_price_ctx)
        
        # Normalize weights
        scores = [C, Q, T, K, P]
        weights = [0.30, 0.20, 0.25, 0.15, 0.10]
        
        scores, weights = self.normalize_weights(scores, weights)
        
        if not scores:
            return {
                "insider": tx.get("Insider Name"),
                "C": C, "Q": Q, "T": T, "K": K, "P": P,
                "score": 0.0,
                "signal": "NOISE"
            }
        
        # Compute base score
        base = self.power_mean(scores, weights, p=2)
        
        # Apply interaction boost
        boost = self.interaction_boost(C, Q, T, K, P)
        
        final_score = base * boost
        
        return {
            "insider": tx.get("Insider Name"),
            "C": C, "Q": Q, "T": T, "K": K, "P": P,
            "score": final_score,
            "signal": self.classify(final_score)
        }
    
    def aggregate_ticker_signal(self, transaction_results: List[Dict]) -> Optional[Dict]:
        """
        Aggregate transaction-level signals to ticker-level.
        
        Args:
            transaction_results: List of transaction scores
            
        Returns:
            Aggregated ticker signal or None
        """
        if not transaction_results:
            return None
        
        weighted_sum = 0.0
        total_weight = 0.0
        max_score = 0.0
        
        for tx in transaction_results:
            score = tx.get("score")
            C = tx.get("C")
            Q = tx.get("Q")
            
            if score is None:
                continue
            
            # Default fallback if missing
            C = C if C is not None else 0.5
            Q = Q if Q is not None else 0.5
            
            weight = 0.6 * C + 0.4 * Q
            
            weighted_sum += score * weight
            total_weight += weight
            
            max_score = max(max_score, score)
        
        if total_weight == 0:
            return None
        
        weighted_score = weighted_sum / total_weight
        
        # Cluster effect
        num_insiders = len(transaction_results)
        cluster_adjustment = min(1.0, math.log(1 + num_insiders) / 2)
        
        # Final aggregation
        final_score = (
            0.6 * weighted_score +
            0.3 * max_score +
            0.1 * cluster_adjustment
        )
        
        return {
            "ticker_score": final_score,
            "weighted_score": weighted_score,
            "max_score": max_score,
            "cluster_factor": cluster_adjustment,
            "num_insiders": num_insiders,
            "signal": self.classify(final_score)
        }
    
    def generate_explanations(self, ticker_data: Dict, tx_results: List[Dict], 
                            ticker_signal: Optional[Dict]) -> Tuple[List[str], List[str]]:
        """
        Generate human-readable explanations for the signal.
        
        Args:
            ticker_data: Full ticker data
            tx_results: Transaction scores
            ticker_signal: Aggregated ticker signal
            
        Returns:
            Tuple of (goods, bads) explanation lists
        """
        goods = []
        bads = []
        
        earnings_ctx = ticker_data.get("earnings_context", {})
        price_ctx = ticker_data.get("price_context", {})
        sector_ctx = ticker_data.get("sector_context", {})
        insider_price_ctx = ticker_data.get("insider_price_context", {})
        position_ctx = ticker_data.get("position_sizing_context", {})
        behavior_ctx = ticker_data.get("insider_behavior_context", {})
        
        # Conviction (C)
        ratio = position_ctx.get("insider_value_to_mcap")
        if ratio is not None:
            if ratio > 0.02:
                goods.append(f"High conviction: insider buying is {round(ratio*100, 2)}% of market cap")
            elif ratio < 0.005:
                bads.append("Low conviction relative to company size")
        
        # Timing (T)
        p1 = earnings_ctx.get("price_change_1d_post_earnings")
        p3 = earnings_ctx.get("price_change_3d_post_earnings")
        
        if p1 is not None:
            if p1 < 0:
                goods.append("Insider buying after negative earnings reaction (1D)")
            elif p1 > 0.05:
                bads.append("Insider buying after strong positive move (less edge)")
        
        if p3 is not None:
            if p3 < 0:
                goods.append("Sustained negative reaction post earnings (3D)")
        
        # Positioning (P)
        drawdown = price_ctx.get("stock_drawdown_30d")
        if drawdown is not None:
            if drawdown > 0.2:
                goods.append("Stock is in drawdown — potential bottoming signal")
            elif drawdown < 0.05:
                bads.append("Stock not significantly discounted")
        
        # Insider price edge
        diff = insider_price_ctx.get("price_diff_pct")
        if diff is not None:
            if diff < 0:
                goods.append("Current price below insider buy price (entry still attractive)")
            elif diff > 0.15:
                bads.append("Stock has already moved significantly above insider buy price")
        
        # Sector Context
        sector_ret = sector_ctx.get("sector_return_30d")
        if sector_ret is not None:
            if sector_ret < 0:
                goods.append("Sector weakness — insider buying is contrarian")
            elif sector_ret > 0.1:
                bads.append("Sector already strong — less contrarian edge")
        
        # Coordination (K)
        count = behavior_ctx.get("unique_insider_count", 0)
        if count >= 2:
            goods.append(f"Cluster buying detected ({count} insiders)")
        elif count == 1:
            bads.append("Single insider — weaker confirmation")
        
        if behavior_ctx.get("has_repeated_buys"):
            goods.append("Repeated buying by insider — strong conviction signal")
        
        # Aggregation Insights
        if ticker_signal:
            if ticker_signal.get("max_score", 0) > 0.8:
                goods.append("At least one very strong insider signal present")
            
            if ticker_signal.get("weighted_score", 0) < 0.5:
                bads.append("Overall insider consensus is weak")
        
        return goods, bads
    
    def score_ticker(self, ticker: str, ticker_data: Dict) -> Dict:
        """
        Score all transactions for a ticker and aggregate.
        
        Args:
            ticker: Ticker symbol
            ticker_data: Full ticker data with enrichments
            
        Returns:
            Complete scoring result with signals and explanations
        """
        self.logger.debug(f"Scoring ticker: {ticker}")
        
        txs = ticker_data.get("insider_transactions", [])
        
        # Score each transaction
        tx_results = []
        for tx in txs:
            tx_score = self.score_transaction(tx, ticker_data)
            tx_results.append(tx_score)
        
        # Aggregate to ticker level
        ticker_signal = self.aggregate_ticker_signal(tx_results)
        
        # Generate explanations
        goods, bads = self.generate_explanations(ticker_data, tx_results, ticker_signal)
        
        return {
            "transactions": tx_results,
            "ticker_signal": ticker_signal,
            "analysis": {
                "goods": goods,
                "bads": bads
            }
        }
    
    def score_dataset(self, grouped_data: Dict) -> Dict:
        """
        Score entire dataset of tickers.
        
        Args:
            grouped_data: Grouped JSON data with 'tickers' key
            
        Returns:
            Scored dataset with signals
        """
        self.logger.info("Starting signal generation...")
        
        tickers_data = grouped_data.get("tickers", {})
        output = {}
        
        total = len(tickers_data)
        for idx, (ticker, ticker_data) in enumerate(tickers_data.items(), 1):
            self.logger.info(f"  [{idx}/{total}] {ticker}")
            
            try:
                output[ticker] = self.score_ticker(ticker, ticker_data)
            except Exception as e:
                self.logger.error(f"Failed to score {ticker}: {e}", exc_info=True)
                output[ticker] = {
                    "transactions": [],
                    "ticker_signal": None,
                    "analysis": {
                        "goods": [],
                        "bads": [f"Error during scoring: {str(e)}"]
                    }
                }
        
        self.logger.info("✓ Signal generation complete")
        return output
