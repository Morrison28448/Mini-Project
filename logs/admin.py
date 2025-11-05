from django.contrib import admin

from .models import Intern, Staff, Task


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


