import csv
import json
from io import StringIO

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from . import services
from .serializers import (
    ProjectCreateSerializer,
    ProjectResponseSerializer,
    TaskResponseSerializer,
    UploadRequestSerializer,
    FileUploadSerializer,
    UploadPreviewResponseSerializer,
    TaskAnnotationRequestSerializer,
    ProjectStatsResponseSerializer,
    WorkerCreateSerializer,
    WorkerResponseSerializer,
    TaskAssignRequestSerializer,
    AnnotationCreateSerializer,
    AnnotationResponseSerializer,
    TaskConsensusResponseSerializer,
)


@api_view(["GET"])
def root(request):
    return Response({"message": "API is working"})


@extend_schema(
    methods=["GET"],
    responses=ProjectResponseSerializer(many=True),
)
@extend_schema(
    methods=["POST"],
    request=ProjectCreateSerializer,
    responses=ProjectResponseSerializer,
)
@api_view(["GET", "POST"])
@parser_classes([JSONParser])
def projects_root(request):
    if request.method == "GET":
        projects = services.list_projects()
        return Response(ProjectResponseSerializer(projects, many=True).data)

    serializer = ProjectCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    project = services.create_project(serializer.validated_data)
    return Response(ProjectResponseSerializer(project).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_project(request, project_id: int):
    project = services.get_project(project_id)
    if not project:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(ProjectResponseSerializer(project).data)


@extend_schema(
    methods=["POST"],
    request=UploadRequestSerializer,
    responses=UploadPreviewResponseSerializer,
)
@api_view(["POST"])
@parser_classes([JSONParser])
def preview_project_upload(request, project_id: int):
    project = services.get_project(project_id)
    if not project:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = UploadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        result = services.preview_upload(
            content=data["content"],
            file_format=data["format"],
            split_mode=data["split_mode"],
            chunk_size=data["chunk_size"],
            text_column=data.get("text_column"),
            text_field=data.get("text_field"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(UploadPreviewResponseSerializer(result).data)


@extend_schema(
    methods=["POST"],
    request=UploadRequestSerializer,
    responses=TaskResponseSerializer(many=True),
)
@api_view(["POST"])
@parser_classes([JSONParser])
def upload_project_data(request, project_id: int):
    project = services.get_project(project_id)
    if not project:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = UploadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        tasks = services.upload_data(
            project_id=project_id,
            content=data["content"],
            file_format=data["format"],
            split_mode=data["split_mode"],
            chunk_size=data["chunk_size"],
            text_column=data.get("text_column"),
            text_field=data.get("text_field"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(TaskResponseSerializer(tasks, many=True).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_project_tasks(request, project_id: int):
    return Response(TaskResponseSerializer(services.get_project_tasks(project_id), many=True).data)


@api_view(["GET"])
def get_all_tasks(request):
    return Response(TaskResponseSerializer(services.get_all_tasks(), many=True).data)


@api_view(["GET"])
def get_next_task(request):
    task = services.get_next_task()
    if not task:
        return Response({"message": "No tasks available"})
    return Response(TaskResponseSerializer(task).data)


@api_view(["GET"])
def get_task(request, task_id: int):
    task = services.get_task(task_id)
    if not task:
        return Response({"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TaskResponseSerializer(task).data)


@extend_schema(
    methods=["POST"],
    responses=TaskResponseSerializer,
)
@api_view(["POST"])
def auto_label_single_task(request, task_id: int):
    task = services.auto_label_task(task_id)
    if not task:
        return Response({"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TaskResponseSerializer(task).data)


@extend_schema(
    methods=["POST"],
    responses=TaskResponseSerializer(many=True),
)
@api_view(["POST"])
def auto_label_project(request, project_id: int):
    project = services.get_project(project_id)
    if not project:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
    tasks = services.auto_label_project_tasks(project_id)
    return Response(TaskResponseSerializer(tasks, many=True).data)


@extend_schema(
    methods=["POST"],
    request=TaskAnnotationRequestSerializer,
    responses=TaskResponseSerializer,
)
@api_view(["POST"])
@parser_classes([JSONParser])
def annotate_single_task(request, task_id: int):
    serializer = TaskAnnotationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    task = services.annotate_task(
        task_id=task_id,
        final_label=data["final_label"],
        annotator_comment=data.get("annotator_comment"),
    )
    if not task:
        return Response({"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TaskResponseSerializer(task).data)


@extend_schema(
    methods=["GET"],
    responses=WorkerResponseSerializer(many=True),
)
@extend_schema(
    methods=["POST"],
    request=WorkerCreateSerializer,
    responses=WorkerResponseSerializer,
)
@api_view(["GET", "POST"])
@parser_classes([JSONParser])
def workers_root(request):
    if request.method == "GET":
        return Response(WorkerResponseSerializer(services.get_workers(), many=True).data)

    serializer = WorkerCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    worker = services.create_worker(serializer.validated_data)
    return Response(WorkerResponseSerializer(worker).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_worker(request, worker_id: int):
    worker = services.get_worker(worker_id)
    if not worker:
        return Response({"detail": "Worker not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(WorkerResponseSerializer(worker).data)


@extend_schema(
    methods=["POST"],
    request=TaskAssignRequestSerializer,
    responses=TaskResponseSerializer,
)
@api_view(["POST"])
@parser_classes([JSONParser])
def assign_task(request, task_id: int):
    serializer = TaskAssignRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    task = services.assign_task_to_worker(task_id, serializer.validated_data["worker_id"])
    if not task:
        return Response({"detail": "Task or Worker not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TaskResponseSerializer(task).data)


@api_view(["GET"])
def get_worker_tasks(request, worker_id: int):
    worker = services.get_worker(worker_id)
    if not worker:
        return Response({"detail": "Worker not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TaskResponseSerializer(services.get_tasks_for_worker(worker_id), many=True).data)


@extend_schema(
    methods=["POST"],
    responses=TaskResponseSerializer(many=True),
)
@api_view(["POST"])
def auto_assign_project_tasks(request, project_id: int):
    assigned_tasks = services.auto_assign_tasks_by_specialization(project_id)
    return Response(TaskResponseSerializer(assigned_tasks, many=True).data)


@extend_schema(
    methods=["POST"],
    request=AnnotationCreateSerializer,
    responses=AnnotationResponseSerializer,
)
@api_view(["POST"])
@parser_classes([JSONParser])
def create_task_annotation(request, task_id: int):
    serializer = AnnotationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    result = services.create_annotation(
        task_id=task_id,
        worker_id=data["worker_id"],
        label=data["label"],
        comment=data.get("comment"),
    )

    if result is None:
        return Response({"detail": "Task or Worker not found"}, status=status.HTTP_404_NOT_FOUND)
    if result == "already_exists":
        return Response({"detail": "This worker already annotated this task"}, status=status.HTTP_400_BAD_REQUEST)

    return Response(AnnotationResponseSerializer(result).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_task_annotations(request, task_id: int):
    annotations = services.get_annotations_for_task(task_id)
    return Response(AnnotationResponseSerializer(annotations, many=True).data)


@extend_schema(
    methods=["GET"],
    responses=TaskConsensusResponseSerializer,
)
@api_view(["GET"])
def get_task_consensus(request, task_id: int):
    result = services.get_task_consensus(task_id)
    if not result:
        return Response({"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TaskConsensusResponseSerializer(result).data)


@extend_schema(
    methods=["GET"],
    responses=ProjectStatsResponseSerializer,
)
@api_view(["GET"])
def get_project_stats(request, project_id: int):
    stats = services.get_project_stats(project_id)
    if not stats:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(ProjectStatsResponseSerializer(stats).data)


@api_view(["GET"])
def export_project_json(request, project_id: int):
    export_result = services.get_export_dataset(project_id)
    if not export_result:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    json_content = json.dumps(export_result["items"], ensure_ascii=False, indent=2)
    response = StreamingHttpResponse(iter([json_content]), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="project_{project_id}_dataset.json"'
    return response


@api_view(["GET"])
def export_project_csv(request, project_id: int):
    export_result = services.get_export_dataset(project_id)
    if not export_result:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "text", "suggested_label", "final_label", "status", "annotator_comment"],
    )
    writer.writeheader()
    writer.writerows(export_result["items"])

    csv_content = output.getvalue()
    csv_with_bom = "\ufeff" + csv_content

    response = StreamingHttpResponse(iter([csv_with_bom]), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="project_{project_id}_dataset.csv"'
    return response


@extend_schema(
    methods=["POST"],
    request=FileUploadSerializer,
    responses=UploadPreviewResponseSerializer,
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def preview_project_file_upload(request, project_id: int):
    project = services.get_project(project_id)
    if not project:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

    file_bytes = file_obj.read()
    content = services.decode_uploaded_file(file_bytes)

    file_format = request.data.get("format")
    split_mode = request.data.get("split_mode", "line")
    chunk_size = int(request.data.get("chunk_size", 300))
    text_column = request.data.get("text_column")
    text_field = request.data.get("text_field")

    try:
        result = services.preview_upload(
            content=content,
            file_format=file_format,
            split_mode=split_mode,
            chunk_size=chunk_size,
            text_column=text_column,
            text_field=text_field,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(UploadPreviewResponseSerializer(result).data)


@extend_schema(
    methods=["POST"],
    request=FileUploadSerializer,
    responses=TaskResponseSerializer(many=True),
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_project_file(request, project_id: int):
    project = services.get_project(project_id)
    if not project:
        return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

    file_bytes = file_obj.read()
    content = services.decode_uploaded_file(file_bytes)

    file_format = request.data.get("format")
    split_mode = request.data.get("split_mode", "line")
    chunk_size = int(request.data.get("chunk_size", 300))
    text_column = request.data.get("text_column")
    text_field = request.data.get("text_field")

    try:
        tasks = services.upload_data(
            project_id=project_id,
            content=content,
            file_format=file_format,
            split_mode=split_mode,
            chunk_size=chunk_size,
            text_column=text_column,
            text_field=text_field,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(TaskResponseSerializer(tasks, many=True).data, status=status.HTTP_201_CREATED)
