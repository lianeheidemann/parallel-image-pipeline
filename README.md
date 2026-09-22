# Processamento Paralelo de Imagens

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9%2B-green)](https://opencv.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-013243)](https://numpy.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/lianeheidemann/processamento-paralelo-de-imagens)](https://github.com/lianeheidemann/processamento-paralelo-de-imagens/commits/main)
[![Deploy GitHub Pages](https://github.com/lianeheidemann/processamento-paralelo-de-imagens/actions/workflows/pages.yml/badge.svg)](https://github.com/lianeheidemann/processamento-paralelo-de-imagens/actions/workflows/pages.yml)

Comparação entre processamento **sequencial** e **paralelo** (`multiprocessing`)
de um mesmo pipeline de imagem — escala de cinza → blur gaussiano → detecção
de bordas (Sobel) — com verificação de corretude bit a bit e medição de
*speedup* frente à Lei de Amdahl.

🔗 **[Página do projeto](https://lianeheidemann.github.io/processamento-paralelo-de-imagens/)** — publicada automaticamente a cada merge na `main` ([workflow](.github/workflows/pages.yml))

## Estrutura

```
dataset/                  imagens de entrada
output/sequential/        saída da versão sequencial
output/parallel/          saída da versão paralela
results/                  relatórios CSV + benchmark.csv
src/
  image_processor.py       pipeline aplicado a uma imagem
  generate_dataset.py      gera um dataset sintético
  sequential.py             versão sequencial (1 processo)
  parallel.py                versão paralela (multiprocessing.Pool)
  verify.py                   compara saídas via SHA-256
  benchmark.py                roda sequencial + paralelo e calcula o speedup
```

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Uso

```bash
# 1. gerar dataset sintético
python src/generate_dataset.py --count 1000 --output dataset

# 2. executar versão sequencial
python src/sequential.py --dataset dataset --output output/sequential --report results/sequential_report.csv

# 3. executar versão paralela (padrão: todos os núcleos)
python src/parallel.py --dataset dataset --output output/parallel --report results/parallel_report.csv --workers 4

# 4. verificar que as saídas são idênticas
python src/verify.py --sequential output/sequential --parallel output/parallel

# 5. benchmark completo (sequencial + N processos, com verificação e Lei de Amdahl)
python src/benchmark.py --dataset dataset --workers 2 4 8
```

O benchmark grava `results/benchmark.csv` com as colunas `processos`,
`tempo_s`, `speedup` e `speedup_amdahl_previsto`. Para publicar esses números
na [página do projeto](#processamento-paralelo-de-imagens), copie o arquivo
para `docs/data/benchmark.csv` e faça commit — a página detecta e usa esses
dados automaticamente; sem eles, mostra dados de exemplo.

## Detalhes técnicos

**Seção crítica.** Na versão paralela, os processos compartilham um contador
de progresso (`multiprocessing.Value`) e o relatório CSV. Ambos são
protegidos pelo mesmo `multiprocessing.Lock`, delimitando a menor seção
crítica possível — o processamento da imagem em si fica fora do lock:

```python
with _lock:
    _counter.value += 1
    with open(_report_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([image_path.name, f"{elapsed:.4f}", process_label])
```

**Corretude.** `verify.py` calcula o SHA-256 de cada arquivo de saída e
confirma que sequencial e paralelo produzem exatamente os mesmos bytes.

**Speedup.** `Speedup = Tempo_sequencial / Tempo_paralelo`. A fração
paralelizável `p` é estimada a partir do speedup observado e usada na Lei de
Amdahl (`1 / ((1 - p) + p / N)`) para prever o speedup com outras contagens
de processos, permitindo comparar previsto vs. observado.

## Licença

Distribuído sob a licença [MIT](LICENSE).
