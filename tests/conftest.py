import sys
from pathlib import Path

# Os scripts importam modulos pelo nome (por exemplo, "from common import ...").
# O caminho de local/ contem o pipeline; aws/ contem o painel que o reutiliza.
ROOT = Path(__file__).resolve().parent.parent
for folder in ("local", "aws"):
    sys.path.insert(0, str(ROOT / folder))
