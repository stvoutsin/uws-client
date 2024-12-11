"""Script to perform image cutouts from the Rubin Science Platform using the SODA service."""

import click
import asyncio
from typing import Optional
from pathlib import Path
from .client import async_cutout
from .logger import logger
import logging


@click.command()
@click.argument("image_ids", nargs=-1, required=True)
@click.option(
    "--circle",
    "-c",
    multiple=True,
    help='Circle cutout specification in format "RA DEC RADIUS"',
)
@click.option("--pos", "-p", multiple=True, help="Position cutout specification")
@click.option("--polygon", multiple=True, help="Polygon cutout specification")
@click.option(
    "--base-url",
    default="https://data-dev.lsst.cloud",
    help="Base URL for the SODA service",
)
@click.option(
    "--token",
    envvar="RUBIN_TOKEN",
    required=True,
    help="Authentication token (can also be set via RUBIN_TOKEN environment variable)",
)
@click.option(
    "--output-dir",
    "-o",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory for cutout files",
)
@click.option("--run-id", help="Optional client-provided job identifier")
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def cli(
    image_ids: tuple[str],
    circle: tuple[str],
    pos: tuple[str],
    polygon: tuple[str],
    base_url: str,
    token: str,
    output_dir: Path,
    run_id: Optional[str],
    debug: bool,
) -> None:
    """Perform image cutouts from the Rubin Science Platform.

    IMAGE_IDS should be one or more butler URIs identifying the images to cut out from.

    Example:
        vo-cutout --circle "55.7467 -32.2862 0.05" \\
            butler://dp02/20d28216-534a-4102-b8a7-1c7f32a9b78c
    """
    if debug:
        logger.setLevel(logging.DEBUG)

    circle_list = list(circle) if circle else None
    pos_list = list(pos) if pos else None
    polygon_list = list(polygon) if polygon else None

    try:
        asyncio.run(
            async_cutout(
                image_ids=list(image_ids),
                circle=circle_list,
                pos=pos_list,
                polygon=polygon_list,
                base_url=base_url,
                token=token,
                output_dir=str(output_dir),
                run_id=run_id,
            )
        )
    except Exception as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
