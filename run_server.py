import sys
import os
from pathlib import Path

# Ajouter la racine du projet au chemin Python
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from etlhub.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
