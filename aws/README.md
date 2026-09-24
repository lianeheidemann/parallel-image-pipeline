# aws/ — nuvem (EC2)

Executa o código de [`local/`](../local/) numa instância EC2 e publica o resultado num painel HTTP.

| Arquivo | Papel |
|---|---|
| `user-data.sh` | Colado em *User data* ao criar a instância: instala o projeto, registra o painel no `systemd` e roda o benchmark no 1º boot |
| `server.py` | Painel somente leitura na porta 80 (`/` e `/benchmark.csv`), com tipo de instância e zona |

Instância: `us-east-1`, Ubuntu 24.04, `c5.large`, 30 GiB gp3, par `vockey` (AWS Academy).

| Porta | Origem | Uso |
|---|---|---|
| 22/TCP | IP da equipe (`/32`) | SSH |
| 80/TCP | `0.0.0.0/0` | Painel |

Acompanhar: `ssh -i labsuser.pem ubuntu@IP-PÚBLICO` e `tail -f ~/parallel-image-pipeline/results/setup.log`.
Painel local: `python aws/server.py` (porta 8080).
