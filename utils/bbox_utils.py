"""Bounding box utility functions."""

from typing import List, Tuple


def expand_bbox(bbox: List[float], padding: float = 0.5) -> List[float]:
    """
    Expand bounding box by padding amount.

    Args:
        bbox: [x0, y0, x1, y1] coordinates
        padding: Amount to expand in each direction

    Returns:
        Expanded bbox coordinates
    """
    if len(bbox) != 4:
        raise ValueError(f"Invalid bbox format: {bbox}. Expected [x0, y0, x1, y1]")

    x0, y0, x1, y1 = bbox
    return [
        x0 - padding,
        y0 - padding,
        x1 + padding,
        y1 + padding
    ]


def bbox_area(bbox: List[float]) -> float:
    """
    Calculate area of bounding box.

    Args:
        bbox: [x0, y0, x1, y1] coordinates

    Returns:
        Area in square units
    """
    if len(bbox) != 4:
        raise ValueError(f"Invalid bbox format: {bbox}")

    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0
    return width * height


def bbox_overlap(bbox1: List[float], bbox2: List[float]) -> float:
    """
    Calculate overlap area between two bounding boxes.

    Args:
        bbox1: First bbox [x0, y0, x1, y1]
        bbox2: Second bbox [x0, y0, x1, y1]

    Returns:
        Overlap area
    """
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2

    # Calculate intersection
    x0_i = max(x0_1, x0_2)
    y0_i = max(y0_1, y0_2)
    x1_i = min(x1_1, x1_2)
    y1_i = min(y1_1, y1_2)

    if x1_i <= x0_i or y1_i <= y0_i:
        return 0.0

    return (x1_i - x0_i) * (y1_i - y0_i)


def bbox_iou(bbox1: List[float], bbox2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) for two bounding boxes.

    Args:
        bbox1: First bbox [x0, y0, x1, y1]
        bbox2: Second bbox [x0, y0, x1, y1]

    Returns:
        IoU value between 0 and 1
    """
    overlap = bbox_overlap(bbox1, bbox2)
    if overlap == 0:
        return 0.0

    area1 = bbox_area(bbox1)
    area2 = bbox_area(bbox2)
    union = area1 + area2 - overlap

    return overlap / union if union > 0 else 0.0


def bbox_contains_point(bbox: List[float], x: float, y: float) -> bool:
    """
    Check if point is inside bounding box.

    Args:
        bbox: [x0, y0, x1, y1] coordinates
        x: Point x coordinate
        y: Point y coordinate

    Returns:
        True if point is inside bbox
    """
    x0, y0, x1, y1 = bbox
    return x0 <= x <= x1 and y0 <= y <= y1


def normalize_bbox(bbox: List[float], page_width: float, page_height: float) -> List[float]:
    """
    Normalize bbox coordinates to [0, 1] range.

    Args:
        bbox: [x0, y0, x1, y1] coordinates
        page_width: PDF page width
        page_height: PDF page height

    Returns:
        Normalized bbox coordinates
    """
    x0, y0, x1, y1 = bbox
    return [
        x0 / page_width,
        y0 / page_height,
        x1 / page_width,
        y1 / page_height
    ]


def denormalize_bbox(bbox: List[float], page_width: float, page_height: float) -> List[float]:
    """
    Denormalize bbox coordinates from [0, 1] range.

    Args:
        bbox: Normalized [x0, y0, x1, y1] coordinates
        page_width: PDF page width
        page_height: PDF page height

    Returns:
        Absolute bbox coordinates
    """
    x0, y0, x1, y1 = bbox
    return [
        x0 * page_width,
        y0 * page_height,
        x1 * page_width,
        y1 * page_height
    ]


def merge_bboxes(bboxes: List[List[float]]) -> List[float]:
    """
    Merge multiple bounding boxes into one encompassing box.

    Args:
        bboxes: List of [x0, y0, x1, y1] coordinates

    Returns:
        Merged bbox encompassing all input boxes
    """
    if not bboxes:
        raise ValueError("Cannot merge empty list of bboxes")

    x0_min = min(bbox[0] for bbox in bboxes)
    y0_min = min(bbox[1] for bbox in bboxes)
    x1_max = max(bbox[2] for bbox in bboxes)
    y1_max = max(bbox[3] for bbox in bboxes)

    return [x0_min, y0_min, x1_max, y1_max]


def bbox_center(bbox: List[float]) -> Tuple[float, float]:
    """
    Calculate center point of bounding box.

    Args:
        bbox: [x0, y0, x1, y1] coordinates

    Returns:
        Tuple of (center_x, center_y)
    """
    x0, y0, x1, y1 = bbox
    return ((x0 + x1) / 2, (y0 + y1) / 2)
