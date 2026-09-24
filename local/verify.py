"""Verifica, por SHA-256, se as saidas sequencial e paralela sao identicas byte a byte.

E a prova de corretude (condicao 3 da Ficha A): a versao paralela produz o mesmo
que a sequencial. Rodado a cada execucao do benchmark, tambem mostra que o
resultado fica estavel com a mesma entrada, como pede o criterio de sincronizacao.
"""

import argparse
import hashlib
from pathlib import Path

from common import PARALLEL_OUTPUT, SEQUENTIAL_OUTPUT


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(dir_a: Path, dir_b: Path) -> bool:
    files_a = {p.name: p for p in dir_a.glob("*.png")}
    files_b = {p.name: p for p in dir_b.glob("*.png")}

    # Sem nenhum arquivo nao ha o que comparar: tratar como falha evita que
    # um dataset vazio (ou caminho errado) passe como "tudo identico".
    if not files_a and not files_b:
        print(f"Nenhum .png encontrado em {dir_a} nem em {dir_b}.")
        return False

    # Nomes diferentes: uma das versoes deixou de processar (ou processou a mais) alguma imagem.
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
    parser.add_argument("--sequential", type=Path, default=SEQUENTIAL_OUTPUT)
    parser.add_argument("--parallel", type=Path, default=PARALLEL_OUTPUT)
    args = parser.parse_args()

    ok = verify(args.sequential, args.parallel)
    # Codigo de saida 1 quando diverge: o CI e os scripts tratam como falha.
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
