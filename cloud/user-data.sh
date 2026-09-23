#!/bin/bash
# Preparacao da instancia EC2 (Ubuntu 24.04). Cole este arquivo inteiro no campo
# "User data" ao lancar a instancia: ele roda como root, uma vez, no primeiro boot.
#
# 1. instala Python e baixa o projeto em /home/ubuntu/parallel-image-pipeline
# 2. sobe o painel de resultados (src/server.py) na porta 80 como servico systemd
# 3. gera o dataset e roda o benchmark; o painel mostra o andamento e o resultado
#
# Decisoes da Ficha E que ficam fora deste script (feitas no console):
# - Grupo de seguranca: 22/TCP so do IP da equipe (/32), nunca 0.0.0.0/0;
#   80/TCP aberta para o painel, que e somente leitura.
# - Tipo c5.large: familia sem creditos de CPU. Nas familias t2/t3 a CPU cai quando
#   os creditos acabam, o que distorceria a medicao.
# - Disco EBS de 30 GiB: dataset, saidas e resultados sobrevivem a "Stop", mas nao
#   a "Terminate" (antes de apagar a instancia, copie results/).
#
# Acompanhe por SSH:  tail -f ~/parallel-image-pipeline/results/setup.log
set -euo pipefail

# ---- parametros da medicao (os mesmos da ficha da Etapa 1) ----
COUNT=2000          # numero de imagens
WIDTH=1920          # largura (px)
HEIGHT=1080         # altura (px)
WORKERS="2"         # processos medidos = vCPUs da c5.large
REPEAT=3            # rodadas; o CSV guarda a mediana
REPO_URL="https://github.com/lianeheidemann/parallel-image-pipeline.git"

APP_USER=ubuntu
APP_DIR="/home/${APP_USER}/parallel-image-pipeline"
RESULTS="${APP_DIR}/results"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3-venv

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
ExecStart=${APP_DIR}/.venv/bin/python src/server.py --port 80
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
  touch '${RESULTS}/setup.running'
  trap 'code=\$?; rm -f \"${RESULTS}/setup.running\"; [ \$code -eq 0 ] || echo \"[\$(date \"+%F %T\")] FALHOU (codigo \$code)\" >> \"${RESULTS}/setup.log\"' EXIT
  {
    echo \"[\$(date '+%F %T')] gerando ${COUNT} imagens ${WIDTH}x${HEIGHT}\"
    .venv/bin/python src/generate_dataset.py --count ${COUNT} --width ${WIDTH} --height ${HEIGHT}
    echo \"[\$(date '+%F %T')] benchmark: processos ${WORKERS}, ${REPEAT} rodadas\"
    .venv/bin/python src/benchmark.py --workers ${WORKERS} --repeat ${REPEAT}
    echo \"[\$(date '+%F %T')] concluido\"
  } >> '${RESULTS}/setup.log' 2>&1
"
