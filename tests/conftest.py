import sys
from pathlib import Path

# Os scripts de src/ importam uns aos outros pelo nome (ex.: "from common import ...").
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
