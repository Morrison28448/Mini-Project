from __future__ import annotations

from django import forms

from .models import Task, TaskStatus, Staff, Intern
from .models import Assignment, Submission, Department


from django.contrib.auth.models import User


class SuperuserUserForm(forms.ModelForm):
	# allow admin to optionally set a new password
	new_password = forms.CharField(required=False, widget=forms.PasswordInput, help_text="Leave blank to keep existing password")

	class Meta:
		model = User
		fields = ["first_name", "last_name", "email", "is_active", "is_staff", "is_superuser"]

	def clean_email(self):
		email = self.cleaned_data.get("email")
		if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
			raise forms.ValidationError("Another user with this email already exists.")
		return email


class InternProfileForm(forms.ModelForm):
	class Meta:
		model = Intern
		fields = ["name", "email", "department"]


class StaffProfileForm(forms.ModelForm):
	class Meta:
		model = Staff
		fields = ["name", "department", "position"]


class StaffSignupForm(forms.Form):
	name = forms.CharField(max_length=120)
	email = forms.EmailField()
	password = forms.CharField(widget=forms.PasswordInput, min_length=8)
	department = forms.ChoiceField(choices=Department.choices)
	position = forms.CharField(max_length=120)
	is_superuser = forms.BooleanField(required=False, label="Grant admin rights")

	def clean_email(self):
		email = self.cleaned_data.get("email")
		# ensure no existing user with this email
		from django.contrib.auth.models import User
		if User.objects.filter(email__iexact=email).exists():
			raise forms.ValidationError("A user with this email already exists.")
		return email


class InternSignupForm(forms.ModelForm):
	password = forms.CharField(widget=forms.PasswordInput)

	class Meta:
		model = Intern
		fields = ["name", "email", "password", "department"]


class TaskForm(forms.ModelForm):
	date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
	status = forms.ChoiceField(choices=TaskStatus.choices)
	staff_name = forms.CharField(required=False, label="Staff Name")
	staff_identifier = forms.CharField(required=False, label="Staff ID")
	staff_phone = forms.CharField(required=False, label="Staff Phone")

	class Meta:
		model = Task
		fields = ["date", "task_description", "staff_name", "staff_identifier", "staff_phone", "status"]


class HRFilterForm(forms.Form):
	start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
	end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
	status = forms.ChoiceField(choices=[("", "All")] + list(TaskStatus.choices), required=False)
	staff_id = forms.IntegerField(required=False)
	intern_name = forms.CharField(required=False)


class PasswordResetForm(forms.Form):
	auto_generate = forms.BooleanField(
		required=False,
		label="Auto-generate password",
		help_text="Check this to automatically generate a secure password, or leave unchecked to enter your own."
	)
	custom_password = forms.CharField(
		required=False,
		widget=forms.PasswordInput(attrs={"placeholder": "Enter custom password", "class": "form-control"}),
		label="Custom Password",
		min_length=8,
		help_text="Enter at least 8 characters. Leave empty if auto-generating."
	)
	
	def clean(self):
		cleaned_data = super().clean()
		auto_generate = cleaned_data.get("auto_generate")
		custom_password = cleaned_data.get("custom_password")
		
		if not auto_generate and not custom_password:
			raise forms.ValidationError("Either check 'Auto-generate password' or enter a custom password.")
		
		return cleaned_data


class AssignmentForm(forms.ModelForm):
	departments = forms.MultipleChoiceField(
		choices=Department.choices,
		widget=forms.CheckboxSelectMultiple,
		required=True,
		label="Departments",
	)

	due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

	class Meta:
		model = Assignment
		fields = ["title", "description", "departments", "due_date", "allow_file_upload"]

	def clean_departments(self):
		depts = self.cleaned_data.get("departments") or []
		# store as comma-separated string
		return ",".join(depts)


class SubmissionForm(forms.ModelForm):
	class Meta:
		model = Submission
		fields = ["text", "upload"]

	def clean(self):
		cleaned = super().clean()
		text = cleaned.get("text")
		upload = cleaned.get("upload")
		if not text and not upload:
			raise forms.ValidationError("Please provide text or upload a file for your submission.")
		return cleaned


