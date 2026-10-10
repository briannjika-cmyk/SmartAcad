# SmartAcad

Academic Management and Student Performance Tracking System

SmartAcad is a Django-based academic management system for tracking student performance, attendance, grades, and learning behaviors through role-based dashboards. The project supports multiple user roles, including students, lecturers, academic administrators, and system administrators, and includes an academic risk assessment component that uses a trained model to classify students based on attendance, GPA, study habits, and questionnaire data.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Objectives](#objectives)
3. [Features and Functionality](#features-and-functionality)
4. [User Roles](#user-roles)
5. [Technology Stack](#technology-stack)
6. [Project Structure](#project-structure)
7. [Installation and Setup](#installation-and-setup)
8. [Database Configuration and Models](#database-configuration-and-models)
9. [How to Run the Application](#how-to-run-the-application)
10. [Usage Instructions](#usage-instructions)
11. [Security Considerations](#security-considerations)
12. [Testing and Troubleshooting](#testing-and-troubleshooting)
13. [Future Improvements](#future-improvements)
14. [Contribution Guidelines](#contribution-guidelines)
15. [License](#license)

---

## Project Overview

SmartAcad is a final-year academic management system designed to improve how educational institutions manage student records, monitor academic performance, and identify students who may require early support. The system brings together academic results, attendance, learning questionnaires, and course/program management into a unified Django application.

The project is structured around a role-based workflow:

- Students can access their results and attendance records and submit self-assessment questionnaires.
- Lecturers can manage marks, view attendance records, and review questionnaires.
- Academic Administrators can manage academic operations for assigned programs and student records.
- System Administrators can manage the platform through the Django admin interface.

---

## Objectives

The main goals of SmartAcad are to:

- Centralize academic data for students, lecturers, and administrators
- Automate GPA calculation based on marks and course credits
- Simplify attendance tracking across courses and dates
- Allow lecturers to record and verify marks efficiently
- Support academic administrators in managing programs and student admissions
- Encourage proactive support by assessing academic risk using a trained model
- Provide a clean role-based dashboard experience for different users

---

## Features and Functionality

### Student Features

- View personal academic results
- Review GPA and academic performance history
- View attendance summaries by course
- Submit a questionnaire on study habits and learning difficulties
- Change account password
- Access a personalized dashboard

### Lecturer Features

- Access a lecturer-specific dashboard
- View assigned courses and students
- Enter and save student marks
- Automatically assign grades based on a mark threshold
- View academic records for assigned courses
- Record attendance per student and course
- Review submitted student questionnaires
- Monitor student performance trends

### Academic Administrator Features

- Manage assigned programs
- Admit students and create Django user accounts automatically
- View academic records
- Update student results and grade information
- View attendance summaries
- Review student questionnaires
- Monitor risk-related academic data

### System Administrator Features

- Full system access via Django admin
- Manage programs, lecturers, students, and courses
- Assign academic administrators to programs
- Manage lecturer-course relations
- Configure institutional data and records

### Academic Risk Assessment

The project includes an academic risk model component implemented using scikit-learn and joblib. The risk module:

- Loads the pre-trained model and metadata from the model artifacts directory
- Computes key risk features using:
  - attendance percentage
  - GPA
  - study hours
  - assignment completion
  - learning difficulty indicators
  - study habit indicators
- Classifies students into risk categories:
  - High
  - Medium
  - Low
- Returns intervention recommendations based on risk level and missing data

This functionality is defined in `smartacad/core/academic_risk.py` and used by the academic admin dashboard.

---

## User Roles

### 1. Student

A Student user can:

- log in through the shared login page
- view their dashboard
- access academic results
- check attendance records
- submit their study questionnaire
- change their password

### 2. Lecturer

A Lecturer user can:

- view assigned courses
- register marks for students
- track attendance
- review questionnaire responses
- access student academic records and course performance

### 3. Academic Administrator

An Academic Administrator can:

- manage student admissions
- assign students to programs
- view and update academic records
- manage conditions related to institutional performance
- monitor attendance and questionnaires

### 4. System Administrator

A System Administrator can:

- use the Django admin interface
- manage programs and lecturers
- oversee institutional records
- perform system-level maintenance and configuration

---

## Technology Stack

### Backend

- Python
- Django 5.2
- SQLite (used for development)

### Machine Learning

- scikit-learn
- joblib

### Frontend

- Django template system
- HTML
- CSS
- JavaScript (where used in templates)

### Additional Tools

- Django admin
- Django authentication system
- Django ORM

---

## Project Structure

```text
SmartAcad/
├── README.md
├── .gitignore
├── smartacad/
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3
│   ├── smartacad/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── academic_risk.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── management/
│   │   ├── migrations/
│   │   ├── model_artifacts/
│   │   ├── models.py
│   │   ├── signals.py
│   │   ├── templates/
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   └── templates/
│       └── admin/
└──
```

### Main Modules

- `smartacad/manage.py`  
  Django management entry point.

- `smartacad/smartacad/settings.py`  
  Project configuration, including app registration, database setup, and middleware.

- `smartacad/core/models.py`  
  Data models for Program, Student, Lecturer, Course, AcademicRecord, StudentQuestionnaire, Attendance, and related relationships.

- `smartacad/core/views.py`  
  Core application logic, including dashboards, authentication flow, role-based redirection, and risk assessment logic.

- `smartacad/core/forms.py`  
  Validation and form logic for student admissions and academic record updates.

- `smartacad/core/admin.py`  
  Django admin customization and restricted permissions.

- `smartacad/core/academic_risk.py`  
  Academic risk model loading and risk classification logic.

- `smartacad/core/tests.py`  
  Unit and integration tests covering the application workflow.

---

## Installation and Setup

### Prerequisites

Before setting up the project, ensure you have the following installed:

- Python 3.8 or later
- pip
- Git
- A virtual environment manager

### 1. Clone the Repository

```bash
git clone https://github.com/briannjika-cmyk/SmartAcad.git
cd SmartAcad
```

### 2. Create a Virtual Environment

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate
```

#### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

From the project directory:

```bash
cd smartacad
pip install -r requirements.txt
```

The repository's installed dependencies include:

```text
Django>=5.2,<5.3
scikit-learn>=1.6,<2
joblib>=1.4,<2
```

---

## Database Configuration and Models

### Database

The project is configured with SQLite as the default database in development:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

This configuration is defined in `smartacad/smartacad/settings.py`.

### Core Models

#### Program

Represents an academic program.

```python
class Program(models.Model):
    program_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, unique=True)
    academic_admin = models.ForeignKey(User, ...)
```

#### Student

Stores student data including personal details, academic program, and GPA.

```python
class Student(models.Model):
    user = models.OneToOneField(User, ...)
    program = models.ForeignKey(Program, ...)
    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    programme = models.CharField(max_length=100)
    year_of_study = models.PositiveIntegerField()
    gpa = models.DecimalField(...)
```

#### Lecturer

Stores lecturer information and linked departmental assignments.

```python
class Lecturer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, ...)
    lecturer_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
```

#### Course

Defines a course and its credit weighting.

```python
class Course(models.Model):
    lecturer = models.ForeignKey(Lecturer, ...)
    program = models.ForeignKey(Program, ...)
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=100)
    credits = models.DecimalField(...)
```

#### AcademicRecord

Stores student marks and course results.

```python
class AcademicRecord(models.Model):
    student = models.ForeignKey(Student, ...)
    course_code = models.CharField(max_length=20)
    course_name = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)
    marks = models.DecimalField(...)
    grade = models.CharField(max_length=5)
    academic_year = models.CharField(max_length=20)
    credits = models.DecimalField(...)
```

#### StudentCourseEnrollment

Tracks student-course enrollment and prevents duplicates.

```python
class StudentCourseEnrollment(models.Model):
    student = models.ForeignKey(Student, ...)
    course = models.ForeignKey(Course, ...)
```

#### StudentQuestionnaire

Stores student learning habits and difficulties.

```python
class StudentQuestionnaire(models.Model):
    student = models.OneToOneField(Student, ...)
    submitted = models.BooleanField(default=False)
    study_hours = models.DecimalField(...)
    assignment_completion = models.DecimalField(...)
    learning_difficulties = models.TextField(...)
    study_habits = models.TextField(...)
    learning_resource_access = models.TextField(...)
```

#### Attendance

Tracks student attendance and prevents duplicate entries.

```python
class Attendance(models.Model):
    student = models.ForeignKey(Student, ...)
    course_code = models.CharField(max_length=20)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[("Present", "Present"), ("Absent", "Absent")])
```

### GPA Calculation

The system uses a weighted GPA model based on course credits and grade points:

- A = 4.00
- B = 3.00
- C = 2.00
- D = 1.00
- E = 0.00

The GPA is recalculated automatically when marks or course credits are updated.

---

## How to Run the Application

### Start the Development Server

From the project directory:

```bash
cd smartacad
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

### Start the Server on a Custom Port

```bash
python manage.py runserver 8080
```

### Run Django Checks

```bash
python manage.py check
```

### Create a Superuser

```bash
python manage.py createsuperuser
```

---

## Usage Instructions

### Shared Login

The application uses a common login route at:

```text
http://127.0.0.1:8000/login/
```

Users can log in using their username and password.

---

### Student Usage

1. Log in to the system.
2. Go to the student dashboard.
3. View academic records and attendance summary.
4. Open the results page.
5. Submit or update the student questionnaire.
6. Change the password if needed.

---

### Lecturer Usage

1. Log in as a lecturer.
2. Open the lecturer dashboard.
3. Select a course and student to enter marks.
4. Save marks and grade information.
5. View attendance summary for assigned courses.
6. Review submitted questionnaires.

---

### Academic Administrator Usage

1. Log in as an academic administrator.
2. Open the academic admin dashboard.
3. Review program and student overview.
4. Add new students and assign them to a program.
5. View academic records and update them.
6. Monitor attendance and risk metrics.

---

### System Administrator Usage

1. Log in to the Django admin interface.
2. Open `/admin/`.
3. Manage programs, lecturers, and students.
4. Assign academic administrators to programs.
5. Maintain course and record data.

---

## Security Considerations

### Authentication and Authorization

The application uses Django’s built-in authentication system and group-based authorization. Role handling is implemented using user groups such as:

- Student
- Lecturer
- Academic Admin
- System Administrator

The project also enforces password validation and role-based redirects in views.

### Security Recommendations

For a production environment, the following security measures should be added:

1. Move the `SECRET_KEY` to environment variables.
2. Set DEBUG to `False` in production.
3. Restrict `ALLOWED_HOSTS`.
4. Use HTTPS with secure cookies.
5. Employ proper web server configuration.
6. Use strong database credentials.
7. Limit access to administrative functions.
8. Monitor logs and failed authentication attempts.

### Current Code Observations

The project currently uses a default development configuration:

```python
SECRET_KEY = "django-insecure-..."
DEBUG = True
ALLOWED_HOSTS = []
```

This is appropriate for local development, but it is not suitable for production without further hardening.

---

## Testing and Troubleshooting

### Running Tests

From the project directory:

```bash
cd smartacad
python manage.py test
```

### Common Issues

#### 1. ModuleNotFoundError: No module named 'django'

Solution:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Database Migration Issues

Solution:

```bash
python manage.py migrate
```

#### 3. Port 8000 Already in Use

Solution:

```bash
python manage.py runserver 8080
```

#### 4. Missing ML Model Files

If the model artifacts are missing, the academic risk module may be unable to load them. Ensure that the required files exist in:

```text
smartacad/core/model_artifacts/
```

#### 5. Login or Access Problems

Check whether the user is assigned to the correct Django group and ensure the correct login route is used.

---

## Future Improvements

Planned enhancements could include:

- improved data visualization for attendance and academic performance
- more detailed analytics dashboards
- improved reporting and export options
- stronger production security hardening
- better integration with institutional systems
- expanded use of academic prediction models
- better role-based data filtering and reporting
- improved UI/UX and responsive design

---

## Contribution Guidelines

Contributions are welcome. To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Write tests where appropriate.
5. Submit a pull request.

Example:

```bash
git checkout -b feature/my-improvement
git add .
git commit -m "feat: add academic dashboard improvements"
git push origin feature/my-improvement
```

Before submitting a pull request, ensure that the project still passes tests:

```bash
python manage.py test
```

---

## License

This project does not currently include a LICENSE file in the repository root. Before public release or distribution, it is recommended to add an explicit open-source license (for example, the MIT License) and include the corresponding LICENSE file in the project root.

If you intend to publish the project publicly, add a license file such as:

```bash
# MIT License

Copyright (c) 2026 SmartAcad

Permission is hereby granted, free of charge, to any person or obtaining a copy
of this software and associated documentation files (the Software is called
"SmartAcad"), to use, sell, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom
the Software is furnished to do so, subject to the following conditions:

The above copyright notice and the permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. INFRINGEMENT SHALL NOT
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE. INFRINGEMENT, OR OTHER DEALINGS IN THE SOFTWARE.
```

---

This README reflects the actual functionality implemented in the repository and was written to match the current codebase rather than inventing unsupported features.
