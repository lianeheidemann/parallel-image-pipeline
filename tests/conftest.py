import sys
from pathlib import Path

# Os scripts importam modulos pelo nome (por exemplo, "from common import ...").
# code/local/ contem o pipeline, code/aws/ o painel que o reutiliza e
# code/analysis/ a comparacao dos 3 cenarios.
ROOT = Path(__file__).resolve().parent.parent
for folder in ("local", "aws", "analysis"):
    sys.path.insert(0, str(ROOT / "code" / folder))
