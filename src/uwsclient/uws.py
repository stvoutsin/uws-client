import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any, Union
from .logger import logger
import os
from abc import ABC, abstractmethod


class UWSClient(ABC):
    """Base client for interacting with UWS services."""

    def __init__(self, base_url: str, token: str):
        """Initialize the client.

        Parameters
        ----------
        base_url
            Base URL of the UWS service
        token
            Authentication token for the service
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/xml",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _prepare_form_data(
        self, params: Dict[str, Union[List[str], str]]
    ) -> Dict[str, Union[List[str], str]]:
        """Prepare parameters for form encoding."""
        form_data: Dict[str, Union[List[str], str]] = {}

        for key, value in params.items():
            if isinstance(value, list):
                form_data[key] = list(str(v) for v in value)
            elif value is not None:
                form_data[key] = str(value)

        return form_data

    def _parse_uws_response(self, xml_text: str) -> Dict[str, Any]:
        """Parse a UWS XML response into a dictionary.

        Parameters
        ----------
        xml_text
            XML response text from the UWS service

        Returns
        -------
            Dictionary containing the parsed job information
        """
        root = ET.fromstring(xml_text)

        ns = {
            "uws": "http://www.ivoa.net/xml/UWS/v1.0",
            "xlink": "http://www.w3.org/1999/xlink",
        }

        def find_text(elem: str) -> Optional[str]:
            """Helper to find element text with namespace."""
            element = root.find(f"uws:{elem}", ns)
            return element.text if element is not None else None

        result: Dict[str, Any] = {
            "job_id": find_text("jobId"),
            "run_id": find_text("runId"),
            "owner_id": find_text("ownerId"),
            "phase": find_text("phase"),
            "creation_time": find_text("creationTime"),
            "start_time": find_text("startTime"),
            "end_time": find_text("endTime"),
            "execution_duration": find_text("executionDuration"),
            "destruction": find_text("destruction"),
        }

        params_elem = root.find("uws:parameters", ns)
        if params_elem is not None:
            parameters = {}
            for param in params_elem.findall("uws:parameter", ns):
                param_id = param.get("id")
                if param_id:
                    parameters[param_id] = {
                        "value": param.text,
                        "by_reference": param.get("byReference"),
                        "is_post": param.get("isPost"),
                    }
            result["parameters"] = parameters

        results_elem = root.find("uws:results", ns)
        if results_elem is not None:
            results = []
            for result_elem in results_elem.findall("uws:result", ns):
                result_info = {
                    "id": result_elem.get("id"),
                    "href": result_elem.get(f'{{{ns["xlink"]}}}href'),
                    "mime_type": result_elem.get("mime-type"),
                }
                results.append(result_info)
            result["results"] = results

        return result

    @abstractmethod
    def get_jobs_endpoint(self) -> str:
        """Return the endpoint for job operations.

        Returns
        -------
        str
            The endpoint URL for job operations
        """
        pass

    async def create_job(
        self, params: Dict, run_id: Optional[str] = None, auto_start: bool = True
    ) -> str:
        """Create a new UWS job.

        Parameters
        ----------
        params
            Job parameters
        run_id
            Optional client-provided run identifier
        auto_start
            Whether to start the job immediately

        Returns
        -------
        str
            Job ID of the created job
        """
        if run_id:
            params["runid"] = run_id
        if auto_start:
            params["phase"] = "RUN"

        form_data = self._prepare_form_data(params)
        logger.debug(f"Submitting job with parameters: {params}")

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(
                self.get_jobs_endpoint(), data=form_data, allow_redirects=False
            ) as response:
                if response.status == 303:
                    location = response.headers.get("Location", "")
                    job_id = location.split("/")[-1]
                    logger.debug(f"Job created with ID: {job_id}")
                    return job_id
                else:
                    text = await response.text()
                    logger.error(f"Failed to create job: {text}")
                    raise Exception(f"Failed to create job: {text}")

    async def get_job_status(self, job_id: str) -> dict:
        """Get the current status of a job.

        Parameters
        ----------
        job_id
            ID of the job to check

        Returns
        -------
            Dictionary containing job status information
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"{self.get_jobs_endpoint()}/{job_id}") as response:
                if response.status == 200:
                    xml_text = await response.text()
                    return self._parse_uws_response(xml_text)
                else:
                    text = await response.text()
                    raise Exception(
                        f"Failed to get job status: " f"{response.status} {text}"
                    )

    async def get_job_results(self, job_id: str) -> List[dict]:
        """Get the results of a completed job.

        Parameters
        ----------
        job_id
            ID of the completed job

        Returns
        -------
            List of result references containing download URLs
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"{self.get_jobs_endpoint()}/{job_id}") as response:
                if response.status == 200:
                    xml_text = await response.text()
                    job_info = self._parse_uws_response(xml_text)
                    return job_info.get("results", [])
                else:
                    text = await response.text()
                    raise Exception(f"Failed to get results: {text}")

    async def download_result(self, result_url: str, output_path: str) -> None:
        """Download a job result to a file.

        Parameters
        ----------
        result_url
            URL of the result to download
        output_path
            Path where the file should be saved
        """
        abs_output_path = os.path.abspath(output_path)

        os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)
        headers = self.headers.copy()
        headers.pop("Accept")

        logger.info(f"Downloading result to: {abs_output_path}")

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(result_url) as response:
                if response.status == 200:
                    with open(abs_output_path, "wb") as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    logger.info(f"Successfully downloaded to: {abs_output_path}")
                else:
                    error = await response.text()
                    logger.error(f"Failed to download result: {error}")
                    raise Exception(f"Failed to download result: {error}")
