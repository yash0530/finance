"""
pattern_detectors.py — pure chart-pattern geometry detectors.

Extracted from the legacy S&P 500 scanner so the preserved technicals tool
(via research_engine._detect_all_patterns) keeps a stable import target after
the scanner's HTTP routes were removed. No Flask, no network — pure functions
over price/date lists.
"""

import numpy as np

def detect_head_and_shoulders(prices: list, dates: list, window: int = 20) -> dict:
    """
    Detect Head and Shoulders pattern in price data using combinatorial subset peak
    searches and slanted diagonal neckline geometry.
    
    The pattern consists of:
    - Left Shoulder: A peak
    - Head: A higher peak
    - Right Shoulder: A lower peak similar to the left shoulder
    - Neckline: Slanted support line connecting the intermediate troughs
    
    Args:
        prices: List of closing prices (chronological order)
        dates: List of dates corresponding to prices
        window: Rolling window size for local maxima/minima detection
    
    Returns:
        dict with pattern details or None if no pattern found
    """
    if len(prices) < window * 5:  # Need enough data for pattern
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Find local maxima (peaks) using rolling window
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    if len(local_maxima) < 3:
        return None
    
    # Find local minima (troughs) using rolling window
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_minima) < 2:
        return None
    
    # Look for Head and Shoulders pattern in recent data
    search_start = max(0, n - 120)  # Last ~6 months of daily data
    
    best_pattern = None
    best_confidence = 0
    
    # Filter extrema within the active search window
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    
    # Cap to top 15 most recent peaks to enforce strict O(K^3) performance boundaries
    recent_maxima = recent_maxima[-15:]
    
    # 1. Combinatorial peak search (non-consecutive triplets)
    m_len = len(recent_maxima)
    for i in range(m_len - 2):
        for j in range(i + 1, m_len - 1):
            for k in range(j + 1, m_len):
                left_idx, left_price = recent_maxima[i]
                head_idx, head_price = recent_maxima[j]
                right_idx, right_price = recent_maxima[k]
                
                # Head must be higher than both shoulders
                if head_price <= left_price or head_price <= right_price:
                    continue
                
                # Shoulders should be roughly equal (within 15%)
                max_shoulder = max(left_price, right_price)
                if max_shoulder <= 0:
                    continue
                shoulder_diff = abs(left_price - right_price) / max_shoulder
                if shoulder_diff > 0.15:
                    continue
                
                # 2. Find intermediate troughs between shoulders and head
                left_trough_candidates = [m for m in local_minima if left_idx < m[0] < head_idx]
                right_trough_candidates = [m for m in local_minima if head_idx < m[0] < right_idx]
                
                if not left_trough_candidates or not right_trough_candidates:
                    continue
                
                left_trough = min(left_trough_candidates, key=lambda x: x[1])
                right_trough = min(right_trough_candidates, key=lambda x: x[1])
                
                t1_idx, t1_price = left_trough
                t2_idx, t2_price = right_trough
                
                # 3. Calculate Slanted Diagonal Neckline: y = m*x + c
                dx = t2_idx - t1_idx
                if dx == 0:
                    continue
                neckline_slope = (t2_price - t1_price) / dx
                neckline_intercept = t1_price - neckline_slope * t1_idx
                
                # Head height relative to the slanted neckline at head's index
                neckline_at_head = neckline_slope * head_idx + neckline_intercept
                if neckline_at_head <= 0:
                    continue
                
                head_height = head_price - neckline_at_head
                head_height_ratio = head_height / neckline_at_head
                
                # Head should be significantly higher than neckline (at least 5%)
                if head_height_ratio < 0.05:
                    continue
                
                # Calculate pattern confidence score (0-100)
                shoulder_symmetry = 1.0 - shoulder_diff
                height_score = min(head_height_ratio * 5.0, 1.0)
                recency = (right_idx - search_start) / (n - search_start) if (n - search_start) > 0 else 1.0
                
                confidence = int((shoulder_symmetry * 0.3 + height_score * 0.4 + recency * 0.3) * 100)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    
                    # Project slanted neckline to present day (n-1) and target
                    neckline_today = neckline_slope * (n - 1) + neckline_intercept
                    target_price = neckline_today - head_height
                    
                    current_price = prices[-1]
                    price_vs_neckline = (current_price - neckline_today) / neckline_today if neckline_today > 0 else 0.0
                    
                    best_pattern = {
                        'detected': True,
                        'confidence': confidence,
                        'left_shoulder': {
                            'date': dates[left_idx],
                            'price': round(left_price, 2)
                        },
                        'head': {
                            'date': dates[head_idx],
                            'price': round(head_price, 2)
                        },
                        'right_shoulder': {
                            'date': dates[right_idx],
                            'price': round(right_price, 2)
                        },
                        'neckline': round(neckline_today, 2),  # current value of neckline
                        'target_price': round(target_price, 2),
                        'current_price': round(current_price, 2),
                        'price_vs_neckline_pct': round(price_vs_neckline * 100, 2),
                        'pattern_height_pct': round(head_height_ratio * 100, 2)
                    }
    
    return best_pattern


def _fit_ols_line(x: list, y: list) -> tuple:
    """
    Fits an OLS linear regression line y = m * x + c and returns (slope, intercept, r_squared).
    """
    if len(x) < 2:
        return 0.0, 0.0, 0.0
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    slope, intercept = np.polyfit(x_arr, y_arr, 1)
    
    # Calculate R-squared
    y_pred = slope * x_arr + intercept
    y_mean = np.mean(y_arr)
    ss_res = np.sum((y_arr - y_pred) ** 2)
    ss_tot = np.sum((y_arr - y_mean) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    return float(slope), float(intercept), float(r_squared)


def detect_inverse_head_shoulders(prices: list, dates: list, window: int = 20) -> dict:
    """
    Detect Inverse Head and Shoulders pattern (bullish reversal) using combinatorial
    extrema search and slanted necklines.
    """
    if len(prices) < window * 5:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Find local minima (troughs) using rolling window
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    if len(local_minima) < 3:
        return None
        
    # Find local maxima (peaks) for neckline
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
            
    if len(local_maxima) < 2:
        return None
        
    search_start = max(0, n - 120)
    best_pattern = None
    best_confidence = 0
    
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    recent_minima = recent_minima[-15:]  # Enforce combinatorial limits
    
    m_len = len(recent_minima)
    for i in range(m_len - 2):
        for j in range(i + 1, m_len - 1):
            for k in range(j + 1, m_len):
                left_idx, left_price = recent_minima[i]
                head_idx, head_price = recent_minima[j]
                right_idx, right_price = recent_minima[k]
                
                # Head must be lower (deeper trough) than both shoulders
                if head_price >= left_price or head_price >= right_price:
                    continue
                    
                # Shoulders should be roughly equal (within 15%)
                max_shoulder = max(left_price, right_price)
                if max_shoulder <= 0:
                    continue
                shoulder_diff = abs(left_price - right_price) / max_shoulder
                if shoulder_diff > 0.15:
                    continue
                    
                # Find neckline intermediate peaks between shoulders
                left_peak_candidates = [m for m in local_maxima if left_idx < m[0] < head_idx]
                right_peak_candidates = [m for m in local_maxima if head_idx < m[0] < right_idx]
                
                if not left_peak_candidates or not right_peak_candidates:
                    continue
                    
                left_peak = max(left_peak_candidates, key=lambda x: x[1])
                right_peak = max(right_peak_candidates, key=lambda x: x[1])
                
                t1_idx, t1_price = left_peak
                t2_idx, t2_price = right_peak
                
                # Slanted neckline: y = m*x + c
                dx = t2_idx - t1_idx
                if dx == 0:
                    continue
                neckline_slope = (t2_price - t1_price) / dx
                neckline_intercept = t1_price - neckline_slope * t1_idx
                
                # Head depth relative to the slanted neckline at head's position
                neckline_at_head = neckline_slope * head_idx + neckline_intercept
                if neckline_at_head <= 0:
                    continue
                    
                head_depth = neckline_at_head - head_price
                head_depth_ratio = head_depth / neckline_at_head
                
                # Head should be significantly lower than neckline (at least 5%)
                if head_depth_ratio < 0.05:
                    continue
                    
                shoulder_symmetry = 1.0 - shoulder_diff
                depth_score = min(head_depth_ratio * 5.0, 1.0)
                recency = (right_idx - search_start) / (n - search_start) if (n - search_start) > 0 else 1.0
                
                confidence = int((shoulder_symmetry * 0.3 + depth_score * 0.4 + recency * 0.3) * 100)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    
                    # Project slanted neckline to present day (n-1) and target
                    neckline_today = neckline_slope * (n - 1) + neckline_intercept
                    target_price = neckline_today + head_depth
                    
                    current_price = prices[-1]
                    price_vs_neckline = (current_price - neckline_today) / neckline_today if neckline_today > 0 else 0.0
                    
                    best_pattern = {
                        'detected': True,
                        'pattern_type': 'inverse_head_shoulders',
                        'pattern_name': 'Inverse Head & Shoulders',
                        'signal': 'bullish',
                        'confidence': confidence,
                        'left_shoulder': {
                            'date': dates[left_idx],
                            'price': round(left_price, 2)
                        },
                        'head': {
                            'date': dates[head_idx],
                            'price': round(head_price, 2)
                        },
                        'right_shoulder': {
                            'date': dates[right_idx],
                            'price': round(right_price, 2)
                        },
                        'neckline': round(neckline_today, 2),
                        'target_price': round(target_price, 2),
                        'current_price': round(current_price, 2),
                        'price_vs_neckline_pct': round(price_vs_neckline * 100, 2),
                        'pattern_height_pct': round(head_depth_ratio * 100, 2)
                    }
                    
    return best_pattern


def detect_double_top(prices: list, dates: list, window: int = 15) -> dict:
    """
    Detect Double Top pattern (bearish reversal) using combinatorial search.
    """
    if len(prices) < window * 4:
        return None
        
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
            
    if len(local_maxima) < 2:
        return None
        
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    search_start = max(0, n - 100)
    best_pattern = None
    best_confidence = 0
    
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_maxima = recent_maxima[-15:]  # Combinatorial limit
    
    m_len = len(recent_maxima)
    for i in range(m_len - 1):
        for j in range(i + 1, m_len):
            first_idx, first_price = recent_maxima[i]
            second_idx, second_price = recent_maxima[j]
            
            # Peaks should be roughly equal (within 3%)
            peak_diff = abs(first_price - second_price) / max(first_price, second_price)
            if peak_diff > 0.03:
                continue
                
            # Need sufficient distance between peaks
            if second_idx - first_idx < window * 2:
                continue
                
            # Find trough between peaks
            trough_candidates = [m for m in local_minima if first_idx < m[0] < second_idx]
            if not trough_candidates:
                continue
                
            trough = min(trough_candidates, key=lambda x: x[1])
            neckline = trough[1]
            
            # Pattern height should be significant (at least 5%)
            pattern_height = (first_price - neckline) / neckline
            if pattern_height < 0.05:
                continue
                
            peak_symmetry = 1.0 - peak_diff
            height_score = min(pattern_height * 5.0, 1.0)
            recency = (second_idx - search_start) / (n - search_start) if (n - search_start) > 0 else 1.0
            
            confidence = int((peak_symmetry * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
            
            if confidence > best_confidence:
                best_confidence = confidence
                
                target_price = neckline - (first_price - neckline)
                current_price = prices[-1]
                
                best_pattern = {
                    'detected': True,
                    'pattern_type': 'double_top',
                    'pattern_name': 'Double Top',
                    'signal': 'bearish',
                    'confidence': confidence,
                    'first_peak': {'date': dates[first_idx], 'price': round(first_price, 2)},
                    'second_peak': {'date': dates[second_idx], 'price': round(second_price, 2)},
                    'trough': {'date': dates[trough[0]], 'price': round(trough[1], 2)},
                    'neckline': round(neckline, 2),
                    'target_price': round(target_price, 2),
                    'current_price': round(current_price, 2),
                    'pattern_height_pct': round(pattern_height * 100, 2)
                }
                
    return best_pattern


def detect_double_bottom(prices: list, dates: list, window: int = 15) -> dict:
    """
    Detect Double Bottom pattern (bullish reversal) using combinatorial search.
    """
    if len(prices) < window * 4:
        return None
        
    prices = np.array(prices)
    n = len(prices)
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    if len(local_minima) < 2:
        return None
        
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
            
    search_start = max(0, n - 100)
    best_pattern = None
    best_confidence = 0
    
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    recent_minima = recent_minima[-15:]  # Combinatorial limit
    
    m_len = len(recent_minima)
    for i in range(m_len - 1):
        for j in range(i + 1, m_len):
            first_idx, first_price = recent_minima[i]
            second_idx, second_price = recent_minima[j]
            
            # Troughs should be roughly equal (within 3%)
            trough_diff = abs(first_price - second_price) / max(first_price, second_price)
            if trough_diff > 0.03:
                continue
                
            if second_idx - first_idx < window * 2:
                continue
                
            # Find peak between troughs
            peak_candidates = [m for m in local_maxima if first_idx < m[0] < second_idx]
            if not peak_candidates:
                continue
                
            peak = max(peak_candidates, key=lambda x: x[1])
            neckline = peak[1]
            
            pattern_height = (neckline - first_price) / first_price
            if pattern_height < 0.05:
                continue
                
            trough_symmetry = 1.0 - trough_diff
            height_score = min(pattern_height * 5.0, 1.0)
            recency = (second_idx - search_start) / (n - search_start) if (n - search_start) > 0 else 1.0
            
            confidence = int((trough_symmetry * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
            
            if confidence > best_confidence:
                best_confidence = confidence
                
                target_price = neckline + (neckline - first_price)
                current_price = prices[-1]
                
                best_pattern = {
                    'detected': True,
                    'pattern_type': 'double_bottom',
                    'pattern_name': 'Double Bottom',
                    'signal': 'bullish',
                    'confidence': confidence,
                    'first_trough': {'date': dates[first_idx], 'price': round(first_price, 2)},
                    'second_trough': {'date': dates[second_idx], 'price': round(second_price, 2)},
                    'peak': {'date': dates[peak[0]], 'price': round(peak[1], 2)},
                    'neckline': round(neckline, 2),
                    'target_price': round(target_price, 2),
                    'current_price': round(current_price, 2),
                    'pattern_height_pct': round(pattern_height * 100, 2)
                }
                
    return best_pattern


def detect_triple_top(prices: list, dates: list, window: int = 12) -> dict:
    """
    Detect Triple Top pattern (bearish reversal) using combinatorial search
    over the top 15 extrema.
    """
    if len(prices) < window * 6:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    if len(local_maxima) < 3:
        return None
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    search_start = max(0, n - 150)
    best_pattern = None
    best_confidence = 0
    
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_maxima = recent_maxima[-15:]  # Combinatorial limit
    
    m_len = len(recent_maxima)
    for i in range(m_len - 2):
        for j in range(i + 1, m_len - 1):
            for k in range(j + 1, m_len):
                first_idx, first_price = recent_maxima[i]
                second_idx, second_price = recent_maxima[j]
                third_idx, third_price = recent_maxima[k]
                
                # Check peaks roughly equal (within 5%)
                avg_peak = (first_price + second_price + third_price) / 3.0
                max_diff = max(abs(first_price - avg_peak), abs(second_price - avg_peak), abs(third_price - avg_peak)) / avg_peak
                if max_diff > 0.05:
                    continue
                
                # Find neckline troughs between peaks
                trough1_candidates = [m for m in local_minima if first_idx < m[0] < second_idx]
                trough2_candidates = [m for m in local_minima if second_idx < m[0] < third_idx]
                
                if not trough1_candidates or not trough2_candidates:
                    continue
                
                trough1 = min(trough1_candidates, key=lambda x: x[1])
                trough2 = min(trough2_candidates, key=lambda x: x[1])
                
                neckline = min(trough1[1], trough2[1])
                pattern_height = (avg_peak - neckline) / neckline
                if pattern_height < 0.05:
                    continue
                
                symmetry = 1.0 - max_diff
                height_score = min(pattern_height * 5, 1.0)
                recency = (third_idx - search_start) / (n - search_start) if (n - search_start) > 0 else 1.0
                
                confidence = int((symmetry * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    target_price = neckline - (avg_peak - neckline)
                    current_price = prices[-1]
                    
                    best_pattern = {
                        'detected': True,
                        'pattern_type': 'triple_top',
                        'pattern_name': 'Triple Top',
                        'signal': 'bearish',
                        'confidence': confidence,
                        'first_peak': {'date': dates[first_idx], 'price': round(first_price, 2)},
                        'second_peak': {'date': dates[second_idx], 'price': round(second_price, 2)},
                        'third_peak': {'date': dates[third_idx], 'price': round(third_price, 2)},
                        'neckline': round(neckline, 2),
                        'target_price': round(target_price, 2),
                        'current_price': round(current_price, 2),
                        'pattern_height_pct': round(pattern_height * 100, 2)
                    }
    return best_pattern


def detect_triple_bottom(prices: list, dates: list, window: int = 12) -> dict:
    """
    Detect Triple Bottom pattern (bullish reversal) using combinatorial search
    over the top 15 extrema.
    """
    if len(prices) < window * 6:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_minima) < 3:
        return None
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
            
    search_start = max(0, n - 150)
    best_pattern = None
    best_confidence = 0
    
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    recent_minima = recent_minima[-15:]  # Combinatorial limit
    
    m_len = len(recent_minima)
    for i in range(m_len - 2):
        for j in range(i + 1, m_len - 1):
            for k in range(j + 1, m_len):
                first_idx, first_price = recent_minima[i]
                second_idx, second_price = recent_minima[j]
                third_idx, third_price = recent_minima[k]
                
                # Check troughs roughly equal (within 5%)
                avg_trough = (first_price + second_price + third_price) / 3.0
                max_diff = max(abs(first_price - avg_trough), abs(second_price - avg_trough), abs(third_price - avg_trough)) / avg_trough
                if max_diff > 0.05:
                    continue
                
                # Find neckline peaks between troughs
                peak1_candidates = [m for m in local_maxima if first_idx < m[0] < second_idx]
                peak2_candidates = [m for m in local_maxima if second_idx < m[0] < third_idx]
                
                if not peak1_candidates or not peak2_candidates:
                    continue
                
                peak1 = max(peak1_candidates, key=lambda x: x[1])
                peak2 = max(peak2_candidates, key=lambda x: x[1])
                
                neckline = max(peak1[1], peak2[1])
                pattern_height = (neckline - avg_trough) / avg_trough
                if pattern_height < 0.05:
                    continue
                
                symmetry = 1.0 - max_diff
                height_score = min(pattern_height * 5, 1.0)
                recency = (third_idx - search_start) / (n - search_start) if (n - search_start) > 0 else 1.0
                
                confidence = int((symmetry * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    target_price = neckline + (neckline - avg_trough)
                    current_price = prices[-1]
                    
                    best_pattern = {
                        'detected': True,
                        'pattern_type': 'triple_bottom',
                        'pattern_name': 'Triple Bottom',
                        'signal': 'bullish',
                        'confidence': confidence,
                        'first_trough': {'date': dates[first_idx], 'price': round(first_price, 2)},
                        'second_trough': {'date': dates[second_idx], 'price': round(second_price, 2)},
                        'third_trough': {'date': dates[third_idx], 'price': round(third_price, 2)},
                        'neckline': round(neckline, 2),
                        'target_price': round(target_price, 2),
                        'current_price': round(current_price, 2),
                        'pattern_height_pct': round(pattern_height * 100, 2)
                    }
    return best_pattern


def detect_ascending_triangle(prices: list, dates: list, window: int = 10) -> dict:
    """
    Detect Ascending Triangle pattern (bullish continuation) using OLS regression
    trendlines with R^2 >= 0.70.
    """
    if len(prices) < 60:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    if len(local_maxima) < 2 or len(local_minima) < 2:
        return None
        
    search_start = max(0, n - 80)
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    if len(recent_maxima) < 2 or len(recent_minima) < 2:
        return None
        
    # Flat resistance (peaks within 2% of the average)
    peak_prices = [m[1] for m in recent_maxima]
    resistance = np.mean(peak_prices)
    resistance_flatness = max(abs(p - resistance) / resistance for p in peak_prices)
    if resistance_flatness > 0.02:
        return None
        
    # OLS Rising support
    trough_indices = [m[0] for m in recent_minima]
    trough_prices = [m[1] for m in recent_minima]
    
    slope, intercept, r_squared = _fit_ols_line(trough_indices, trough_prices)
    if slope <= 0 or r_squared < 0.70:
        return None
        
    current_support = slope * (n - 1) + intercept
    pattern_height = (resistance - current_support) / current_support
    if pattern_height < 0.03:
        return None
        
    flatness_score = 1.0 - resistance_flatness * 20
    height_score = min(pattern_height * 10, 1.0)
    convergence = min(slope * 1000, 1.0)
    
    confidence = int((flatness_score * 0.4 + height_score * 0.3 + convergence * 0.3) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 30:
        return None
        
    target_price = resistance + (resistance - current_support)
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'ascending_triangle',
        'pattern_name': 'Ascending Triangle',
        'signal': 'bullish',
        'confidence': confidence,
        'resistance': round(resistance, 2),
        'support_start': round(slope * trough_indices[0] + intercept, 2),
        'support_current': round(current_support, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'pattern_height_pct': round(pattern_height * 100, 2)
    }


def detect_descending_triangle(prices: list, dates: list, window: int = 10) -> dict:
    """
    Detect Descending Triangle pattern (bearish continuation) using OLS regression
    trendlines with R^2 >= 0.70.
    """
    if len(prices) < 60:
        return None
        
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    if len(local_maxima) < 2 or len(local_minima) < 2:
        return None
        
    search_start = max(0, n - 80)
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    if len(recent_maxima) < 2 or len(recent_minima) < 2:
        return None
        
    # Flat support (troughs within 2% of the average)
    trough_prices = [m[1] for m in recent_minima]
    support = np.mean(trough_prices)
    support_flatness = max(abs(p - support) / support for p in trough_prices)
    if support_flatness > 0.02:
        return None
        
    # OLS Falling resistance
    peak_indices = [m[0] for m in recent_maxima]
    peak_prices = [m[1] for m in recent_maxima]
    
    slope, intercept, r_squared = _fit_ols_line(peak_indices, peak_prices)
    if slope >= 0 or r_squared < 0.70:
        return None
        
    current_resistance = slope * (n - 1) + intercept
    pattern_height = (current_resistance - support) / support
    if pattern_height < 0.03:
        return None
        
    flatness_score = 1.0 - support_flatness * 20
    height_score = min(pattern_height * 10, 1.0)
    convergence = min(abs(slope) * 1000, 1.0)
    
    confidence = int((flatness_score * 0.4 + height_score * 0.3 + convergence * 0.3) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 30:
        return None
        
    target_price = support - (current_resistance - support)
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'descending_triangle',
        'pattern_name': 'Descending Triangle',
        'signal': 'bearish',
        'confidence': confidence,
        'support': round(support, 2),
        'resistance_start': round(slope * peak_indices[0] + intercept, 2),
        'resistance_current': round(current_resistance, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'pattern_height_pct': round(pattern_height * 100, 2)
    }


def detect_cup_and_handle(prices: list, dates: list, window: int = 10) -> dict:
    """
    Detect Cup and Handle pattern (bullish continuation) using rounded cup
    depth measurements and handle pullbacks.
    """
    if len(prices) < 80:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Look for cup in the last 60-100 days
    cup_start = max(0, n - 100)
    cup_data = prices[cup_start:]
    cup_n = len(cup_data)
    
    if cup_n < 40:
        return None
        
    # Find the lowest point (bottom of cup)
    cup_bottom_idx = np.argmin(cup_data)
    if cup_bottom_idx < 10 or cup_bottom_idx > cup_n - 15:
        return None
        
    # Check for U-shape: prices should rise on both sides of bottom
    left_half = cup_data[:cup_bottom_idx]
    right_half = cup_data[cup_bottom_idx:]
    
    if len(left_half) < 5 or len(right_half) < 10:
        return None
        
    # Left lip and right lip should be near the same level
    left_lip = max(left_half[:10]) if len(left_half) >= 10 else max(left_half)
    right_lip = max(right_half[-15:-5]) if len(right_half) >= 15 else max(right_half[-5:])
    
    lip_diff = abs(left_lip - right_lip) / max(left_lip, right_lip)
    if lip_diff > 0.10:  # Lips within 10%
        return None
        
    cup_bottom = cup_data[cup_bottom_idx]
    cup_depth = (left_lip - cup_bottom) / left_lip
    
    if cup_depth < 0.10 or cup_depth > 0.50:  # Cup should be 10-50% deep
        return None
        
    # Check for handle (small pullback in last 15 days)
    handle_data = cup_data[-15:]
    handle_low = min(handle_data)
    
    handle_depth = (right_lip - handle_low) / right_lip
    if handle_depth > cup_depth * 0.5 or handle_depth <= 0:  # Handle shouldn't be too deep
        return None
        
    lip_uniformity = 1.0 - lip_diff
    depth_score = min(cup_depth * 3, 1.0)
    shape_score = 0.7 if handle_depth < cup_depth * 0.3 else 0.4
    
    confidence = int((lip_uniformity * 0.3 + depth_score * 0.4 + shape_score * 0.3) * 100)
    
    if confidence < 35:
        return None
        
    resistance = max(left_lip, right_lip)
    target_price = resistance + (resistance - cup_bottom)
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'cup_and_handle',
        'pattern_name': 'Cup and Handle',
        'signal': 'bullish',
        'confidence': confidence,
        'cup_bottom': round(cup_bottom, 2),
        'cup_bottom_date': dates[cup_start + cup_bottom_idx],
        'left_lip': round(left_lip, 2),
        'right_lip': round(right_lip, 2),
        'resistance': round(resistance, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'cup_depth_pct': round(cup_depth * 100, 2)
    }


def detect_bullish_flag(prices: list, dates: list, window: int = 5) -> dict:
    """
    Detect Bullish Flag pattern (bullish continuation) using OLS regression
    on flag channel consolidation.
    """
    if len(prices) < 40:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Look for a strong upward move in the past 30-50 days
    pole_end = n - 15
    pole_start = max(0, pole_end - 30)
    
    pole_data = prices[pole_start:pole_end]
    if len(pole_data) < 15:
        return None
        
    # Find start and end of the pole
    pole_low_idx = np.argmin(pole_data[:10])
    pole_high_idx = np.argmax(pole_data[-10:]) + len(pole_data) - 10
    
    pole_low = pole_data[pole_low_idx]
    pole_high = pole_data[pole_high_idx]
    
    # Pole should show significant gain (at least 10%)
    pole_gain = (pole_high - pole_low) / pole_low
    if pole_gain < 0.10:
        return None
        
    # Flag data: consolidation in last 15 days
    flag_indices = list(range(pole_end, n))
    flag_prices = prices[pole_end:]
    if len(flag_prices) < 8:
        return None
        
    # Fit OLS line to consolidation prices to verify negative or flat slope
    slope, intercept, r_squared = _fit_ols_line(flag_indices, flag_prices)
    
    # Slope should be negative or slightly flat, not strongly rising
    max_allowable_slope = 0.01 * (pole_high / len(flag_prices))
    if slope > max_allowable_slope:
        return None
        
    flag_high = max(flag_prices)
    flag_low = min(flag_prices)
    flag_range = (flag_high - flag_low) / flag_high
    
    # Flag should be tight consolidation (less than 8%)
    if flag_range > 0.08:
        return None
        
    # Flag should be near pole high (not too much pullback)
    flag_pullback = (pole_high - flag_low) / pole_high
    if flag_pullback > 0.10:
        return None
        
    pole_strength = min(pole_gain * 5, 1.0)
    consolidation = 1.0 - (flag_range * 10)
    position_score = 1.0 - (flag_pullback * 10)
    
    confidence = int((pole_strength * 0.4 + consolidation * 0.3 + position_score * 0.3) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 35:
        return None
        
    target_price = pole_high + (pole_high - pole_low)  # Measured move
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'bullish_flag',
        'pattern_name': 'Bullish Flag',
        'signal': 'bullish',
        'confidence': confidence,
        'pole_low': round(pole_low, 2),
        'pole_high': round(pole_high, 2),
        'flag_high': round(flag_high, 2),
        'flag_low': round(flag_low, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'pole_gain_pct': round(pole_gain * 100, 2)
    }


def detect_falling_wedge(prices: list, dates: list, window: int = 8) -> dict:
    """
    Detect Falling Wedge pattern (bullish reversal) using double OLS trendlines
    with R^2 >= 0.70 and convergence criteria.
    """
    if len(prices) < 50:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
            
    if len(local_maxima) < 2 or len(local_minima) < 2:
        return None
        
    search_start = max(0, n - 70)
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    if len(recent_maxima) < 2 or len(recent_minima) < 2:
        return None
        
    # Fit OLS for both peak and trough trendlines
    peak_indices = [m[0] for m in recent_maxima]
    peak_prices = [m[1] for m in recent_maxima]
    trough_indices = [m[0] for m in recent_minima]
    trough_prices = [m[1] for m in recent_minima]
    
    res_slope, res_intercept, res_r2 = _fit_ols_line(peak_indices, peak_prices)
    sup_slope, sup_intercept, sup_r2 = _fit_ols_line(trough_indices, trough_prices)
    
    # Both slopes must be negative (falling)
    if res_slope >= 0 or sup_slope >= 0:
        return None
        
    # Trendlines must be statistically tight
    if res_r2 < 0.70 or sup_r2 < 0.70:
        return None
        
    # Lines must be converging (resistance slopes down faster than support)
    if abs(sup_slope) >= abs(res_slope):
        return None
        
    # Calculate spreads using OLS trendline projections
    initial_res = res_slope * peak_indices[0] + res_intercept
    initial_sup = sup_slope * trough_indices[0] + sup_intercept
    initial_spread = initial_res - initial_sup
    
    current_res = res_slope * (n - 1) + res_intercept
    current_sup = sup_slope * (n - 1) + sup_intercept
    current_spread = current_res - current_sup
    
    # Must be narrowing, and lines must not cross within the historical dataset
    if current_spread <= 0 or current_spread >= initial_spread or initial_spread <= 0:
        return None
        
    convergence = (initial_spread - current_spread) / initial_spread
    if convergence < 0.20:
        return None
        
    convergence_score = min(convergence * 2, 1.0)
    slope_score = min(abs(res_slope) * 100, 1.0)
    
    confidence = int((convergence_score * 0.5 + slope_score * 0.5) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 30:
        return None
        
    breakout_level = current_res
    target_price = breakout_level + initial_spread
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'falling_wedge',
        'pattern_name': 'Falling Wedge',
        'signal': 'bullish',
        'confidence': confidence,
        'resistance_start': round(initial_res, 2),
        'resistance_current': round(current_res, 2),
        'support_start': round(initial_sup, 2),
        'support_current': round(current_sup, 2),
        'breakout_level': round(breakout_level, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'convergence_pct': round(convergence * 100, 2)
    }


PATTERN_DETECTORS = {
    'head_shoulders': ('Head & Shoulders', 'bearish', detect_head_and_shoulders),
    'inverse_head_shoulders': ('Inverse Head & Shoulders', 'bullish', detect_inverse_head_shoulders),
    'double_top': ('Double Top', 'bearish', detect_double_top),
    'double_bottom': ('Double Bottom', 'bullish', detect_double_bottom),
    'triple_top': ('Triple Top', 'bearish', detect_triple_top),
    'triple_bottom': ('Triple Bottom', 'bullish', detect_triple_bottom),
    'ascending_triangle': ('Ascending Triangle', 'bullish', detect_ascending_triangle),
    'descending_triangle': ('Descending Triangle', 'bearish', detect_descending_triangle),
    'cup_and_handle': ('Cup and Handle', 'bullish', detect_cup_and_handle),
    'bullish_flag': ('Bullish Flag', 'bullish', detect_bullish_flag),
    'falling_wedge': ('Falling Wedge', 'bullish', detect_falling_wedge),
}

