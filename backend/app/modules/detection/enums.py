import enum


class DetectionSource(str, enum.Enum):
    DETECTED = "DETECTED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
    MANUAL_PROVIDED = "MANUAL_PROVIDED"
