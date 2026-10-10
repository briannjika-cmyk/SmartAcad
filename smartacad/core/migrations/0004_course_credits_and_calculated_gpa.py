from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models
import django.core.validators


def calculate_existing_gpas(apps, schema_editor):
    Student = apps.get_model("core", "Student")
    AcademicRecord = apps.get_model("core", "AcademicRecord")
    database = schema_editor.connection.alias
    grade_points = {
        "A": Decimal("4.00"),
        "B": Decimal("3.00"),
        "C": Decimal("2.00"),
        "D": Decimal("1.00"),
        "E": Decimal("0.00"),
    }

    for student in Student.objects.using(database).all().iterator():
        weighted_points = Decimal("0.00")
        total_credits = Decimal("0.00")
        records = AcademicRecord.objects.using(database).filter(
            student_id=student.pk
        ).values_list("grade", "credits")

        for grade, credits in records:
            weighted_points += grade_points[grade] * credits
            total_credits += credits

        gpa = (
            (weighted_points / total_credits).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            if total_credits
            else Decimal("0.00")
        )
        Student.objects.using(database).filter(pk=student.pk).update(gpa=gpa)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_program_studentcourseenrollment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="gpa",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=3,
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="credits",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("3.00"),
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.01")
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="academicrecord",
            name="credits",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("3.00"),
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.01")
                    )
                ],
            ),
        ),
        migrations.RunPython(
            calculate_existing_gpas,
            migrations.RunPython.noop,
        ),
    ]
