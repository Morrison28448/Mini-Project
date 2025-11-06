from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
	path("login/", views.simple_login, name="login"),
	path("logout/", views.logout_view, name="logout"),
	# No public signup; interns are created by admins

	# Default root should be the login page
	path("", views.simple_login, name="login_home"),


	# Staff login and dashboard
	path("staff/login/", views.staff_login, name="staff_login"),
	path("staff/dashboard/", views.staff_dashboard, name="staff_dashboard"),
	path("staff/create-staff/", views.staff_create_staff, name="staff_create_staff"),
	path("superuser/users/", views.superuser_users, name="superuser_users"),
	path("superuser/users/<int:user_id>/", views.superuser_user_edit, name="superuser_user_edit"),
	path("staff/intern/<int:intern_id>/", views.staff_intern_detail, name="staff_intern_detail"),
	path("staff/intern/<int:intern_id>/reset-password/", views.staff_reset_intern_password, name="staff_reset_intern_password"),
	path("staff/compare/", views.staff_compare, name="staff_compare"),
	path("staff/assignments/", views.staff_assignments, name="staff_assignments"),
	path("staff/assignments/<int:assignment_id>/edit/", views.staff_assignment_edit, name="staff_assignment_edit"),
	path("staff/assignments/<int:assignment_id>/delete/", views.staff_assignment_delete, name="staff_assignment_delete"),
	path("staff/submissions/", views.staff_submissions, name="staff_submissions"),
	path("staff/submission/<int:submission_id>/", views.staff_submission_detail, name="staff_submission_detail"),

	# Intern / post-login router
	path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
	path("intern/", views.intern_dashboard, name="intern_dashboard"),
	path("intern/analytics/", views.intern_analytics, name="intern_analytics"),
	path("task/create/", views.task_create, name="task_create"),
	path("task/<int:task_id>/update-status/", views.task_update_status, name="task_update_status"),
	path("assignments/<int:assignment_id>/submit/", views.assignment_submit, name="assignment_submit"),

	# HR / Supervisor
	path("hr/", views.hr_dashboard, name="hr_dashboard"),
	path("hr/export/csv/", views.hr_export_csv, name="hr_export_csv"),
]


