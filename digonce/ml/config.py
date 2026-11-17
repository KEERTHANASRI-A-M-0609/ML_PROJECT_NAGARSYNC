"""Central configuration — all magic numbers live here."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "datasets" / "raw"
DATA_PROC = ROOT / "datasets" / "processed"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Reproducibility
SEED = 42

# Tamil Nadu statewide geometry (approx bounding box)
REGION_NAME = "Tamil Nadu"
LAT_MIN, LAT_MAX = 8.07, 13.58
LON_MIN, LON_MAX = 76.23, 80.35
GRID_ROWS, GRID_COLS = 16, 16
# District hubs — ward/dma id == district index
# (name, lat, lon, relative corridor weight)
DISTRICTS = [
    ("Chennai", 13.0827, 80.2707, 1.6),
    ("Chengalpattu", 12.6939, 79.9750, 1.0),
    ("Kanchipuram", 12.8342, 79.7036, 0.9),
    ("Tiruvallur", 13.1439, 79.9080, 0.9),
    ("Vellore", 12.9165, 79.1325, 1.1),
    ("Ranipet", 12.9279, 79.3320, 0.7),
    ("Tirupattur", 12.4950, 78.5670, 0.7),
    ("Krishnagiri", 12.5186, 78.2137, 0.8),
    ("Dharmapuri", 12.1211, 78.1582, 0.7),
    ("Salem", 11.6643, 78.1460, 1.3),
    ("Namakkal", 11.2194, 78.1670, 0.8),
    ("Erode", 11.3410, 77.7172, 1.1),
    ("Tiruppur", 11.1085, 77.3411, 1.2),
    ("Coimbatore", 11.0168, 76.9558, 1.5),
    ("Nilgiris", 11.4102, 76.6950, 0.6),
    ("Karur", 10.9601, 78.0766, 0.7),
    ("Tiruchirappalli", 10.7905, 78.7047, 1.3),
    ("Perambalur", 11.2333, 78.8833, 0.5),
    ("Ariyalur", 11.1370, 79.0750, 0.5),
    ("Thanjavur", 10.7870, 79.1378, 1.0),
    ("Tiruvarur", 10.7660, 79.6330, 0.6),
    ("Nagapattinam", 10.7672, 79.8449, 0.6),
    ("Mayiladuthurai", 11.1010, 79.6550, 0.5),
    ("Cuddalore", 11.7480, 79.7714, 0.9),
    ("Villupuram", 11.9401, 79.4861, 0.8),
    ("Kallakurichi", 11.7380, 78.9620, 0.5),
    ("Pudukkottai", 10.3833, 78.8000, 0.7),
    ("Sivaganga", 9.8430, 78.4810, 0.6),
    ("Madurai", 9.9252, 78.1198, 1.4),
    ("Theni", 10.0104, 77.4768, 0.7),
    ("Dindigul", 10.3673, 77.9803, 0.9),
    ("Virudhunagar", 9.5680, 77.9624, 0.8),
    ("Ramanathapuram", 9.3716, 78.8300, 0.6),
    ("Thoothukudi", 8.7642, 78.1348, 1.0),
    ("Tirunelveli", 8.7139, 77.7567, 1.1),
    ("Tenkasi", 8.9590, 77.3150, 0.6),
    ("Kanniyakumari", 8.0883, 77.5385, 0.8),
]
N_DISTRICTS = len(DISTRICTS)
N_WARDS = N_DISTRICTS          # alias — ward id == district id
N_DMAS = N_DISTRICTS
WARD_ROWS, WARD_COLS = 1, N_DISTRICTS  # legacy imports

N_CORRIDORS = 900
N_JUNCTIONS = 12

# Asset cost (lakh INR, lognormal base)
MOBILISATION = {"arterial": 4.0, "sub_arterial": 2.8, "local": 1.8}
WORK_COST = {
    "road_arterial": (14.0, 0.25),
    "road_sub_arterial": (9.0, 0.25),
    "road_local": (4.5, 0.25),
    "pipe": (9.0, 0.30),
    "streetlight": (1.0, 0.20),
    "bridge": (38.0, 0.20),
}

# Simulation timeline
HISTORY_MONTHS = 36
SIM_MONTHS = 12
TOTAL_MONTHS = HISTORY_MONTHS + SIM_MONTHS   # 48

# Train / calibration / test month indices (0-based within history)
TRAIN_END = 24        # months 0–23
CALIB_END = 30        # months 24–29
TEST_END = 36         # months 30–35

# Failure calibration target
TARGET_FAILURE_RATE = 0.025   # ~2.5 % per asset per month

# Budget: ~25 % of total replacement value / 12 months
ANNUAL_BUDGET_FRACTION = 0.25

# Simulation seeds
N_SEEDS = 30
N_SEEDS_FAST = 10

# Leak detector
LEAK_CONTAMINATION = 0.10
LEAK_SCORE_WINDOW = 14   # days before month start

# ILP solver limits
ILP_TIME_LIMIT = 60      # seconds
ILP_MIP_GAP = 0.02
ILP_MAX_CANDIDATES = 400

# Health score threshold for risk display
RISK_HEALTHY = 0.30      # p below which health = 100*(1-sqrt(p/0.30))


def district_name(ward_id: int) -> str:
    """Map ward/district id → display name."""
    if 0 <= int(ward_id) < len(DISTRICTS):
        return DISTRICTS[int(ward_id)][0]
    return f"District {ward_id}"
