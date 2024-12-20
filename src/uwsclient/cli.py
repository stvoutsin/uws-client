import asyncio
import click
from uwsclient import UWSClient


@click.group()
@click.option('--base-url', required=True,
              help='Base URL of the UWS service')
@click.option('--token', required=True,
              help='Authentication token')
@click.pass_context
def cli(ctx, base_url, token):
    """CLI for interacting with a UWS service."""
    ctx.ensure_object(dict)
    ctx.obj['BASE_URL'] = base_url
    ctx.obj['TOKEN'] = token


@cli.command()
@click.option('--params', required=True, type=str,
              help='Job parameters as a JSON string')
@click.option('--run-id', default=None,
              help='Optional run ID for the job')
@click.option('--auto-start', is_flag=True, default=True,
              help='Whether to start the job automatically')
@click.pass_context
def create_job(ctx, params, run_id, auto_start):
    """Create a new job on the UWS service."""
    async def _create_job():
        async with UWSClient(ctx.obj['BASE_URL'], ctx.obj['TOKEN']) as client:
            job_id = await client.create_job(eval(params), run_id, auto_start)
            click.echo(f"Job created with ID: {job_id}")

    asyncio.run(_create_job())


@cli.command()
@click.argument('job-id', required=True)
@click.pass_context
def job_status(ctx, job_id):
    """Get the status of a job."""
    async def _job_status():
        async with UWSClient(ctx.obj['BASE_URL'], ctx.obj['TOKEN']) as client:
            status = await client.get_job_status(job_id)
            click.echo(status)

    asyncio.run(_job_status())


@cli.command()
@click.argument('job-id', required=True)
@click.argument('output-dir', required=True,
                type=click.Path(file_okay=False, dir_okay=True))
@click.pass_context
def download_results(ctx, job_id, output_dir):
    """Download results of a completed job."""
    async def _download_results():
        async with UWSClient(ctx.obj['BASE_URL'], ctx.obj['TOKEN']) as client:
            results = await client.get_job_results(job_id)
            for i, result in enumerate(results):
                if result.get('href'):
                    output_path = f"{output_dir}/result_{i}.fits"
                    await client.download_result(result['href'], output_path)
                    click.echo(f"Downloaded result to {output_path}")

    asyncio.run(_download_results())


@cli.command()
@click.argument('job-id', required=True)
@click.option('--timeout', default=3600,
              help='Maximum wait time in seconds')
@click.option('--poll-interval', default=10,
              help='Time between status checks in seconds')
@click.pass_context
def wait_for_completion(ctx, job_id, timeout, poll_interval):
    """Wait for a job to complete."""
    async def _wait_for_completion():
        async with UWSClient(ctx.obj['BASE_URL'], ctx.obj['TOKEN']) as client:
            status = await client.wait_for_job_completion(job_id,
                                                          timeout,
                                                          poll_interval)
            click.echo(f"Job completed with phase: {status['phase']}")

    asyncio.run(_wait_for_completion())


if __name__ == '__main__':
    cli()
