from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import AcademicRecord, recalculate_student_gpa


@receiver(pre_save, sender=AcademicRecord)
def remember_previous_record_student(sender, instance, raw=False, **kwargs):
    if not raw and instance.pk:
        instance._previous_student_id = (
            sender.objects.filter(pk=instance.pk)
            .values_list("student_id", flat=True)
            .first()
        )


@receiver(post_save, sender=AcademicRecord)
def update_gpa_after_record_save(sender, instance, raw=False, **kwargs):
    if raw:
        return

    student_ids = {
        instance.student_id,
        getattr(instance, "_previous_student_id", None),
    }
    for student_id in student_ids - {None}:
        recalculate_student_gpa(student_id)


@receiver(post_delete, sender=AcademicRecord)
def update_gpa_after_record_delete(sender, instance, **kwargs):
    recalculate_student_gpa(instance.student_id)
