<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/logo-dark.png">
    <img src="assets/logo/logo.png" alt="Processamento Paralelo de Imagens" width="390">
  </picture>
</h1>

<p align="center">
  Pipeline experimental para estudar processamento de imagens, paralelismo de dados e desempenho computacional.
</p>

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9%2B-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-013243?logo=numpy&logoColor=white)](https://numpy.org/)
[![CI](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/pages.yml/badge.svg)](https://github.com/lianeheidemann/parallel-image-pipeline/actions/workflows/pages.yml)

[**Experimentar no navegador**](https://lianeheidemann.github.io/parallel-image-pipeline/)

</div>

## Visão geral

Este projeto compara a execução **sequencial** e **paralela** de um pipeline determinístico de processamento de imagens. Cada arquivo passa pelas mesmas operações — escala de cinza, suavização gaussiana e detecção de bordas com Sobel — para que a diferença de tempo represente principalmente a estratégia de distribuição do trabalho.

O estudo combina três perspectivas:

- **Processamento de imagens:** transformação dos pixels e extração de bordas;
- **Computação paralela:** distribuição de imagens independentes entre processos ou faixas entre Web Workers;
- **Avaliação de desempenho:** tempo, *speedup*, Lei de Amdahl e verificação de corretude.

## Pipeline de processamento

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-v3/pipeline-dark.svg?v=3">
    <source media="(prefers-color-scheme: light)" srcset="assets/readme-v3/pipeline-light.svg?v=3">
    <img src="assets/readme-v3/pipeline-light.svg?v=3" alt="Pipeline: imagem BGR, escala de cinza, blur gaussiano, Sobel X e Y, magnitude e saída PNG" width="100%">
  </picture>
</p>

Para cada imagem, `local/image_processor.py` executa:

1. leitura da imagem colorida em BGR;
2. conversão para escala de cinza com `cv2.cvtColor`;
3. suavização com `cv2.GaussianBlur` e kernel 5 × 5;
4. cálculo dos gradientes horizontal e vertical com Sobel;
5. combinação dos gradientes pela magnitude;
6. limitação dos valores ao intervalo de 0 a 255;
7. gravação do mapa de bordas em PNG.

O blur reduz pequenas variações e ruído antes do cálculo do gradiente. O Sobel estima mudanças de intensidade nos eixos X e Y; regiões com magnitude elevada indicam contornos visuais.

## Arquitetura

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-v3/architecture-dark.svg?v=1">
    <source media="(prefers-color-scheme: light)" srcset="assets/readme-v3/architecture-light.svg?v=1">
    <img src="assets/readme-v3/architecture-light.svg?v=1" alt="Arquitetura das versões local, AWS e web do pipeline" width="100%">
  </picture>
</p>

A versão sequencial e a paralela em Python compartilham exatamente a mesma função de processamento. Isso evita que diferenças no algoritmo contaminem a comparação de desempenho.

## Ambientes de execução

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-v3/environments-dark.svg?v=2">
    <source media="(prefers-color-scheme: light)" srcset="assets/readme-v3/environments-light.svg?v=2">
    <img src="assets/readme-v3/environments-light.svg?v=2" alt="Comparação entre Python local, AWS EC2 e GitHub Pages" width="100%">
  </picture>
</p>

| Característica | Python local | AWS EC2 | GitHub Pages |
|---|---|---|---|
| Linguagem | Python | Python | JavaScript |
| Executor | CPython | CPython | Navegador |
| Paralelismo | `multiprocessing.Pool` | `multiprocessing.Pool` | Web Workers |
| Unidade de trabalho | Uma imagem | Uma imagem | Uma faixa horizontal |
| Distribuição | `Pool.map`, `chunksize=1` | Igual à versão local | Fila em `runner.js` |
| Resultado | PNGs e CSVs | PNGs, CSVs e painel HTTP | Exibição na própria página |
| GIL | Cada processo possui seu próprio GIL | Cada processo possui seu próprio GIL | Não se aplica |
| Implementação dos filtros | OpenCV | OpenCV | JavaScript |

> Os tempos obtidos no navegador não devem ser comparados diretamente aos tempos do Python: além do ambiente de execução, também mudam a implementação dos filtros e a granularidade das tarefas.

## Estratégia de paralelismo

### Python: uma imagem por processo

O trabalho é predominantemente **CPU-bound**. Para aproveitar mais de um núcleo no CPython, o projeto utiliza processos independentes em vez de threads comuns.

O `multiprocessing.Pool` mantém um conjunto de processos disponíveis. Com `chunksize=1`, cada item distribuído pelo `Pool.map` corresponde a uma imagem. Quando um processo termina, recebe a próxima imagem da fila.

A escrita do relatório CSV e o contador de imagens concluídas formam uma seção crítica protegida por `multiprocessing.Lock`. O bloqueio envolve apenas a atualização compartilhada, mantendo o processamento pesado fora da região serializada.

### Navegador: uma faixa por Web Worker

Na versão web, uma imagem é dividida em faixas horizontais. A thread principal distribui essas faixas entre 2, 4 ou 8 Web Workers e monta o resultado quando as respostas chegam.

Os workers são isolados e se comunicam por mensagens. A junção final ocorre na thread principal, sem escrita concorrente direta no mesmo relatório ou buffer de saída.

### AWS: o mesmo experimento em outro computador

A AWS não introduz um terceiro algoritmo paralelo. A instância EC2 executa o mesmo `multiprocessing` da versão local. Seu papel é oferecer um ambiente remoto padronizado e disponibilizar o arquivo `benchmark.csv` em um painel HTTP somente leitura.

## Metodologia de desempenho

O benchmark intercala as rodadas sequenciais e paralelas para reduzir o favorecimento causado por cache de disco ou variação momentânea da frequência da CPU. Para cada configuração, registra a **mediana** das rodadas.

O ganho é calculado por:

```text
speedup = tempo_sequencial / tempo_paralelo
```

A Lei de Amdahl estima o limite teórico do ganho:

```text
S(N) = 1 / ((1 - p) + p / N)
```

Onde:

- `S(N)` é o *speedup* previsto com `N` processos;
- `p` é a fração paralelizável estimada;
- `1 - p` representa a parte necessariamente sequencial.

Mais processos não garantem aceleração proporcional. Criação de processos, comunicação, acesso ao disco, seção crítica, divisão desigual das tarefas e topologia da CPU introduzem custos adicionais.

## Verificação de corretude

Desempenho só é relevante se a versão paralela preservar o resultado. O `local/verify.py` calcula SHA-256 para cada par de arquivos produzido pelas execuções sequencial e paralela.

A verificação byte a byte detecta:

- imagens ausentes;
- nomes divergentes;
- diferenças nos pixels;
- arquivos gerados de maneira incompleta ou incorreta.

Se alguma configuração divergir, o benchmark termina com código de erro.

## Estrutura do repositório

```text
parallel-image-pipeline/
├── .github/workflows/       # CI e publicação do GitHub Pages
├── assets/                  # Logos e imagens da documentação
├── aws/
│   ├── server.py            # Painel HTTP somente leitura
│   └── user-data.sh         # Preparação da instância EC2
├── dataset/                 # Imagens JPG de entrada
├── local/
│   ├── image_processor.py   # Cinza → blur → Sobel
│   ├── sequential.py        # Execução com um processo
│   ├── parallel.py          # Pool de processos
│   ├── benchmark.py         # Medição, speedup e Amdahl
│   ├── verify.py            # Verificação SHA-256
│   └── generate_dataset.py  # Geração do conjunto sintético
├── output/
│   ├── sequential/          # Mapas de bordas sequenciais
│   └── parallel/            # Mapas de bordas paralelos
├── results/                 # Relatórios CSV
├── tests/                   # Testes Python, AWS e web
└── web/                     # Interface e Web Workers
```

Documentação específica:

- [Execução local](local/)
- [Versão web](web/)
- [Implantação na AWS](aws/)

## Instalação

Requisitos principais:

- Python 3.10 ou superior;
- OpenCV 4.9 ou superior;
- NumPy 1.26 ou superior;
- Pillow 10 ou superior.

No Windows:

```bash
git clone https://github.com/lianeheidemann/parallel-image-pipeline.git
cd parallel-image-pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Execução

Gere um conjunto sintético de imagens:

```bash
python local/generate_dataset.py --count 2000 --width 1920 --height 1080
```

Execute cada etapa separadamente:

```bash
python local/sequential.py
python local/parallel.py --workers 4
python local/verify.py
```

Ou execute o experimento completo:

```bash
python local/benchmark.py --workers 2 4 8 --repeat 3
```

Parâmetros importantes:

| Parâmetro | Função |
|---|---|
| `--dataset CAMINHO` | Usa outra pasta de imagens JPG |
| `--workers 2 4 8` | Compara diferentes quantidades de processos |
| `--repeat 3` | Define o número de rodadas por configuração |
| `--no-verify` | Desativa a verificação das saídas |

Contagens de processos superiores aos núcleos lógicos disponíveis são ignoradas pelo benchmark.

## Resultados gerados

| Arquivo ou pasta | Conteúdo |
|---|---|
| `output/sequential/` | Um mapa de bordas PNG para cada imagem |
| `output/parallel/` | Saída equivalente produzida em paralelo |
| `results/sequential_report.csv` | Tempo e registro da execução sequencial |
| `results/parallel_report_N.csv` | Relatório da execução com `N` processos |
| `results/benchmark.csv` | Tempo mediano, *speedup*, Amdahl e verificação |

O conjunto de referência com 2.000 imagens de 1920 × 1080 pode ocupar aproximadamente 11 GB. Tempo e armazenamento variam conforme o hardware e o formato dos arquivos.

## GitHub Pages

A demonstração web processa as imagens localmente no navegador: nenhum arquivo é enviado ou armazenado pelo projeto.

Acesse:

**https://lianeheidemann.github.io/parallel-image-pipeline/**

Para executar localmente:

```bash
npx http-server web
```

## AWS EC2

Configuração documentada para o AWS Academy:

- região `us-east-1`;
- Ubuntu Server 24.04 LTS;
- instância `c5.large`;
- volume de 30 GiB gp3;
- `aws/user-data.sh` como *User data*.

| Porta | Origem | Uso |
|---|---|---|
| 22/TCP | IP da equipe (`/32`) | Administração por SSH |
| 80/TCP | `0.0.0.0/0` | Painel de resultados |

A porta 22 não deve ficar aberta para a internet inteira. O painel aceita apenas consultas e não inicia novos processamentos.

Para executar o painel localmente:

```bash
python aws/server.py
```

Acesse `http://localhost:8080/`.

## Testes

Instale as dependências de desenvolvimento:

```bash
pip install -r requirements-dev.txt
```

Execute os testes Python:

```bash
pytest -q
```

Execute os testes da versão web:

```bash
node --test tests/web/*.test.mjs
```

Os testes cobrem a Lei de Amdahl, equivalência sequencial/paralela, verificação das imagens, painel HTTP, processamento por faixas e versionamento do cache web.

## Limitações do experimento

- o pipeline local aceita somente imagens JPG;
- lotes pequenos podem não compensar o custo de criar e coordenar processos;
- uma única imagem ocupa apenas uma tarefa no Python, independentemente do número de workers;
- a versão web divide uma imagem em faixas e, por isso, possui granularidade diferente;
- resultados de desempenho dependem do processador, armazenamento, carga do sistema e configuração da máquina;
- o benchmark avalia paralelismo em uma única máquina, não processamento distribuído entre vários nós.

## Licença

Distribuído sob a licença [MIT](LICENSE).
