#!/usr/bin/env python3
"""End-to-end pipeline driver for the GreenPower Utilities capstone.

Runs the full sequence in dependency order and prints a summary:

    acquire -> clean -> store -> features -> models -> anomaly -> figures

Usage:
    python run_pipeline.py                 # synthetic data (runs anywhere)
    python run_pipeline.py --source real   # download real public datasets
"""
import argparse
import time
from src import data_acquisition, clean, storage, features, models, anomaly, viz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["synthetic", "real"], default="synthetic")
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 66)
    print(" GreenPower Utilities — Energy Consumption Analytics Pipeline")
    print("=" * 66)

    # 1. acquire
    import sys
    sys.argv = ["data_acquisition", "--source", args.source]
    data_acquisition.main()
    # 2-6
    clean.main()
    storage.main()
    features.main()
    models.main()
    anomaly.main()
    viz.main()

    print("=" * 66)
    print(f" Pipeline complete in {time.time() - t0:0.1f}s. "
          f"Outputs in outputs/ , database in data/greenpower.db")
    print("=" * 66)


if __name__ == "__main__":
    main()
