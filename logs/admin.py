from django.contrib import admin

from .models import Intern, Staff, Task, Assignment, Submission


@admin.register(Intern)
class InternAdmin(admin.ModelAdmin):
	list_display = ("name", "email", "department")
	search_fields = ("name", "email")
	list_filter = ("department",)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
	list_display = ("name", "department", "position")
	list_filter = ("department",)
	search_fields = ("name", "position")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
	list_display = ("intern", "staff", "date", "status")
	list_filter = ("status", "date", "intern__department")
	search_fields = ("intern__name", "staff__name", "task_description")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
	list_display = ("title", "departments", "posted_by", "created_at", "due_date")
	list_filter = ("posted_by",)
	search_fields = ("title", "description")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
	list_display = ("assignment", "intern", "submitted_at")
	list_filter = ("submitted_at",)
	search_fields = ("intern__name", "assignment__title")


