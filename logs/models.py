from __future__ import annotations

from django.conf import settings
from django.db import models


class Department(models.TextChoices):
	ENGINEERING = "Engineering", "Engineering"
	HR = "HR", "HR"
	FINANCE = "Finance", "Finance"
	OPERATIONS = "Operations", "Operations"
	SALES = "Sales", "Sales"
	OTHER = "Other", "Other"


class Intern(models.Model):
	name = models.CharField(max_length=120)
	email = models.EmailField(unique=True)
	password = models.CharField(max_length=128)
	department = models.CharField(max_length=32, choices=Department.choices)
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="intern_profile",
	)

	def __str__(self) -> str:
		return f"{self.name} ({self.department})"


class Staff(models.Model):
	name = models.CharField(max_length=120)
	department = models.CharField(max_length=32, choices=Department.choices)
	position = models.CharField(max_length=120)

	def __str__(self) -> str:
		return f"{self.name} - {self.position}"


class TaskStatus(models.TextChoices):
	PENDING = "Pending", "Pending"
	RESOLVED = "Resolved", "Resolved"


class Task(models.Model):
	intern = models.ForeignKey(Intern, on_delete=models.CASCADE, related_name="tasks")
	# Optional reference to Staff (kept for admin reporting), but interns will enter details manually
	staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
	# Manually entered staff details by intern
	staff_name = models.CharField(max_length=120, blank=True)
	staff_identifier = models.CharField(max_length=64, blank=True)
	staff_phone = models.CharField(max_length=32, blank=True)
	task_description = models.TextField()
	date = models.DateField()
	status = models.CharField(max_length=16, choices=TaskStatus.choices, default=TaskStatus.PENDING)
	remarks = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-date", "-created_at"]

	def __str__(self) -> str:
		return f"{self.intern.name} - {self.date} - {self.status}"


class Assignment(models.Model):
	title = models.CharField(max_length=200)
	description = models.TextField()
	# departments stored as comma-separated values matching Department choices
	departments = models.CharField(max_length=200)
	posted_by = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
	)
	due_date = models.DateField(null=True, blank=True)
	allow_file_upload = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self) -> str:
		return f"Assignment: {self.title}"

	def get_departments_list(self):
		return [d.strip() for d in (self.departments or "").split(",") if d.strip()]


class Submission(models.Model):
	assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
	intern = models.ForeignKey(Intern, on_delete=models.CASCADE, related_name="submissions")
	text = models.TextField(blank=True)
	upload = models.FileField(upload_to="submissions/", null=True, blank=True)
	submitted_at = models.DateTimeField(auto_now_add=True)
	reviewed = models.BooleanField(default=False)
	review_notes = models.TextField(blank=True)

	class Meta:
		ordering = ["-submitted_at"]

	def __str__(self) -> str:
		return f"Submission by {self.intern.name} for {self.assignment.title}"


