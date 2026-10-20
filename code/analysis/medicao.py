"""Obtem o benchmark de cada cenario: roda o local e o web neste PC, baixa o da AWS.

Local e web rodam um depois do outro, nunca juntos: disputariam a CPU e um
distorceria o tempo do outro.
"""

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from cenarios import (
    POR_CHAVE,
    RESULTS,
    ROOT,
)
from dados import ler_csv


def executar(titulo: str, comando: list[str]) -> None:
    print(f"\n### {titulo}\n$ {' '.join(comando)}", flush=True)
    subprocess.run(comando, cwd=ROOT, check=True)


def conferir_dataset(dataset: Path) -> None:
    """O dataset ja vem no repositorio; nada e gerado aqui."""
    imagens = len(list(dataset.glob("*.jpg")))
    if imagens == 0:
        raise SystemExit(f"Nenhuma imagem .jpg em {dataset}: o dataset padrao vem no repositorio (dataset/dataset-100).")
    print(f"Dataset {dataset}: {imagens} imagens.")


def medir_local(dataset: Path, workers: list[int], repeat: int, results: Path = RESULTS) -> None:
    pasta = POR_CHAVE["local"].pasta(results)
    descrever_pc(pasta)
    executar("Python local (este PC)", [
        sys.executable, str(ROOT / "code" / "local" / "benchmark.py"), "--dataset", str(dataset), "--results", str(pasta),
        "--workers", *map(str, workers), "--repeat", str(repeat)])


def medir_web(dataset: Path, url: str | None, results: Path = RESULTS) -> None:
    """url=None serve code/web/ deste checkout (o mesmo codigo, antes de publicar no Pages)."""
    node = shutil.which("node")
    if node is None:
        raise SystemExit("node nao encontrado: instale o Node.js ou use --skip-web.")
    cenario = POR_CHAVE["web"]
    descrever_pc(cenario.pasta(results), web=url or "code/web deste checkout (servido localmente)")
    executar("GitHub Pages (Chromium headless neste PC)", [
        node, str(Path(__file__).with_name("web-benchmark.mjs")), "--dataset", str(dataset),
        "--out", str(cenario.csv(results)), *(["--url", url] if url else [])])


def baixar(url: str, timeout: float) -> bytes:
    # Acesso direto ao IP da EC2: ignora proxies configurados no ambiente.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as response:
        return response.read()


def baixar_aws(endereco: str, results: Path = RESULTS, timeout: float = 15) -> Path:
    """Baixa /comparacao.csv e /comparacao-maquina.txt do painel da EC2 (code/aws/server.py)."""
    base = endereco if endereco.startswith(("http://", "https://")) else f"http://{endereco}"
    base = base.rstrip("/")
    cenario = POR_CHAVE["aws"]
    print(f"\n### AWS EC2\nBaixando {base}/comparacao.csv", flush=True)
    cenario.pasta(results).mkdir(parents=True, exist_ok=True)
    destino = cenario.csv(results)
    destino.write_bytes(baixar(f"{base}/comparacao.csv", timeout))
    linhas = ler_csv(destino)
    if not linhas or "tempo_s" not in linhas[0]:
        destino.unlink()
        raise SystemExit(f"{base}/comparacao.csv nao e um CSV de benchmark.")
    try:
        cenario.maquina(results).write_bytes(baixar(f"{base}/comparacao-maquina.txt", timeout))
    except OSError:
        print("Aviso: painel sem /comparacao-maquina.txt; o relatorio sai sem a maquina da AWS.")
    return destino


def descrever_pc(pasta: Path, web: str | None = None) -> None:
    """Grava maquina.txt do cenario: processador, nucleos, sistema e energia deste PC."""
    energia = fonte_de_energia()
    if energia == "bateria":
        print("Aviso: notebook na bateria; ligue o carregador ou os tempos nao valem.")
    linhas = [f"maquina: {nome_do_processador()}", f"nucleos: {os.cpu_count()} logicos",
              f"sistema: {platform.system()} {platform.release()}, Python {platform.python_version()}",
              *([f"energia: {energia}"] if energia else []),
              *([f"navegador: Chromium headless abrindo {web}"] if web else []),
              f"data: {datetime.now():%d/%m/%Y %H:%M}"]
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "maquina.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def nome_do_processador() -> str:
    """Nome do processador (platform.processor() no Windows so da a familia)."""
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "desconhecida"


def fonte_de_energia() -> str | None:
    """"carregador ligado" ou "bateria" no Windows; None em outros sistemas."""
    if sys.platform != "win32":
        return None
    import ctypes

    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]

    status = SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None
    return {1: "carregador ligado", 0: "bateria"}.get(status.ACLineStatus)
