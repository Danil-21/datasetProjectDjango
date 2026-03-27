from django.urls import path
from . import views


urlpatterns = [
    # Projects
    path("projects", views.projects_root),
    path("projects/<int:project_id>", views.get_project),
    path("projects/<int:project_id>/preview-upload", views.preview_project_upload),
    path("projects/<int:project_id>/upload", views.upload_project_data),
    path("projects/<int:project_id>/preview-file", views.preview_project_file_upload),
    path("projects/<int:project_id>/upload-file", views.upload_project_file),
    path("projects/<int:project_id>/tasks", views.get_project_tasks),
    path("projects/<int:project_id>/auto-label", views.auto_label_project),
    path("projects/<int:project_id>/auto-assign", views.auto_assign_project_tasks),
    path("projects/<int:project_id>/stats", views.get_project_stats),
    path("projects/<int:project_id>/export/json", views.export_project_json),
    path("projects/<int:project_id>/export/csv", views.export_project_csv),

    # Tasks
    path("tasks", views.get_all_tasks),
    path("tasks/next", views.get_next_task),
    path("tasks/<int:task_id>", views.get_task),
    path("tasks/<int:task_id>/auto-label", views.auto_label_single_task),
    path("tasks/<int:task_id>/annotate", views.annotate_single_task),
    path("tasks/<int:task_id>/annotations", views.get_task_annotations),
    path("tasks/<int:task_id>/consensus", views.get_task_consensus),
    path("tasks/<int:task_id>/assign", views.assign_task),

    # Workers (top-level as in README)
    path("workers", views.workers_root),
    path("workers/<int:worker_id>", views.get_worker),
    path("workers/<int:worker_id>/tasks", views.get_worker_tasks),

    # Compatibility with original FastAPI routes under /projects
    path("projects/workers", views.workers_root),
    path("projects/workers/<int:worker_id>/tasks", views.get_worker_tasks),
    path("projects/tasks/<int:task_id>/annotate", views.annotate_single_task),
    path("projects/tasks/<int:task_id>/annotations", views.get_task_annotations),
    path("projects/tasks/<int:task_id>/consensus", views.get_task_consensus),
]
