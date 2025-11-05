from __future__ import annotations

from django import forms

from .models import Task, TaskStatus, Staff, Intern


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


