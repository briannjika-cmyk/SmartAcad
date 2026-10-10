from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


GRADE_POINTS = {
    "A": Decimal("4.00"),
    "B": Decimal("3.00"),
    "C": Decimal("2.00"),
    "D": Decimal("1.00"),
    "E": Decimal("0.00"),
}


class Program(models.Model):
    program_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, unique=True)
    academic_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_programs",
        limit_choices_to={"groups__name": "Academic Admin"},
    )

    def __str__(self):
        return f"{self.program_code} - {self.name}"


class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )
    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    programme = models.CharField(max_length=100)
    year_of_study = models.PositiveIntegerField()
    gpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    def __str__(self):
        return self.full_name


class Lecturer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lecturers",
    )
    lecturer_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name


class Course(models.Model):
    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.CASCADE
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="courses",
    )
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=100)
    credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("3.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class AcademicRecord(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )
    course_code = models.CharField(max_length=20)
    course_name = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5)
    academic_year = models.CharField(max_length=20)
    credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("3.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    def __str__(self):
        return f"{self.student.full_name} - {self.course_code}"


def recalculate_student_gpa(student_id):
    weighted_points = Decimal("0.00")
    total_credits = Decimal("0.00")

    records = AcademicRecord.objects.filter(
        student_id=student_id
    ).values_list("grade", "credits")

    for grade, credits in records:
        grade_points = GRADE_POINTS[grade]
        weighted_points += grade_points * credits
        total_credits += credits

    gpa = (
        (weighted_points / total_credits).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if total_credits
        else Decimal("0.00")
    )
    Student.objects.filter(pk=student_id).update(gpa=gpa)


class StudentCourseEnrollment(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="student_enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="uniq_student_course_enroll",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.course.course_code}"


class StudentQuestionnaire(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE
    )

    submitted = models.BooleanField(
        default=False
    )

    study_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )

    assignment_completion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    learning_difficulties = models.TextField(
        blank=True
    )

    study_habits = models.TextField(
        blank=True
    )

    learning_resource_access = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"Questionnaire - {self.student.full_name}"


class Attendance(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )
    course_code = models.CharField(max_length=20)
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=[
            ("Present", "Present"),
            ("Absent", "Absent"),
        ]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course_code", "date"],
                name="unique_student_course_date"
            )
        ]

    def __str__(self):
        return (
            f"{self.student.full_name} - "
            f"{self.course_code} - {self.date}"
        )