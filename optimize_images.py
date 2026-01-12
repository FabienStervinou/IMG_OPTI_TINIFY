import os
import re
import sys
import shutil
import argparse
import unicodedata
from pathlib import Path

from PIL import Image


try:
    from dotenv import load_dotenv

    script_dir = Path(__file__).parent.resolve()
    env_path = script_dir / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

try:
    import pillow_avif
    AVIF_SUPPORTED = True
except Exception:
    AVIF_SUPPORTED = False

try:
    import tinify
    TINIFY_AVAILABLE = True
except Exception:
    TINIFY_AVAILABLE = False


TARGET_SIZE = 3333
TARGET_DPI = (53, 53)


def sanitize_filename(stem: str) -> str:
    stem = stem.replace("-", "_").replace(" ", "_")
    stem = unicodedata.normalize("NFKD", stem)
    stem = "".join(c for c in stem if not unicodedata.combining(c))
    stem = stem.lower()
    stem = re.sub(r"[^a-z0-9_]+", "", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem or "image"


def is_landscape(img: Image.Image) -> bool:
    return img.width >= img.height


def resize_preserve_ratio(img: Image.Image, max_size: int = TARGET_SIZE) -> Image.Image:
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("RGB")
    else:
        img = img.convert("RGB")

    w, h = img.size

    if w >= h:
        # landscape
        new_w = max_size
        new_h = int(h * (max_size / w))
    else:
        # portrait
        new_h = max_size
        new_w = int(w * (max_size / h))

    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def tinify_compress_file(input_path: Path, output_path: Path) -> None:
    if not TINIFY_AVAILABLE:
        raise RuntimeError("Le module 'tinify' n'est pas installé.")
    key = os.environ.get("TINIFY_KEY")

    if not key:
        key = os.getenv("TINIFY_KEY")

    if not key:
        raise RuntimeError("Variable d'environnement TINIFY_KEY manquante.")
    tinify.key = key

    source = tinify.from_file(str(input_path))
    source.to_file(str(output_path))


def save_formats_from_image(img: Image.Image, base_out: Path, quality: int = 85) -> dict:
    written = {}

    jpg_path = base_out.with_suffix(".jpg")
    img.save(jpg_path, format="JPEG", quality=quality, optimize=True, dpi=TARGET_DPI)
    written["jpg"] = jpg_path

    webp_path = base_out.with_suffix(".webp")
    img.save(webp_path, format="WEBP", quality=quality, method=6, dpi=TARGET_DPI)
    written["webp"] = webp_path

    if AVIF_SUPPORTED:
        avif_path = base_out.with_suffix(".avif")
        # quality range is plugin-dependent; 50-80 is common sweet spot
        img.save(avif_path, format="AVIF", quality=quality, dpi=TARGET_DPI)
        written["avif"] = avif_path

    return written


def process_one(
    src: Path,
    rel: Path,
    out_dir: Path,
    no_rename: bool,
    use_tinypng: bool,
    quality: int,
    keep_structure: bool
) -> None:
    try:
        with Image.open(src) as im:
            orientation = "landscape" if is_landscape(im) else "portrait"
            img_resized = resize_preserve_ratio(im, TARGET_SIZE)

        subdir = rel.parent if keep_structure else Path()
        target_dir = out_dir / subdir
        ensure_dir(target_dir)

        # base filename - rename unless --no-rename is active
        stem = src.stem if no_rename else sanitize_filename(src.stem)

        base_out = target_dir / stem

        if use_tinypng:
            # 1) Save a "working" PNG (best for tinypng) then compress
            tmp_png = base_out.with_suffix(".tmp.png")
            img_resized.save(tmp_png, format="PNG", optimize=True, dpi=TARGET_DPI)
            compressed_png = base_out.with_suffix(".tmp_compressed.png")
            tinify_compress_file(tmp_png, compressed_png)
            tmp_png.unlink(missing_ok=True)

            # reopen compressed png for conversions
            with Image.open(compressed_png) as cim:
                cim = cim.convert("RGB")
                written = save_formats_from_image(cim, base_out, quality=quality)
            # remove the compressed PNG (only JPG/WEBP/AVIF are kept)
            compressed_png.unlink(missing_ok=True)
        else:
            # no tinypng: convert directly from img_resized
            written = save_formats_from_image(img_resized, base_out, quality=quality)

        print(f"[OK] {src.name} -> {stem} ({orientation}) | " +
              ", ".join(str(p.name) for p in written.values()))

    except Exception as e:
        print(f"[ERR] {src}: {e}", file=sys.stderr)


def iter_images(input_dir: Path, recursive: bool):
    exts = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}
    if recursive:
        for p in input_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                yield p
    else:
        for p in input_dir.glob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                yield p


def main():
    ap = argparse.ArgumentParser(description="Optimise images: 3333x3333, 53 DPI, JPG/WEBP/AVIF, renommage.")
    ap.add_argument("input_dir", type=str, help="Dossier source contenant les images")
    ap.add_argument("--out", type=str, default="output", help="Dossier de sortie (défaut: output)")
    ap.add_argument("--recursive", action="store_true", help="Parcourt récursivement les sous-dossiers")
    ap.add_argument("--no-rename", action="store_true", help="Désactive le renommage automatique (par défaut, les fichiers sont renommés)")
    ap.add_argument("--tinypng", action="store_true", help="Compresse via TinyPNG (requiert TINIFY_KEY)")
    ap.add_argument("--quality", type=int, default=85, help="Qualité JPG/WEBP/AVIF (défaut: 85)")
    ap.add_argument("--keep-structure", action="store_true", help="Conserve l'arborescence relative dans le dossier output")
    args = ap.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    ensure_dir(out_dir)

    if args.tinypng and not TINIFY_AVAILABLE:
        print("Erreur: tinify n'est pas installé. Fais: pip install tinify", file=sys.stderr)
        sys.exit(1)

    if args.tinypng:
        tinify_key = os.environ.get("TINIFY_KEY")
        if not tinify_key:
            script_dir = Path(__file__).parent.resolve()
            env_path = script_dir / ".env"
            print("Erreur: TINIFY_KEY manquant.", file=sys.stderr)
            print(f"Créez un fichier .env dans {script_dir} avec: TINIFY_KEY='votre_cle'", file=sys.stderr)
            print("Ou utilisez: export TINIFY_KEY='votre_cle'", file=sys.stderr)
            if env_path.exists():
                print(f"Note: Le fichier .env existe à {env_path} mais la clé n'a pas été chargée.", file=sys.stderr)
                print("Assurez-vous que python-dotenv est installé: pip install python-dotenv", file=sys.stderr)
            sys.exit(1)

    if not input_dir.exists():
        print(f"Erreur: dossier introuvable: {input_dir}", file=sys.stderr)
        sys.exit(1)

    if not AVIF_SUPPORTED:
        print("[INFO] AVIF non disponible (installe 'pillow-avif-plugin' si tu veux l'export AVIF).")

    files = list(iter_images(input_dir, args.recursive))
    if not files:
        print("Aucune image trouvée.")
        return

    for src in files:
        rel = src.relative_to(input_dir)
        process_one(
            src=src,
            rel=rel,
            out_dir=out_dir,
            no_rename=args.no_rename,
            use_tinypng=args.tinypng,
            quality=args.quality,
            keep_structure=args.keep_structure
        )


if __name__ == "__main__":
    main()
