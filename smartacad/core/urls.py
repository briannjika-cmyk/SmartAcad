from django.urls import path
from . import views
from .views import smartacad_login


urlpatterns = [
    path("", views.home, name="home"),
    path("login/", smartacad_login, name="login_alias"),
    path(
        "account/change-password/",
        views.change_password,
        name="change_password",
    ),

    # Student
    path(
        "dashboard/",
        views.student_dashboard,
        name="student_dashboard"
    ),
    path(
        "dashboard/results/",
        views.student_academic_results,
        name="student_academic_results"
    ),
    path(
        "dashboard/attendance/",
        views.student_attendance_records,
        name="student_attendance_records"
    ),

    # Lecturer
    # Lecturer

path(
    "lecturer-dashboard/",
    views.lecturer_dashboard,
    name="lecturer_dashboard"
),

path(
    "lecturer-dashboard/marks/",
    views.lecturer_enter_marks,
    name="lecturer_enter_marks"
),

path(
    "lecturer-dashboard/students/",
    views.lecturer_students,
    name="lecturer_students"
),

path(
    "lecturer-dashboard/academic-records/",
    views.lecturer_academic_records,
    name="lecturer_academic_records"
),

path(
    "lecturer-dashboard/attendance/",
    views.lecturer_attendance,
    name="lecturer_attendance"
),

path(
    "lecturer-dashboard/attendance/save/",
    views.lecturer_save_attendance,
    name="lecturer_save_attendance"
),

path(
    "lecturer-dashboard/questionnaires/",
    views.lecturer_questionnaires,
    name="lecturer_questionnaires"
),

    # Academic Admin
    path(
        "admin-dashboard/",
        views.academic_admin_dashboard,
        name="academic_admin_dashboard"
    ),
    path(
        "admin-dashboard/students/",
        views.academic_admin_students,
        name="academic_admin_students"
    ),
    path(
        "admin-dashboard/programs/",
        views.academic_admin_programs,
        name="academic_admin_programs"
    ),
    path(
        "admin-dashboard/courses/",
        views.academic_admin_courses,
        name="academic_admin_courses"
    ),
    path(
        "admin-dashboard/academic-records/",
        views.academic_admin_academic_records,
        name="academic_admin_academic_records"
    ),
    path(
        "admin-dashboard/academic-records/<int:record_id>/update/",
        views.academic_admin_update_academic_record,
        name="academic_admin_update_academic_record",
    ),
    path(
        "admin-dashboard/attendance/",
        views.academic_admin_attendance,
        name="academic_admin_attendance"
    ),
    path(
        "admin-dashboard/questionnaires/",
        views.academic_admin_questionnaires,
        name="academic_admin_questionnaires"
    ),

    # Student questionnaire
    path(
        "questionnaire/",
        views.student_questionnaire,
        name="student_questionnaire"
    ),
]