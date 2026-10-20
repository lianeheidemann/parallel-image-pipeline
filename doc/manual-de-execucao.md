<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/logo/logo-dark-v2.png">
    <img src="../assets/logo/logo.png" alt="Processamento Paralelo de Imagens" width="350">
  </picture>
</h1>

<p align="center"><strong>Manual de execução</strong></p>

Como rodar os 3 códigos do projeto — **Python local**, **AWS EC2** e **GitHub Pages** — e comparar quanto
tempo cada um leva para processar o mesmo conjunto de imagens.

## 1. Visão geral

### O que é medido

Em todos os cenários, cada imagem passa pelas mesmas 6 etapas, e o tempo medido é o dessas etapas (a geração
de imagens não entra):

| # | Etapa | Python (`code/local/image_processor.py`) | JavaScript (`code/web/assets/pipeline.js`) |
|---|---|---|---|
| 01 | Entrada | `cv2.imread` | `createImageBitmap` + `getImageData` |
| 02 | Escala de cinza | `cv2.cvtColor` | `processPixels` |
| 03 | Blur gaussiano 5×5 | `cv2.GaussianBlur` | `processPixels` |
| 04 | Sobel X e Y | `cv2.Sobel` | `processPixels` |
| 05 | Magnitude | `cv2.magnitude` + limite 0–255 | `processPixels` |
| 06 | Arquivo de saída | `cv2.imwrite` (PNG) | `convertToBlob` (PNG) |

### Os 3 cenários

| Cenário | Código | Linguagem | Como paraleliza |
|---|---|---|---|
| Local | [`code/local/`](../code/local/) | Python | `multiprocessing.Pool`: **processos** nos núcleos da CPU do PC, uma imagem por processo |
| AWS EC2 | [`code/aws/`](../code/aws/) | Python | o mesmo código do local numa `c5.large` (2 vCPUs) |
| GitHub Pages | [`code/web/`](../code/web/) | JavaScript | **Web Workers** do navegador, uma imagem por worker |

Cada cenário mede o **sequencial** (1 processo ou a thread principal do navegador) e o **paralelo** com 2, 4 e
8 processos/workers. Conta só a mediana de 3 rodadas, e o resultado paralelo é comparado com o sequencial
(SHA-256 no Python, pixel a pixel na web).

### Datasets

Os dois já vêm no repositório; nenhum código precisa gerar imagens.

| Pasta | Imagens | Uso |
|---|---|---|
| `dataset/dataset-100` | 100 × 1920×1080 | o mesmo nos 3 cenários: é o que a comparação usa |
| `dataset/dataset-2000` | 2000 × 640×480 (Git LFS) | benchmark maior do Python (local e AWS) |

### Onde fica cada coisa

```
code/local/      pipeline Python (sequencial, paralelo, verificação, benchmark)
code/aws/        painel HTTP e script de inicialização da EC2
code/web/        página do GitHub Pages (JavaScript + Web Workers)
code/analysis/   roda os 3 cenários e gera tabela e gráficos (+ package.json do medidor da web)
dataset/         dataset-100 e dataset-2000
output/          tudo que o código gera: sequential/, parallel/, results/, graficos/
doc/analysis/    relatório da comparação (comparacao.md)
```

## 2. Pré-requisitos (uma vez)

Todos os comandos são rodados **na raiz do repositório**.

**Python 3.10 ou superior**

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
(no Git Bash: `source .venv/Scripts/activate`; no Linux/macOS: `source .venv/bin/activate`)
```bash
pip install -r requirements.txt
```

**Git LFS** — baixa as imagens do `dataset-2000` (sem ele, a pasta fica só com ponteiros de poucos bytes):

```bash
git lfs install
```
```bash
git lfs pull
```

**Node.js 22** — só para medir o GitHub Pages pelo computador (abre a página num Chromium sem janela). O `package.json` fica em `code/analysis/`, junto do medidor:

```bash
npm install --prefix code/analysis
```
```bash
npx --prefix code/analysis playwright install chromium
```

> **Antes de medir num notebook:** ligue o carregador e use *Configurações → Sistema → Energia → Modo de energia →
> Melhor desempenho*. Na bateria o Windows reduz a CPU e os tempos não valem. O `comparar.py` avisa quando detecta
> bateria.

## 3. Código 1 — Python local (`code/local/`)

Experimento completo: sequencial e paralelo com 2, 4 e 8 processos, 3 rodadas intercaladas, verificação SHA-256
e estimativa da Lei de Amdahl.

```bash
python code/local/benchmark.py --dataset dataset/dataset-100 --workers 2 4 8 --repeat 3
```

Sem `--dataset`, usa `dataset/dataset-2000`:

```bash
python code/local/benchmark.py
```

| Opção | Efeito |
|---|---|
| `--dataset PASTA` | pasta com as imagens `.jpg` (padrão: `dataset/dataset-2000`) |
| `--workers 2 4 8` | quantidades de processos medidas; por padrão, valores acima dos núcleos lógicos são ignorados |
| `--allow-oversubscription` | permite medir mais processos que núcleos lógicos; usado na AWS para comparar 4 e 8 processos numa `c5.large` de 2 vCPUs |
| `--repeat 3` | rodadas por configuração; o resultado é a mediana |
| `--results PASTA` | onde gravar os CSVs (padrão: `output/results/`) |
| `--no-verify` | pula a comparação SHA-256 das saídas |

Cada etapa também pode ser rodada sozinha:

```bash
python code/local/sequential.py --dataset dataset/dataset-100
```
```bash
python code/local/parallel.py --dataset dataset/dataset-100 --workers 4
```
```bash
python code/local/verify.py
```

Saídas:
- `output/sequential/` e `output/parallel/`: um PNG de bordas por imagem;
- `output/results/benchmark.csv`: tempo mediano, speedup, Amdahl e verificação de cada configuração;
- `output/results/sequential_report.csv` e `parallel_report_N.csv`: tempo de cada imagem e o processo que a fez.

O benchmark termina com erro (código 1) se a saída paralela for diferente da sequencial.

## 4. Código 2 — AWS EC2 (`code/aws/`)

A EC2 roda o mesmo código Python do local. Nenhuma credencial da AWS é usada pelo seu computador: a instância
clona o repositório do GitHub, mede e publica os resultados num painel HTTP, e o seu computador só baixa esses
resultados.

Resumo (passo a passo completo, com cada campo do console, em [`code/aws/README.md`](../code/aws/README.md)):

1. Envie suas mudanças ao GitHub (incluindo o `dataset-2000` no LFS): a instância roda o que estiver lá.
2. No console da AWS (região `us-east-1`), crie uma instância **Ubuntu Server 24.04**, tipo **c5.large**, par de
   chaves **vockey**, disco **30 GiB gp3**.
3. Grupo de segurança: **SSH 22/TCP só do seu IP** e **HTTP 80/TCP** aberto (o painel é somente leitura).
4. Em *Advanced details → User data*, cole o conteúdo de [`code/aws/user-data.sh`](../code/aws/user-data.sh). No
   primeiro boot ele instala tudo, mede `dataset-100` e depois `dataset-2000` com 1, 2, 4 e 8 processos. Na `c5.large` de 2 vCPUs, as configurações de 4 e 8 processos medem a sobrecarga de processos acima da capacidade da instância.
5. Acompanhe pelo navegador em `http://IP-PÚBLICO/` ou por SSH:

   ```bash
   ssh -i labsuser.pem ubuntu@IP-PÚBLICO
   ```
   ```bash
   tail -f ~/parallel-image-pipeline/output/results/setup.log
   ```

6. Quando o log mostrar `comparacao pronta`, traga o resultado para a comparação (seção 6).

Rotas do painel: `/` (página), `/comparacao.csv` e `/comparacao-maquina.txt` (dataset-100, usados na comparação)
e `/benchmark.csv` (dataset-2000).

Para testar o painel sem AWS (mostra o que houver em `output/results/`):

```bash
python code/aws/server.py --port 8080
```

e abra `http://localhost:8080/`.

## 5. Código 3 — GitHub Pages (`code/web/`)

### Pelo navegador

1. Abra **https://lianeheidemann.github.io/parallel-image-pipeline/**.
2. Selecione (ou arraste) as imagens de `dataset/dataset-100`.
3. Em **Web Workers**, escolha 2, 4 ou 8 (o valor destacado nos quadros de resumo) e clique em **Processar imagens**.
4. A página mede o sequencial e 2, 4 e 8 Web Workers (3 rodadas), compara os pixels e mostra os tempos.
5. **Baixar CSV** salva os tempos no mesmo formato do Python.

As imagens são processadas no próprio navegador; nada é enviado ou salvo em servidor.

### Rodar a página localmente

```bash
npx http-server code/web
```

e abra o endereço que o comando mostrar (por padrão `http://localhost:8080`).

### Medição automática (sem clicar)

Abre a página num Chromium sem janela, envia as imagens e salva o CSV:

```bash
node code/analysis/web-benchmark.mjs --dataset dataset/dataset-100 --url https://lianeheidemann.github.io/parallel-image-pipeline/
```

Sem `--url`, mede a pasta `code/web/` deste computador (útil antes de publicar). O CSV vai para
`output/results/analysis/web/benchmark.csv` (mude com `--out ARQUIVO`).

### Publicar

O GitHub Pages é atualizado sozinho a cada push na `main` que altere `code/web/`
(`.github/workflows/pages.yml`). Ao mudar qualquer arquivo de `code/web/`, suba o `?v=` de todos os arquivos para
o mesmo valor (o teste `tests/web/cache-version.test.mjs` confere), senão o navegador pode usar a versão antiga.

## 6. Comparar os 3 cenários

`code/analysis/comparar.py` mede o local e a web neste computador (um depois do outro, nunca juntos), baixa o
resultado da AWS e gera tabela e gráficos:

```bash
python code/analysis/comparar.py --aws-ip IP-PÚBLICO
```

| Opção | Efeito |
|---|---|
| `--aws-ip IP` | baixa o resultado do painel da EC2; sem ele, a AWS aparece **zerada (pendente)** |
| `--skip-local` / `--skip-web` | não mede de novo; reaproveita o CSV já salvo em `output/results/analysis/` |
| `--web-local` | mede `code/web/` deste computador em vez da página publicada |
| `--workers 2 4 8`, `--repeat 3` | contagens de processos e rodadas do Python local |
| `--out PASTA`, `--graficos PASTA` | onde gravar o relatório e os gráficos |

Exemplos:

```bash
python code/analysis/comparar.py
```
(mede local e web; AWS pendente)
```bash
python code/analysis/comparar.py --skip-local --skip-web --aws-ip IP-PÚBLICO
```
(só junta a AWS às medições já feitas)
```bash
python code/analysis/comparar.py --skip-local --skip-web
```
(só refaz o relatório e os gráficos)

Saídas:

| Arquivo | Conteúdo |
|---|---|
| [`doc/analysis/comparacao.md`](analysis/comparacao.md) | cenários e máquinas, tempos, comparação direta ("× mais lento"), resumo e gráficos |
| `output/results/analysis/dados.csv` | todos os tempos medidos dos 3 cenários, com a coluna `cenario` |
| `output/graficos/cenarios.svg` | sequencial × paralelo mais rápido de cada cenário |
| `output/graficos/tempo.svg` | tempo com cada número de processos ou Web Workers |

As medições de cada cenário ficam em `output/results/analysis/{local,aws,web}/` (`benchmark.csv` e `maquina.txt`).

## 7. Testes

```bash
pip install -r requirements-dev.txt
```
```bash
pytest -q
```
```bash
node --test tests/web/*.test.mjs
```

## 8. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `python` não encontrado ou `ModuleNotFoundError: cv2` | ambiente virtual não ativado ou dependências não instaladas | ative o `.venv` e rode `pip install -r requirements.txt` |
| Paralelo "superlinear" ou tempos que variam muito | notebook na bateria ou em economia de energia | carregador ligado e modo *Melhor desempenho* |
| `node nao encontrado` | Node.js não instalado | instale o Node.js 22 ou use `--skip-web` |
| Erro do Playwright ao abrir o navegador | Playwright ou Chromium não instalados | `npm install --prefix code/analysis` e `npx --prefix code/analysis playwright install chromium` |
| Imagens do `dataset-2000` com poucos bytes | só os ponteiros do LFS foram baixados | `git lfs install` e `git lfs pull` |
| `--aws-ip` responde 404 | a EC2 ainda está medindo | espere `comparacao pronta` no `setup.log` |
| `Nenhuma imagem .jpg em dataset/dataset-100` | pasta vazia ou caminho errado | rode da raiz do repositório; confira o `git pull` |
| Benchmark termina com "saida paralela diferente" | resultado paralelo divergiu do sequencial | apague `output/sequential` e `output/parallel` e rode de novo |
