# UWS Cutout Client Library

A Python library for interacting with Universal Worker Service (UWS) services asynchronously.

## Installation

```bash
pip install .
```

## Example Usage

```python

    """Example usage of the UWS client."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    async with UWSClient(
            base_url="https://data-dev.lsst.cloud/api/cutout",
            token=""
    ) as client:
        try:
            # Create job
            job_id = await client.create_job({
                "circle": "",
                "id": ""
            })
            logger(f"Created job: {job_id}")

            # Wait for completion
            status = await client.wait_for_job_completion(job_id, timeout=300)
            logger.info(f"Final status: {status['phase']}")

            # Get and download results if successful
            if status['phase'] == UWSPhase.COMPLETED.value:
                results = await client.get_job_results(job_id)
                for i, result in enumerate(results):
                    if result.get('href'):
                        output_path = f"cutout_result_{i}.fits"
                        await client.download_result(result['href'],
                                                     output_path)
                        logger.info(f"Downloaded result to {output_path}")

        except Exception as e:
            logger.info(f"Error: {e}")
```

## License

This project is licensed under the GNU General Public License - see the LICENSE file for details.
