import json
import click
from typing import Dict, Union, List
from uwsclient import UWSClient


@click.group()
@click.option("--base-url", required=True, help="Base URL of the UWS service")
@click.option("--token", required=True, help="Authentication token")
@click.pass_context
def cli(ctx: click.Context, base_url: str, token: str) -> None:
    """CLI for interacting with a UWS service."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = UWSClient(base_url, token)


@cli.command()
@click.option(
    "--params", required=True, type=str, help="Job parameters as a JSON string"
)
@click.option("--run-id", default=None, help="Optional run ID for the job")
@click.option(
    "--auto-start",
    is_flag=True,
    default=True,
    help="Whether to start the job automatically",
)
@click.pass_context
def create_job(
    ctx: click.Context, params: str, run_id: str | None, auto_start: bool
) -> None:
    """Create a new job on the UWS service.

    Parameters should be provided as a JSON string, e.g.:
    --params='{"circle": "45.0,50.0,0.5", "id": "example_id"}'
    """
    client: UWSClient = ctx.obj["client"]
    try:
        params_dict: Dict[str, Union[str, List[str]]] = json.loads(params)
        job_id = client.create_job(params_dict, run_id, auto_start)
        click.echo(f"Job created with ID: {job_id}")
    except json.JSONDecodeError:
        click.echo("Error: Parameters must be valid JSON", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Error creating job: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("job-id", required=True)
@click.pass_context
def job_status(ctx: click.Context, job_id: str) -> None:
    """Get the status of a job."""
    client: UWSClient = ctx.obj["client"]
    try:
        status = client.get_job_status(job_id)
        click.echo(json.dumps(status, indent=2))
    except Exception as e:
        click.echo(f"Error getting job status: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("job-id", required=True)
@click.argument(
    "output-dir", required=True, type=click.Path(file_okay=False, dir_okay=True)
)
@click.pass_context
def download_results(ctx: click.Context, job_id: str, output_dir: str) -> None:
    """Download results of a completed job."""
    client: UWSClient = ctx.obj["client"]
    try:
        results = client.get_job_results(job_id)
        for i, result in enumerate(results):
            if result.get("href"):
                output_path = f"{output_dir}/result_{i}.fits"
                client.download_result(result["href"], output_path)
                click.echo(f"Downloaded result to {output_path}")
    except Exception as e:
        click.echo(f"Error downloading results: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("job-id", required=True)
@click.option("--timeout", default=3600, help="Maximum wait time in seconds")
@click.option(
    "--poll-interval", default=10, help="Time between status checks in seconds"
)
@click.pass_context
def wait_for_completion(
    ctx: click.Context, job_id: str, timeout: int, poll_interval: int
) -> None:
    """Wait for a job to complete."""
    client: UWSClient = ctx.obj["client"]
    try:
        status = client.wait_for_job_completion(job_id, timeout, poll_interval)
        click.echo(
            f"Job completed with phase: {status['phase']}\n"
            f"Full status: {json.dumps(status, indent=2)}"
        )
    except TimeoutError as e:
        click.echo(f"Timeout: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Error waiting for completion: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.pass_context
def close(ctx: click.Context) -> None:
    """Close the client session."""
    client: UWSClient = ctx.obj["client"]
    try:
        client.close()
        click.echo("Client session closed successfully")
    except Exception as e:
        click.echo(f"Error closing client session: {e}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    cli(obj={})
