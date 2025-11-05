from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
	path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
	path("logout/", auth_views.LogoutView.as_view(), name="logout"),
	path("signup/", views.intern_signup, name="signup"),

	# Intern
	path("", views.intern_dashboard, name="intern_dashboard"),
	path("task/create/", views.task_create, name="task_create"),
	path("task/<int:task_id>/update-status/", views.task_update_status, name="task_update_status"),

	# HR / Supervisor
	path("hr/", views.hr_dashboard, name="hr_dashboard"),
	path("hr/export/csv/", views.hr_export_csv, name="hr_export_csv"),
]


