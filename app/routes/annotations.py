from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

router = APIRouter()


@router.post("/tasks/{task_id}/annotate", response_model=schemas.AnnotationResponse)
def annotate_task(task_id: int, annotation: schemas.AnnotationCreate, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return crud.create_annotation(db, task_id, annotation)


@router.get("/tasks/{task_id}/annotations", response_model=List[schemas.AnnotationResponse])
def get_annotations(task_id: int, db: Session = Depends(get_db)):
    return crud.get_task_annotations(db, task_id)