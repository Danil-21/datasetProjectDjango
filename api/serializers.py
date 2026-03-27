from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, OpenApiTypes
from .models import Project, Task, Worker, Annotation


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["name", "description", "data_type", "labeling_type", "instruction", "source_name"]


class ProjectResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "data_type", "labeling_type", "instruction", "source_name"]


class TaskResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    assigned_to = serializers.IntegerField(source="assigned_to.id", allow_null=True, required=False, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "project_id",
            "text",
            "status",
            "suggested_label",
            "final_label",
            "annotator_comment",
            "assigned_to",
        ]


class UploadRequestSerializer(serializers.Serializer):
    content = serializers.CharField()
    format = serializers.ChoiceField(choices=["text", "csv", "json"], default="text")
    split_mode = serializers.ChoiceField(choices=["line", "sentence", "paragraph", "fixed_chunk"], default="line")
    chunk_size = serializers.IntegerField(default=300)
    text_column = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    text_field = serializers.CharField(required=False, allow_null=True, allow_blank=True)


@extend_schema_field(OpenApiTypes.BINARY)
class BinaryFileField(serializers.FileField):
    pass


class FileUploadSerializer(serializers.Serializer):
    file = BinaryFileField()
    format = serializers.ChoiceField(choices=["text", "csv", "json"])
    split_mode = serializers.ChoiceField(choices=["line", "sentence", "paragraph", "fixed_chunk"], default="line")
    chunk_size = serializers.IntegerField(default=300)
    text_column = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    text_field = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class UploadPreviewResponseSerializer(serializers.Serializer):
    format = serializers.CharField()
    split_mode = serializers.CharField(allow_null=True)
    total_raw_items = serializers.IntegerField()
    valid_items = serializers.IntegerField()
    empty_removed = serializers.IntegerField()
    duplicates_removed = serializers.IntegerField()
    preview_items = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField(), required=False)


class TaskAnnotationRequestSerializer(serializers.Serializer):
    final_label = serializers.CharField()
    annotator_comment = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ProjectStatsResponseSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    total_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    done_tasks = serializers.IntegerField()
    auto_labeled_tasks = serializers.IntegerField()
    human_verified_tasks = serializers.IntegerField()
    label_distribution = serializers.DictField(child=serializers.IntegerField())


class WorkerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["name", "role", "specialization"]


class WorkerResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "role", "specialization"]


class TaskAssignRequestSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField()


class AnnotationCreateSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField()
    label = serializers.CharField()
    comment = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class AnnotationResponseSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(source="task.id", read_only=True)
    worker_id = serializers.IntegerField(source="worker.id", read_only=True)

    class Meta:
        model = Annotation
        fields = ["id", "task_id", "worker_id", "label", "comment"]


class TaskConsensusResponseSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    total_annotations = serializers.IntegerField()
    label_counts = serializers.DictField(child=serializers.IntegerField())
    consensus_label = serializers.CharField(allow_null=True)
    agreement_score = serializers.FloatField()
    needs_review = serializers.BooleanField()
