from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.forms.models import BaseInlineFormSet

from .forms import sync_program_course_enrollments
from .models import (
    Student,
    Lecturer,
    Course,
    AcademicRecord,
    StudentQuestionnaire,
    Attendance,
    Program,
    recalculate_student_gpa,
    StudentCourseEnrollment,
)


def is_main_admin(user):
    return (
        user.is_superuser
        or user.groups.filter(name="System Administrator").exists()
    )


class ProgramAdminForm(forms.ModelForm):
    academic_admin = forms.ModelChoiceField(
        queryset=User.objects.filter(
            groups__name="Academic Admin"
        ).distinct(),
        label="Academic admin",
    )

    class Meta:
        model = Program
        fields = ("program_code", "name", "academic_admin")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    form = ProgramAdminForm
    list_display = ("program_code", "name", "academic_admin")

    def has_module_permission(self, request):
        return is_main_admin(request.user)

    def has_add_permission(self, request):
        return is_main_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_main_admin(request.user)


class LecturerAdminForm(forms.ModelForm):
    program = forms.ModelChoiceField(
        queryset=Program.objects.order_by("name"),
        required=True,
    )

    class Meta:
        model = Lecturer
        fields = (
            "user",
            "program",
            "lecturer_id",
            "full_name",
            "email",
            "department",
        )


class LecturerCourseInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        form.instance.program = self.instance.program
        return super().save_new(form, commit=commit)

    def save_existing(self, form, instance, commit=True):
        instance.program = self.instance.program
        return super().save_existing(form, instance, commit=commit)


class CourseInline(admin.TabularInline):
    model = Course
    formset = LecturerCourseInlineFormSet
    fields = ("course_code", "course_name", "credits")
    extra = 1
    min_num = 1
    validate_min = True

    def has_add_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_main_admin(request.user)


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    form = LecturerAdminForm
    inlines = (CourseInline,)
    list_display = ("lecturer_id", "full_name", "email", "program")
    search_fields = ("lecturer_id", "full_name", "email")
    list_filter = ("program",)

    def has_module_permission(self, request):
        return is_main_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_add_permission(self, request):
        return is_main_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def save_model(self, request, obj, form, change):
        obj._previous_program_id = (
            Lecturer.objects.get(pk=obj.pk).program_id if change else None
        )
        super().save_model(request, obj, form, change)
        lecturer_group, _ = Group.objects.get_or_create(name="Lecturer")
        obj.user.groups.add(lecturer_group)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sync_program_course_enrollments(
            [
                form.instance._previous_program_id,
                form.instance.program_id,
            ]
        )


admin.site.register(StudentCourseEnrollment)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    readonly_fields = ("gpa",)
    list_display = (
        "student_id",
        "full_name",
        "email",
        "programme",
        "year_of_study",
        "gpa",
    )
    search_fields = (
        "student_id",
        "full_name",
        "email",
    )
    list_filter = (
        "programme",
        "year_of_study",
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_code",
        "course_name",
        "credits",
        "lecturer",
    )
    search_fields = (
        "course_code",
        "course_name",
    )
    list_filter = ("lecturer",)

    def has_module_permission(self, request):
        return is_main_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_add_permission(self, request):
        return is_main_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_main_admin(request.user)

    def save_model(self, request, obj, form, change):
        previous_program_id = None
        if change:
            previous = Course.objects.get(pk=obj.pk)
            previous_program_id = previous.program_id
            if previous.credits != obj.credits:
                affected_student_ids = list(
                    AcademicRecord.objects.filter(
                        course_code=obj.course_code
                    ).values_list("student_id", flat=True).distinct()
                )
                AcademicRecord.objects.filter(
                    course_code=obj.course_code
                ).update(credits=obj.credits)
                for student_id in affected_student_ids:
                    recalculate_student_gpa(student_id)
        super().save_model(request, obj, form, change)
        sync_program_course_enrollments(
            [previous_program_id, obj.program_id]
        )


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course_code",
        "course_name",
        "semester",
        "marks",
        "grade",
        "credits",
        "academic_year",
    )
    search_fields = (
        "student__full_name",
        "student__student_id",
        "course_code",
        "course_name",
    )
    list_filter = (
        "semester",
        "academic_year",
        "grade",
    )


@admin.register(StudentQuestionnaire)
class StudentQuestionnaireAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "study_hours",
        "assignment_completion",
    )
    search_fields = (
        "student__full_name",
        "student__student_id",
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course_code",
        "date",
        "status",
    )
    search_fields = (
        "student__full_name",
        "student__student_id",
        "course_code",
    )
    list_filter = (
        "course_code",
        "status",
        "date",
    )