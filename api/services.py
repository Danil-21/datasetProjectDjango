import csv
import json
import re
from io import StringIO
from typing import Dict, List, Optional

from django.db import transaction

from .models import Project, Task, Worker, Annotation


def decode_uploaded_file(file_bytes: bytes) -> str:
    encodings_to_try = ["utf-8", "utf-8-sig", "cp1251", "latin-1"]
    for encoding in encodings_to_try:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode uploaded file. Supported encodings: utf-8, utf-8-sig, cp1251")


def parse_upload_content(
    content: str,
    file_format: str,
    split_mode: str = "line",
    chunk_size: int = 300,
    text_column: Optional[str] = None,
    text_field: Optional[str] = None,
) -> List[str]:
    texts: List[str] = []

    if file_format == "text":
        if split_mode == "line":
            texts = [line.strip() for line in content.splitlines() if line.strip()]
        elif split_mode == "sentence":
            parts = re.split(r"[.!?]\s+|\n", content)
            texts = [part.strip() for part in parts if part.strip()]
        elif split_mode == "paragraph":
            parts = re.split(r"\n\s*\n", content)
            texts = [part.strip() for part in parts if part.strip()]
        elif split_mode == "fixed_chunk":
            content = content.strip()
            chunk_size = max(chunk_size, 50)
            texts = [
                content[i : i + chunk_size].strip()
                for i in range(0, len(content), chunk_size)
                if content[i : i + chunk_size].strip()
            ]
        else:
            raise ValueError("Unsupported split_mode for text upload")

    elif file_format == "csv":
        if not text_column:
            raise ValueError("text_column is required for CSV upload")

        csv_file = StringIO(content)
        sample = content[:1024]

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        csv_file.seek(0)
        reader = csv.DictReader(csv_file, delimiter=delimiter)

        if not reader.fieldnames:
            raise ValueError("CSV file has no headers")

        if text_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{text_column}' not found in CSV. Available columns: {reader.fieldnames}"
            )

        for row in reader:
            value = row.get(text_column)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                texts.append(text)

    elif file_format == "json":
        if not text_field:
            raise ValueError("text_field is required for JSON upload")

        data = json.loads(content)

        if not isinstance(data, list):
            raise ValueError("JSON content must be a list of objects")

        for item in data:
            text = str(item.get(text_field, "")).strip()
            if text:
                texts.append(text)
    else:
        raise ValueError("Unsupported upload format")

    return texts


def clean_text_items(texts: List[str]) -> Dict:
    total_raw_items = len(texts)

    non_empty = [t.strip() for t in texts if t and t.strip()]
    empty_removed = total_raw_items - len(non_empty)

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
        "warnings": warnings,
    }


def preview_upload(
    content: str,
    file_format: str,
    split_mode: str = "line",
    chunk_size: int = 300,
    text_column: Optional[str] = None,
    text_field: Optional[str] = None,
) -> Dict:
    texts = parse_upload_content(
        content=content,
        file_format=file_format,
        split_mode=split_mode,
        chunk_size=chunk_size,
        text_column=text_column,
        text_field=text_field,
    )
    cleaned = clean_text_items(texts)

    return {
        "format": file_format,
        "split_mode": split_mode if file_format == "text" else None,
        "total_raw_items": cleaned["total_raw_items"],
        "valid_items": cleaned["valid_items"],
        "empty_removed": cleaned["empty_removed"],
        "duplicates_removed": cleaned["duplicates_removed"],
        "preview_items": cleaned["cleaned_items"][:10],
        "warnings": cleaned["warnings"],
    }


def create_project(data: Dict) -> Project:
    return Project.objects.create(**data)


def list_projects():
    return Project.objects.all()


def get_project(project_id: int) -> Optional[Project]:
    return Project.objects.filter(id=project_id).first()


@transaction.atomic
def upload_data(project_id: int, content: str, file_format: str, split_mode: str, chunk_size: int,
                text_column: Optional[str], text_field: Optional[str]):
    texts = parse_upload_content(
        content=content,
        file_format=file_format,
        split_mode=split_mode,
        chunk_size=chunk_size,
        text_column=text_column,
        text_field=text_field,
    )
    cleaned = clean_text_items(texts)

    tasks = []
    for text in cleaned["cleaned_items"]:
        task = Task.objects.create(project_id=project_id, text=text, status="pending")
        tasks.append(task)
    return tasks


def get_project_tasks(project_id: int):
    return Task.objects.filter(project_id=project_id)


def get_all_tasks():
    return Task.objects.all()


@transaction.atomic
def get_next_task():
    task = Task.objects.filter(status="pending").order_by("id").first()
    if task:
        task.status = "in_progress"
        task.save(update_fields=["status"])
    return task


def get_task(task_id: int) -> Optional[Task]:
    return Task.objects.filter(id=task_id).first()


def suggest_label_for_text(text: str) -> str:
    text_lower = text.lower()

    medical_keywords = [
        "пациент", "температура", "кашель", "горло", "врач", "диагноз",
        "болит", "лечение", "симптом", "болезнь"
    ]

    tech_keywords = [
        "apple", "google", "microsoft", "iphone", "android", "windows",
        "приложение", "сервер", "код", "ai", "модель", "данные"
    ]

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


@transaction.atomic
def auto_label_task(task_id: int) -> Optional[Task]:
    task = Task.objects.filter(id=task_id).first()
    if not task:
        return None
    task.suggested_label = suggest_label_for_text(task.text)
    task.save(update_fields=["suggested_label"])
    return task


@transaction.atomic
def auto_label_project_tasks(project_id: int):
    tasks = Task.objects.filter(project_id=project_id)
    for task in tasks:
        task.suggested_label = suggest_label_for_text(task.text)
    Task.objects.bulk_update(tasks, ["suggested_label"])
    return tasks


@transaction.atomic
def annotate_task(task_id: int, final_label: str, annotator_comment: Optional[str]):
    task = Task.objects.filter(id=task_id).first()
    if not task:
        return None
    task.final_label = final_label
    task.annotator_comment = annotator_comment
    task.status = "done"
    task.save(update_fields=["final_label", "annotator_comment", "status"])
    return task


def get_project_stats(project_id: int) -> Optional[Dict]:
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return None

    tasks = Task.objects.filter(project_id=project_id)
    total_tasks = tasks.count()
    pending_tasks = tasks.filter(status="pending").count()
    done_tasks = tasks.filter(status="done").count()
    auto_labeled_tasks = tasks.exclude(suggested_label__isnull=True).count()
    human_verified_tasks = tasks.exclude(final_label__isnull=True).count()

    label_distribution: Dict[str, int] = {}
    for task in tasks:
        label = task.final_label or task.suggested_label
        if not label:
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
        "label_distribution": label_distribution,
    }


def get_export_dataset(project_id: int) -> Optional[Dict]:
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return None

    tasks = Task.objects.filter(project_id=project_id)
    export_items = []
    for task in tasks:
        export_items.append(
            {
                "id": task.id,
                "text": task.text,
                "suggested_label": task.suggested_label,
                "final_label": task.final_label,
                "status": task.status,
                "annotator_comment": task.annotator_comment,
            }
        )
    return {"project": project, "items": export_items}


def create_worker(data: Dict) -> Worker:
    return Worker.objects.create(**data)


def get_workers():
    return Worker.objects.all()


def get_worker(worker_id: int) -> Optional[Worker]:
    return Worker.objects.filter(id=worker_id).first()


@transaction.atomic
def assign_task_to_worker(task_id: int, worker_id: int):
    task = Task.objects.filter(id=task_id).first()
    worker = Worker.objects.filter(id=worker_id).first()
    if not task or not worker:
        return None

    task.assigned_to_id = worker_id
    if task.status == "pending":
        task.status = "in_progress"
    task.save(update_fields=["assigned_to", "status"])
    return task


def get_tasks_for_worker(worker_id: int):
    return Task.objects.filter(assigned_to_id=worker_id)


@transaction.atomic
def auto_assign_tasks_by_specialization(project_id: int):
    tasks = Task.objects.filter(project_id=project_id)
    if not tasks.exists():
        return []

    workers = Worker.objects.all()
    if not workers.exists():
        return []

    label_to_specialization = {
        "illness": "medicine",
        "technology": "technology",
        "finance": "finance",
        "person": "general",
        "organization": "general",
        "other": "general",
    }

    assigned_tasks = []
    worker_indexes = {}

    for task in tasks:
        if task.assigned_to_id is not None:
            continue

        label = task.suggested_label or "other"
        needed_specialization = label_to_specialization.get(label, "general")

        suitable_workers = [w for w in workers if w.specialization == needed_specialization]
        if not suitable_workers:
            suitable_workers = [w for w in workers if w.specialization == "general"]
        if not suitable_workers:
            continue

        if needed_specialization not in worker_indexes:
            worker_indexes[needed_specialization] = 0
        index = worker_indexes[needed_specialization] % len(suitable_workers)
        chosen_worker = suitable_workers[index]

        task.assigned_to_id = chosen_worker.id
        if task.status == "pending":
            task.status = "in_progress"
        task.save(update_fields=["assigned_to", "status"])
        assigned_tasks.append(task)
        worker_indexes[needed_specialization] += 1

    return assigned_tasks


@transaction.atomic
def create_annotation(task_id: int, worker_id: int, label: str, comment: Optional[str]):
    task = Task.objects.filter(id=task_id).first()
    worker = Worker.objects.filter(id=worker_id).first()
    if not task or not worker:
        return None

    if Annotation.objects.filter(task_id=task_id, worker_id=worker_id).exists():
        return "already_exists"

    annotation = Annotation.objects.create(
        task_id=task_id,
        worker_id=worker_id,
        label=label,
        comment=comment,
    )

    if task.status == "pending":
        task.status = "in_progress"
        task.save(update_fields=["status"])

    return annotation


def get_annotations_for_task(task_id: int):
    return Annotation.objects.filter(task_id=task_id)


def get_task_consensus(task_id: int) -> Optional[Dict]:
    task = Task.objects.filter(id=task_id).first()
    if not task:
        return None

    annotations = Annotation.objects.filter(task_id=task_id)
    total_annotations = annotations.count()

    if total_annotations == 0:
        return {
            "task_id": task_id,
            "total_annotations": 0,
            "label_counts": {},
            "consensus_label": None,
            "agreement_score": 0.0,
            "needs_review": False,
        }

    label_counts: Dict[str, int] = {}
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
        "needs_review": needs_review,
    }
