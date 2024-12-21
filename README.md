# UWS Cutout Client Library

A Python library for interacting with Universal Worker Service (UWS) services asynchronously.

## Installation

```bash
pip install .
```

## Example Usage

```python

from uwsclient import UWSClient
from uwsclient.models import UWSPhase

# Create client instance
client = UWSClient(
    base_url="https://example.com/cutout/",
    token=""
)

# Cell 2 - Create and submit job
query_params = {
    "circle": "55.7467 -32.2862 0.05",
    "id": ""
}

job_id = client.create_job(query_params)
print(f"Created job: {job_id}")

# Cell 3 - Wait for completion
status = client.wait_for_job_completion(job_id, timeout=300)
print(f"Final status: {status['phase']}")

# Cell 4 - Download results if successful
if status['phase'] == UWSPhase.COMPLETED.value:
    results = client.get_job_results(job_id)
    for i, result in enumerate(results):
        if result.get('href'):
            output_path = f"cutout_result_{i}.fits"
            client.download_result(result['href'], output_path)
            print(f"Downloaded result to {output_path}")

# Cell 5 - Cleanup when done
client.close()
```

## License

This project is licensed under the GNU General Public License - see the LICENSE file for details.
