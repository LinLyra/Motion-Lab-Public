import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from lykon_motion.models.train_sklearn import train_random_forest


parser = argparse.ArgumentParser(description="Train the leakage-safe RF baseline")
parser.add_argument(
    "--allow-synthetic",
    action="store_true",
    help="Allow dummy data for a demo only; outputs are isolated under reports/demo.",
)
args = parser.parse_args()
output_dir = ROOT / "outputs" / "reports"
if args.allow_synthetic:
    output_dir = output_dir / "demo"

result = train_random_forest(
    ROOT / "data" / "processed" / "features.csv",
    output_dir,
    allow_synthetic=args.allow_synthetic,
)
print(result["report"])
print("Saved:", result["model_path"])
if args.allow_synthetic:
    print("WARNING: demo output uses synthetic data and is not a scientific result.")
