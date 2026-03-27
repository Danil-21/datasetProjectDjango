from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional


# ---------- PROJECT ----------
class ProjectCreate(BaseModel):
    name: str
    description: str
    data_type: str = "text"       # text / csv / json
    labeling_type: str = "ner"
    instruction: str = ""
    source_name: str = ""


class ProjectResponse(ProjectCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- TASK ----------
class TaskResponse(BaseModel):
    id: int
    project_id: int
    text: str
    status: str
    suggested_label: Optional[str] = None
    final_label: Optional[str] = None
    annotator_comment: Optional[str] = None

    assigned_to: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- ANNOTATION ----------
class AnnotationCreate(BaseModel):
    labels: List[Dict]


class AnnotationResponse(BaseModel):
    id: int
    task_id: int
    labels: List[Dict]

    model_config = ConfigDict(from_attributes=True)


# ---------- DATASET UPLOAD ----------
class UploadRequest(BaseModel):
    content: str
    format: str = "text"                 # text / csv / json

    # для text
    split_mode: str = "line"             # line / sentence / paragraph / fixed_chunk
    chunk_size: int = 300                # для fixed_chunk

    # для csv
    text_column: Optional[str] = None

    # для json
    text_field: Optional[str] = None


class UploadPreviewResponse(BaseModel):
    format: str
    split_mode: Optional[str] = None

    total_raw_items: int
    valid_items: int
    empty_removed: int
    duplicates_removed: int

    preview_items: List[str]
    warnings: List[str] = []


class TaskAnnotationRequest(BaseModel):
    final_label: str
    annotator_comment: Optional[str] = None


class ProjectStatsResponse(BaseModel):
    project_id: int
    project_name: str

    total_tasks: int
    pending_tasks: int
    done_tasks: int

    auto_labeled_tasks: int
    human_verified_tasks: int

    label_distribution: Dict[str, int]


class WorkerCreate(BaseModel):
    name: str
    role: str = "annotator"
    specialization: Optional[str] = None


class WorkerResponse(BaseModel):
    id: int
    name: str
    role: str
    specialization: Optional[str] = None

    class Config:
        orm_mode = True


class TaskAssignRequest(BaseModel):
    worker_id: int


class AnnotationCreate(BaseModel):
    worker_id: int
    label: str
    comment: Optional[str] = None


class AnnotationResponse(BaseModel):
    id: int
    task_id: int
    worker_id: int
    label: str
    comment: Optional[str] = None

    class Config:
        orm_mode = True


class TaskConsensusResponse(BaseModel):
    task_id: int
    total_annotations: int
    label_counts: Dict[str, int]
    consensus_label: Optional[str] = None
    agreement_score: float
    needs_review: bool