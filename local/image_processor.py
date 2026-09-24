"""Pipeline aplicado a cada imagem: escala de cinza -> blur gaussiano -> bordas (Sobel).

E a mesma funcao nas versoes sequencial e paralela; elas so diferem em como
distribuem as imagens. Por isso a comparacao de tempo e justa.
- A saida depende so dos pixels da propria imagem: as partes sao independentes
  e podem rodar ao mesmo tempo (condicao 1 da Ficha A).
- E deterministica: a mesma entrada gera os mesmos bytes, o que permite verificar
  a versao paralela contra a sequencial byte a byte (condicao 3).
- E calculo puro sobre pixels (limitado por processador), o que justifica usar
  processos em vez de threads (Ficha B).
"""

from pathlib import Path

import cv2
import numpy as np


def process_image(image_path: Path, output_path: Path) -> None:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Nao foi possivel ler a imagem: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), sigmaX=0)

    sobel_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(sobel_x, sobel_y)
    edges = np.clip(magnitude, 0, 255).astype(np.uint8)

    if not cv2.imwrite(str(output_path), edges):
        raise OSError(f"Nao foi possivel gravar a imagem: {output_path}")


def output_filename(image_path: Path) -> str:
    return f"{image_path.stem}.png"
