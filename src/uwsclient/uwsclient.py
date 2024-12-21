from __future__ import annotations

import requests
import logging
import time
from typing import Optional, Dict, Any, Union, List, TypeAlias
import xml.etree.ElementTree as ET
import os
from .models import UWSPhase

Params: TypeAlias = Dict[str, Union[str, List[str]]]
JobStatus: TypeAlias = Dict[str, Any]
ResultInfo: TypeAlias = Dict[str, str]


class UWSClient:
    """A client for interacting with Universal Worker Service (UWS) servers.

    This client provides methods to create jobs, monitor their status,
    and retrieve results from a UWS service. It uses synchronous HTTP requests
    and can be used in any Python environment.

    Attributes
    ----------
    base_url : str
        Base URL of the UWS service
    headers : dict
        HTTP headers used for all requests
    session : requests.Session
        HTTP session for making requests
    logger : logging.Logger
        Logger instance for this client
    """

    def __init__(self, base_url: str, token: str) -> None:
        """Initialize a new UWS client.

        Parameters
        ----------
        base_url
            Base URL of the UWS service. Trailing slashes will be stripped.
        token
            Authentication token for the service. Will be included as a Bearer token
            in request headers.

        Notes
        -----
        The client automatically creates a requests.Session object that will be
        used for all HTTP requests. This session should be closed using the
        close() method when the client is no longer needed.
        """
        self.base_url: str = base_url.rstrip("/")
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/xml",
        }
        self.session: requests.Session = requests.Session()
        self.session.headers.update(self.headers)
        self.logger: logging.Logger = logging.getLogger(__name__)

    def close(self) -> None:
        """Close the client's HTTP session.

        This method should be called when the client is no longer needed to
        ensure proper cleanup of resources.
        """
        self.session.close()

    @staticmethod
    def _parse_uws_response(xml_text: str) -> JobStatus:
        """Parse a UWS XML response into a dictionary.

        Parameters
        ----------
        xml_text
            XML response from the UWS service

        Returns
        -------
        dict
            Dictionary containing the parsed job information
        """
        root = ET.fromstring(xml_text)
        ns = {
            "uws": "http://www.ivoa.net/xml/UWS/v1.0",
            "xlink": "http://www.w3.org/1999/xlink",
        }

        def find_text(elem: str) -> Optional[str]:
            element = root.find(f"uws:{elem}", ns)
            return element.text if element is not None else None

        job: JobStatus = {
            "job_id": find_text("jobId"),
            "phase": find_text("phase"),
            "run_id": find_text("runId"),
            "owner_id": find_text("ownerId"),
            "creation_time": find_text("creationTime"),
            "start_time": find_text("startTime"),
            "end_time": find_text("endTime"),
            "execution_duration": find_text("executionDuration"),
            "destruction": find_text("destruction"),
            "results": [],
        }

        results_elem = root.find("uws:results", ns)
        if results_elem is not None:
            results: List[ResultInfo] = []
            for result_elem in results_elem.findall("uws:result", ns):
                result_info = {
                    "id": result_elem.get("id", ""),
                    "href": result_elem.get(f'{{{ns["xlink"]}}}href', ""),
                    "mime_type": result_elem.get("mime-type", ""),
                }
                results.append(result_info)
            job["results"] = results

        return job

    def create_job(
        self, params: Params, run_id: Optional[str] = None, auto_start: bool = True
    ) -> str:
        """Create a new UWS job.

        Parameters
        ----------
        params
            Dictionary of job parameters. The exact parameters depend on the
            UWS service being used.
        run_id
            Client-provided identifier for the job
        auto_start
            Whether to start the job immediately

        Returns
        -------
        str
            The job identifier assigned by the server

        Raises
        ------
        requests.RequestException
            If the HTTP request fails
        Exception
            If job creation fails for any other reason
        """
        if run_id:
            params["runid"] = run_id
        if auto_start:
            params["phase"] = "RUN"

        self.logger.debug(f"Creating job with parameters: {params}")
        resp = self.session.post(
            f"{self.base_url}/jobs", data=params, allow_redirects=False
        )

        if resp.status_code == 303:
            location = resp.headers.get("Location", "")
            job_id = location.split("/")[-1]
            self.logger.debug(f"Created job: {job_id}")
            return job_id
        else:
            raise Exception(f"Failed to create job: {resp.status_code} {resp.text}")

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get the current status of a job.

        Parameters
        ----------
        job_id
            Job identifier

        Returns
        -------
        dict
            Dictionary containing job status information

        Raises
        ------
        requests.RequestException
            If the HTTP request fails
        Exception
            If status retrieval fails for any other reason
        """
        resp = self.session.get(f"{self.base_url}/jobs/{job_id}")
        if resp.status_code == 200:
            return UWSClient._parse_uws_response(resp.text)
        else:
            raise Exception(f"Failed to get job status: {resp.status_code} {resp.text}")

    def get_job_results(self, job_id: str) -> List[ResultInfo]:
        """Get the results of a completed job.

        Parameters
        ----------
        job_id
            Job identifier

        Returns
        -------
        list
            List of dictionaries containing result information

        Raises
        ------
        requests.RequestException
            If the HTTP request fails
        Exception
            If result retrieval fails for any other reason
        """
        status = self.get_job_status(job_id)
        return status.get("results", [])

    def download_result(self, result_url: str, output_path: str) -> None:
        """Download a job result to a file.

        Parameters
        ----------
        result_url
            URL where the result can be downloaded
        output_path
            Path where the file should be saved. Parent directories will be
            created if they don't exist.

        Raises
        ------
        requests.RequestException
            If the HTTP request fails
        IOError
            If there are problems writing the file
        Exception
            If download fails for any other reason
        """
        abs_output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)

        self.logger.info(f"Downloading result to: {abs_output_path}")
        with self.session.get(result_url, stream=True) as resp:
            if resp.status_code == 200:
                with open(abs_output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.logger.info(f"Successfully downloaded to: {abs_output_path}")
            else:
                raise Exception(
                    f"Failed to download result: {resp.status_code} {resp.text}"
                )

    def wait_for_job_completion(
        self, job_id: str, timeout: int = 3600, poll_interval: int = 10
    ) -> JobStatus:
        """Wait for a job to complete.

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
        dict
            Final job status

        Raises
        ------
        TimeoutError
            If job does not complete within timeout period
        requests.RequestException
            If HTTP requests fail
        Exception
            If status checks fail for any other reason

        Notes
        -----
        The method considers a job complete when its phase is one of:
        COMPLETED, ERROR, or ABORTED
        """
        start_time = time.time()

        while True:
            status = self.get_job_status(job_id)
            phase = UWSPhase(status.get("phase", "UNKNOWN"))
            self.logger.info(f"Current phase: {phase}")

            if phase in (UWSPhase.COMPLETED, UWSPhase.ERROR, UWSPhase.ABORTED):
                return status

            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Job {job_id} did not complete within {timeout} seconds"
                )

            time.sleep(poll_interval)
