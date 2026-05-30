import pytest
import numpy as np
from pattern_detectors import (
    detect_head_and_shoulders,
    detect_inverse_head_shoulders,
    detect_double_top,
    detect_double_bottom,
    detect_triple_top,
    detect_triple_bottom,
    detect_ascending_triangle,
    detect_descending_triangle,
    detect_cup_and_handle,
    detect_bullish_flag,
    detect_falling_wedge,
    _fit_ols_line
)

# Generate mock dates helper
def make_dates(n):
    return [f"2026-01-{i+1:02d}" for i in range(n)]

# Vertex linear interpolation helper to prevent spurious flat extrema
def generate_pattern_prices(vertices: list, length: int) -> list:
    prices = [0.0] * length
    vertices = sorted(vertices, key=lambda x: x[0])
    
    # Ensure boundary coverage
    if vertices[0][0] > 0:
        vertices.insert(0, (0, vertices[0][1]))
    if vertices[-1][0] < length - 1:
        vertices.append((length - 1, vertices[-1][1]))
        
    for idx in range(len(vertices) - 1):
        x1, y1 = vertices[idx]
        x2, y2 = vertices[idx + 1]
        for x in range(x1, x2 + 1):
            if x2 == x1:
                prices[x] = y1
            else:
                prices[x] = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return prices

def test_ols_fit_helper():
    x = [0, 1, 2, 3, 4]
    y = [2.0, 3.0, 4.0, 5.0, 6.0]
    slope, intercept, r2 = _fit_ols_line(x, y)
    assert pytest.approx(slope) == 1.0
    assert pytest.approx(intercept) == 2.0
    assert pytest.approx(r2) == 1.0

def test_detect_head_and_shoulders():
    # HS pattern: Left shoulder (peak), Head (higher peak), Right shoulder (lower peak)
    # Neckline troughs in between
    vertices = [
        (5, 15.0),   # Left shoulder peak
        (8, 9.0),    # Neckline trough 1
        (12, 18.0),  # Head peak
        (16, 9.5),   # Neckline trough 2
        (19, 14.5),  # Right shoulder peak
    ]
    prices = generate_pattern_prices(vertices, 25)
    dates = make_dates(25)
    
    result = detect_head_and_shoulders(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert pytest.approx(result['left_shoulder']['price']) == 15.0
    assert pytest.approx(result['head']['price']) == 18.0
    assert pytest.approx(result['right_shoulder']['price']) == 14.5

def test_detect_inverse_head_shoulders():
    # IHS pattern: Left shoulder (trough), Head (deeper trough), Right shoulder (higher trough)
    vertices = [
        (5, 85.0),   # Left shoulder trough
        (8, 98.0),   # Neckline peak 1
        (12, 78.0),  # Head trough
        (16, 96.0),  # Neckline peak 2
        (19, 84.0),  # Right shoulder trough
    ]
    prices = generate_pattern_prices(vertices, 25)
    dates = make_dates(25)
    
    result = detect_inverse_head_shoulders(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'inverse_head_shoulders'
    assert pytest.approx(result['left_shoulder']['price']) == 85.0
    assert pytest.approx(result['head']['price']) == 78.0
    assert pytest.approx(result['right_shoulder']['price']) == 84.0

def test_detect_double_top():
    # Double Top: Two similar peaks with a trough between them
    vertices = [
        (4, 70.0),   # Peak 1
        (9, 40.0),   # Trough
        (14, 70.5),  # Peak 2
    ]
    prices = generate_pattern_prices(vertices, 20)
    dates = make_dates(20)
    
    result = detect_double_top(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'double_top'
    assert pytest.approx(result['first_peak']['price']) == 70.0
    assert pytest.approx(result['second_peak']['price']) == 70.5
    assert pytest.approx(result['trough']['price']) == 40.0

def test_detect_double_bottom():
    # Double Bottom: Two similar troughs with a peak between them
    vertices = [
        (4, 80.0),   # Trough 1
        (9, 115.0),  # Peak
        (14, 81.0),  # Trough 2
    ]
    prices = generate_pattern_prices(vertices, 20)
    dates = make_dates(20)
    
    result = detect_double_bottom(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'double_bottom'
    assert pytest.approx(result['first_trough']['price']) == 80.0
    assert pytest.approx(result['second_trough']['price']) == 81.0
    assert pytest.approx(result['peak']['price']) == 115.0

def test_detect_triple_top():
    # Triple Top: Three similar peaks with troughs in between
    vertices = [
        (4, 80.0),   # Peak 1
        (8, 50.0),   # Trough 1
        (12, 81.0),  # Peak 2
        (16, 49.0),  # Trough 2
        (20, 79.5),  # Peak 3
    ]
    prices = generate_pattern_prices(vertices, 30)
    dates = make_dates(30)
    
    result = detect_triple_top(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'triple_top'
    assert pytest.approx(result['first_peak']['price']) == 80.0
    assert pytest.approx(result['second_peak']['price']) == 81.0
    assert pytest.approx(result['third_peak']['price']) == 79.5

def test_detect_triple_bottom():
    # Triple Bottom: Three similar troughs with peaks in between
    vertices = [
        (4, 80.0),   # Trough 1
        (8, 110.0),  # Peak 1
        (12, 79.0),  # Trough 2
        (16, 112.0), # Peak 2
        (20, 81.0),  # Trough 3
    ]
    prices = generate_pattern_prices(vertices, 30)
    dates = make_dates(30)
    
    result = detect_triple_bottom(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'triple_bottom'
    assert pytest.approx(result['first_trough']['price']) == 80.0
    assert pytest.approx(result['second_trough']['price']) == 79.0
    assert pytest.approx(result['third_trough']['price']) == 81.0

def test_detect_ascending_triangle():
    # Ascending Triangle: Flat resistance, rising support
    # Interleaved peaks and troughs, starting at 0 and ending at 69 to prevent flat boundaries
    vertices = [
        (0, 100.0),   # Peak 1
        (10, 80.0),   # Trough 1
        (20, 100.0),  # Peak 2
        (30, 83.0),   # Trough 2
        (40, 100.0),  # Peak 3
        (50, 86.0),   # Trough 3
        (60, 100.0),  # Peak 4
        (69, 89.0),   # Trough 4
    ]
    prices = generate_pattern_prices(vertices, 70)
    dates = make_dates(70)
    
    result = detect_ascending_triangle(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'ascending_triangle'
    assert pytest.approx(result['resistance'], abs=1.5) == 100.0

def test_detect_descending_triangle():
    # Descending Triangle: Flat support, falling resistance
    # Interleaved peaks and troughs, starting at 0 and ending at 69 to prevent flat boundaries
    vertices = [
        (0, 80.0),    # Trough 1
        (10, 100.0),  # Peak 1
        (20, 80.0),   # Trough 2
        (30, 95.0),   # Peak 2
        (40, 80.0),   # Trough 3
        (50, 90.0),   # Peak 3
        (60, 80.0),   # Trough 4
        (69, 85.0),   # Peak 4
    ]
    prices = generate_pattern_prices(vertices, 70)
    dates = make_dates(70)
    
    result = detect_descending_triangle(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'descending_triangle'
    assert pytest.approx(result['support'], abs=1.5) == 80.0

def test_detect_cup_and_handle():
    # Cup and Handle: rounded bottom cup + handle pullback
    vertices = [
        (10, 100.0),  # Left lip
        (40, 70.0),   # Cup bottom
        (70, 98.0),   # Right lip
        (80, 90.0),   # Handle bottom
        (85, 95.0),   # Present day
    ]
    prices = generate_pattern_prices(vertices, 90)
    dates = make_dates(90)
    
    result = detect_cup_and_handle(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'cup_and_handle'
    assert pytest.approx(result['cup_bottom']) == 70.0

def test_detect_bullish_flag():
    # Bullish flag: strong pole up, tight flag down
    vertices = [
        (5, 100.0),   # Pole start
        (30, 130.0),  # Pole high
        (49, 126.0),  # Present day
    ]
    prices = generate_pattern_prices(vertices, 50)
    dates = make_dates(50)
    
    result = detect_bullish_flag(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'bullish_flag'
    assert pytest.approx(result['pole_high']) == 130.0

def test_detect_falling_wedge():
    # Falling Wedge: both sloping downward and converging
    # Resistance peaks at: 10 (150), 20 (130), 30 (110), 40 (90)
    # Support troughs at: 12 (100), 22 (90), 32 (80), 42 (70)
    vertices = [
        (10, 150.0),
        (12, 100.0),
        (20, 130.0),
        (22, 90.0),
        (30, 110.0),
        (32, 80.0),
        (40, 90.0),
        (42, 70.0)
    ]
    prices = generate_pattern_prices(vertices, 60)
    prices[-1] = 80.0
    dates = make_dates(60)
    
    result = detect_falling_wedge(prices, dates, window=2)
    assert result is not None
    assert result['detected'] is True
    assert result['pattern_type'] == 'falling_wedge'
