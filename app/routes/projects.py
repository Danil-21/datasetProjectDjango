import json, csv
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO
from app.database import get_db
from app import crud, schemas

router = APIRouter()


@router.post("/", response_model=schemas.ProjectResponse)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    return crud.create_project(db, project)


@router.get("/", response_model=List[schemas.ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    return crud.get_projects(db)


@router.post("/workers", response_model=schemas.WorkerResponse)
def create_worker(worker: schemas.WorkerCreate, db: Session = Depends(get_db)):
    """
    Создать нового исполнителя.
    """
    return crud.create_worker(db, worker)


@router.get("/workers", response_model=List[schemas.WorkerResponse])
def get_all_workers(db: Session = Depends(get_db)):
    """
    Получить список всех исполнителей.
    """
    return crud.get_workers(db)


@router.get("/{project_id}", response_model=schemas.ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/preview-upload", response_model=schemas.UploadPreviewResponse)
def preview_project_upload(project_id: int, upload: schemas.UploadRequest, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return crud.preview_upload(upload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/upload", response_model=List[schemas.TaskResponse])
def upload_project_data(project_id: int, upload: schemas.UploadRequest, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return crud.upload_data(db, project_id, upload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/tasks", response_model=List[schemas.TaskResponse])
def get_project_tasks(project_id: int, db: Session = Depends(get_db)):
    return crud.get_project_tasks(db, project_id)


@router.get("/{project_id}/stats")
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    return crud.get_project_stats(db, project_id)


@router.post("/{project_id}/preview-file", response_model=schemas.UploadPreviewResponse)
async def preview_project_file_upload(
    project_id: int,
    file: UploadFile = File(...),
    format: str = Form(...),              # text / csv / json
    split_mode: str = Form("line"),       # только для text
    chunk_size: int = Form(300),          # только для fixed_chunk
    text_column: str = Form(None),        # для csv
    text_field: str = Form(None),         # для json
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # content = (await file.read()).decode("utf-8")
    file_bytes = await file.read()
    content = crud.decode_uploaded_file(file_bytes)

    upload = crud.build_upload_request_from_file_content(
        content=content,
        file_format=format,
        split_mode=split_mode,
        chunk_size=chunk_size,
        text_column=text_column,
        text_field=text_field
    )

    try:
        return crud.preview_upload(upload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/{project_id}/upload-file", response_model=List[schemas.TaskResponse])
async def upload_project_file(
    project_id: int,
    file: UploadFile = File(...),
    format: str = Form(...),              # text / csv / json
    split_mode: str = Form("line"),       # только для text
    chunk_size: int = Form(300),          # только для fixed_chunk
    text_column: str = Form(None),        # для csv
    text_field: str = Form(None),         # для json
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # content = (await file.read()).decode("utf-8")
    file_bytes = await file.read()
    content = crud.decode_uploaded_file(file_bytes)

    upload = crud.build_upload_request_from_file_content(
        content=content,
        file_format=format,
        split_mode=split_mode,
        chunk_size=chunk_size,
        text_column=text_column,
        text_field=text_field
    )

    try:
        return crud.upload_data(db, project_id, upload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# Позволяет нажать кнопку и сказать 'Предложи label для этой задачи'
@router.post("/tasks/{task_id}/auto-label", response_model=schemas.TaskResponse)
def auto_label_single_task(task_id: int, db: Session = Depends(get_db)):
    """
    Автоматическая предразметка одной задачи.
    """
    task = crud.auto_label_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.post("/tasks/{task_id}/annotations", response_model=schemas.AnnotationResponse)
def create_task_annotation(
    task_id: int,
    annotation: schemas.AnnotationCreate,
    db: Session = Depends(get_db)
):
    """
    Добавить независимую разметку задачи от исполнителя.
    """
    result = crud.create_annotation(db, task_id, annotation)

    if result is None:
        raise HTTPException(status_code=404, detail="Task or Worker not found")

    if result == "already_exists":
        raise HTTPException(status_code=400, detail="This worker already annotated this task")

    return result


@router.get("/tasks/{task_id}/annotations", response_model=List[schemas.AnnotationResponse])
def get_task_annotations(task_id: int, db: Session = Depends(get_db)):
    """
    Получить все независимые разметки задачи.
    """
    return crud.get_annotations_for_task(db, task_id)


@router.get("/tasks/{task_id}/consensus", response_model=schemas.TaskConsensusResponse)
def get_task_consensus(task_id: int, db: Session = Depends(get_db)):
    """
    Получить consensus и оценку согласованности по задаче.
    """
    result = crud.get_task_consensus(db, task_id)

    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    return result


# берёт все задачи проекта и всем проставляет suggested_label
@router.post("/{project_id}/auto-label", response_model=List[schemas.TaskResponse])
def auto_label_project(project_id: int, db: Session = Depends(get_db)):
    """
    Автоматическая предразметка всех задач проекта.
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return crud.auto_label_project_tasks(db, project_id)


@router.post("/{project_id}/auto-assign", response_model=List[schemas.TaskResponse])
def auto_assign_project_tasks(project_id: int, db: Session = Depends(get_db)):
    """
    Автоматически распределить задачи проекта между исполнителями
    по специализации.
    """
    assigned_tasks = crud.auto_assign_tasks_by_specialization(db, project_id)

    if assigned_tasks is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return assigned_tasks


@router.post("/tasks/{task_id}/annotate", response_model=schemas.TaskResponse)
def annotate_single_task(
    task_id: int,
    annotation: schemas.TaskAnnotationRequest,
    db: Session = Depends(get_db)
):
    """
    Ручная разметка / подтверждение задачи человеком.
    """
    task = crud.annotate_task(db, task_id, annotation)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.get("/{project_id}/stats", response_model=schemas.ProjectStatsResponse)
def get_project_statistics(project_id: int, db: Session = Depends(get_db)):
    """
    Получить статистику и прогресс по проекту.
    """
    stats = crud.get_project_stats(db, project_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Project not found")

    return stats


@router.get("/{project_id}/export/json")
def export_project_json(project_id: int, db: Session = Depends(get_db)):
    """
    Экспорт готового датасета проекта в JSON.
    """
    export_result = crud.get_export_dataset(db, project_id)

    if not export_result:
        raise HTTPException(status_code=404, detail="Project not found")

    json_content = json.dumps(export_result["items"], ensure_ascii=False, indent=2)

    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="project_{project_id}_dataset.json"'
        }
    )


@router.get("/{project_id}/export/csv")
def export_project_csv(project_id: int, db: Session = Depends(get_db)):
    """
    Экспорт готового датасета проекта в CSV.
    """
    export_result = crud.get_export_dataset(db, project_id)

    if not export_result:
        raise HTTPException(status_code=404, detail="Project not found")

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "text", "suggested_label", "final_label", "status", "annotator_comment"]
    )

    writer.writeheader()
    writer.writerows(export_result["items"])

    csv_content = output.getvalue()

    # Добавляем BOM для корректного открытия UTF-8 CSV в Excel / Windows
    csv_with_bom = "\ufeff" + csv_content

    return StreamingResponse(
        iter([csv_with_bom]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="project_{project_id}_dataset.csv"'
        }
    )


@router.post("/tasks/{task_id}/assign", response_model=schemas.TaskResponse)
def assign_task(
    task_id: int,
    assignment: schemas.TaskAssignRequest,
    db: Session = Depends(get_db)
):
    """
    Назначить задачу исполнителю.
    """
    task = crud.assign_task_to_worker(db, task_id, assignment.worker_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task or Worker not found")

    return task


@router.get("/workers/{worker_id}/tasks", response_model=List[schemas.TaskResponse])
def get_worker_tasks(worker_id: int, db: Session = Depends(get_db)):
    """
    Получить все задачи, назначенные исполнителю.
    """
    worker = crud.get_worker(db, worker_id)

    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    return crud.get_tasks_for_worker(db, worker_id)