# local/ — Python + multiprocessing

Pipeline que roda no seu computador. É o mesmo código executado na instância EC2 (ver [`aws/`](../aws/)).

| Arquivo | Papel |
|---|---|
| `image_processor.py` | Processamento de uma imagem: cinza → blur gaussiano → Sobel (OpenCV) |
| `sequential.py` | Versão sequencial (1 processo) |
| `parallel.py` | Versão paralela: `multiprocessing.Pool`, `chunksize=1`, seção crítica com `Lock` |
| `verify.py` | Compara as saídas sequencial e paralela (SHA-256) |
| `benchmark.py` | Intercala rodadas, grava a mediana, speedup e estimativa de Amdahl |
| `generate_dataset.py` | Gera imagens sintéticas em `dataset/` |
| `common.py` | Caminhos padrão, listagem de imagens e relatório CSV |

Rode da raiz do repositório (as pastas `dataset/`, `output/` e `results/` ficam na raiz):

```bash
python local/generate_dataset.py --count 2000 --width 1920 --height 1080
python local/benchmark.py --workers 2 4 8 --repeat 3
```
