# Parallel Image Batch Processor

Sistema para comparar o desempenho do processamento sequencial e paralelo de
grandes lotes de imagens, usando Python, OpenCV e `multiprocessing`.

Cada imagem passa pelo mesmo pipeline:

```
imagem original -> grayscale -> blur gaussiano -> deteccao de bordas (Sobel) -> salvar
```

Como cada imagem e processada de forma independente, o trabalho e
naturalmente divisivel entre processos (paralelismo de dados).

## Estrutura

```
dataset/            imagens de entrada (geradas ou suas proprias)
output/
  sequential/        saida da versao sequencial
  parallel/           saida da versao paralela
src/
  image_processor.py  pipeline de processamento de uma imagem
  generate_dataset.py gera um dataset sintetico de imagens
  sequential.py        versao sequencial (1 processo)
  parallel.py           versao paralela (multiprocessing.Pool)
  verify.py              compara as saidas via SHA-256
  benchmark.py            roda sequencial + paralelo (N workers) e calcula o speedup
results/               CSVs de saida (relatorios por execucao + benchmark.csv)
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

1. Gerar o dataset sintetico (1000 imagens por padrao):

```bash
python src/generate_dataset.py --count 1000 --output dataset
```

2. Rodar a versao sequencial:

```bash
python src/sequential.py --dataset dataset --output output/sequential --report results/sequential_report.csv
```

3. Rodar a versao paralela (por padrao usa todos os cores disponiveis):

```bash
python src/parallel.py --dataset dataset --output output/parallel --report results/parallel_report.csv --workers 4
```

4. Verificar que as duas versoes produziram o mesmo resultado:

```bash
python src/verify.py --sequential output/sequential --parallel output/parallel
```

5. Rodar o benchmark completo (sequencial + 2/4/8 processos, com verificacao e Lei de Amdahl):

```bash
python src/benchmark.py --dataset dataset --workers 2 4 8
```

O resultado fica em `results/benchmark.csv`, com colunas `processos`,
`tempo_s`, `speedup` e `speedup_amdahl_previsto`.

## Estado compartilhado / secao critica

Na versao paralela (`src/parallel.py`), os processos compartilham:

- um contador de imagens concluidas (`multiprocessing.Value`)
- o arquivo `results/*.csv` (escrita compartilhada)

Ambos sao protegidos pela mesma `multiprocessing.Lock`, delimitando a menor
secao critica possivel:

```python
with _lock:
    _counter.value += 1
    with open(_report_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([image_path.name, f"{elapsed:.4f}", process_label])
```

## Verificacao de corretude (SHA-256)

Depois de rodar as duas versoes, `verify.py` calcula o SHA-256 de cada
arquivo de saida e confirma que sequencial e paralelo produzem exatamente os
mesmos bytes, imprimindo `N/N arquivos identicos.` quando tudo bate.

## Speedup e Lei de Amdahl

```
Speedup = Tempo_sequencial / Tempo_paralelo
```

O `benchmark.py` tambem estima a fracao paralelizavel `p` a partir do
speedup observado com o primeiro numero de processos testado e usa a Lei de
Amdahl para prever o speedup esperado com outras contagens de processos,
permitindo comparar previsto vs observado.
