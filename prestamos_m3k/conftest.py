"""Permite importar los módulos de la app al ejecutar pytest desde cualquier carpeta."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
