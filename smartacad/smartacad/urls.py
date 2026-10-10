from django.contrib import admin
from django.urls import include, path

from core.views import smartacad_login, smartacad_logout


urlpatterns = [
    path(
        "admin/logout/",
        smartacad_logout,
        name="admin_logout",
    ),
    path(
        "admin/login/",
        smartacad_login,
        name="admin_login"
    ),
    path("admin/", admin.site.urls),

    path(
        "accounts/login/",
        smartacad_login,
        name="login"
    ),

    path(
        "accounts/logout/",
        smartacad_logout,
        name="logout"
    ),

    path("", include("core.urls")),
]

admin.site.login_template = "login.html"
admin.site.site_header = "SmartAcad Administration"
admin.site.site_title = "SmartAcad Admin"
admin.site.index_title = "Administration dashboard"