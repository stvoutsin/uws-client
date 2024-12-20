from __future__ import annotations

import aiohttp
import logging
import asyncio
from models import UWSPhase
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, Union, List
import os
from logger import logger


class UWSClient:
    """A client for interacting with Universal Worker Service (UWS) servers.
    This client provides methods to create jobs, monitor their status,
    and retrieve results.

    The client should be used as an async context manager to ensure proper
    resource cleanup.
    """

    def __init__(self, base_url: str, token: str) -> None:
        """Initialize a new UWS client.

        Parameters
        ----------
        base_url
            Base URL of the UWS service
        token
            Authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/xml"
        }
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self) -> UWSClient:
        """Enter the async context manager.

        Creates and initializes the HTTP session.

        Returns
        -------
        self
            The initialized UWS client
        """
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type: Optional[type],
                        exc_val: Optional[Exception],
                        exc_tb: Optional[Any]) -> None:
        """Exit the async context manager.

        Ensures the HTTP session is properly closed.

        Parameters
        ----------
        exc_type
            The type of the raised exception, if any
        exc_val
            The instance of the raised exception, if any
        exc_tb
            The traceback of the raised exception, if any
        """
        if self.session:
            await self.session.close()

    def _check_session(self) -> None:
        """Check if the session is initialized.

        Raises
        ------
        RuntimeError
            If the client is not used as a context manager
        """
        if self.session is None:
            raise RuntimeError("UWSClient must be used as an "
                               "async context manager")

    @staticmethod
    def _parse_uws_response(xml_text: str) -> Dict[str, Any]:
        """Parse a UWS XML response into a dictionary.

        Parameters
        ----------
        xml_text
            XML response from the UWS service

        Returns
        -------
        Dictionary containing the parsed job information
        """
        root = ET.fromstring(xml_text)
        ns = {
            "uws": "http://www.ivoa.net/xml/UWS/v1.0",
            "xlink": "http://www.w3.org/1999/xlink"
        }

        def find_text(elem: str) -> Optional[str]:
            element = root.find(f"uws:{elem}", ns)
            return element.text if element is not None else None

        job: Dict[str, str | List | Any] = {
            "job_id": find_text("jobId"),
            "phase": find_text("phase"),
            "run_id": find_text("runId"),
            "owner_id": find_text("ownerId"),
            "creation_time": find_text("creationTime"),
            "start_time": find_text("startTime"),
            "end_time": find_text("endTime"),
            "execution_duration": find_text("executionDuration"),
            "destruction": find_text("destruction"),
            "results": []
        }

        results_elem = root.find("uws:results", ns)
        if results_elem is not None:
            results = []
            for result_elem in results_elem.findall("uws:result", ns):
                result_info = {
                    "id": result_elem.get("id"),
                    "href": result_elem.get(f'{{{ns["xlink"]}}}href'),
                    "mime_type": result_elem.get("mime-type")
                }
                results.append(result_info)
            job["results"] = results

        return job

    async def create_job(self,
                         params: Dict[str, Union[str, List[str]]],
                         run_id: Optional[str] = None,
                         auto_start: bool = True) -> str:
        """Create a new UWS job.

        Parameters
        ----------
        params
            Job parameters
        run_id
            Optional client-provided identifier
        auto_start
            Whether to start the job immediately

        Returns
        -------
        The job identifier

        Raises
        ------
        Exception
            If job creation fails
        RuntimeError
            If client is not used as context manager
        """
        self._check_session()

        if run_id:
            params["runid"] = run_id
        if auto_start:
            params["phase"] = "RUN"

        self.logger.debug(f"Creating job with parameters: {params}")
        async with self.session.post(f"{self.base_url}/jobs",    # type: ignore[union-attr]
                                     data=params,
                                     allow_redirects=False) as resp:
            if resp.status == 303:
                location = resp.headers.get("Location", "")
                job_id = location.split("/")[-1]
                self.logger.debug(f"Created job: {job_id}")
                return job_id
            else:
                text = await resp.text()
                raise Exception(f"Failed to create job: {resp.status} {text}")

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the current status of a job.

        Parameters
        ----------
        job_id
            Job identifier

        Returns
        -------
        Dictionary containing job status information

        Raises
        ------
        Exception
            If status retrieval fails
        RuntimeError
            If client is not used as context manager
        """
        self._check_session()

        async with self.session.get(f"{self.base_url}/jobs/{job_id}") as resp:     # type: ignore[union-attr]
            if resp.status == 200:
                text = await resp.text()
                return UWSClient._parse_uws_response(text)
            else:
                text = await resp.text()
                raise Exception(f"Failed to get job status: {resp.status} "
                                f"{text}")

    async def get_job_results(self, job_id: str) -> List[Dict[str, str]]:
        """Get the results of a completed job.

        Parameters
        ----------
        job_id
            Job identifier

        Returns
        -------
        List of result references containing download URLs

        Raises
        ------
        Exception
            If result retrieval fails
        RuntimeError
            If client is not used as context manager
        """
        self._check_session()
        status = await self.get_job_status(job_id)
        return status.get("results", [])

    async def download_result(self, result_url: str, output_path: str) -> None:
        """Download a job result to a file.

        Parameters
        ----------
        result_url
            URL of the result to download
        output_path
            Path where the file should be saved

        Raises
        ------
        Exception
            If download fails
        RuntimeError
            If client is not used as context manager
        """
        self._check_session()

        abs_output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)

        self.logger.info(f"Downloading result to: {abs_output_path}")
        async with self.session.get(result_url) as resp:     # type: ignore[union-attr]
            if resp.status == 200:
                with open(abs_output_path, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
                self.logger.info(f"Successfully downloaded to: "
                                 f"{abs_output_path}")
            else:
                text = await resp.text()
                raise Exception(f"Failed to download result: "
                                f"{resp.status} {text}")

    async def wait_for_job_completion(self,
                                      job_id: str,
                                      timeout: int = 3600,
                                      poll_interval: int = 10) -> (
            Dict)[str, Any]:
        """
        Wait for a job to complete.

        Parameters
        ----------
        job_id
            Job identifier
        timeout
            Maximum time to wait in seconds
        poll_interval
            Time between status checks in seconds

        Returns
        -------
        Final job status

        Raises
        ------
        TimeoutError
            If job does not complete within timeout
        Exception
            If status check fails
        RuntimeError
            If client is not used as context manager
        """
        self._check_session()

        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self.get_job_status(job_id)
            phase = UWSPhase(status.get("phase", "UNKNOWN"))
            self.logger.info(f"Current phase: {phase}")
            if phase in (UWSPhase.COMPLETED, UWSPhase.ERROR, UWSPhase.ABORTED):
                return status

            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"Job {job_id} did not complete within {timeout} seconds"
                )

            await asyncio.sleep(poll_interval)


async def main() -> None:
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

if __name__ == "__main__":
    asyncio.run(main())