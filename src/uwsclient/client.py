from .uws import UWSClient
from typing import List, Optional
import os
import asyncio
from .logger import logger


class SODAClient(UWSClient):
    """Client for performing async SODA cutouts with the Rubin SP"""

    def get_jobs_endpoint(self) -> str:
        """Return the endpoint for SODA job operations.

        Returns
        -------
        str
            The endpoint URL for SODA jobs
        """
        return f"{self.base_url}/api/cutout/jobs"

    async def create_cutout_job(
        self,
        image_ids: List[str],
        *,
        pos: Optional[List[str]] = None,
        circle: Optional[List[str]] = None,
        polygon: Optional[List[str]] = None,
        run_id: Optional[str] = None,
        auto_start: bool = True,
    ) -> str:
        """Create a new async cutout job.

        Parameters
        ----------
        image_ids
            List of image identifiers to cut out from
        pos
            Optional RANGE/CIRCLE/POLYGON position specifications
        circle
            Optional circle cutout specifications
        polygon
            Optional polygon vertex specifications
        run_id
            Optional client-provided job identifier
        auto_start
            Whether to start the job immediately

        Returns
        -------
            Job ID of the created job
        """
        params = {
            "id": image_ids,
        }
        if pos:
            params["pos"] = pos
        if circle:
            params["circle"] = circle
        if polygon:
            params["polygon"] = polygon

        return await self.create_job(params, run_id=run_id, auto_start=auto_start)


async def async_cutout(
    image_ids: List[str],
    token: str,
    circle: Optional[List[str]] = None,
    pos: Optional[List[str]] = None,
    polygon: Optional[List[str]] = None,
    base_url: str = "https://data-dev.lsst.cloud",
    output_dir: str = ".",
    run_id: Optional[str] = None,
) -> None:
    """Async function to perform the cutout operation.

    Parameters
    ----------
    image_ids
        List of image identifiers to cut out from
    circle
        Optional circle cutout specifications
    pos
        Optional RANGE/CIRCLE/POLYGON position specifications
    polygon
        Optional polygon vertex specifications
    base_url
        Base URL of the SODA service
    token
        Authentication token for the service
    output_dir
        Output directory for cutout files
    run_id
        Optional client-provided job identifier
    """
    client = SODAClient(base_url=base_url, token=token)

    try:
        job_id = await client.create_cutout_job(
            image_ids=image_ids,
            circle=circle,
            pos=pos,
            polygon=polygon,
            run_id=run_id,
            auto_start=True,
        )
        logger.info(f"Created job {job_id}")

        while True:
            status = await client.get_job_status(job_id)
            phase = status.get("phase")
            logger.info(f"Job status: {phase}")

            if phase == "COMPLETED":
                results = await client.get_job_results(job_id)
                logger.info(f"Got {len(results)} results")

                for i, result in enumerate(results):
                    output_path = os.path.join(output_dir, f"cutout_{i}.fits")
                    await client.download_result(result["href"], output_path)
                break

            elif phase in ("ERROR", "ABORTED"):
                error_msg = f"Job failed with phase {phase}"
                logger.error(error_msg)
                raise Exception(error_msg)

            await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"Error during cutout process: {str(e)}")
        raise
