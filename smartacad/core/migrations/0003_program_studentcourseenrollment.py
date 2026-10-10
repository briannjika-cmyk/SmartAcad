from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_programs(apps, schema_editor):
    Program = apps.get_model("core", "Program")
    Student = apps.get_model("core", "Student")
    database = schema_editor.connection.alias

    names = (
        Student.objects.using(database)
        .exclude(programme="")
        .values_list("programme", flat=True)
        .distinct()
        .order_by("programme")
    )
    for index, name in enumerate(names, start=1):
        program, _ = Program.objects.using(database).get_or_create(
            name=name,
            defaults={"program_code": f"LEGACY-{index:04d}"},
        )
        Student.objects.using(database).filter(
            programme=name,
            program__isnull=True,
        ).update(program_id=program.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_studentquestionnaire_submitted"),
    ]

    operations = [
        migrations.CreateModel(
            name="Program",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("program_code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name="student",
            name="program",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="core.program",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="program",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="core.program",
            ),
        ),
        migrations.RunPython(
            assign_legacy_programs,
            migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="StudentCourseEnrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_enrollments",
                        to="core.course",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_enrollments",
                        to="core.student",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("student", "course"),
                        name="uniq_student_course_enroll",
                    ),
                ],
            },
        ),
    ]
