#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
#     "typer>=0.27.1",
# ]
# ///

import json
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from shutil import which
from typing import Annotated

import typer
from rich.console import Console
from rich.filesize import decimal as fmt_decimal
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(add_completion=False)
console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_cargo_version() -> str:
    cargo_path = PROJECT_ROOT / "Cargo.toml"
    if cargo_path.exists():
        with cargo_path.open("rb") as f:
            cargo_data = tomllib.load(f)
        return cargo_data.get("package", {}).get("version", "0.1.0")
    return "0.1.0"


def get_rust_version() -> str:
    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    if dockerfile_path.exists():
        for line in dockerfile_path.read_text().splitlines():
            if line.startswith("ARG RUST_VERSION="):
                return line.split("=")[1].strip()
    return "1.97.1"


TAG = get_cargo_version()
RUST_VERSION = get_rust_version()
IMAGE_NAME = "inventory-rs"
OUTPUT_DIR = PROJECT_ROOT / "out"
ARCHIVE_PATH = OUTPUT_DIR / f"{IMAGE_NAME}-{TAG}.tar.zst"

BASE_IMAGE_KEYWORDS = (
    "FROM",
    "alpine",
    "minirootfs",
    "apk",
    "buildkit",
    "rust",
    "ENV PATH=/usr/local",
    "adduser",
)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        console.print(
            f"[bold red]Error:[/] Command failed: [yellow]{' '.join(cmd)}[/]\n"
            f"{res.stderr.strip()}"
        )
        raise typer.Exit(code=1)
    return res


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if not ctx.invoked_subcommand:
        build()


@app.command()
def build() -> None:
    console.print("Relabeling SELinux context for bind mounts...")
    subprocess.run(
        [
            "chcon",
            "-R",
            "-t",
            "container_file_t",
            "Cargo.toml",
            "Cargo.lock",
            "Toasty.toml",
            "Dockerfile",
            "src",
            "toasty",
        ],
        capture_output=True,
        check=False,
    )

    console.print(
        f"Building container image {IMAGE_NAME}:{TAG} using Rust {RUST_VERSION}..."
    )
    run(
        [
            "buildah",
            "build",
            "--layers",
            "--build-arg",
            f"RUST_VERSION={RUST_VERSION}",
            "--build-arg",
            "PORT=8082",
            "-t",
            f"{IMAGE_NAME}:{TAG}",
            ".",
        ]
    )

    console.print(
        f"Successfully built {IMAGE_NAME}:{TAG} and tagged as {IMAGE_NAME}:latest"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    console.print(
        f"Pushing image to OCI archive with zstd compression: {ARCHIVE_PATH}..."
    )
    run(
        [
            "buildah",
            "push",
            "--compression-format",
            "zstd",
            f"{IMAGE_NAME}:{TAG}",
            f"oci-archive:{ARCHIVE_PATH}",
        ]
    )
    console.print(
        f"Successfully exported OCI archive with zstd compression to {ARCHIVE_PATH}"
    )

    console.print()
    diagnostics()


def get_history_data(image_ref: str) -> list[dict] | None:
    """Retrieve layer history and sizes using buildah inspect."""
    if not which("buildah"):
        return None

    res = subprocess.run(
        ["buildah", "inspect", "--type", "image", image_ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return None

    b_data = json.loads(res.stdout)
    history = b_data.get("History", [])
    manifest_raw = b_data.get("Manifest", "{}")
    match manifest_raw:
        case str():
            manifest = json.loads(manifest_raw)
        case _:
            manifest = manifest_raw
    layers = manifest.get("layers", [])

    h_list = []
    layer_idx = 0
    img_id = b_data.get("FromImageID", "N/A")[:12]
    for h in history:
        is_empty = h.get("empty_layer", False)
        sz = (
            layers[layer_idx]["size"]
            if (not is_empty and layer_idx < len(layers))
            else 0
        )
        if not is_empty:
            layer_idx += 1
        h_list.append(
            {
                "id": img_id,
                "Created": h.get("created", "N/A"),
                "CreatedBy": h.get("created_by", ""),
                "size": sz,
            }
        )
    return h_list


def categorize_layers(history_data: list[dict]) -> Counter[str]:
    """Categorize layer sizes by command pattern using Counter and pattern matching."""
    totals: Counter[str] = Counter()
    for item in history_data:
        size = item.get("size", 0)
        cmd = item.get("CreatedBy", "") or ""
        match cmd:
            case c if "COPY" in c or "/bin/server" in c:
                totals["binary"] += size
            case c if "cargo" in c or "target" in c or "musl" in c:
                totals["build_deps"] += size
            case c if any(k in c for k in BASE_IMAGE_KEYWORDS):
                totals["base"] += size
            case _:
                totals["setup"] += size
    return totals


def fmt_size(b: int) -> str:
    """Format byte size using rich's built-in decimal formatter."""
    return f"{fmt_decimal(b):>10}"


def fmt_pct(b: int, tot: int) -> str:
    pct = (b / tot) * 100
    if pct < 0.1 and b > 0:
        return "[ <0.1% ]"
    return f"[{pct:5.1f}% ]"


@app.command()
def diagnostics(
    image_name: Annotated[
        str, typer.Argument(help="Image repository name")
    ] = IMAGE_NAME,
    tag: Annotated[str, typer.Argument(help="Image tag")] = TAG,
    archive_path: Annotated[
        str, typer.Argument(help="Path to exported OCI archive")
    ] = str(ARCHIVE_PATH),
) -> None:
    """Display container image size breakdown and archive stats."""
    image_ref = f"{image_name}:{tag}"
    archive_file = Path(archive_path)

    history_data = get_history_data(image_ref)
    if not history_data:
        console.print(
            f"[bold red]Error:[/] Could not inspect image [yellow]{image_ref}[/]. "
            "Run '[bold cyan]uv run --script scripts/image.py build[/]' first."
        )
        raise typer.Exit(code=1)

    img_id = history_data[0].get("id", "N/A")
    created_at = history_data[0].get("Created", "N/A")

    totals = categorize_layers(history_data)
    total_size = sum(item.get("size", 0) for item in history_data) or 1

    console.print(
        Panel.fit(
            f"[bold green]Image ID:[/] [white]{img_id}[/]\n[bold green]Created At:[/] [white]{created_at}[/]",
            title=f"[bold cyan]IMAGE SIZE DIAGNOSTICS: {image_ref}[/]",
            border_style="blue",
        )
    )

    table = Table(
        title="Component Breakdown (Uncompressed Image)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Component", style="cyan")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")

    table.add_row(
        "1. Base Image (alpine)",
        fmt_size(totals["base"]),
        fmt_pct(totals["base"], total_size),
    )
    table.add_row(
        "2. Compiled Binary (/bin/server)",
        fmt_size(totals["binary"]),
        fmt_pct(totals["binary"], total_size),
    )
    table.add_row(
        "3. Setup & Metadata",
        fmt_size(totals["setup"]),
        fmt_pct(totals["setup"], total_size),
    )

    console.print(table)
    console.print(
        f"[bold]Total Uncompressed Image Size:[/] [green]{fmt_size(total_size)}[/] ({total_size:,} bytes)\n"
    )

    if not archive_file.exists():
        console.print(
            f"Archive Path:       [cyan]{archive_file}[/] [dim](Not exported yet)[/]"
        )
        return

    arch_size = archive_file.stat().st_size
    ratio = (arch_size / total_size) * 100
    savings_mb = (total_size - arch_size) / (1024 * 1024)
    factor = total_size / arch_size if arch_size > 0 else 0
    console.print("[bold underline]--- Compressed Export Archive ---[/]")
    console.print(f"Archive Path:       [cyan]{archive_file}[/]")
    console.print(
        f"Archive Size:       [green]{fmt_size(arch_size)}[/] ({arch_size:,} bytes)"
    )
    console.print(
        f"Compression Ratio:  [yellow]{ratio:.1f}%[/] of original size ({factor:.2f}x compression)\n"
    )

    console.print("\n[bold underline]--- Insights ---[/]")
    console.print(
        f"* Base image accounts for [yellow]{(totals['base'] / total_size) * 100:.1f}%[/] of total image footprint."
    )
    console.print(
        f"* Compiled Rust binary accounts for [yellow]{(totals['binary'] / total_size) * 100:.1f}%[/] of image size."
    )
    console.print(
        f"* Compressed zstd archive saves [green]{savings_mb:.2f} MB[/] compared to container storage."
    )


if __name__ == "__main__":
    app()
