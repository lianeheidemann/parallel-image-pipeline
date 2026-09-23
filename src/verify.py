"""Compara, via SHA-256, se as saidas sequencial e paralela sao identicas."""

import argparse
import hashlib
from pathlib import Path

from common import PROJECT_ROOT


def hash_file(path: Path) -> str:
    # Le o arquivo inteiro em memoria e calcula o hash SHA-256 dos bytes,
    # usado para comparar o conteudo de duas imagens sem abri-las como imagem.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(dir_a: Path, dir_b: Path) -> bool:
    # Mapeia nome do arquivo -> caminho, para permitir comparar por nome
    # mesmo que os arquivos estejam em pastas diferentes.
    files_a = {p.name: p for p in dir_a.glob("*.png")}
    files_b = {p.name: p for p in dir_b.glob("*.png")}

    # Sem nenhum arquivo nao ha o que comparar: tratar como falha evita que
    # um dataset vazio (ou caminho errado) passe como "tudo identico".
    if not files_a and not files_b:
        print(f"Nenhum .png encontrado em {dir_a} nem em {dir_b}.")
        return False

    # Primeiro verifica se os DOIS conjuntos tem os mesmos nomes de arquivo.
    # Se algum arquivo existe so em um lado, ja nao ha como comparar conteudo.
    if files_a.keys() != files_b.keys():
        only_a = files_a.keys() - files_b.keys()
        only_b = files_b.keys() - files_a.keys()
        print(f"Conjuntos de arquivos diferentes. So em {dir_a}: {sorted(only_a)[:5]} "
              f"So em {dir_b}: {sorted(only_b)[:5]}")
        return False

    # Compara o hash de cada par de arquivos com o mesmo nome.
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
        # Mostra so os 10 primeiros nomes divergentes para nao poluir a saida.
        print(f"Divergencias em: {mismatches[:10]}{'...' if len(mismatches) > 10 else ''}")
        print("Resultado sequencial != resultado paralelo.")
        return False

    print("Resultado sequencial = resultado paralelo.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica se duas pastas de saida sao identicas (SHA-256)")
    # Por padrao compara output/sequential com output/parallel na raiz do projeto,
    # mas os caminhos podem ser sobrescritos via linha de comando.
    parser.add_argument("--sequential", type=Path, default=PROJECT_ROOT / "output" / "sequential")
    parser.add_argument("--parallel", type=Path, default=PROJECT_ROOT / "output" / "parallel")
    args = parser.parse_args()

    ok = verify(args.sequential, args.parallel)
    # Codigo de saida 0 = sucesso (identicos), 1 = falha (divergentes),
    # convencao usada por scripts/CI para detectar erro.
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
