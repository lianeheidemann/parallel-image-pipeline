# code/local/ — Python + multiprocessing

Pipeline que roda no seu computador. É o mesmo código executado na instância EC2 (ver [`aws/`](../aws/)).

| Arquivo | Papel |
|---|---|
| `image_processor.py` | As 6 etapas de uma imagem (OpenCV): ler o JPG → cinza → blur gaussiano → Sobel X/Y → magnitude → gravar o PNG |
| `sequential.py` | Versão sequencial (1 processo) |
| `parallel.py` | Versão paralela: `multiprocessing.Pool`, `chunksize=1`, seção crítica com `Lock` |
| `verify.py` | Compara as saídas sequencial e paralela (SHA-256) |
| `benchmark.py` | Intercala rodadas, grava a mediana, speedup e estimativa de Amdahl |
| `generate_dataset.py` | Gera imagens sintéticas em `dataset/dataset-2000/` |
| `common.py` | Caminhos padrão, listagem de imagens e relatório CSV |

Rode da raiz do repositório (as pastas `dataset/` — com `dataset-100/` e `dataset-2000/` —, e `output/` — com `sequential/`, `parallel/` e `results/` — ficam na raiz):

```bash
python code/local/benchmark.py --dataset dataset/dataset-100 --workers 2 4 8 --repeat 3
```

Os datasets já vêm no repositório. Passo a passo completo dos 3 códigos: [`doc/manual-de-execucao.md`](../../doc/manual-de-execucao.md).
