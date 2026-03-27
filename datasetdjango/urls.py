from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from api import views as api_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api_views.root),
    path("", include("api.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
