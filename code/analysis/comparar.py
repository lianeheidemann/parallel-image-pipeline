"""Processa o mesmo dataset nos 3 cenarios: tabela em doc/analysis/, graficos em output/graficos/.

    python code/analysis/comparar.py                      # mede local e web
    python code/analysis/comparar.py --aws-ip 54.1.2.3    # e baixa o resultado da EC2
    python code/analysis/comparar.py --skip-local --skip-web --aws-ip 54.1.2.3

1. usa dataset/dataset-100/ (100 imagens 1920x1080 versionadas: as mesmas em todo lugar);
2. Local (Python): code/local/benchmark.py neste PC;
3. GitHub Pages (JavaScript): a pagina publicada num Chromium headless deste PC;
4. AWS EC2 (Python): baixa do painel da instancia (code/aws/user-data.sh mede o mesmo dataset);
5. junta output/results/analysis/<cenario>/benchmark.csv em doc/analysis/.

Cenario pulado reaproveita o CSV que ja estiver em output/results/analysis/; sem ele, aparece
como pendente no relatorio.
"""

import argparse
from pathlib import Path

import medicao
import relatorio
from cenarios import DATASET, DOC, GRAFICOS, PAGES_URL, RESULTS
from dados import carregar


def inteiro_positivo(valor: str) -> int:
    numero = int(valor)
    if numero < 1:
        raise argparse.ArgumentTypeError(f"deve ser >= 1 (recebido: {valor})")
    return numero


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compara o tempo do mesmo dataset em Local (Python), AWS e GitHub Pages")
    parser.add_argument("--aws-ip", help="IP publico (ou endereco) do painel da EC2")
    parser.add_argument("--skip-local", action="store_true", help="Nao mede o local; usa o CSV existente")
    parser.add_argument("--skip-web", action="store_true", help="Nao mede a web; usa o CSV existente")
    parser.add_argument("--url", default=PAGES_URL, help="Pagina web medida (padrao: GitHub Pages)")
    parser.add_argument("--web-local", action="store_true",
                        help="Mede code/web/ deste checkout em vez da pagina publicada (antes do deploy)")
    parser.add_argument("--workers", type=inteiro_positivo, nargs="+", default=[2, 4, 8])
    parser.add_argument("--repeat", type=inteiro_positivo, default=3, help="Rodadas por configuracao (mediana)")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--results", type=Path, default=RESULTS, help="Pasta dos CSVs de cada cenario")
    parser.add_argument("--out", type=Path, default=DOC, help="Pasta do relatorio")
    parser.add_argument("--graficos", type=Path, default=GRAFICOS, help="Pasta dos graficos SVG")
    args = parser.parse_args(argv)

    if not (args.skip_local and args.skip_web):
        medicao.conferir_dataset(args.dataset)
    if not args.skip_local:
        medicao.medir_local(args.dataset, args.workers, args.repeat, args.results)
    if not args.skip_web:
        medicao.medir_web(args.dataset, None if args.web_local else args.url, args.results)
    if args.aws_ip:
        medicao.baixar_aws(args.aws_ip, args.results)

    print()
    relatorio.gerar(carregar(args.results), args.out, args.graficos, args.results / "dados.csv")


if __name__ == "__main__":
    main()
