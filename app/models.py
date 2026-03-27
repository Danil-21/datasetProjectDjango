from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class ProjectDB(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)

    data_type = Column(String, default="text")        # text / csv / json
    labeling_type = Column(String, default="ner")
    instruction = Column(String, default="")
    source_name = Column(String, default="")          # имя файла / источника

    tasks = relationship("TaskDB", back_populates="project")


class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    text = Column(String, nullable=False)
    status = Column(String, default="pending")
    suggested_label = Column(String, nullable=True)
    final_label = Column(String, nullable=True)
    annotator_comment = Column(Text, nullable=True)
    assigned_to = Column(Integer, ForeignKey("workers.id"), nullable=True)

    project = relationship("ProjectDB", back_populates="tasks")
    annotations = relationship("AnnotationDB", back_populates="task")


# class AnnotationDB(Base):
#     __tablename__ = "annotations"

#     id = Column(Integer, primary_key=True, index=True)
#     task_id = Column(Integer, ForeignKey("tasks.id"))
#     labels = Column(JSON, nullable=False)

#     task = relationship("TaskDB", back_populates="annotations")


class WorkerDB(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, default="annotator")
    specialization = Column(String, nullable=True)

    annotations = relationship("AnnotationDB", back_populates="worker")


class AnnotationDB(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)

    label = Column(String, nullable=False)
    comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    task = relationship("TaskDB", back_populates="annotations")
    worker = relationship("WorkerDB", back_populates="annotations")