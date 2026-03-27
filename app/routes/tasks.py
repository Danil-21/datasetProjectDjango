from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

router = APIRouter()


@router.get("/")
def get_all_tasks(db: Session = Depends(get_db)):
    return crud.get_all_tasks(db)


@router.get("/next")
def get_next_task(db: Session = Depends(get_db)):
    task = crud.get_next_task(db)
    if not task:
        return {"message": "No tasks available"}
    return task


@router.post("/{task_id}/suggest")
def suggest_annotation(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    text = task.text
    labels = []

    words = text.split()

    for word in words:
        if word.lower() in ["apple", "google", "microsoft"]:
            labels.append({"text": word, "tag": "ORG"})
        if word.lower() in ["iphone", "android", "windows"]:
            labels.append({"text": word, "tag": "PRODUCT"})

    return {
        "task_id": task_id,
        "suggested_labels": labels
    }