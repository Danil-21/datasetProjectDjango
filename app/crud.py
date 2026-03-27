import re
import csv
import json
from typing import List
from io import StringIO
from sqlalchemy.orm import Session
from app import models, schemas


# ---------------- PROJECTS ----------------
def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.ProjectDB(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_projects(db: Session):
    return db.query(models.ProjectDB).all()


def get_project(db: Session, project_id: int):
    return db.query(models.ProjectDB).filter(models.ProjectDB.id == project_id).first()


# ---------------- DATASET INGESTION ----------------
def upload_data(db: Session, project_id: int, upload: schemas.UploadRequest):
    texts = parse_upload_content(upload)
    cleaned = clean_text_items(texts)

    new_tasks = []

    for text in cleaned["cleaned_items"]:
        task = models.TaskDB(
            project_id=project_id,
            text=text,
            status="pending"
        )
        db.add(task)
        new_tasks.append(task)

    db.commit()

    for task in new_tasks:
        db.refresh(task)

    return new_tasks


# ---------------- TASKS ----------------
def get_project_tasks(db: Session, project_id: int):
    return db.query(models.TaskDB).filter(models.TaskDB.project_id == project_id).all()


def get_all_tasks(db: Session):
    return db.query(models.TaskDB).all()


def get_next_task(db: Session):
    task = db.query(models.TaskDB).filter(models.TaskDB.status == "pending").first()
    if task:
        task.status = "in_progress"
        db.commit()
        db.refresh(task)
    return task


def get_task(db: Session, task_id: int):
    return db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()


# ---------------- ANNOTATIONS ----------------
# def create_annotation(db: Session, task_id: int, annotation: schemas.AnnotationCreate):
#     db_annotation = models.AnnotationDB(
#         task_id=task_id,
#         labels=annotation.labels
#     )
#     db.add(db_annotation)

#     task = get_task(db, task_id)
#     if task:
#         task.status = "done"

#     db.commit()
#     db.refresh(db_annotation)
#     return db_annotation


# def get_task_annotations(db: Session, task_id: int):
#     return db.query(models.AnnotationDB).filter(models.AnnotationDB.task_id == task_id).all()
# ---------------- ANNOTATIONS ----------------
def create_annotation(db: Session, task_id: int, annotation: schemas.AnnotationCreate):
    """
    Сохраняет независимую разметку задачи от конкретного исполнителя.
    Один worker не может дважды размечать одну и ту же задачу.
    """
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    worker = db.query(models.WorkerDB).filter(models.WorkerDB.id == annotation.worker_id).first()

    if not task or not worker:
        return None

    existing = db.query(models.AnnotationDB).filter(
        models.AnnotationDB.task_id == task_id,
        models.AnnotationDB.worker_id == annotation.worker_id
    ).first()

    if existing:
        return "already_exists"

    db_annotation = models.AnnotationDB(
        task_id=task_id,
        worker_id=annotation.worker_id,
        label=annotation.label,
        comment=annotation.comment
    )

    db.add(db_annotation)

    if task.status == "pending":
        task.status = "in_progress"

    db.commit()
    db.refresh(db_annotation)

    return db_annotation


def get_annotations_for_task(db: Session, task_id: int):
    """
    Возвращает все независимые разметки по задаче.
    """
    return db.query(models.AnnotationDB).filter(
        models.AnnotationDB.task_id == task_id
    ).all()


def get_task_consensus(db: Session, task_id: int):
    """
    Считает consensus по задаче:
    - сколько аннотаций
    - какая метка лидирует
    - нужен ли review
    """
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()

    if not task:
        return None

    annotations = db.query(models.AnnotationDB).filter(
        models.AnnotationDB.task_id == task_id
    ).all()

    total_annotations = len(annotations)

    if total_annotations == 0:
        return {
            "task_id": task_id,
            "total_annotations": 0,
            "label_counts": {},
            "consensus_label": None,
            "agreement_score": 0.0,
            "needs_review": False
        }

    label_counts = {}
    for ann in annotations:
        label_counts[ann.label] = label_counts.get(ann.label, 0) + 1

    consensus_label = max(label_counts, key=label_counts.get)
    top_count = label_counts[consensus_label]

    agreement_score = round(top_count / total_annotations, 2)

    needs_review = agreement_score < 0.8

    return {
        "task_id": task_id,
        "total_annotations": total_annotations,
        "label_counts": label_counts,
        "consensus_label": consensus_label,
        "agreement_score": agreement_score,
        "needs_review": needs_review
    }

# ---------------- STATS ----------------



def decode_uploaded_file(file_bytes: bytes) -> str:
    encodings_to_try = ["utf-8", "utf-8-sig", "cp1251", "latin-1"]

    for encoding in encodings_to_try:
        try:
            content = file_bytes.decode(encoding)
            print(f"File decoded successfully with encoding: {encoding}")
            return content
        except UnicodeDecodeError:
            continue

    raise ValueError("Could not decode uploaded file. Supported encodings: utf-8, utf-8-sig, cp1251")


def parse_upload_content(upload: schemas.UploadRequest):
    texts = []

    # -------- TEXT --------
    if upload.format == "text":
        if upload.split_mode == "line":
            texts = [line.strip() for line in upload.content.splitlines() if line.strip()]

        elif upload.split_mode == "sentence":
            parts = re.split(r"[.!?]\s+|\n", upload.content)
            texts = [part.strip() for part in parts if part.strip()]

        elif upload.split_mode == "paragraph":
            parts = re.split(r"\n\s*\n", upload.content)
            texts = [part.strip() for part in parts if part.strip()]

        elif upload.split_mode == "fixed_chunk":
            content = upload.content.strip()
            chunk_size = max(upload.chunk_size, 50)

            texts = [
                content[i:i + chunk_size].strip()
                for i in range(0, len(content), chunk_size)
                if content[i:i + chunk_size].strip()
            ]

        else:
            raise ValueError("Unsupported split_mode for text upload")

    # -------- CSV --------
    elif upload.format == "csv":
        if not upload.text_column:
            raise ValueError("text_column is required for CSV upload")

        csv_file = StringIO(upload.content)
        sample = upload.content[:1024]

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        csv_file.seek(0)
        reader = csv.DictReader(csv_file, delimiter=delimiter)

        if not reader.fieldnames:
            raise ValueError("CSV file has no headers")

        if upload.text_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{upload.text_column}' not found in CSV. "
                f"Available columns: {reader.fieldnames}"
            )

        for row in reader:
            value = row.get(upload.text_column)

            if value is None:
                continue

            text = str(value).strip()
            if text:
                texts.append(text)

    # -------- JSON --------
    elif upload.format == "json":
        if not upload.text_field:
            raise ValueError("text_field is required for JSON upload")

        data = json.loads(upload.content)

        if not isinstance(data, list):
            raise ValueError("JSON content must be a list of objects")

        for item in data:
            text = str(item.get(upload.text_field, "")).strip()
            if text:
                texts.append(text)

    else:
        raise ValueError("Unsupported upload format")

    return texts


def preview_upload(upload: schemas.UploadRequest):
    texts = parse_upload_content(upload)
    cleaned = clean_text_items(texts)

    return {
        "format": upload.format,
        "split_mode": upload.split_mode if upload.format == "text" else None,
        "total_raw_items": cleaned["total_raw_items"],
        "valid_items": cleaned["valid_items"],
        "empty_removed": cleaned["empty_removed"],
        "duplicates_removed": cleaned["duplicates_removed"],
        "preview_items": cleaned["cleaned_items"][:10],
        "warnings": cleaned["warnings"]
    }


def build_upload_request_from_file_content(
    content: str,
    file_format: str,
    split_mode: str = "line",
    chunk_size: int = 300,
    text_column: str = None,
    text_field: str = None
):
    return schemas.UploadRequest(
        content=content,
        format=file_format,
        split_mode=split_mode,
        chunk_size=chunk_size,
        text_column=text_column,
        text_field=text_field
    )


def clean_text_items(texts: List[str]):
    total_raw_items = len(texts)

    # 1. убрать пустые
    non_empty = [t.strip() for t in texts if t and t.strip()]
    empty_removed = total_raw_items - len(non_empty)

    # 2. убрать дубликаты, сохраняя порядок
    seen = set()
    unique_items = []
    for text in non_empty:
        normalized = text.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_items.append(text)

    duplicates_removed = len(non_empty) - len(unique_items)

    warnings = []
    if empty_removed > 0:
        warnings.append(f"Found and removed {empty_removed} empty items")
    if duplicates_removed > 0:
        warnings.append(f"Found and removed {duplicates_removed} duplicate items")

    return {
        "cleaned_items": unique_items,
        "total_raw_items": total_raw_items,
        "valid_items": len(unique_items),
        "empty_removed": empty_removed,
        "duplicates_removed": duplicates_removed,
        "warnings": warnings
    }


def suggest_label_for_text(text: str) -> str:
    """
    Простейшая AI-like предразметка по ключевым словам.
    Возвращает suggested label для текста.
    """
    text_lower = text.lower()

    # Медицина
    medical_keywords = [
        "пациент", "температура", "кашель", "горло", "врач", "диагноз",
        "болит", "лечение", "симптом", "болезнь"
    ]

    # Технологии
    tech_keywords = [
        "apple", "google", "microsoft", "iphone", "android", "windows",
        "приложение", "сервер", "код", "ai", "модель", "данные"
    ]

    # Финансы
    finance_keywords = [
        "банк", "деньги", "кредит", "оплата", "счет", "доход",
        "расход", "инвестиции", "налог", "финансы"
    ]

    if any(word in text_lower for word in medical_keywords):
        return "illness"

    if any(word in text_lower for word in tech_keywords):
        return "technology"

    if any(word in text_lower for word in finance_keywords):
        return "finance"

    return "other"


# проходит по всем задачам проекта и для каждой предлагает label
def auto_label_task(db: Session, task_id: int):
    """
    Автоматически предлагает label для одной задачи
    и сохраняет suggested_label в БД.
    """
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()

    if not task:
        return None

    suggested = suggest_label_for_text(task.text)
    task.suggested_label = suggested

    db.commit()
    db.refresh(task)

    return task


# массово обновляет все задачи проекта.
def auto_label_project_tasks(db: Session, project_id: int):
    """
    Автоматически предлагает label для всех задач проекта.
    """
    tasks = db.query(models.TaskDB).filter(models.TaskDB.project_id == project_id).all()

    updated_tasks = []

    for task in tasks:
        task.suggested_label = suggest_label_for_text(task.text)
        updated_tasks.append(task)

    db.commit()

    for task in updated_tasks:
        db.refresh(task)

    return updated_tasks


def annotate_task(db: Session, task_id: int, annotation: schemas.TaskAnnotationRequest):
    """
    Человек подтверждает или исправляет suggested label.
    Сохраняется финальная разметка.
    """
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()

    if not task:
        return None

    task.final_label = annotation.final_label
    task.annotator_comment = annotation.annotator_comment
    task.status = "done"

    db.commit()
    db.refresh(task)

    return task


def get_project_stats(db: Session, project_id: int):
    """
    Возвращает статистику по проекту:
    - прогресс разметки
    - сколько задач предразмечено ИИ
    - сколько подтверждено человеком
    - распределение финальных меток
    """
    project = db.query(models.ProjectDB).filter(models.ProjectDB.id == project_id).first()

    if not project:
        return None

    tasks = db.query(models.TaskDB).filter(models.TaskDB.project_id == project_id).all()

    total_tasks = len(tasks)
    pending_tasks = sum(1 for t in tasks if t.status == "pending")
    done_tasks = sum(1 for t in tasks if t.status == "done")

    auto_labeled_tasks = sum(1 for t in tasks if t.suggested_label is not None)
    human_verified_tasks = sum(1 for t in tasks if t.final_label is not None)

    label_distribution = {}
    for task in tasks:
        if task.final_label:
            label = task.final_label
        elif task.suggested_label:
            label = task.suggested_label
        else:
            continue

        label_distribution[label] = label_distribution.get(label, 0) + 1

    return {
        "project_id": project.id,
        "project_name": project.name,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "done_tasks": done_tasks,
        "auto_labeled_tasks": auto_labeled_tasks,
        "human_verified_tasks": human_verified_tasks,
        "label_distribution": label_distribution
    }


def get_export_dataset(db: Session, project_id: int):
    """
    Подготавливает финальный датасет проекта для экспорта.
    """
    project = db.query(models.ProjectDB).filter(models.ProjectDB.id == project_id).first()

    if not project:
        return None

    tasks = db.query(models.TaskDB).filter(models.TaskDB.project_id == project_id).all()

    export_data = []
    for task in tasks:
        export_data.append({
            "id": task.id,
            "text": task.text,
            "suggested_label": task.suggested_label,
            "final_label": task.final_label,
            "status": task.status,
            "annotator_comment": task.annotator_comment
        })

    return {
        "project": project,
        "items": export_data
    }


def create_worker(db: Session, worker: schemas.WorkerCreate):
    """
    Создаёт нового исполнителя (аннотатора / эксперта).
    """
    db_worker = models.WorkerDB(
        name=worker.name,
        role=worker.role,
        specialization=worker.specialization
    )
    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)
    return db_worker


def get_workers(db: Session):
    """
    Возвращает всех исполнителей.
    """
    return db.query(models.WorkerDB).all()


def get_worker(db: Session, worker_id: int):
    """
    Возвращает одного исполнителя по ID.
    """
    return db.query(models.WorkerDB).filter(models.WorkerDB.id == worker_id).first()


def assign_task_to_worker(db: Session, task_id: int, worker_id: int):
    """
    Назначает задачу конкретному исполнителю.
    """
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    worker = db.query(models.WorkerDB).filter(models.WorkerDB.id == worker_id).first()

    if not task or not worker:
        return None

    task.assigned_to = worker_id

    if task.status == "pending":
        task.status = "in_progress"

    db.commit()
    db.refresh(task)

    return task


def get_tasks_for_worker(db: Session, worker_id: int):
    """
    Возвращает все задачи, назначенные исполнителю.
    """
    return db.query(models.TaskDB).filter(models.TaskDB.assigned_to == worker_id).all()


def auto_assign_tasks_by_specialization(db: Session, project_id: int):
    """
    Автоматически назначает задачи исполнителям по специализации.
    Основано на suggested_label задачи.
    """
    tasks = db.query(models.TaskDB).filter(models.TaskDB.project_id == project_id).all()

    if not tasks:
        return []

    workers = db.query(models.WorkerDB).all()

    if not workers:
        return []

    # Соответствие label -> specialization worker-а
    label_to_specialization = {
        "illness": "medicine",
        "technology": "technology",
        "finance": "finance",
        "person": "general",
        "organization": "general",
        "other": "general"
    }

    assigned_tasks = []

    # Чтобы задачи распределялись между несколькими подходящими workers
    worker_indexes = {}

    for task in tasks:
        if task.assigned_to is not None:
            continue  # не трогаем уже назначенные задачи

        label = task.suggested_label or "other"
        needed_specialization = label_to_specialization.get(label, "general")

        suitable_workers = [
            w for w in workers
            if w.specialization == needed_specialization
        ]

        # Если по специализации никого нет — ищем general
        if not suitable_workers:
            suitable_workers = [
                w for w in workers
                if w.specialization == "general"
            ]

        if not suitable_workers:
            continue  # если вообще никого нет, задачу не назначаем

        # round-robin распределение
        if needed_specialization not in worker_indexes:
            worker_indexes[needed_specialization] = 0

        index = worker_indexes[needed_specialization] % len(suitable_workers)
        chosen_worker = suitable_workers[index]

        task.assigned_to = chosen_worker.id

        if task.status == "pending":
            task.status = "in_progress"

        assigned_tasks.append(task)
        worker_indexes[needed_specialization] += 1

    db.commit()

    for task in assigned_tasks:
        db.refresh(task)

    return assigned_tasks


def get_task_consensus(db: Session, task_id: int):
    """
    Считает consensus по задаче:
    - сколько аннотаций
    - какая метка лидирует
    - нужен ли review
    """
    task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()

    if not task:
        return None

    annotations = db.query(models.AnnotationDB).filter(models.AnnotationDB.task_id == task_id).all()

    total_annotations = len(annotations)

    if total_annotations == 0:
        return {
            "task_id": task_id,
            "total_annotations": 0,
            "label_counts": {},
            "consensus_label": None,
            "agreement_score": 0.0,
            "needs_review": False
        }

    label_counts = {}
    for ann in annotations:
        label_counts[ann.label] = label_counts.get(ann.label, 0) + 1

    # Находим лидирующий label
    consensus_label = max(label_counts, key=label_counts.get)
    top_count = label_counts[consensus_label]

    agreement_score = round(top_count / total_annotations, 2)

    # Простейшее правило:
    # если согласие < 0.8, значит нужна review-проверка
    needs_review = agreement_score < 0.8

    return {
        "task_id": task_id,
        "total_annotations": total_annotations,
        "label_counts": label_counts,
        "consensus_label": consensus_label,
        "agreement_score": agreement_score,
        "needs_review": needs_review
    }


