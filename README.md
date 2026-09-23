# Processamento Paralelo de Imagens

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9%2B-green)](https://opencv.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-013243)](https://numpy.org/)
[![CI](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/ci.yml)
[![Deploy GitHub Pages](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/pages.yml/badge.svg)](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/pages.yml)

Comparação entre processamento **sequencial** e **paralelo** (`multiprocessing`)
de um mesmo pipeline de imagem — escala de cinza → blur gaussiano → detecção
de bordas (Sobel) — com verificação de corretude bit a bit e medição de
*speedup* frente à Lei de Amdahl.

🌐 **[Página do projeto](https://lianeheidemann.github.io/parallel-image-pipeline/)** 

## Python ou página web?

O projeto tem duas formas de rodar o mesmo pipeline:

| | Scripts Python (`src/`) | Página web (GitHub Pages) |
|---|---|---|
| Onde roda | No seu computador, por um terminal | No navegador, sem instalar nada |
| Imagens de entrada | Arquivos `.jpg` na pasta `dataset/` (ou outra, com `--dataset`) | As que você escolher na página |
| Resultados | Salvos em `output/` e `results/` | Só na tela; nada é salvo |
| Paralelismo | Processos (`multiprocessing`) + OpenCV | Web Workers + JavaScript |
| Para que serve | Medição do trabalho: tempos, speedup, Lei de Amdahl, verificação SHA-256 | Visualizar rapidamente o resultado com as suas imagens |

Para rodar com as suas imagens e guardar os resultados, use os **scripts Python**.
Não é preciso IDE: qualquer terminal serve (PowerShell, Terminal do macOS/Linux
ou o terminal integrado do VS Code/PyCharm).

## Estrutura

```
dataset/                  imagens de entrada
output/sequential/        saída da versão sequencial
output/parallel/          saída da versão paralela
results/                  relatórios CSV + benchmark.csv
src/
  common.py                caminhos padrão, relatório CSV e utilitários compartilhados
  image_processor.py       pipeline aplicado a uma imagem
  generate_dataset.py      gera um dataset sintético
  sequential.py            versão sequencial (1 processo)
  parallel.py              versão paralela (multiprocessing.Pool)
  verify.py                compara saídas via SHA-256
  benchmark.py             roda sequencial + paralelo e calcula o speedup
docs/                     página web (GitHub Pages)
tests/                    testes (pytest + node --test)
```

## Arquitetura

```mermaid
flowchart LR
    GEN["generate_dataset.py"] --> DS[("dataset/*.jpg")]

    DS --> SEQ["sequential.py\n(1 processo)"]
    DS --> PAR["parallel.py\n(multiprocessing.Pool)"]

    SEQ --> IP["image_processor.py\ngray → blur → Sobel"]
    PAR --> IP

    IP --> OUT_SEQ[("output/sequential/*.png")]
    IP --> OUT_PAR[("output/parallel/*.png")]

    OUT_SEQ --> VER["verify.py\nSHA-256"]
    OUT_PAR --> VER

    BENCH["benchmark.py"] -.orquestra.-> SEQ
    BENCH -.orquestra.-> PAR
    BENCH -.orquestra.-> VER
    BENCH --> CSV[("results/benchmark.csv\nspeedup + Amdahl")]
```

`image_processor.py` concentra a lógica de transformação de uma única
imagem e é reutilizado tanto pela versão sequencial quanto pela paralela —
as duas diferem apenas em **como** distribuem o trabalho, nunca no
resultado. `common.py` centraliza o que é puramente infraestrutural
(caminhos padrão, listagem do dataset, escrita do relatório CSV), evitando
que cada script redefina o mesmo caminho ou formato de CSV. `benchmark.py`
não reimplementa nada: chama `sequential.run`, `parallel.run` e
`verify.verify` diretamente, garantindo que o número comparado é sempre o
mesmo que roda isoladamente.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
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
python src/benchmark.py --dataset dataset --workers 2 4 8 --repeat 3
```

### Usar suas próprias imagens

1. Copie as imagens para a pasta `dataset/`. Só arquivos **`.jpg`** são lidos
   (`.png`, `.jpeg` e `.webp` são ignorados; no Linux/macOS, `.JPG` em
   maiúsculas também).
2. Rode os scripts pelo terminal, a partir da pasta do projeto:

```bash
python src/sequential.py
python src/parallel.py --workers 4
python src/verify.py
```

Para usar outra pasta sem copiar nada, passe `--dataset`:

```bash
python src/benchmark.py --dataset C:\Users\voce\Fotos --workers 2 4 --repeat 3
```

Para o volume registrado na ficha da Etapa 1 (sequencial levando minutos):

```bash
python src/generate_dataset.py --count 2000 --width 1920 --height 1080   # ≈ 3,6 GB
python src/benchmark.py --workers 2 4 8 --repeat 3                        # ≈ 3 min por rodada sequencial
```

Contando entrada e as duas saídas, isso ocupa cerca de 11 GB de disco.

O benchmark Python grava `results/benchmark.csv` com as colunas `processos`,
`tempo_s`, `speedup`, `speedup_amdahl_previsto` e `verificado`. Cada
configuração roda `--repeat` vezes (padrão 3), com as rodadas intercaladas, e o
CSV guarda a mediana. O comando termina com código 1 se alguma saída paralela
diferir da sequencial. As pastas `output/` são limpas a cada execução.

## Onde ficam os arquivos

Tudo fica **no seu computador**, dentro da pasta do projeto:

| Pasta | O que guarda |
|---|---|
| `dataset/` | Imagens de entrada (`.jpg`), suas ou geradas por `generate_dataset.py` |
| `output/sequential/` | Uma imagem de bordas (`.png`) por entrada, gerada pela versão sequencial |
| `output/parallel/` | O mesmo, gerado pela versão paralela (idêntico byte a byte) |
| `results/` | `sequential_report.csv` e `parallel_report_N.csv` (tempo de cada imagem e processo que a tratou) e `benchmark.csv` (resumo) |

- Cada execução **apaga os `.png` antigos** da pasta de saída antes de começar;
  copie para outro lugar o que quiser guardar.
- Essas pastas estão no `.gitignore`: as imagens e os relatórios **não vão
  para o GitHub** num `git push`.

## Página web

A [página do projeto](https://lianeheidemann.github.io/parallel-image-pipeline/)
roda o mesmo pipeline em JavaScript, direto no navegador:

- compara o processamento **sequencial** (thread principal) com **2, 4 e 8
  Web Workers**; cada imagem é cortada em faixas horizontais, uma por worker;
- confere pixel a pixel que o resultado paralelo é igual ao sequencial;
- cada configuração roda 3 vezes, em rodadas intercaladas, e o gráfico mostra
  a mediana;
- aceita imagens **JPG, PNG ou WebP, sem limite de quantidade nem de tamanho**.
  O limite prático é a memória do navegador/aparelho; se uma imagem não puder
  ser carregada, a página diz qual foi.

As imagens **não são enviadas para nenhum servidor e não são salvas**: ficam só
na memória da aba e somem ao recarregar ou fechar a página. A página também não
lê a pasta `dataset/` nem grava em `output/`. Para guardar uma imagem de bordas,
clique com o botão direito em "Bordas detectadas" e escolha "Salvar imagem como…".

Os tempos são medidos no navegador e não se comparam diretamente com o
benchmark Python (`multiprocessing`/OpenCV). Para rodar a página localmente
(módulos ES não abrem via `file://`):

```bash
npx http-server docs
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q                               # Amdahl, verify.py, sequencial == paralelo
node --test tests/*.test.mjs            # versão web: faixas == imagem inteira, versões ?v= iguais
```

## Detalhes técnicos

**Estratégia.** Paralelismo de **dados**: o dataset é dividido em imagens
(`chunksize=1` no `Pool.map`), e cada worker aplica a mesma operação a uma
imagem por vez — não há divisão por etapas do pipeline. A distribuição usa
**processos** (`multiprocessing`), não threads: o trabalho é limitado por
CPU (OpenCV/NumPy) e, no CPython, threads não somam núcleos para esse tipo
de carga (GIL); cada processo tem seu próprio interpretador.

**Seção crítica.** Na versão paralela, os processos compartilham um contador
de progresso (`multiprocessing.Value`, em memória compartilhada) e o
relatório CSV — esse é o único estado compartilhado do programa. Ambos são
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
