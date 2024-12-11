# UWS Cutout Client Library

A Python library for interacting with Universal Worker Service (UWS) services, with specific implementation for SODA cutouts in the Rubin Science Platform.

## Installation

```bash
pip install .
```

## Usage

The library provides two ways to interact with the SODA service:

### 1. High-level Interface

Use the `async_cutout()` function for a simple, straightforward way to perform cutouts:

```python
import asyncio
from uwsclient import async_cutout

async def main():
    # Perform a cutout using circle parameters
    cutout_files = await async_cutout(
        image_ids=["butler://dp02/.."],
        token="your_token_here",
        circle=["55.7467 -32.2862 0.05"],
        output_dir="./cutouts"
    )
    print(f"Created cutouts: {cutout_files}")

# Run the async function
asyncio.run(main())
```

### 2. Low-level Interface

Use the `SODAClient` class directly for more control over the cutout process:

```python
import asyncio
from uwsclient import SODAClient

async def advanced_usage():
    # Initialize the client
    client = SODAClient(
        base_url="https://data-dev.lsst.cloud",
        token="your_token_here"
    )

    # Create a cutout job
    job_id = await client.create_cutout_job(
        image_ids=["butler://dp02/..."],
        circle=["55.7467 -32.2862 0.05"]
    )

    # Monitor job status
    while True:
        status = await client.get_job_status(job_id)
        print(f"Job status: {status.get('phase')}")

        if status.get('phase') == 'COMPLETED':
            # Get job results
            results = await client.get_job_results(job_id)

            # Download results
            for i, result in enumerate(results):
                await client.download_result(
                    result["href"],
                    f"cutout_{i}.fits"
                )
            break

        elif status.get('phase') in ('ERROR', 'ABORTED'):
            raise Exception(f"Job failed: {status}")

        await asyncio.sleep(5)

# Run the async function
asyncio.run(advanced_usage())
```
### Cutout Specific Parameters

- image_ids: List of butler URIs for images
- circle: Optional circle cutout specifications
- pos: Optional position specifications
- polygon: Optional polygon specifications


### Command Line Interface Parameters

```bash
vo-cutout [OPTIONS] IMAGE_IDS...

Options:
  -c, --circle TEXT     Circle cutout specification in format "RA DEC RADIUS"
  -p, --pos TEXT       Position cutout specification
  --polygon TEXT       Polygon cutout specification
  --base-url TEXT      Base URL for the SODA service [default: https://data-dev.lsst.cloud]
  --token TEXT         Authentication token (can also be set via RUBIN_TOKEN environment variable)
  -o, --output-dir PATH  Output directory for cutout files [default: .]
  --run-id TEXT        Optional client-provided job identifier
  --debug / --no-debug  Enable debug logging
  --help              Show this message and exit
```

### Command Line Examples

```bash
# Using circle parameters
vo-cutout --circle "55.7467 -32.2862 0.05" \
    butler://dp02/..

# Specifying output directory
vo-cutout -o ./cutouts --circle "55.7467 -32.2862 0.05" \
    butler://dp02/..

# Using environment variable for token
export RUBIN_TOKEN="your_token_here"
vo-cutout --circle "55.7467 -32.2862 0.05" \
    butler://dp02/..
```

## Authentication

The library requires a token for authentication. You can provide it in several ways:

1. Directly in the code when using the Python interface
2. Via the `--token` option in the CLI
3. Via the `RUBIN_TOKEN` environment variable

## License

This project is licensed under the GNU General Public License - see the LICENSE file for details.
