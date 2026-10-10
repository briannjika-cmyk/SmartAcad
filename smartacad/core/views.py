import logging

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Student,
    Lecturer,
    Course,
    AcademicRecord,
    StudentQuestionnaire,
    Attendance,
    Program,
)
from .forms import (
    AcademicRecordUpdateForm,
    StudentAdmissionForm,
    grade_for_marks,
)
from .academic_risk import (
    FEATURES,
    HIGH_RISK_THRESHOLD,
    METADATA_PATH,
    MODEL_PATH,
    classify_risk,
    intervention_recommendations,
    load_model,
    load_model_metadata,
    questionnaire_features,
    recommendations_for_missing_data,
)


logger = logging.getLogger(__name__)


def home(request):
    return redirect("login")


def smartacad_login(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect_user_by_role(user)

        error = "Invalid username or password."

    return render(
        request,
        "login.html",
        {"error": error},
    )


def smartacad_logout(request):
    logout(request)
    return redirect("login")


@login_required
def change_password(request):
    is_student = (
        request.user.groups.filter(name="Student").exists()
        or Student.objects.filter(user=request.user).exists()
    )
    is_academic_admin = request.user.groups.filter(
        name="Academic Admin"
    ).exists()
    is_lecturer = (
        request.user.groups.filter(name="Lecturer").exists()
        or Lecturer.objects.filter(user=request.user).exists()
    )
    if not (is_student or is_academic_admin or is_lecturer):
        return redirect_user_by_role(request.user)
    dashboard_url = (
        "student_dashboard"
        if is_student
        else "lecturer_dashboard"
        if is_lecturer
        else "academic_admin_dashboard"
    )

    form = PasswordChangeForm(
        user=request.user,
        data=request.POST if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("change_password")

    return render(
        request,
        "change_password.html",
        {"form": form, "dashboard_url": dashboard_url},
    )


def redirect_user_by_role(user):
    if user.is_superuser:
        return redirect("/admin/")

    if user.groups.filter(name="System Administrator").exists():
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        return redirect("/admin/")

    if user.is_staff:
        return redirect("/admin/")

    if user.groups.filter(name="Student").exists():
        return redirect("student_dashboard")

    if user.groups.filter(name="Lecturer").exists():
        return redirect("lecturer_dashboard")

    if user.groups.filter(name="Academic Admin").exists():
        return redirect("academic_admin_dashboard")

    return redirect("login")


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(
            request,
            "student_dashboard.html",
            {
                "error": (
                    "Your account is not linked to a student record. "
                    "Please contact the administrator."
                )
            },
        )

    attendance_records = (
        Attendance.objects
        .filter(student=student)
        .order_by("-date")
    )

    total_classes = attendance_records.count()
    present_classes = attendance_records.filter(status="Present").count()

    if total_classes > 0:
        attendance_percentage = (
            present_classes / total_classes
        ) * 100
    else:
        attendance_percentage = 0

    try:
        questionnaire = StudentQuestionnaire.objects.get(
            student=student,
            submitted=True,
        )
    except StudentQuestionnaire.DoesNotExist:
        questionnaire = None

    context = {
        "student": student,
        "total_classes": total_classes,
        "present_classes": present_classes,
        "attendance_percentage": attendance_percentage,
        "questionnaire": questionnaire,
    }

    return render(
        request,
        "student_dashboard.html",
        context,
    )


@login_required
def student_academic_results(request):
    student = get_object_or_404(Student, user=request.user)
    academic_records = (
        AcademicRecord.objects
        .filter(student=student)
        .order_by("-academic_year", "course_code")
    )

    return render(
        request,
        "student_academic_results.html",
        {
            "student": student,
            "academic_records": academic_records,
        },
    )


@login_required
def student_attendance_records(request):
    student = get_object_or_404(Student, user=request.user)
    attendance_records = (
        Attendance.objects
        .filter(student=student)
        .order_by("course_code", "-date")
    )

    attendance_table = []
    course_codes = (
        attendance_records
        .values_list("course_code", flat=True)
        .distinct()
        .order_by("course_code")
    )

    for course_code in course_codes:
        course_records = attendance_records.filter(
            course_code=course_code
        ).order_by("-date")
        total_course_classes = course_records.count()
        present_course_classes = course_records.filter(
            status="Present"
        ).count()
        attendance_table.append(
            {
                "course_code": course_code,
                "present_classes": present_course_classes,
                "total_classes": total_course_classes,
                "attendance_percentage": (
                    present_course_classes / total_course_classes * 100
                ),
            }
        )

    return render(
        request,
        "student_attendance_records.html",
        {
            "student": student,
            "attendance_table": attendance_table,
        },
    )


# =========================================================
# STUDENT QUESTIONNAIRE
# =========================================================

LEARNING_DIFFICULTY_OPTIONS = (
    "No significant difficulties",
    "Understanding course concepts",
    "Concentration",
    "Time management",
    "Language barriers",
    "Access to learning resources",
    "Exam or test anxiety",
    "Other",
)

STUDY_HABIT_OPTIONS = (
    "Following a daily study schedule",
    "Weekly revision",
    "Studying with a group",
    "Taking notes",
    "Practising with questions",
    "Using online learning resources",
    "Seeking help from a lecturer or tutor",
    "Other",
)


def questionnaire_choice_context(value, choices):
    selected = []
    details = []
    for line in value.splitlines():
        if line in choices:
            selected.append(line)
        elif line.startswith("Additional details: "):
            details.append(line.removeprefix("Additional details: "))
        elif line:
            details.append(line)
    return selected, "\n".join(details)


@login_required
def student_questionnaire(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect("student_dashboard")

    questionnaire, created = StudentQuestionnaire.objects.get_or_create(
        student=student
    )

    if request.method == "POST":
        study_hours = request.POST.get("study_hours")
        assignment_completion = request.POST.get(
            "assignment_completion"
        )
        learning_difficulties = request.POST.getlist(
            "learning_difficulties"
        )
        study_habits = request.POST.getlist("study_habits")
        learning_difficulties = [
            option for option in learning_difficulties
            if option in LEARNING_DIFFICULTY_OPTIONS
        ]
        study_habits = [
            option for option in study_habits
            if option in STUDY_HABIT_OPTIONS
        ]
        difficulty_details = request.POST.get(
            "learning_difficulties_details", ""
        ).strip()
        habit_details = request.POST.get("study_habits_details", "").strip()
        learning_resource_access = request.POST.get(
            "learning_resource_access"
        )

        questionnaire.study_hours = (
            study_hours if study_hours else None
        )
        questionnaire.assignment_completion = (
            assignment_completion
            if assignment_completion
            else None
        )
        if difficulty_details:
            learning_difficulties.append(
                f"Additional details: {difficulty_details}"
            )
        if habit_details:
            study_habits.append(f"Additional details: {habit_details}")
        questionnaire.learning_difficulties = "\n".join(
            learning_difficulties
        )
        questionnaire.study_habits = "\n".join(study_habits)
        questionnaire.learning_resource_access = (
            learning_resource_access or ""
        )
        questionnaire.submitted = True
        questionnaire.save()

        messages.success(
            request,
            "Your questionnaire has been submitted successfully.",
        )

        return redirect("student_dashboard")

    context = {
        "student": student,
        "questionnaire": questionnaire,
        "learning_difficulty_options": LEARNING_DIFFICULTY_OPTIONS,
        "study_habit_options": STUDY_HABIT_OPTIONS,
    }
    (
        context["selected_learning_difficulties"],
        context["learning_difficulties_details"],
    ) = questionnaire_choice_context(
        questionnaire.learning_difficulties,
        LEARNING_DIFFICULTY_OPTIONS,
    )
    (
        context["selected_study_habits"],
        context["study_habits_details"],
    ) = questionnaire_choice_context(
        questionnaire.study_habits,
        STUDY_HABIT_OPTIONS,
    )

    return render(
        request,
        "student_questionnaire.html",
        context,
    )


# =========================================================
# LECTURER DASHBOARD
# =========================================================

@login_required
def lecturer_dashboard(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    try:
        lecturer = Lecturer.objects.get(user=request.user)
    except Lecturer.DoesNotExist:
        return render(
            request,
            "lecturer_dashboard.html",
            {
                "error": (
                    "Your account is not linked to a lecturer record. "
                    "Please contact the administrator."
                )
            },
        )

    courses = (
        Course.objects
        .filter(lecturer=lecturer)
        .order_by("course_code")
    )

    questionnaires = (
        StudentQuestionnaire.objects
        .filter(submitted=True)
        .select_related("student")
        .order_by("student__student_id")
    )
    course_codes = courses.values_list("course_code", flat=True)
    academic_records = AcademicRecord.objects.filter(
        course_code__in=course_codes
    )
    students = Student.objects.all().order_by("student_id")

    context = {
        "lecturer": lecturer,
        "courses": courses,
        "students": students,
        "questionnaires": questionnaires,
        "course_count": courses.count(),
        "student_count": students.count(),
        "academic_record_count": academic_records.count(),
        "questionnaire_count": questionnaires.count(),
    }

    return render(
        request,
        "lecturer_dashboard.html",
        context,
    )


# =========================================================
# LECTURER - ENTER MARKS
# =========================================================

@login_required
def lecturer_enter_marks(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    lecturer = get_object_or_404(
        Lecturer,
        user=request.user,
    )

    courses = (
        Course.objects
        .filter(lecturer=lecturer)
        .order_by("course_code")
    )

    students = Student.objects.all().order_by("student_id")

    selected_student = None
    selected_course = None

    student_id = request.GET.get("student_id")
    course_id = request.GET.get("course_id")

    if student_id:
        selected_student = get_object_or_404(
            Student,
            id=student_id,
        )

    if course_id:
        selected_course = get_object_or_404(
            Course,
            id=course_id,
            lecturer=lecturer,
        )

    if request.method == "POST":
        student_id = request.POST.get("student")
        course_id = request.POST.get("course")
        semester = request.POST.get("semester")
        marks = request.POST.get("marks")
        academic_year = request.POST.get("academic_year")

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        course = get_object_or_404(
            Course,
            id=course_id,
            lecturer=lecturer,
        )

        if not all(
            [
                semester,
                marks,
                academic_year,
            ]
        ):
            messages.error(
                request,
                "Please fill in all required fields.",
            )
        else:
            try:
                marks_value = float(marks)

                if marks_value < 0 or marks_value > 100:
                    messages.error(
                        request,
                        "Marks must be between 0 and 100.",
                    )
                elif AcademicRecord.objects.filter(
                    student=student,
                    course_code=course.course_code,
                ).exists():
                    messages.error(
                        request,
                        "A result for this student and course "
                        "has already been entered.",
                    )
                else:
                    grade = grade_for_marks(marks_value)
                    AcademicRecord.objects.create(
                        student=student,
                        course_code=course.course_code,
                        course_name=course.course_name,
                        semester=semester,
                        marks=marks_value,
                        grade=grade,
                        academic_year=academic_year,
                        credits=course.credits,
                    )

                    messages.success(
                        request,
                        f"Marks for {student.full_name} "
                        "have been saved successfully.",
                    )

                    return redirect(
                        "lecturer_academic_records"
                    )

            except ValueError:
                messages.error(
                    request,
                    "Please enter a valid mark.",
                )

    return render(
        request,
        "lecturer_enter_marks.html",
        {
            "lecturer": lecturer,
            "courses": courses,
            "students": students,
            "selected_student": selected_student,
            "selected_course": selected_course,
        },
    )


# =========================================================
# LECTURER - STUDENTS
# =========================================================

@login_required
def lecturer_students(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    lecturer = get_object_or_404(
        Lecturer,
        user=request.user,
    )

    search_query = request.GET.get("search", "").strip()

    students = Student.objects.all().order_by("student_id")

    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query)
            | Q(student_id__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    paginator = Paginator(students, 20)
    students_page = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "lecturer_students.html",
        {
            "lecturer": lecturer,
            "students": students_page,
            "search_query": search_query,
        },
    )


# =========================================================
# LECTURER - ACADEMIC RECORDS
# =========================================================

@login_required
def lecturer_academic_records(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    lecturer = get_object_or_404(
        Lecturer,
        user=request.user,
    )

    search_query = request.GET.get("search", "").strip()

    course_codes = Course.objects.filter(
        lecturer=lecturer
    ).values_list(
        "course_code",
        flat=True,
    )

    records = (
        AcademicRecord.objects
        .select_related("student")
        .filter(course_code__in=course_codes)
        .order_by(
            "-academic_year",
            "student__student_id",
        )
    )

    if search_query:
        records = records.filter(
            Q(student__full_name__icontains=search_query)
            | Q(student__student_id__icontains=search_query)
            | Q(course_code__icontains=search_query)
            | Q(course_name__icontains=search_query)
        )

    paginator = Paginator(records, 20)
    records_page = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "lecturer_academic_records.html",
        {
            "lecturer": lecturer,
            "records": records_page,
            "search_query": search_query,
        },
    )


# =========================================================
# LECTURER - ATTENDANCE
# =========================================================

@login_required
def lecturer_attendance(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    lecturer = get_object_or_404(
        Lecturer,
        user=request.user,
    )

    course_codes = Course.objects.filter(
        lecturer=lecturer
    ).values_list(
        "course_code",
        flat=True,
    )

    search_query = request.GET.get("search", "").strip()

    attendance_records = (
        Attendance.objects
        .filter(course_code__in=course_codes)
        .select_related("student")
        .order_by(
            "student__student_id",
            "course_code",
            "-date",
        )
    )

    if search_query:
        attendance_records = attendance_records.filter(
            Q(student__full_name__icontains=search_query)
            | Q(student__student_id__icontains=search_query)
        )

    attendance_table = []

    student_ids = (
        attendance_records
        .values_list("student_id", flat=True)
        .distinct()
        .order_by("student_id")
    )

    for student_id in student_ids:
        student_records = attendance_records.filter(
            student_id=student_id
        )

        student = student_records.first().student
        total_classes = student_records.count()
        present_classes = student_records.filter(
            status="Present"
        ).count()

        if total_classes > 0:
            attendance_percentage = (
                present_classes / total_classes
            ) * 100
        else:
            attendance_percentage = 0

        attendance_table.append(
            {
                "student": student,
                "present_classes": present_classes,
                "total_classes": total_classes,
                "attendance_percentage": attendance_percentage,
            }
        )

    paginator = Paginator(attendance_table, 20)
    attendance_page = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "lecturer_attendance.html",
        {
            "lecturer": lecturer,
            "attendance_table": attendance_page,
            "search_query": search_query,
        },
    )


# =========================================================
# LECTURER - SAVE ATTENDANCE FROM DASHBOARD
# =========================================================

@login_required
def lecturer_save_attendance(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    lecturer = get_object_or_404(
        Lecturer,
        user=request.user,
    )

    if request.method != "POST":
        return redirect("lecturer_dashboard")

    student_id = request.POST.get("student_id", "").strip()
    course_code = request.POST.get("course_code")
    date = request.POST.get("date")
    status = request.POST.get("status")

    course_exists = Course.objects.filter(
        lecturer=lecturer,
        course_code=course_code,
    ).exists()

    if not all(
        [
            student_id,
            course_code,
            date,
            status,
            course_exists,
        ]
    ):
        messages.error(
            request,
            "Please provide valid attendance information.",
        )
        return redirect("lecturer_dashboard")

    student = Student.objects.filter(student_id=student_id).first()
    if student is None:
        messages.error(
            request,
            f"No student was found with ID {student_id}.",
        )
        return redirect("lecturer_dashboard")

    attendance_details = {
        "student": student,
        "course_code": course_code,
        "date": date,
    }

    if Attendance.objects.filter(**attendance_details).exists():
        messages.error(
            request,
            "Attendance for this student, course, and date "
            "has already been entered.",
        )
        return redirect("lecturer_dashboard")

    try:
        with transaction.atomic():
            Attendance.objects.create(
                **attendance_details,
                status=status,
            )
    except IntegrityError:
        messages.error(
            request,
            "Attendance for this student, course, and date "
            "has already been entered.",
        )
        return redirect("lecturer_dashboard")

    messages.success(
        request,
        "Attendance has been saved successfully.",
    )

    return redirect("lecturer_dashboard")


# =========================================================
# LECTURER - QUESTIONNAIRES
# =========================================================

@login_required
def lecturer_questionnaires(request):
    if not request.user.groups.filter(name="Lecturer").exists():
        return redirect_user_by_role(request.user)

    lecturer = get_object_or_404(
        Lecturer,
        user=request.user,
    )

    students = Student.objects.all().order_by("student_id")

    submitted_questionnaires = (
        StudentQuestionnaire.objects
        .filter(submitted=True)
        .select_related("student")
        .order_by("student__student_id")
    )

    submitted_student_ids = submitted_questionnaires.values_list(
        "student_id",
        flat=True,
    )

    students_not_submitted = (
        students
        .exclude(id__in=submitted_student_ids)
        .order_by("student_id")
    )

    return render(
        request,
        "lecturer_questionnaires.html",
        {
            "lecturer": lecturer,
            "submitted_questionnaires": submitted_questionnaires,
            "students_not_submitted": students_not_submitted,
            "submitted_count": submitted_questionnaires.count(),
            "not_submitted_count": students_not_submitted.count(),
        },
    )


# =========================================================
# ACADEMIC ADMIN DASHBOARD
# =========================================================

@login_required
def academic_admin_dashboard(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    total_students = Student.objects.count()
    total_lecturers = Lecturer.objects.count()
    total_courses = Course.objects.count()
    total_academic_records = AcademicRecord.objects.count()
    total_questionnaires = StudentQuestionnaire.objects.filter(
        submitted=True
    ).count()
    total_attendance_records = Attendance.objects.count()

    students = list(Student.objects.all().order_by("student_id"))
    attendance_summary = {
        row["student_id"]: row
        for row in Attendance.objects.values("student_id").annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status="Present")),
        )
    }
    students_with_records = set(
        AcademicRecord.objects.values_list(
            "student_id",
            flat=True,
        ).distinct()
    )
    questionnaires = {
        questionnaire.student_id: questionnaire
        for questionnaire in StudentQuestionnaire.objects.filter(
            submitted=True
        )
    }
    risk_students = []

    model = None
    model_metadata = None
    model_error = None
    risk_threshold = HIGH_RISK_THRESHOLD
    model_ready = MODEL_PATH.exists() or METADATA_PATH.exists()
    if model_ready:
        try:
            model = load_model()
            model_metadata = load_model_metadata()
            if tuple(model_metadata["features"]) != FEATURES:
                raise ValueError(
                    "The trained model feature schema does not match "
                    "the current application."
                )
            risk_threshold = model_metadata.get(
                "decision_policy", {}
            ).get("high_risk_threshold", HIGH_RISK_THRESHOLD)
            if (
                isinstance(risk_threshold, bool)
                or not isinstance(risk_threshold, (int, float))
                or not 0 <= risk_threshold <= 1
            ):
                raise ValueError(
                    "The trained model has an invalid High-risk threshold."
                )
        except (
            AttributeError,
            EOFError,
            KeyError,
            ModuleNotFoundError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            logger.exception("Could not load the academic-risk model.")
            model_error = str(exc)
            model = None
            model_metadata = None

    risk_order = {"High": 0, "Medium": 1, "Low": 2}
    filtered_risk_students = []
    for student in students:
        attendance = attendance_summary.get(
            student.pk,
            {"total": 0, "present": 0},
        )
        total_classes = attendance["total"]
        attendance_percentage = (
            attendance["present"] / total_classes * 100
            if total_classes
            else None
        )
        questionnaire = questionnaires.get(student.pk)
        study_hours = (
            questionnaire.study_hours if questionnaire else None
        )
        assignment_completion = (
            questionnaire.assignment_completion
            if questionnaire
            else None
        )
        required_data_available = (
            model is not None
            and student.pk in students_with_records
            and attendance_percentage is not None
            and questionnaire is not None
            and study_hours is not None
            and assignment_completion is not None
        )

        if required_data_available:
            features = [
                attendance_percentage,
                float(student.gpa),
                float(study_hours),
                float(assignment_completion),
                *questionnaire_features(questionnaire),
            ]
            probabilities = model.predict_proba([features])[0]
            class_probabilities = {
                label: float(probability)
                for label, probability in zip(model.classes_, probabilities)
            }
            risk_level = classify_risk(
                class_probabilities,
                high_risk_threshold=risk_threshold,
            )
            confidence = class_probabilities[risk_level]
            interventions = intervention_recommendations(
                risk_level=risk_level,
                attendance_percentage=attendance_percentage,
                gpa=float(student.gpa),
                study_hours=float(study_hours),
                assignment_completion=float(assignment_completion),
                questionnaire=questionnaire,
            )
        elif model is None:
            risk_level = "Model unavailable"
            confidence = None
            class_probabilities = {}
            interventions = [
                "Ask the system administrator to train or repair the "
                "academic-risk model before using predictions."
            ]
        else:
            risk_level = "Not enough data"
            confidence = None
            class_probabilities = {}
            missing_data = []
            if student.pk not in students_with_records:
                missing_data.append("academic results")
            if attendance_percentage is None:
                missing_data.append("attendance records")
            if questionnaire is None:
                missing_data.append("a submitted questionnaire")
            else:
                if study_hours is None:
                    missing_data.append("study hours in the questionnaire")
                if assignment_completion is None:
                    missing_data.append(
                        "assignment completion in the questionnaire"
                    )
            interventions = recommendations_for_missing_data(missing_data)

        risk_students.append(
            {
                "student": student,
                "gpa": student.gpa,
                "attendance_percentage": attendance_percentage,
                "assignment_completion": assignment_completion,
                "risk_level": risk_level,
                "model_score_percentage": (
                    round(confidence * 100, 1)
                    if confidence is not None
                    else None
                ),
                "class_probabilities": class_probabilities,
                "interventions": interventions,
                "risk_order": risk_order.get(risk_level, 3),
                "high_risk_probability": class_probabilities.get(
                    "High",
                    0,
                ),
            }
        )

    risk_students.sort(
        key=lambda item: (
            item["risk_order"],
            -item["high_risk_probability"],
            item["student"].student_id,
        )
    )
    filtered_risk_students = [
        item for item in risk_students if item["risk_level"] == "High"
    ]

    context = {
        "total_students": total_students,
        "total_lecturers": total_lecturers,
        "total_courses": total_courses,
        "total_academic_records": total_academic_records,
        "total_questionnaires": total_questionnaires,
        "total_attendance_records": total_attendance_records,
        "risk_preview": filtered_risk_students[:5],
        "risk_model_ready": model is not None,
        "risk_model_error": model_error,
        "risk_model_validation": (
            model_metadata.get("validation") if model_metadata else None
        ),
        "risk_model_decision_policy": (
            {"high_risk_threshold": risk_threshold}
            if model_metadata
            else None
        ),
    }

    return render(
        request,
        "academic_admin_dashboard.html",
        context,
    )


# =========================================================
# ACADEMIC ADMIN - STUDENTS
# =========================================================

@login_required
def academic_admin_students(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    admission_form = StudentAdmissionForm(academic_admin=request.user)
    if request.method == "POST":
        admission_form = StudentAdmissionForm(
            request.POST,
            academic_admin=request.user,
        )
        if admission_form.is_valid():
            admission_form.save()
            messages.success(
                request,
                "Student admitted and login account created successfully.",
            )
            return redirect("academic_admin_students")

    students_list = Student.objects.all().order_by("student_id")

    paginator = Paginator(students_list, 20)
    students = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "academic_admin_students.html",
        {
            "students": students,
            "admission_form": admission_form,
            "has_programs": admission_form.fields[
                "program"
            ].queryset.exists(),
        },
    )


@login_required
def academic_admin_programs(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    if request.method == "POST":
        return HttpResponseForbidden(
            "Only a system administrator can create programs."
        )

    return render(
        request,
        "academic_admin_programs.html",
        {
            "programs": Program.objects.select_related(
                "academic_admin"
            ).order_by("name"),
        },
    )


@login_required
def academic_admin_courses(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    return HttpResponseForbidden(
        "Only a system administrator can assign courses to lecturers."
    )


# =========================================================
# ACADEMIC ADMIN - ACADEMIC RECORDS
# =========================================================

@login_required
def academic_admin_academic_records(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    search_query = request.GET.get("search", "").strip()

    records_list = (
        AcademicRecord.objects
        .select_related("student")
        .order_by(
            "student__student_id",
            "-academic_year",
            "course_code",
        )
    )

    if search_query:
        records_list = records_list.filter(
            Q(student__full_name__icontains=search_query)
            | Q(student__student_id__icontains=search_query)
        )

    paginator = Paginator(records_list, 20)
    records = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "academic_admin_academic_records.html",
        {
            "records": records,
            "search_query": search_query,
        },
    )


@login_required
def academic_admin_update_academic_record(request, record_id):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    record = get_object_or_404(
        AcademicRecord.objects.select_related("student"),
        pk=record_id,
    )
    form = AcademicRecordUpdateForm(
        request.POST or None,
        instance=record,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Academic record updated successfully.",
        )
        return redirect("academic_admin_academic_records")

    return render(
        request,
        "academic_admin_update_academic_record.html",
        {
            "form": form,
            "record": record,
        },
    )


# =========================================================
# ACADEMIC ADMIN - ATTENDANCE
# =========================================================

@login_required
def academic_admin_attendance(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    search_query = request.GET.get("search", "").strip()
    attendance_list = Attendance.objects.select_related("student")
    if search_query:
        matching_course_codes = Course.objects.filter(
            course_name__icontains=search_query
        ).values_list("course_code", flat=True)
        attendance_list = attendance_list.filter(
            Q(course_code__icontains=search_query)
            | Q(course_code__in=matching_course_codes)
            | Q(student__student_id__icontains=search_query)
            | Q(student__full_name__icontains=search_query)
        )

    course_groups = {}
    course_names = dict(
        Course.objects.filter(
            course_code__in=attendance_list.values("course_code").distinct()
        ).values_list("course_code", "course_name")
    )
    for record in attendance_list.order_by(
        "course_code",
        "student__student_id",
    ):
        group = course_groups.setdefault(
            record.course_code,
            {
                "course_code": record.course_code,
                "course_name": course_names.get(
                    record.course_code,
                    record.course_code,
                ),
                "students": {},
            },
        )
        student_summary = group["students"].setdefault(
            record.student_id,
            {
                "student": record.student,
                "present": 0,
                "total_classes": 0,
            },
        )
        student_summary["total_classes"] += 1
        if record.status == "Present":
            student_summary["present"] += 1

    for group in course_groups.values():
        summaries = list(group["students"].values())
        for summary in summaries:
            summary["attendance_percentage"] = (
                summary["present"] / summary["total_classes"] * 100
            )
        group["students"] = summaries

    paginator = Paginator(list(course_groups.values()), 10)
    attendance_courses = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "academic_admin_attendance.html",
        {
            "attendance_courses": attendance_courses,
            "search_query": search_query,
        },
    )


# =========================================================
# ACADEMIC ADMIN - QUESTIONNAIRES
# =========================================================

@login_required
def academic_admin_questionnaires(request):
    if not request.user.groups.filter(
        name="Academic Admin"
    ).exists():
        return redirect_user_by_role(request.user)

    questionnaire_list = (
        StudentQuestionnaire.objects
        .filter(submitted=True)
        .select_related("student")
        .order_by("student__student_id")
    )

    paginator = Paginator(questionnaire_list, 20)
    questionnaires = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "academic_admin_questionnaires.html",
        {"questionnaires": questionnaires},
    )
