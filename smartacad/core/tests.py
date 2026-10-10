from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import Group, User
from django.urls import reverse

from .models import (
    AcademicRecord,
    Attendance,
    Course,
    Lecturer,
    Program,
    Student,
    StudentCourseEnrollment,
    StudentQuestionnaire,
)
from .academic_risk import FEATURES, classify_risk, questionnaire_features


class StudentDashboardResultsTests(TestCase):
    def test_dashboard_shows_only_logged_in_students_results(self):
        user = User.objects.create_user(username="student1")
        student = Student.objects.create(
            user=user,
            student_id="STU001",
            full_name="Test Student",
            email="student1@example.com",
            programme="Computer Science",
            year_of_study=1,
            gpa="3.50",
        )
        other_student = Student.objects.create(
            student_id="STU002",
            full_name="Other Student",
            email="student2@example.com",
            programme="Mathematics",
            year_of_study=1,
            gpa="3.20",
        )
        AcademicRecord.objects.create(
            student=student,
            course_code="CS101",
            course_name="Introduction to Computing",
            semester="Semester 1",
            marks="72.50",
            grade="B",
            academic_year="2026",
        )
        AcademicRecord.objects.create(
            student=other_student,
            course_code="MATH999",
            course_name="Private Result",
            semester="Semester 1",
            marks="95.00",
            grade="A",
            academic_year="2026",
        )

        self.client.force_login(user)
        dashboard_response = self.client.get(reverse("student_dashboard"))
        results_response = self.client.get(
            reverse("student_academic_results")
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "View Academic Results")
        self.assertContains(dashboard_response, "View Attendance")
        self.assertNotContains(dashboard_response, "Introduction to Computing")
        self.assertEqual(results_response.status_code, 200)
        self.assertContains(results_response, "CS101")
        self.assertContains(results_response, "Introduction to Computing")
        self.assertContains(results_response, "72.50")
        self.assertContains(results_response, "B")
        self.assertNotContains(results_response, "MATH999")
        self.assertNotContains(results_response, "Private Result")

    def test_student_attendance_is_available_on_its_own_page(self):
        user = User.objects.create_user(username="student_attendance")
        student = Student.objects.create(
            user=user,
            student_id="STU003",
            full_name="Attendance Student",
            email="attendance@example.com",
            programme="Computer Science",
            year_of_study=1,
            gpa="3.50",
        )
        other_student = Student.objects.create(
            student_id="STU004",
            full_name="Other Attendance Student",
            email="other-attendance@example.com",
            programme="Mathematics",
            year_of_study=1,
            gpa="3.20",
        )
        Attendance.objects.create(
            student=student,
            course_code="CS101",
            date="2026-10-03",
            status="Present",
        )
        Attendance.objects.create(
            student=other_student,
            course_code="MATH101",
            date="2026-10-03",
            status="Absent",
        )

        self.client.force_login(user)
        dashboard_response = self.client.get(reverse("student_dashboard"))
        attendance_response = self.client.get(
            reverse("student_attendance_records")
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertNotContains(dashboard_response, "MATH101")
        self.assertEqual(attendance_response.status_code, 200)
        self.assertContains(attendance_response, "Course")
        self.assertContains(attendance_response, "CS101")
        self.assertContains(attendance_response, "Total Classes")
        self.assertContains(attendance_response, "Attendance %")
        self.assertNotContains(attendance_response, "Date")
        self.assertNotContains(attendance_response, "2026-10-03")
        self.assertContains(attendance_response, "Present")
        self.assertNotContains(attendance_response, "MATH101")


class DashboardPasswordChangeTests(TestCase):
    def test_student_can_change_password_and_remains_logged_in(self):
        student_user = User.objects.create_user(
            username="password_student",
            password="OriginalStrong!928",
        )
        student_user.groups.add(Group.objects.create(name="Student"))
        Student.objects.create(
            user=student_user,
            student_id="PW001",
            full_name="Password Student",
            email="password.student@example.com",
            programme="Computer Science",
            year_of_study=1,
        )
        self.client.force_login(student_user)

        dashboard = self.client.get(reverse("student_dashboard"))
        self.assertContains(dashboard, reverse("change_password"))

        response = self.client.post(
            reverse("change_password"),
            {
                "old_password": "OriginalStrong!928",
                "new_password1": "NewRiver!9284",
                "new_password2": "NewRiver!9284",
            },
        )

        self.assertRedirects(
            response,
            reverse("change_password"),
            fetch_redirect_response=False,
        )
        student_user.refresh_from_db()
        self.assertTrue(student_user.check_password("NewRiver!9284"))
        self.assertEqual(
            self.client.get(reverse("student_dashboard")).status_code,
            200,
        )

    def test_academic_admin_can_change_password(self):
        academic_admin = User.objects.create_user(
            username="password_academic_admin",
            password="OriginalStrong!928",
        )
        academic_admin.groups.add(
            Group.objects.create(name="Academic Admin")
        )
        self.client.force_login(academic_admin)

        dashboard = self.client.get(reverse("academic_admin_dashboard"))
        self.assertContains(dashboard, reverse("change_password"))

        response = self.client.post(
            reverse("change_password"),
            {
                "old_password": "OriginalStrong!928",
                "new_password1": "NewRiver!9284",
                "new_password2": "NewRiver!9284",
            },
        )

        self.assertRedirects(
            response,
            reverse("change_password"),
            fetch_redirect_response=False,
        )
        academic_admin.refresh_from_db()
        self.assertTrue(academic_admin.check_password("NewRiver!9284"))

    def test_lecturer_can_change_password_and_remains_logged_in(self):
        lecturer_user = User.objects.create_user(
            username="password_lecturer",
            password="OriginalStrong!928",
        )
        lecturer_user.groups.add(Group.objects.create(name="Lecturer"))
        Lecturer.objects.create(
            user=lecturer_user,
            lecturer_id="PWLEC01",
            full_name="Password Lecturer",
            email="password.lecturer@example.com",
            department="Computing",
        )
        self.client.force_login(lecturer_user)

        dashboard = self.client.get(reverse("lecturer_dashboard"))
        self.assertContains(dashboard, reverse("change_password"))

        response = self.client.post(
            reverse("change_password"),
            {
                "old_password": "OriginalStrong!928",
                "new_password1": "NewRiver!9284",
                "new_password2": "NewRiver!9284",
            },
        )

        self.assertRedirects(
            response,
            reverse("change_password"),
            fetch_redirect_response=False,
        )
        lecturer_user.refresh_from_db()
        self.assertTrue(lecturer_user.check_password("NewRiver!9284"))
        self.assertEqual(
            self.client.get(reverse("lecturer_dashboard")).status_code,
            200,
        )

    def test_password_change_rejects_incorrect_current_password(self):
        user = User.objects.create_user(
            username="invalid_current_password_student",
            password="OriginalStrong!928",
        )
        user.groups.add(Group.objects.create(name="Student"))
        self.client.force_login(user)

        response = self.client.post(
            reverse("change_password"),
            {
                "old_password": "IncorrectPassword!123",
                "new_password1": "NewRiver!9284",
                "new_password2": "NewRiver!9284",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your old password was entered incorrectly")
        user.refresh_from_db()
        self.assertTrue(user.check_password("OriginalStrong!928"))


class AcademicRiskModelTests(TestCase):
    def test_high_risk_threshold_is_applied_before_other_categories(self):
        self.assertEqual(
            classify_risk({"High": 0.30, "Low": 0.50, "Medium": 0.20}),
            "High",
        )
        self.assertEqual(
            classify_risk({"High": 0.29, "Low": 0.10, "Medium": 0.61}),
            "Medium",
        )

    def test_questionnaire_answers_map_to_training_features(self):
        questionnaire = SimpleNamespace(
            learning_difficulties=(
                "Understanding course concepts\n"
                "Exam or test anxiety\n"
                "Additional details: private response"
            ),
            study_habits=(
                "Weekly revision\n"
                "Seeking help from a lecturer or tutor"
            ),
        )

        features = questionnaire_features(questionnaire)

        self.assertEqual(len(features), len(FEATURES) - 4)
        self.assertEqual(
            features,
            [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        )

    def test_dashboard_shows_model_prediction_and_personalized_support(self):
        academic_admin = User.objects.create_user(
            username="risk_review_admin",
        )
        academic_admin.groups.add(
            Group.objects.create(name="Academic Admin")
        )
        student = Student.objects.create(
            student_id="RISK001",
            full_name="Risk Review Student",
            email="risk.review@example.com",
            programme="Computing",
            year_of_study=1,
            gpa="1.80",
        )
        AcademicRecord.objects.create(
            student=student,
            course_code="CS901",
            course_name="Foundations",
            semester="Semester 1",
            marks="40",
            grade="E",
            academic_year="2026",
        )
        Attendance.objects.create(
            student=student,
            course_code="CS901",
            date="2026-10-01",
            status="Absent",
        )
        StudentQuestionnaire.objects.create(
            student=student,
            submitted=True,
            study_hours="1.0",
            assignment_completion="35.00",
            learning_difficulties="Understanding course concepts",
            study_habits="Weekly revision",
        )

        class FakeRiskModel:
            classes_ = ("High", "Low", "Medium")

            def predict_proba(self, _features):
                return [[0.7, 0.1, 0.2]]

        metadata = {
            "features": list(FEATURES),
            "validation": {
                "method": "5-fold stratified cross-validation",
                "macro_f1": 0.72,
                "balanced_accuracy": 0.74,
                "per_class": {
                    "High": {
                        "precision": 0.41,
                        "recall": 0.68,
                        "support": 19,
                    },
                },
            },
            "decision_policy": {
                "high_risk_threshold": 0.30,
            },
        }
        self.client.force_login(academic_admin)
        with TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.joblib"
            metadata_path = Path(directory) / "model.json"
            model_path.touch()
            metadata_path.touch()
            with (
                patch("core.views.MODEL_PATH", model_path),
                patch("core.views.METADATA_PATH", metadata_path),
                patch("core.views.load_model", return_value=FakeRiskModel()),
                patch(
                    "core.views.load_model_metadata",
                    return_value=metadata,
                ),
            ):
                response = self.client.get(
                    reverse("academic_admin_dashboard")
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["risk_model_ready"])
        self.assertEqual(
            response.context["risk_model_decision_policy"][
                "high_risk_threshold"
            ],
            0.30,
        )
        item = response.context["risk_preview"][0]
        self.assertEqual(item["risk_level"], "High")
        self.assertEqual(item["model_score_percentage"], 70.0)
        self.assertContains(response, "High Risk")
        self.assertContains(response, "RISK001")
        self.assertContains(response, "Advisor check-in this week")
        self.assertNotContains(response, "Model Score")
        self.assertNotContains(response, "No trained model available.")

    def test_dashboard_does_not_predict_without_required_data(self):
        academic_admin = User.objects.create_user(
            username="incomplete_risk_admin",
        )
        academic_admin.groups.add(
            Group.objects.create(name="Academic Admin")
        )
        Student.objects.create(
            student_id="RISK002",
            full_name="Student Missing Baseline",
            email="missing.baseline@example.com",
            programme="Computing",
            year_of_study=1,
        )
        self.client.force_login(academic_admin)

        with TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.joblib"
            metadata_path = Path(directory) / "model.json"
            model_path.touch()
            metadata_path.touch()
            with (
                patch("core.views.MODEL_PATH", model_path),
                patch("core.views.METADATA_PATH", metadata_path),
                patch("core.views.load_model", return_value=object()),
                patch(
                    "core.views.load_model_metadata",
                    return_value={
                        "features": list(FEATURES),
                        "validation": {
                            "method": "5-fold stratified cross-validation",
                            "macro_f1": 0.5,
                            "balanced_accuracy": 0.5,
                            "per_class": {
                                "High": {"recall": 0.4},
                            },
                        },
                    },
                ),
            ):
                response = self.client.get(
                    reverse("academic_admin_dashboard")
                )

        self.assertEqual(response.context["risk_preview"], [])
        self.assertContains(response, "No students are available for risk review.")


class UnifiedLoginPageTests(TestCase):
    def test_short_login_url_opens_the_shared_login_page(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username")
        self.assertContains(response, "password")

    def test_main_admin_dashboard_uses_smartacad_branding_and_standard_layout(self):
        admin_user = User.objects.create_superuser(
            username="dashboardadmin",
            email="dashboardadmin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(admin_user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SmartAcad Administration")
        self.assertContains(response, "Core")
        self.assertContains(response, "Programs")
        self.assertContains(response, "Recent actions")
        self.assertNotContains(response, "Welcome back, dashboardadmin")

    def test_all_application_roles_can_sign_in_through_the_same_page(self):
        role_destinations = [
            ("Student", "student_dashboard", False, "login"),
            ("Lecturer", "lecturer_dashboard", False, "login"),
            ("Academic Admin", "academic_admin_dashboard", False, "login"),
            ("System Administrator", "/admin/", False, "admin_login"),
        ]

        for index, (role, destination, is_staff, login_route) in enumerate(
            role_destinations,
            start=1,
        ):
            with self.subTest(role=role):
                user = User.objects.create_user(
                    username=f"user{index}",
                    password="StrongPassword123!",
                    is_staff=is_staff,
                )
                user.groups.add(Group.objects.create(name=role))

                response = self.client.post(
                    reverse(login_route),
                    {
                        "username": user.username,
                        "password": "StrongPassword123!",
                    },
                )

                expected_url = (
                    destination
                    if destination.startswith("/")
                    else reverse(destination)
                )
                self.assertRedirects(
                    response,
                    expected_url,
                    fetch_redirect_response=False,
                )
                user.refresh_from_db()
                if role == "System Administrator":
                    self.assertTrue(user.is_staff)
                    self.assertEqual(
                        self.client.get("/admin/").status_code,
                        200,
                    )
                self.client.logout()

    def test_admin_login_uses_smartacad_login_page_and_logs_into_admin(self):
        admin_user = User.objects.create_superuser(
            username="systemadmin",
            email="systemadmin@example.com",
            password="StrongPassword123!",
        )

        login_page = self.client.get("/admin/login/?next=/admin/")
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "Academic Performance Management System")
        self.assertContains(login_page, 'name="username"')
        self.assertContains(login_page, 'name="password"')

        response = self.client.post(
            "/admin/login/?next=/admin/",
            {
                "username": admin_user.username,
                "password": "StrongPassword123!",
                "next": "/admin/",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_superuser)

    def test_admin_logout_redirects_directly_to_shared_login_page(self):
        admin_user = User.objects.create_superuser(
            username="logoutadmin",
            email="logoutadmin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(admin_user)

        response = self.client.get("/admin/logout/")

        self.assertRedirects(
            response,
            reverse("login"),
            fetch_redirect_response=False,
        )
        login_page = self.client.get(response.url)
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "Academic Performance Management System")
        self.assertFalse(login_page.wsgi_request.user.is_authenticated)


class AcademicAdminWorkflowsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="academic_admin",
            password="StrongPassword123!",
        )
        self.user.groups.add(Group.objects.create(name="Academic Admin"))
        self.program = Program.objects.create(
            program_code="BCS",
            name="Computer Science",
            academic_admin=self.user,
        )
        self.lecturer_user = User.objects.create_user(
            username="lecturer_for_admin",
            password="StrongPassword123!",
        )
        self.lecturer = Lecturer.objects.create(
            user=self.lecturer_user,
            program=self.program,
            lecturer_id="LEC500",
            full_name="Assigned Lecturer",
            email="assigned.lecturer@example.com",
            department="Computing",
        )
        self.client.force_login(self.user)

    def test_admin_academic_records_searches_students_by_name_or_id(self):
        searchable_student = Student.objects.create(
            student_id="STU506",
            full_name="Searchable Records Student",
            email="searchable.records@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
            gpa="3.40",
        )
        other_student = Student.objects.create(
            student_id="STU507",
            full_name="Different Student",
            email="different.student@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
            gpa="3.10",
        )
        AcademicRecord.objects.create(
            student=searchable_student,
            course_code="CS506",
            course_name="Student Search",
            semester="Semester 1",
            marks="82.00",
            grade="A",
            academic_year="2026",
        )
        AcademicRecord.objects.create(
            student=other_student,
            course_code="CS507",
            course_name="Other Course",
            semester="Semester 1",
            marks="72.00",
            grade="B",
            academic_year="2026",
        )

        name_search = self.client.get(
            reverse("academic_admin_academic_records"),
            {"search": "Searchable Records"},
        )
        self.assertEqual(name_search.status_code, 200)
        self.assertEqual(name_search.context["records"].paginator.count, 1)
        self.assertContains(name_search, "Searchable Records Student")
        self.assertNotContains(name_search, "Different Student")
        self.assertContains(name_search, 'name="search"')

        id_search = self.client.get(
            reverse("academic_admin_academic_records"),
            {"search": "STU506"},
        )
        self.assertEqual(id_search.context["records"].paginator.count, 1)
        self.assertContains(id_search, "Searchable Records Student")

        no_match = self.client.get(
            reverse("academic_admin_academic_records"),
            {"search": "No such student"},
        )
        self.assertEqual(no_match.context["records"].paginator.count, 0)
        self.assertContains(
            no_match,
            "No academic records match your search.",
        )

    def test_academic_admin_can_update_record_and_grade_recalculates_gpa(self):
        student = Student.objects.create(
            student_id="STU511",
            full_name="Record Update Student",
            email="record.update@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
        )
        record = AcademicRecord.objects.create(
            student=student,
            course_code="CS511",
            course_name="Record Update Course",
            semester="Semester 1",
            marks="65.00",
            grade="B",
            academic_year="2026",
            credits="3.00",
        )
        listing = self.client.get(
            reverse("academic_admin_academic_records")
        )
        update_url = reverse(
            "academic_admin_update_academic_record",
            args=[record.pk],
        )
        self.assertContains(listing, update_url)
        self.assertContains(listing, "Update")
        self.assertEqual(self.client.get(update_url).status_code, 200)

        response = self.client.post(
            update_url,
            {
                "student": student.pk,
                "course_code": "CS511",
                "course_name": "Record Update Course",
                "semester": "Semester 2",
                "marks": "75.00",
                "academic_year": "2026",
                "credits": "3.00",
            },
        )

        self.assertRedirects(
            response,
            reverse("academic_admin_academic_records"),
            fetch_redirect_response=False,
        )
        record.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(record.semester, "Semester 2")
        self.assertEqual(str(record.marks), "75.00")
        self.assertEqual(record.grade, "A")
        self.assertEqual(str(student.gpa), "4.00")

    def test_academic_admin_update_rejects_marks_outside_allowed_range(self):
        student = Student.objects.create(
            student_id="STU512",
            full_name="Invalid Update Student",
            email="invalid.update@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
        )
        record = AcademicRecord.objects.create(
            student=student,
            course_code="CS512",
            course_name="Validation Course",
            semester="Semester 1",
            marks="65.00",
            grade="B",
            academic_year="2026",
        )
        response = self.client.post(
            reverse(
                "academic_admin_update_academic_record",
                args=[record.pk],
            ),
            {
                "student": student.pk,
                "course_code": "CS512",
                "course_name": "Validation Course",
                "semester": "Semester 1",
                "marks": "105.00",
                "academic_year": "2026",
                "credits": "3.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(str(record.marks), "65.00")
        self.assertEqual(record.grade, "B")

    def test_academic_admin_can_view_programs_but_cannot_create_them(self):
        page = self.client.get(reverse("academic_admin_programs"))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, self.program.name)
        self.assertNotContains(page, "Create Program")
        dashboard = self.client.get(reverse("academic_admin_dashboard"))
        self.assertNotContains(dashboard, "Manage Programs")
        student_page = self.client.get(reverse("academic_admin_students"))
        self.assertNotContains(student_page, "Manage Programs")

        response = self.client.post(
            reverse("academic_admin_programs"),
            {"program_code": "BBA", "name": "Business Administration"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Program.objects.filter(program_code="BBA").exists()
        )

    def test_admin_admission_creates_student_login_and_allocates_program(self):
        course = Course.objects.create(
            lecturer=self.lecturer,
            program=self.program,
            course_code="CS500",
            course_name="Foundations",
        )
        response = self.client.post(
            reverse("academic_admin_students"),
            {
                "student_id": "STU500",
                "full_name": "New Student",
                "email": "new.student@example.com",
                "program": self.program.id,
                "year_of_study": 1,
                "password": "MangoRiver!849",
            },
        )

        self.assertRedirects(
            response,
            reverse("academic_admin_students"),
            fetch_redirect_response=False,
        )
        student = Student.objects.get(student_id="STU500")
        self.assertEqual(student.program, self.program)
        self.assertEqual(student.programme, self.program.name)
        self.assertEqual(student.user.username, student.student_id)
        self.assertTrue(student.user.check_password("MangoRiver!849"))
        self.assertEqual(str(student.gpa), "0.00")
        self.assertTrue(student.user.groups.filter(name="Student").exists())
        self.assertTrue(
            StudentCourseEnrollment.objects.filter(
                student=student,
                course=course,
            ).exists()
        )

    def test_admission_rejects_programs_not_assigned_to_this_admin(self):
        other_admin = User.objects.create_user(username="other_academic_admin")
        other_admin.groups.add(
            Group.objects.get_or_create(name="Academic Admin")[0]
        )
        other_program = Program.objects.create(
            program_code="MATH",
            name="Mathematics",
            academic_admin=other_admin,
        )

        response = self.client.post(
            reverse("academic_admin_students"),
            {
                "student_id": "STU599",
                "full_name": "Wrong Program Student",
                "email": "wrong.program@example.com",
                "program": other_program.pk,
                "year_of_study": 1,
                "password": "MangoRiver!849",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(Student.objects.filter(student_id="STU599").exists())

    def test_admission_reports_existing_login_username_without_server_error(self):
        User.objects.create_user(username="STU598")

        response = self.client.post(
            reverse("academic_admin_students"),
            {
                "student_id": "STU598",
                "full_name": "Duplicate Login Student",
                "email": "duplicate.login@example.com",
                "program": self.program.pk,
                "year_of_study": 1,
                "password": "MangoRiver!849",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "An account with this student ID already exists.",
        )
        self.assertFalse(Student.objects.filter(student_id="STU598").exists())


    def test_admin_assigns_course_and_enrolls_student_in_matching_program(self):
        dashboard = self.client.get(reverse("academic_admin_dashboard"))
        self.assertNotContains(dashboard, "Assign Courses to Lecturers")

        course_response = self.client.post(
            reverse("academic_admin_courses"),
            {
                "existing_course": "",
                "course_code": "CS501",
                "course_name": "Algorithms",
                "credits": "4.00",
                "program": self.program.id,
                "lecturer": self.lecturer.id,
            },
        )
        self.assertEqual(course_response.status_code, 403)
        self.assertFalse(Course.objects.filter(course_code="CS501").exists())

    def test_admin_must_enter_course_credits_when_creating_a_course(self):
        response = self.client.post(
            reverse("academic_admin_courses"),
            {
                "existing_course": "",
                "course_code": "CS509",
                "course_name": "Credits Required",
                "program": self.program.id,
                "lecturer": self.lecturer.id,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Course.objects.filter(course_code="CS509").exists())

    def test_admin_credit_update_recalculates_weighted_gpa(self):
        student = Student.objects.create(
            student_id="STU510",
            full_name="Updated Credits Student",
            email="updated.credits@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
        )
        course = Course.objects.create(
            lecturer=self.lecturer,
            program=self.program,
            course_code="CS510",
            course_name="Credit Update",
            credits="3.00",
        )
        Course.objects.create(
            lecturer=self.lecturer,
            program=self.program,
            course_code="CS511",
            course_name="One Credit",
            credits="1.00",
        )
        AcademicRecord.objects.create(
            student=student,
            course_code="CS510",
            course_name=course.course_name,
            semester="Semester 1",
            marks="65.00",
            grade="B",
            academic_year="2026",
            credits="3.00",
        )
        AcademicRecord.objects.create(
            student=student,
            course_code="CS511",
            course_name="One Credit",
            semester="Semester 1",
            marks="75.00",
            grade="A",
            academic_year="2026",
            credits="1.00",
        )

        main_admin = User.objects.create_superuser(
            username="course_admin",
            email="course.admin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(main_admin)
        response = self.client.post(
            reverse("admin:core_course_change", args=[course.pk]),
            {
                "lecturer": self.lecturer.id,
                "program": self.program.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "credits": "4.00",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        course.refresh_from_db()
        self.assertEqual(str(course.credits), "4.00")
        self.assertEqual(str(student.gpa), "3.20")
        self.assertEqual(
            str(
                AcademicRecord.objects.get(
                    course_code="CS510"
                ).credits
            ),
            "4.00",
        )

    def test_reassigning_course_syncs_enrollment_to_its_new_program(self):
        other_program = Program.objects.create(
            program_code="MATH",
            name="Mathematics",
        )
        old_program_student = Student.objects.create(
            student_id="STU502",
            full_name="Computer Science Student",
            email="cs.student@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
            gpa="3.20",
        )
        new_program_student = Student.objects.create(
            student_id="STU504",
            full_name="Mathematics Student",
            email="math.student@example.com",
            programme=other_program.name,
            program=other_program,
            year_of_study=1,
            gpa="3.20",
        )
        course = Course.objects.create(
            lecturer=self.lecturer,
            program=self.program,
            course_code="MATH502",
            course_name="Mathematics Course",
        )
        StudentCourseEnrollment.objects.create(
            student=old_program_student,
            course=course,
        )

        main_admin = User.objects.create_superuser(
            username="reassignment_admin",
            email="reassignment.admin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(main_admin)
        response = self.client.post(
            reverse("admin:core_course_change", args=[course.pk]),
            {
                "lecturer": self.lecturer.id,
                "program": other_program.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "credits": course.credits,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            StudentCourseEnrollment.objects.filter(
                student=old_program_student,
                course=course,
            ).exists()
        )
        self.assertTrue(
            StudentCourseEnrollment.objects.filter(
                student=new_program_student,
                course=course,
            ).exists()
        )

    def test_admin_attendance_groups_courses_and_searches_student_or_course(self):
        student = Student.objects.create(
            student_id="STU505",
            full_name="Searchable Student",
            email="searchable.student@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
            gpa="3.10",
        )
        course = Course.objects.create(
            lecturer=self.lecturer,
            program=self.program,
            course_code="CS505",
            course_name="Searchable Algorithms",
        )
        Attendance.objects.create(
            student=student,
            course_code=course.course_code,
            date="2026-10-01",
            status="Present",
        )
        Attendance.objects.create(
            student=student,
            course_code=course.course_code,
            date="2026-10-02",
            status="Absent",
        )

        response = self.client.get(reverse("academic_admin_attendance"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["attendance_courses"]), 1)
        course_group = response.context["attendance_courses"][0]
        self.assertEqual(course_group["course_code"], course.course_code)
        self.assertEqual(len(course_group["students"]), 1)
        summary = course_group["students"][0]
        self.assertEqual(summary["present"], 1)
        self.assertEqual(summary["total_classes"], 2)
        self.assertEqual(summary["attendance_percentage"], 50)
        self.assertEqual(
            response.content.decode().count("CS505"),
            1,
        )
        self.assertContains(response, "Total Classes")
        self.assertContains(response, "Attendance %")
        self.assertContains(response, "50.0%")
        self.assertNotContains(response, "<th>Date</th>")
        self.assertNotContains(response, "2026-10-01")

        student_search = self.client.get(
            reverse("academic_admin_attendance"),
            {"search": "Searchable Student"},
        )
        self.assertEqual(
            len(student_search.context["attendance_courses"]),
            1,
        )
        self.assertEqual(
            len(student_search.context["attendance_courses"][0]["students"]),
            1,
        )

        course_search = self.client.get(
            reverse("academic_admin_attendance"),
            {"search": "Searchable Algorithms"},
        )
        self.assertEqual(
            len(course_search.context["attendance_courses"]),
            1,
        )

    def test_student_gpa_is_weighted_by_record_credits(self):
        student = Student.objects.create(
            student_id="STU508",
            full_name="GPA Calculation Student",
            email="gpa.calculation@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
        )
        three_credit_record = AcademicRecord.objects.create(
            student=student,
            course_code="CS601",
            course_name="Three Credit Course",
            semester="Semester 1",
            marks="65.00",
            grade="B",
            academic_year="2026",
            credits="3.00",
        )
        one_credit_record = AcademicRecord.objects.create(
            student=student,
            course_code="CS602",
            course_name="One Credit Course",
            semester="Semester 1",
            marks="75.00",
            grade="A",
            academic_year="2026",
            credits="1.00",
        )

        student.refresh_from_db()
        self.assertEqual(str(student.gpa), "3.25")

        three_credit_record.delete()
        student.refresh_from_db()
        self.assertEqual(str(student.gpa), "4.00")

        one_credit_record.delete()
        student.refresh_from_db()
        self.assertEqual(str(student.gpa), "0.00")

    def test_moving_academic_record_recalculates_both_student_gpas(self):
        former_student = Student.objects.create(
            student_id="STU509",
            full_name="Former Record Owner",
            email="former.record.owner@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
        )
        new_student = Student.objects.create(
            student_id="STU510",
            full_name="New Record Owner",
            email="new.record.owner@example.com",
            programme=self.program.name,
            program=self.program,
            year_of_study=1,
        )
        record = AcademicRecord.objects.create(
            student=former_student,
            course_code="CS603",
            course_name="Transferred Course",
            semester="Semester 1",
            marks="65.00",
            grade="B",
            academic_year="2026",
        )

        record.student = new_student
        record.save(update_fields=["student"])

        former_student.refresh_from_db()
        new_student.refresh_from_db()
        self.assertEqual(str(former_student.gpa), "0.00")
        self.assertEqual(str(new_student.gpa), "3.00")

    def test_raw_fixture_signals_do_not_recalculate_gpa(self):
        from unittest.mock import patch

        from .signals import (
            remember_previous_record_student,
            update_gpa_after_record_save,
        )

        record = AcademicRecord(
            id=999,
            student_id=999,
        )
        with patch("core.signals.recalculate_student_gpa") as recalculate:
            remember_previous_record_student(
                AcademicRecord,
                record,
                raw=True,
            )
            update_gpa_after_record_save(
                AcademicRecord,
                record,
                raw=True,
            )

        self.assertFalse(hasattr(record, "_previous_student_id"))
        recalculate.assert_not_called()


class MainAdminProgramCreationTests(TestCase):
    def test_system_administrator_can_create_program_in_django_admin(self):
        user = User.objects.create_user(
            username="system_admin",
            is_staff=True,
        )
        user.groups.add(Group.objects.create(name="System Administrator"))
        academic_admin = User.objects.create_user(
            username="assigned_academic_admin",
            first_name="Assigned",
            last_name="Admin",
        )
        academic_admin.groups.add(Group.objects.create(name="Academic Admin"))
        self.client.force_login(user)

        response = self.client.post(
            "/admin/core/program/add/",
            {
                "program_code": "BBA",
                "name": "Business Administration",
                "academic_admin": academic_admin.pk,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Program.objects.filter(
                program_code="BBA",
                name="Business Administration",
            ).exists()
        )
        program = Program.objects.get(program_code="BBA")
        self.assertEqual(program.academic_admin, academic_admin)

    def test_program_creation_requires_an_academic_admin_assignment(self):
        user = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/admin/core/program/add/",
            {
                "program_code": "BBA",
                "name": "Business Administration",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Program.objects.filter(program_code="BBA").exists())
        self.assertContains(response, "This field is required")

    def test_academic_admin_cannot_create_program_in_django_admin(self):
        user = User.objects.create_user(
            username="academic_admin_staff",
            is_staff=True,
        )
        user.groups.add(Group.objects.create(name="Academic Admin"))
        self.client.force_login(user)

        response = self.client.get("/admin/core/program/add/")

        self.assertEqual(response.status_code, 403)


class MainAdminLecturerCreationTests(TestCase):
    def test_main_admin_assigns_program_and_multiple_courses_when_adding_lecturer(self):
        academic_admin = User.objects.create_user(
            username="program_academic_admin",
        )
        academic_admin.groups.add(
            Group.objects.create(name="Academic Admin")
        )
        program = Program.objects.create(
            program_code="BCS",
            name="Computer Science",
            academic_admin=academic_admin,
        )
        student = Student.objects.create(
            student_id="STU901",
            full_name="Course Enrollment Student",
            email="course.enrollment@example.com",
            programme=program.name,
            program=program,
            year_of_study=1,
        )
        lecturer_user = User.objects.create_user(
            username="new_lecturer_user",
            email="new.lecturer@example.com",
        )
        main_admin = User.objects.create_superuser(
            username="lecturer_creator",
            email="lecturer.creator@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(main_admin)

        response = self.client.post(
            reverse("admin:core_lecturer_add"),
            {
                "user": lecturer_user.pk,
                "program": program.pk,
                "lecturer_id": "LEC901",
                "full_name": "New Lecturer",
                "email": "lecturer@example.com",
                "department": "Computing",
                "course_set-TOTAL_FORMS": "2",
                "course_set-INITIAL_FORMS": "0",
                "course_set-MIN_NUM_FORMS": "1",
                "course_set-MAX_NUM_FORMS": "1000",
                "course_set-0-course_code": "CS901",
                "course_set-0-course_name": "Algorithms",
                "course_set-0-credits": "3.00",
                "course_set-1-course_code": "CS902",
                "course_set-1-course_name": "Databases",
                "course_set-1-credits": "4.00",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302, response.content.decode())
        lecturer = Lecturer.objects.get(lecturer_id="LEC901")
        self.assertEqual(lecturer.program, program)
        self.assertTrue(
            lecturer.user.groups.filter(name="Lecturer").exists()
        )
        courses = Course.objects.filter(lecturer=lecturer).order_by(
            "course_code"
        )
        self.assertEqual(courses.count(), 2)
        self.assertEqual(
            list(courses.values_list("program_id", flat=True)),
            [program.pk, program.pk],
        )
        self.assertEqual(
            StudentCourseEnrollment.objects.filter(
                student=student,
                course__lecturer=lecturer,
            ).count(),
            2,
        )

    def test_academic_admin_cannot_create_lecturer_in_django_admin(self):
        academic_admin = User.objects.create_user(
            username="academic_admin_forbidden",
            is_staff=True,
        )
        academic_admin.groups.add(
            Group.objects.create(name="Academic Admin")
        )
        self.client.force_login(academic_admin)

        response = self.client.get(reverse("admin:core_lecturer_add"))

        self.assertEqual(response.status_code, 403)


class StudentQuestionnaireOptionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="questionnaire_student")
        self.student = Student.objects.create(
            user=self.user,
            student_id="STUQ01",
            full_name="Questionnaire Student",
            email="questionnaire.student@example.com",
            programme="Computer Science",
            year_of_study=1,
            gpa="3.50",
        )
        self.client.force_login(self.user)

    def test_questionnaire_offers_and_saves_multiple_options(self):
        page = self.client.get(reverse("student_questionnaire"))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Understanding course concepts")
        self.assertContains(page, "Weekly revision")

        response = self.client.post(
            reverse("student_questionnaire"),
            {
                "study_hours": "3.5",
                "assignment_completion": "80",
                "learning_difficulties": [
                    "Time management",
                    "Exam or test anxiety",
                ],
                "learning_difficulties_details": "Balancing work and study",
                "study_habits": [
                    "Weekly revision",
                    "Practising with questions",
                ],
                "study_habits_details": "I study more before exams",
                "learning_resource_access": "Library",
            },
        )

        self.assertRedirects(
            response,
            reverse("student_dashboard"),
            fetch_redirect_response=False,
        )
        questionnaire = StudentQuestionnaire.objects.get(student=self.student)
        self.assertEqual(
            questionnaire.learning_difficulties,
            "Time management\nExam or test anxiety\n"
            "Additional details: Balancing work and study",
        )
        self.assertEqual(
            questionnaire.study_habits,
            "Weekly revision\nPractising with questions\n"
            "Additional details: I study more before exams",
        )

        edit_page = self.client.get(reverse("student_questionnaire"))
        self.assertIn(
            "Time management",
            edit_page.context["selected_learning_difficulties"],
        )
        self.assertIn(
            "Weekly revision",
            edit_page.context["selected_study_habits"],
        )


class LecturerDuplicateEntryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lecturer1")
        self.user.groups.add(Group.objects.create(name="Lecturer"))
        self.lecturer = Lecturer.objects.create(
            user=self.user,
            lecturer_id="LEC001",
            full_name="Test Lecturer",
            email="lecturer@example.com",
            department="Computer Science",
        )
        self.student = Student.objects.create(
            student_id="STU101",
            full_name="Test Student",
            email="student101@example.com",
            programme="Computer Science",
            year_of_study=1,
            gpa="3.50",
        )
        self.course = Course.objects.create(
            lecturer=self.lecturer,
            course_code="CS101",
            course_name="Introduction to Computing",
        )
        self.client.force_login(self.user)

    def test_dashboard_statistics_match_saved_system_records(self):
        AcademicRecord.objects.create(
            student=self.student,
            course_code=self.course.course_code,
            course_name=self.course.course_name,
            semester="Semester 1",
            marks="72.50",
            grade="B",
            academic_year="2026",
        )
        StudentQuestionnaire.objects.create(
            student=self.student,
            submitted=True,
        )

        response = self.client.get(reverse("lecturer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["course_count"], 1)
        self.assertEqual(response.context["student_count"], 1)
        self.assertEqual(response.context["academic_record_count"], 1)
        self.assertEqual(response.context["questionnaire_count"], 1)

    def test_lecturer_can_view_submitted_questionnaire(self):
        StudentQuestionnaire.objects.create(
            student=self.student,
            submitted=True,
            study_hours="3.5",
            assignment_completion="80.00",
            learning_difficulties="Time management",
            study_habits="Weekly revision",
            learning_resource_access="Library and online materials",
        )

        dashboard_response = self.client.get(
            reverse("lecturer_dashboard")
        )
        questionnaire_response = self.client.get(
            reverse("lecturer_questionnaires")
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Student Questionnaires")
        self.assertNotContains(dashboard_response, "Weekly revision")
        self.assertEqual(questionnaire_response.status_code, 200)
        self.assertContains(questionnaire_response, "STU101")
        self.assertContains(questionnaire_response, "Time management")
        self.assertContains(
            questionnaire_response,
            "Library and online materials",
        )

    def test_duplicate_result_is_rejected(self):
        AcademicRecord.objects.create(
            student=self.student,
            course_code=self.course.course_code,
            course_name=self.course.course_name,
            semester="Semester 1",
            marks="72.50",
            grade="B",
            academic_year="2026",
        )

        response = self.client.post(
            reverse("lecturer_enter_marks"),
            {
                "student": self.student.id,
                "course": self.course.id,
                "semester": "Semester 2",
                "marks": "85",
                "academic_year": "2027",
                "grade": "A",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "has already been entered")
        self.assertEqual(AcademicRecord.objects.count(), 1)
        record = AcademicRecord.objects.get()
        self.assertEqual(str(record.marks), "72.50")
        self.assertEqual(record.grade, "B")

    def test_marks_determine_grade_from_requested_thresholds(self):
        from .views import grade_for_marks

        for marks, expected_grade in (
            (70, "A"),
            (60, "B"),
            (50, "C"),
            (40, "D"),
            (39.99, "E"),
        ):
            with self.subTest(marks=marks):
                self.assertEqual(grade_for_marks(marks), expected_grade)

        self.course.credits = "4.00"
        self.course.save(update_fields=["credits"])
        response = self.client.post(
            reverse("lecturer_enter_marks"),
            {
                "student": self.student.id,
                "course": self.course.id,
                "semester": "Semester 1",
                "marks": "69.99",
                "academic_year": "2026",
                "grade": "A",
            },
        )
        self.assertRedirects(
            response,
            reverse("lecturer_academic_records"),
            fetch_redirect_response=False,
        )
        record = AcademicRecord.objects.get()
        self.assertEqual(record.grade, "B")
        self.assertEqual(str(record.credits), "4.00")
        self.student.refresh_from_db()
        self.assertEqual(str(self.student.gpa), "3.00")

    def test_duplicate_attendance_is_rejected_without_overwriting(self):
        Attendance.objects.create(
            student=self.student,
            course_code=self.course.course_code,
            date="2026-10-03",
            status="Absent",
        )

        response = self.client.post(
            reverse("lecturer_save_attendance"),
            {
                "student_id": self.student.student_id,
                "course_code": self.course.course_code,
                "date": "2026-10-03",
                "status": "Present",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "has already been entered")
        self.assertEqual(Attendance.objects.count(), 1)
        self.assertEqual(Attendance.objects.get().status, "Absent")

    def test_attendance_records_page_shows_student_summary(self):
        Attendance.objects.create(
            student=self.student,
            course_code=self.course.course_code,
            date="2026-10-03",
            status="Present",
        )

        response = self.client.get(reverse("lecturer_attendance"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Present")
        self.assertContains(response, "Total Classes")
        self.assertContains(response, "Attendance %")
        self.assertContains(response, self.student.full_name)
        self.assertContains(response, "100.0%")

    def test_attendance_rejects_unknown_student_id(self):
        response = self.client.post(
            reverse("lecturer_save_attendance"),
            {
                "student_id": "UNKNOWN",
                "course_code": self.course.course_code,
                "date": "2026-10-03",
                "status": "Present",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No student was found with ID UNKNOWN.")
        self.assertEqual(Attendance.objects.count(), 0)
