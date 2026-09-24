import sys
from pathlib import Path

# Os scripts importam uns aos outros pelo nome (ex.: "from common import ..."):
# local/ tem o pipeline e aws/ o painel, que usa o codigo de local/.
ROOT = Path(__file__).resolve().parent.parent
for folder in ("local", "aws"):
    sys.path.insert(0, str(ROOT / folder))
