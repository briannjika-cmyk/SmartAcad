from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction

from .models import (
    AcademicRecord,
    Course,
    Program,
    Student,
    StudentCourseEnrollment,
)


def grade_for_marks(marks):
    if marks >= 70:
        return "A"
    if marks >= 60:
        return "B"
    if marks >= 50:
        return "C"
    if marks >= 40:
        return "D"
    return "E"


class AcademicRecordUpdateForm(forms.ModelForm):
    marks = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    class Meta:
        model = AcademicRecord
        fields = (
            "student",
            "course_code",
            "course_name",
            "semester",
            "marks",
            "academic_year",
            "credits",
        )

    def save(self, commit=True):
        record = super().save(commit=False)
        record.grade = grade_for_marks(self.cleaned_data["marks"])
        if commit:
            record.save()
            self.save_m2m()
        return record


def sync_student_course_enrollments(student):
    program_course_ids = (
        list(
            Course.objects.filter(program_id=student.program_id)
            .values_list("id", flat=True)
        )
        if student.program_id
        else []
    )
    if program_course_ids:
        StudentCourseEnrollment.objects.filter(
            student=student
        ).exclude(course_id__in=program_course_ids).delete()
    else:
        StudentCourseEnrollment.objects.filter(student=student).delete()

    enrolled_course_ids = set(
        StudentCourseEnrollment.objects.filter(
            student=student,
            course_id__in=program_course_ids,
        ).values_list("course_id", flat=True)
    )
    StudentCourseEnrollment.objects.bulk_create(
        [
            StudentCourseEnrollment(student=student, course_id=course_id)
            for course_id in program_course_ids
            if course_id not in enrolled_course_ids
        ],
        ignore_conflicts=True,
    )


def sync_program_course_enrollments(program_ids):
    program_ids = {program_id for program_id in program_ids if program_id}
    if not program_ids:
        return

    affected_students = (
        Student.objects.filter(program_id__in=program_ids)
        | Student.objects.filter(
            course_enrollments__course__program_id__in=program_ids
        )
    ).distinct()
    for student in affected_students:
        sync_student_course_enrollments(student)


class StudentAdmissionForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        strip=False,
        help_text="Set the student's initial login password.",
    )

    class Meta:
        model = Student
        fields = (
            "student_id",
            "full_name",
            "email",
            "program",
            "year_of_study",
            "password",
        )

    def __init__(self, *args, academic_admin=None, **kwargs):
        super().__init__(*args, **kwargs)
        if academic_admin is not None:
            self.fields["program"].queryset = Program.objects.filter(
                academic_admin=academic_admin
            ).order_by("name")

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"]
        if User.objects.filter(username=student_id).exists():
            raise forms.ValidationError(
                "An account with this student ID already exists."
            )
        return student_id

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password)
        return password

    @transaction.atomic
    def save(self):
        student_id = self.cleaned_data["student_id"]
        password = self.cleaned_data["password"]
        program = self.cleaned_data["program"]
        user = User.objects.create_user(
            username=student_id,
            email=self.cleaned_data["email"],
            password=password,
        )
        user.groups.add(Group.objects.get_or_create(name="Student")[0])

        student = super().save(commit=False)
        student.user = user
        student.program = program
        student.programme = program.name
        student.save()
        sync_student_course_enrollments(student)
        return student
