"""Gera um dataset sintetico de imagens (formas geometricas + ruido) para o benchmark."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from common import PROJECT_ROOT

DEFAULT_SIZE = (640, 480)


def make_image(seed: int, size=DEFAULT_SIZE) -> Image.Image:
    rng = np.random.default_rng(seed)

    noise = rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
    img = Image.fromarray(noise, mode="RGB")
    draw = ImageDraw.Draw(img)

    for _ in range(rng.integers(3, 8)):
        shape = rng.choice(["rectangle", "ellipse", "line"])
        x0, y0 = int(rng.integers(0, size[0])), int(rng.integers(0, size[1]))
        x1, y1 = int(rng.integers(0, size[0])), int(rng.integers(0, size[1]))
        color = tuple(int(c) for c in rng.integers(0, 256, 3))
        x_min, x_max = sorted([x0, x1])
        y_min, y_max = sorted([y0, y1])
        if shape == "rectangle":
            draw.rectangle([x_min, y_min, x_max, y_max], outline=color, width=3)
        elif shape == "ellipse":
            draw.ellipse([x_min, y_min, x_max, y_max], outline=color, width=3)
        else:
            draw.line([x0, y0, x1, y1], fill=color, width=3)

    return img


def generate_dataset(output_dir: Path, count: int, size=DEFAULT_SIZE) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    digits = len(str(count))
    for i in range(1, count + 1):
        img = make_image(seed=i, size=size)
        img.save(output_dir / f"img{i:0{digits}d}.jpg", quality=90)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dataset sintetico de imagens")
    parser.add_argument("--count", type=int, default=1000, help="Numero de imagens a gerar")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dataset", help="Pasta de saida")
    parser.add_argument("--width", type=int, default=DEFAULT_SIZE[0])
    parser.add_argument("--height", type=int, default=DEFAULT_SIZE[1])
    args = parser.parse_args()

    generate_dataset(args.output, args.count, size=(args.width, args.height))
    print(f"{args.count} imagens geradas em {args.output}/")


if __name__ == "__main__":
    main()
