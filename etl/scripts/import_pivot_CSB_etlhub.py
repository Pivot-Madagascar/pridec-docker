import json
import os
from pathlib import Path

from dotenv import load_dotenv

from pivot_dhis_tools import fetch_pivot_csb_etlhub

from config import PIVOT_URL, PIVOT_TOKEN, PARENT_OU, check_envvars

OUT_DIR = Path("inputs/temp_fetch")

def save_etlhub_results(results, out_dir=OUT_DIR):
    """Save each item as <dataElement>_fetched.json and <dataElement>_flags.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in results:
        name = item["dataElement"]
        fetched_path = out_dir / f"{name}_fetched.json"
        flags_path = out_dir / f"{name}_flags.json"

        with open(fetched_path, "w", encoding="utf-8") as f:
            json.dump({"dataValues" :item["fetched_data"]}, f, indent=2, default=str)
        with open(flags_path, "w", encoding="utf-8") as f:
            json.dump(item["summary"], f, indent=2, default=str)

        saved.append((fetched_path, flags_path))
    return saved

if __name__ == "__main__":

    check_envvars(required_vars = {
            'PIVOT_TOKEN': PIVOT_TOKEN,
            'PIVOT_URL': PIVOT_URL,
            'PARENT_OU': PARENT_OU
        }
)

    csb_results = fetch_pivot_csb_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=PIVOT_URL,
                                         prior_months=8)

    save_etlhub_results(csb_results)