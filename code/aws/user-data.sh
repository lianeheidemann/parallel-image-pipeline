#!/bin/bash
# Preparacao da instancia EC2 (Ubuntu 24.04). Cole este arquivo inteiro no campo
# "User data" ao lancar a instancia: ele roda como root, uma vez, no primeiro boot.
#
# 1. instala Python e git-lfs e clona o projeto (com os datasets) em /home/ubuntu/parallel-image-pipeline
# 2. sobe o painel de resultados (code/aws/server.py) na porta 80 como servico systemd
# 3. mede dataset/dataset-100 (o mesmo do PC e do GitHub Pages) e depois
#    dataset/dataset-2000; o painel mostra os dois. Passo a passo: code/aws/README.md
#
# Decisoes da Ficha E que ficam fora deste script (feitas no console):
# - Grupo de seguranca: 22/TCP so do IP da equipe (/32), nunca 0.0.0.0/0;
#   80/TCP aberta para o painel, que e somente leitura.
# - Tipo c5.large: familia sem creditos de CPU. Nas familias t2/t3 a CPU cai quando
#   os creditos acabam, o que distorceria a medicao.
# - Disco EBS de 30 GiB: dataset, saidas e resultados sobrevivem a "Stop", mas nao
#   a "Terminate" (antes de apagar a instancia, copie output/results/).
#
# Acompanhe por SSH:  tail -f ~/parallel-image-pipeline/output/results/setup.log
set -euo pipefail

# ---- parametros da medicao ----
WORKERS="2 4 8"     # 4 e 8 medem sobrecarga acima das 2 vCPUs da c5.large
REPEAT=3            # rodadas; o CSV guarda a mediana
# Dataset de comparacao: as 100 imagens versionadas, que chegam com o git clone (as
# mesmas do PC e do GitHub Pages). Medido antes do benchmark grande.
COMPARE_DIR="dataset/dataset-100"
REPO_URL="https://github.com/lianeheidemann/parallel-image-pipeline.git"

APP_USER=ubuntu
APP_DIR="/home/${APP_USER}/parallel-image-pipeline"
RESULTS="${APP_DIR}/output/results"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git git-lfs python3-venv
# dataset/dataset-2000 (2000 imagens 640x480, ~530 MB) fica no Git LFS: com o git-lfs instalado antes do
# clone, as imagens chegam junto. Nenhum dataset e gerado na instancia.
sudo -u "${APP_USER}" git lfs install

if [ ! -d "${APP_DIR}/.git" ]; then
  sudo -u "${APP_USER}" git clone --depth 1 "${REPO_URL}" "${APP_DIR}"
fi
sudo -u "${APP_USER}" python3 -m venv "${APP_DIR}/.venv"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"

# Painel na porta 80. Roda como o usuario comum; a capability permite abrir uma
# porta < 1024 sem ser root. Habilitado no boot: volta sozinho quando o Learner
# Lab religa a instancia.
cat > /etc/systemd/system/pipeline-panel.service <<EOF
[Unit]
Description=Painel de resultados do pipeline de imagens (HTTP, somente leitura)
After=network-online.target
Wants=network-online.target

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/python code/aws/server.py --port 80
AmbientCapabilities=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now pipeline-panel.service

# Dataset + benchmark como o usuario comum, com o marcador que o painel usa para
# mostrar "em andamento" (removido mesmo se o benchmark falhar).
sudo -u "${APP_USER}" bash -c "
  set -e
  cd '${APP_DIR}'
  mkdir -p '${RESULTS}'
  touch '${RESULTS}/setup.running'
  trap 'code=\$?; rm -f \"${RESULTS}/setup.running\"; [ \$code -eq 0 ] || echo \"[\$(date \"+%F %T\")] FALHOU (codigo \$code)\" >> \"${RESULTS}/setup.log\"' EXIT
  {
    mkdir -p output/results/analysis/aws
    {
      echo \"maquina: \$(lscpu | sed -n 's/^Model name: *//p')\"
      echo \"nucleos: \$(nproc) logicos\"
      echo \"instancia: c5.large (us-east-1), Ubuntu 24.04\"
      echo \"data: \$(date '+%d/%m/%Y %H:%M')\"
    } > output/results/analysis/aws/maquina.txt
    echo \"[\$(date '+%F %T')] comparacao: benchmark, processos ${WORKERS}, ${REPEAT} rodadas\"
    .venv/bin/python code/local/benchmark.py --dataset ${COMPARE_DIR} --results output/results/analysis/aws --workers ${WORKERS} --allow-oversubscription --repeat ${REPEAT}
    echo \"[\$(date '+%F %T')] comparacao pronta: http://IP-PUBLICO/comparacao.csv\"
    echo \"[\$(date '+%F %T')] dataset-2000: benchmark, processos ${WORKERS}, ${REPEAT} rodadas\"
    .venv/bin/python code/local/benchmark.py --workers ${WORKERS} --allow-oversubscription --repeat ${REPEAT}
    echo \"[\$(date '+%F %T')] concluido\"
  } >> '${RESULTS}/setup.log' 2>&1
"
