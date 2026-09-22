"""Compara, via SHA-256, se as saidas sequencial e paralela sao identicas."""

import argparse
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(dir_a: Path, dir_b: Path) -> bool:
    files_a = {p.name: p for p in dir_a.glob("*.png")}
    files_b = {p.name: p for p in dir_b.glob("*.png")}

    if files_a.keys() != files_b.keys():
        only_a = files_a.keys() - files_b.keys()
        only_b = files_b.keys() - files_a.keys()
        print(f"Conjuntos de arquivos diferentes. So em {dir_a}: {sorted(only_a)[:5]} "
              f"So em {dir_b}: {sorted(only_b)[:5]}")
        return False

    mismatches = []
    for name in sorted(files_a):
        hash_a = hash_file(files_a[name])
        hash_b = hash_file(files_b[name])
        if hash_a != hash_b:
            mismatches.append(name)

    total = len(files_a)
    ok = total - len(mismatches)
    print(f"{ok}/{total} arquivos identicos.")

    if mismatches:
        print(f"Divergencias em: {mismatches[:10]}{'...' if len(mismatches) > 10 else ''}")
        print("Resultado sequencial != resultado paralelo.")
        return False

    print("Resultado sequencial = resultado paralelo.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica se duas pastas de saida sao identicas (SHA-256)")
    parser.add_argument("--sequential", type=Path, default=PROJECT_ROOT / "output" / "sequential")
    parser.add_argument("--parallel", type=Path, default=PROJECT_ROOT / "output" / "parallel")
    args = parser.parse_args()

    ok = verify(args.sequential, args.parallel)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
