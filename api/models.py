from django.db import models
from django.utils import timezone


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    data_type = models.CharField(max_length=32, default="text")
    labeling_type = models.CharField(max_length=64, default="ner")
    instruction = models.TextField(blank=True, default="")
    source_name = models.CharField(max_length=255, blank=True, default="")

    def __str__(self) -> str:
        return self.name


class Worker(models.Model):
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=64, default="annotator")
    specialization = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    project = models.ForeignKey(Project, related_name="tasks", on_delete=models.CASCADE)
    text = models.TextField()
    status = models.CharField(max_length=32, default="pending")
    suggested_label = models.CharField(max_length=255, blank=True, null=True)
    final_label = models.CharField(max_length=255, blank=True, null=True)
    annotator_comment = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(Worker, related_name="tasks", on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self) -> str:
        return f"Task {self.id}"


class Annotation(models.Model):
    task = models.ForeignKey(Task, related_name="annotations", on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, related_name="annotations", on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("task", "worker")

    def __str__(self) -> str:
        return f"Annotation {self.id}"
