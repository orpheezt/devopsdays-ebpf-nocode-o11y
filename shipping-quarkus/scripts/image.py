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
import re
import subprocess
from collections import Counter
from enum import StrEnum
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


class Target(StrEnum):
    JVM = "jvm"
    NATIVE = "native"


def get_project_version() -> str:
    gradle_path = PROJECT_ROOT / "build.gradle.kts"
    if gradle_path.exists():
        content = gradle_path.read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    return "1.0.0-SNAPSHOT"


TAG = get_project_version()
IMAGE_NAME = "shipping-quarkus"
OUTPUT_DIR = PROJECT_ROOT / "out"

BASE_IMAGE_KEYWORDS = (
    "FROM",
    "alpine",
    "minirootfs",
    "apk",
    "buildkit",
    "liberica",
    "alpaquita",
    "bellsoft",
    "ENV PATH=/usr/local",
    "adduser",
    "addgroup",
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
def main(
    ctx: typer.Context,
    target: Annotated[
        Target,
        typer.Option("--target", "-t", help="Build target variant (jvm or native)"),
    ] = Target.JVM,
) -> None:
    if not ctx.invoked_subcommand:
        build(target=target)


@app.command()
def build(
    target: Annotated[
        Target,
        typer.Option("--target", "-t", help="Build target variant (jvm or native)"),
    ] = Target.JVM,
) -> None:
    """Build the shipping-quarkus container image and export compressed OCI archive."""
    console.print("Relabeling SELinux context for bind mounts...")
    subprocess.run(
        [
            "chcon",
            "-R",
            "-t",
            "container_file_t",
            "build.gradle.kts",
            "settings.gradle.kts",
            "gradle.properties",
            "gradle",
            "gradlew",
            "src",
            "Dockerfile.jvm",
            "Dockerfile.native",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
    )

    image_tag = f"{IMAGE_NAME}:{target.value}"
    dockerfile = f"Dockerfile.{target.value}"
    archive_path = OUTPUT_DIR / f"{IMAGE_NAME}-{target.value}-{TAG}.tar.zst"

    console.print(
        f"Building container image [bold cyan]{image_tag}[/] using [bold green]{dockerfile}[/]..."
    )
    run(
        [
            "buildah",
            "build",
            "--layers",
            "-f",
            dockerfile,
            "-t",
            image_tag,
            str(PROJECT_ROOT),
        ]
    )

    console.print(f"Successfully built [bold green]{image_tag}[/]")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    console.print(
        f"Pushing image to OCI archive with zstd compression: [cyan]{archive_path}[/]..."
    )
    run(
        [
            "buildah",
            "push",
            "--compression-format",
            "zstd",
            image_tag,
            f"oci-archive:{archive_path}",
        ]
    )
    console.print(
        f"Successfully exported OCI archive with zstd compression to [green]{archive_path}[/]"
    )

    console.print()
    diagnostics(target=target, archive_path=str(archive_path))


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
            case c if any(
                k in c
                for k in (
                    "COPY",
                    "/app/lib",
                    "/app/quarkus",
                    "/app/app",
                    "/app/application",
                    "quarkus-run.jar",
                )
            ):
                totals["app"] += size
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
    target: Annotated[
        Target,
        typer.Option("--target", "-t", help="Build target variant (jvm or native)"),
    ] = Target.JVM,
    archive_path: Annotated[
        str | None,
        typer.Option("--archive-path", "-a", help="Path to exported OCI archive"),
    ] = None,
) -> None:
    """Display container image size breakdown and archive stats."""
    image_ref = f"{IMAGE_NAME}:{target.value}"
    arch_path = (
        Path(archive_path)
        if archive_path
        else OUTPUT_DIR / f"{IMAGE_NAME}-{target.value}-{TAG}.tar.zst"
    )

    history_data = get_history_data(image_ref)
    if not history_data:
        console.print(
            f"[bold red]Error:[/] Could not inspect image [yellow]{image_ref}[/]. "
            f"Run '[bold cyan]uv run --script scripts/image.py build --target {target.value}[/]' first."
        )
        raise typer.Exit(code=1)

    img_id = history_data[0].get("id", "N/A")
    created_at = history_data[0].get("Created", "N/A")

    totals = categorize_layers(history_data)
    total_size = sum(item.get("size", 0) for item in history_data) or 1

    console.print(
        Panel.fit(
            f"[bold green]Image ID:[/] [white]{img_id}[/]\n"
            f"[bold green]Created At:[/] [white]{created_at}[/]\n"
            f"[bold green]Target Mode:[/] [yellow]{target.value.upper()}[/]",
            title=f"[bold cyan]IMAGE SIZE DIAGNOSTICS: {image_ref}[/]",
            border_style="blue",
        )
    )

    table = Table(
        title=f"Component Breakdown ({target.value.upper()} Image)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Component", style="cyan")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")

    base_desc = (
        "Base Image (JRE Liberica / glibc)"
        if target == Target.JVM
        else "Base Image (Alpaquita glibc)"
    )
    app_desc = (
        "Quarkus Fast-JAR & Libraries (/app)"
        if target == Target.JVM
        else "Native Executable (/app/application)"
    )

    table.add_row(
        f"1. {base_desc}",
        fmt_size(totals["base"]),
        fmt_pct(totals["base"], total_size),
    )
    table.add_row(
        f"2. {app_desc}",
        fmt_size(totals["app"]),
        fmt_pct(totals["app"], total_size),
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

    if not arch_path.exists():
        console.print(
            f"Archive Path:       [cyan]{arch_path}[/] [dim](Not exported yet)[/]"
        )
        return

    arch_size = arch_path.stat().st_size
    ratio = (arch_size / total_size) * 100
    savings_mb = (total_size - arch_size) / (1024 * 1024)
    factor = total_size / arch_size if arch_size > 0 else 0
    console.print("[bold underline]--- Compressed Export Archive ---[/]")
    console.print(f"Archive Path:       [cyan]{arch_path}[/]")
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
        f"* Application layer ({app_desc}) accounts for [yellow]{(totals['app'] / total_size) * 100:.1f}%[/] of image size."
    )
    console.print(
        f"* Compressed zstd archive saves [green]{savings_mb:.2f} MB[/] compared to container storage."
    )


if __name__ == "__main__":
    app()
