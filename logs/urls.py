from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
	path("login/", views.simple_login, name="login"),
	path("logout/", views.logout_view, name="logout"),
	# No public signup; interns are created by admins

	# Intern
	path("", views.dashboard_redirect, name="dashboard_redirect"),
	path("intern/", views.intern_dashboard, name="intern_dashboard"),
	path("task/create/", views.task_create, name="task_create"),
	path("task/<int:task_id>/update-status/", views.task_update_status, name="task_update_status"),

	# HR / Supervisor
	path("hr/", views.hr_dashboard, name="hr_dashboard"),
	path("hr/export/csv/", views.hr_export_csv, name="hr_export_csv"),
]


