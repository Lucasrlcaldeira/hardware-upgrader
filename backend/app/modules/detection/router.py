from fastapi import APIRouter, Depends

from app.modules.detection import schemas, service
from app.modules.detection.collectors.base import HardwareCollector

router = APIRouter(prefix="/detection", tags=["detection"])


@router.get("/run", response_model=schemas.DetectionResult)
def get_detection_run(
    collector: HardwareCollector = Depends(service.get_collector),
) -> schemas.DetectionResult:
    return service.run_detection(collector)
