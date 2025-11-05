from __future__ import annotations

from datetime import date
from typing import Iterable

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.http import StreamingHttpResponse

from .forms import InternSignupForm, TaskForm, HRFilterForm
from .models import Intern, Task, TaskStatus


def is_staff_user(user: User) -> bool:
	return bool(user and user.is_staff)


def intern_signup(request: HttpRequest) -> HttpResponse:
	if request.method == "POST":
		form = InternSignupForm(request.POST)
		if form.is_valid():
			intern: Intern = form.save(commit=False)
			# Create a corresponding Django user for auth
			user = User.objects.create_user(
				username=intern.email,
				email=intern.email,
				password=form.cleaned_data["password"],
				first_name=intern.name,
			)
			intern.user = user
			intern.save()
			messages.success(request, "Signup successful. You can now log in.")
			return redirect("login")
	else:
		form = InternSignupForm()
	return render(request, "auth/signup.html", {"form": form})


@login_required
def intern_dashboard(request: HttpRequest) -> HttpResponse:
	# Ensure the logged-in user has an Intern profile
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		messages.info(request, "Please complete intern signup to use the intern dashboard.")
		return redirect("signup")

	form = TaskForm(initial={"date": date.today()})
	tasks = intern.tasks.all()
	return render(
		request,
		"intern/dashboard.html",
		{"form": form, "tasks": tasks, "today": date.today()},
	)


@login_required
def task_create(request: HttpRequest) -> HttpResponse:
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		return redirect("signup")

	if request.method == "POST":
		form = TaskForm(request.POST)
		if form.is_valid():
			task = form.save(commit=False)
			task.intern = intern
			task.save()
			messages.success(request, "Task recorded.")
			return redirect("intern_dashboard")
	else:
		form = TaskForm(initial={"date": date.today()})

	return render(request, "intern/task_form.html", {"form": form})


@login_required
def task_update_status(request: HttpRequest, task_id: int) -> HttpResponse:
	task = get_object_or_404(Task, id=task_id)
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		intern = None

	if intern and task.intern_id == intern.id:
		# Toggle between Pending and Resolved
		task.status = TaskStatus.RESOLVED if task.status == TaskStatus.PENDING else TaskStatus.PENDING
		task.save(update_fields=["status", "updated_at"])
		messages.success(request, "Task status updated.")
		return redirect("intern_dashboard")

	messages.error(request, "You are not allowed to update this task.")
	return redirect("intern_dashboard")


@login_required
@user_passes_test(is_staff_user)
def hr_dashboard(request: HttpRequest) -> HttpResponse:
	form = HRFilterForm(request.GET or None)
	qs = Task.objects.select_related("intern", "staff").all()

	if form.is_valid():
		start_date = form.cleaned_data.get("start_date")
		end_date = form.cleaned_data.get("end_date")
		status = form.cleaned_data.get("status")
		staff_id = form.cleaned_data.get("staff_id")
		intern_name = form.cleaned_data.get("intern_name")

		if start_date:
			qs = qs.filter(date__gte=start_date)
		if end_date:
			qs = qs.filter(date__lte=end_date)
		if status:
			qs = qs.filter(status=status)
		if staff_id:
			qs = qs.filter(staff_id=staff_id)
		if intern_name:
			qs = qs.filter(intern__name__icontains=intern_name)

	return render(request, "hr/dashboard.html", {"form": form, "tasks": qs})


@login_required
@user_passes_test(is_staff_user)
def hr_export_csv(request: HttpRequest) -> HttpResponse:
	form = HRFilterForm(request.GET or None)
	qs = Task.objects.select_related("intern", "staff").all()
	if form.is_valid():
		start_date = form.cleaned_data.get("start_date")
		end_date = form.cleaned_data.get("end_date")
		status = form.cleaned_data.get("status")
		staff_id = form.cleaned_data.get("staff_id")
		intern_name = form.cleaned_data.get("intern_name")

		if start_date:
			qs = qs.filter(date__gte=start_date)
		if end_date:
			qs = qs.filter(date__lte=end_date)
		if status:
			qs = qs.filter(status=status)
		if staff_id:
			qs = qs.filter(staff_id=staff_id)
		if intern_name:
			qs = qs.filter(intern__name__icontains=intern_name)

	def row_iter(rows: Iterable[Task]):
		yield "Intern,Email,Department,Staff,Date,Status,Task,Remarks\n"
		for t in rows:
			yield f"{t.intern.name},{t.intern.email},{t.intern.department},{(t.staff.name if t.staff else '')},{t.date},{t.status},\"{(t.task_description or '').replace('"', "''")}\",\"{(t.remarks or '').replace('"', "''")}\"\n"

	response = StreamingHttpResponse(row_iter(qs), content_type="text/csv")
	response["Content-Disposition"] = f"attachment; filename=intern_tasks_{now().date()}.csv"
	return response


