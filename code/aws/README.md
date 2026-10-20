<p align="center"><strong>Execução do pipeline na AWS</strong></p>

<p align="center"><img src="https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazonaws&logoColor=white" alt="AWS EC2"></p>

Este guia explica como o projeto usa uma instância Amazon EC2 para processar imagens em paralelo e como preparar a instância pelo console da AWS.

## Como o processamento paralelo funciona

A execução na AWS usa o mesmo código Python de [`../local/`](../local/); a EC2 fornece a máquina e o ambiente de execução. Não há distribuição do trabalho entre várias instâncias: os processos paralelos rodam na mesma máquina virtual.

O trabalho é dividido por imagem:

1. O pipeline encontra os arquivos `.jpg` do conjunto de entrada.
2. Para cada imagem, aplica a mesma sequência: conversão para tons de cinza, desfoque gaussiano e detecção de bordas Sobel. O resultado é salvo como `.png`.
3. Na execução paralela, `multiprocessing.Pool` cria processos Python independentes. Cada tarefa processa uma imagem; com `chunksize=1`, o próximo processo disponível recebe a próxima imagem.
4. O processamento dos pixels acontece fora da seção crítica. Um `Lock` protege somente o incremento do contador compartilhado e a gravação de cada linha no CSV de relatório.
5. O benchmark executa as versões sequencial e paralela em rodadas intercaladas, usa a mediana dos tempos e compara as saídas por SHA-256. Uma divergência faz o benchmark terminar com erro.

O script de inicialização configura `WORKERS="2 4 8"` e roda três rodadas (`REPEAT=3`). A `c5.large` tem 2 vCPUs; as medições com 4 e 8 processos são intencionais para mostrar o efeito de criar mais processos que a capacidade de CPU disponível. A opção `--allow-oversubscription` permite essas medições. O relatório registra tempo sequencial, tempo paralelo, speedup, estimativa baseada na Lei de Amdahl e verificação da saída.

O `user-data.sh` executa dois benchmarks, nesta ordem:

| Conjunto | Uso | Resultados |
|---|---|---|
| `dataset/dataset-100` | Comparação entre ambientes, com as mesmas 100 imagens usadas no computador local e no GitHub Pages | `output/results/analysis/aws/benchmark.csv` e `maquina.txt` |
| `dataset/dataset-2000` | Benchmark principal, usando o conjunto padrão dos scripts locais | `output/results/benchmark.csv` |

As imagens do conjunto grande são obtidas pelo Git LFS durante o clone do repositório; o script não as gera na instância. O painel HTTP consulta esses arquivos e resultados em disco. A página `/` mostra os benchmarks e o estado da inicialização; `/benchmark.csv`, `/comparacao.csv` e `/comparacao-maquina.txt` permitem baixar os dados.

## Pré-requisitos

- Acesso a uma conta AWS com permissão para criar instâncias EC2, pares de chaves e grupos de segurança. Em AWS Academy, inicie o Learner Lab antes de criar os recursos.
- O repositório acessível em `https://github.com/lianeheidemann/parallel-image-pipeline.git`.
- O arquivo [`user-data.sh`](user-data.sh), que será colado no campo de dados do usuário da instância.

## Passo a passo para configurar a instância

### 1. Abrir o assistente de criação

1. No console AWS, selecione a região **US East (N. Virginia) `us-east-1`**, abra **EC2** e selecione **Launch instance / Executar instância**. O script registra essa região nos dados da máquina.
2. Dê um nome, por exemplo `parallel-image-pipeline`.
3. Em **Application and OS Images**, escolha **Ubuntu Server 24.04 LTS**, arquitetura **64-bit (x86)**.
4. Em **Instance type**, escolha `c5.large` (2 vCPUs e 4 GiB de memória). O script mede com 2, 4 e 8 processos; as duas últimas configurações excedem as vCPUs da instância. A família C evita que a medição dependa dos créditos de CPU das instâncias T.

### 2. Escolher o par de chaves

Selecione um par existente autorizado pela equipe ou crie um novo e baixe o arquivo `.pem`. Em AWS Academy, use o par disponibilizado pelo laboratório, normalmente chamado `vockey`. Guarde a chave em local seguro: ela é necessária para SSH e não pode ser baixada novamente depois.

### 3. Configurar a rede e o grupo de segurança

Crie ou selecione um grupo de segurança com estas regras de entrada:

| Tipo | Protocolo/porta | Origem | Finalidade |
|---|---|---|---|
| SSH | TCP 22 | IP público da equipe, no formato `x.x.x.x/32` | Administração por SSH |
| HTTP personalizado | TCP 80 | `0.0.0.0/0` | Acesso ao painel de resultados somente leitura |

Se a equipe também usar IPv6, restrinja a regra SSH ao IPv6 autorizado. Não abra a porta 22 para todas as origens. A regra de saída padrão pode permanecer habilitada para permitir a instalação dos pacotes e o clone do repositório.

### 4. Configurar o disco

Em **Configure storage**, use um volume raiz de **30 GiB**, tipo **gp3**. O `dataset-2000` (2000 imagens de 640×480) ocupa cerca de 530 MB; o restante permite instalar dependências e guardar resultados. O disco persiste após **Stop**, mas é removido quando a instância é encerrada com **Terminate**. Copie os arquivos de `output/results/` antes de terminar a instância.

### 5. Colar o script de inicialização

1. Expanda **Advanced details / Detalhes avançados**.
2. No campo **User data**, cole o conteúdo completo de [`user-data.sh`](user-data.sh).
3. Confira que o script está em texto simples e sem cercas Markdown.
4. Revise o resumo e selecione **Launch instance / Executar instância**.

O script roda como `root` no primeiro boot. Ele instala Git, Git LFS e `python3-venv`; clona o projeto em `/home/ubuntu/parallel-image-pipeline`; cria o ambiente virtual; instala `requirements.txt`; habilita o serviço `pipeline-panel` no `systemd`; e inicia os dois benchmarks. A instalação e as medições podem levar vários minutos, em especial por causa do download via Git LFS.

### 6. Acompanhar a inicialização

Na página **Instances**, aguarde os estados **Running** e **2/2 status checks passed**. Copie o **Public IPv4 address** da instância e abra no navegador:

```text
http://IP-PÚBLICO/
```

O painel atualiza a página enquanto o arquivo `output/results/setup.running` existir. Quando a configuração terminar, a página mostra os tempos, o speedup, a fração paralelizável estimada e a verificação das saídas. Os CSVs também ficam disponíveis nos caminhos listados acima.

Para acompanhar a saída completa por SSH:

```bash
ssh -i caminho/para/chave.pem ubuntu@IP-PÚBLICO
tail -f ~/parallel-image-pipeline/results/setup.log
```

O arquivo `output/results/setup.log` registra a execução dos benchmarks. Para consultar também os erros do cloud-init ou do serviço do painel:

```bash
sudo tail -n 100 /var/log/cloud-init-output.log
sudo systemctl status pipeline-panel.service
sudo journalctl -u pipeline-panel.service --no-pager
```

Se o painel abrir, mas ainda não mostrar resultados, confirme no log se o download do dataset e o benchmark foram concluídos. O marcador `output/results/setup.running` desaparece ao terminar, inclusive quando o benchmark falha.

### 7. Parar ou encerrar a instância

Ao terminar a medição, selecione a instância e use **Stop instance** para interromper a execução e preservar o volume EBS. Ao retomá-la, o painel inicia automaticamente pelo `systemd`; o `user-data.sh` não refaz os benchmarks no boot seguinte. Baixe ou copie os resultados antes de usar **Terminate instance**, pois essa ação apaga o volume raiz.

## Executar o painel fora da AWS

Da raiz do repositório, com as dependências instaladas, é possível abrir o painel localmente:

```bash
python code/aws/server.py
```

Por padrão, ele escuta na porta 8080; abra `http://localhost:8080/`. Para escolher outra porta, use `--port`, por exemplo `python code/aws/server.py --port 9000`.

## Arquivos relacionados

- [`user-data.sh`](user-data.sh): provisionamento inicial e execução dos benchmarks.
- [`server.py`](server.py): painel HTTP de resultados, somente leitura.
- [`../local/parallel.py`](../local/parallel.py): distribuição de imagens por processos.
- [`../local/benchmark.py`](../local/benchmark.py): medições, mediana, speedup e verificação.
- [`../local/image_processor.py`](../local/image_processor.py): etapas aplicadas a cada imagem.
