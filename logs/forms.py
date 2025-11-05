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
	staff = forms.ModelChoiceField(queryset=Staff.objects.all(), required=False)

	class Meta:
		model = Task
		fields = ["date", "task_description", "staff", "status"]


class HRFilterForm(forms.Form):
	start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
	end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
	status = forms.ChoiceField(choices=[("", "All")] + list(TaskStatus.choices), required=False)
	staff_id = forms.IntegerField(required=False)
	intern_name = forms.CharField(required=False)


