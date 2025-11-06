from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import views as auth_views
from django.db.models import Q, Count, Max
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from .forms import TaskForm, HRFilterForm, InternSignupForm, PasswordResetForm
from .models import Intern, Task, TaskStatus, Staff
from .forms import AssignmentForm, SubmissionForm, StaffSignupForm, SuperuserUserForm, InternProfileForm, StaffProfileForm
from .models import Assignment, Submission
from django.views.decorators.http import require_POST
from .forms import StaffSignupForm
from django.contrib.auth.models import User


def is_staff_user(user: User) -> bool:
	return bool(user and user.is_staff)


def is_superuser(user: User) -> bool:
	return bool(user and user.is_superuser)


def dashboard_redirect(request: HttpRequest) -> HttpResponse:
	if not request.user.is_authenticated:
		return redirect("login")
	# Staff (including superusers) go to staff dashboard
	if request.user.is_staff:
		return redirect("staff_dashboard")
	# Interns must have an Intern profile
	try:
		_ = request.user.intern_profile
		return redirect("intern_dashboard")
	except Intern.DoesNotExist:
		messages.error(request, "Your account is not configured as an intern. Please contact admin.")
		return redirect("login")


# CSRF-exempt simple login view
@csrf_exempt
def simple_login(request: HttpRequest) -> HttpResponse:
	if request.method == "POST":
		username_input = request.POST.get("username", "").strip()
		password = request.POST.get("password", "")
		# Allow login using either Django username or email
		auth_username = username_input
		if "@" in username_input:
			try:
				matched_user = User.objects.get(email__iexact=username_input)
				auth_username = matched_user.username
			except User.DoesNotExist:
				# Fall back to provided input; authenticate will fail and show error
				pass
		user = authenticate(request, username=auth_username, password=password)
		if user is not None:
			login(request, user)
			return redirect("dashboard_redirect")
		messages.error(request, "Invalid credentials.")
		return render(request, "auth/login.html", status=401)
	return render(request, "auth/login.html")


@login_required
def intern_dashboard(request: HttpRequest) -> HttpResponse:
	# Ensure the logged-in user has an Intern profile
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		messages.error(request, "Your account is not configured as an intern. Please contact admin.")
		return redirect("login")

	form = TaskForm(initial={"date": date.today()})
	tasks = intern.tasks.all()

	# Assignments for the intern's department
	assignments = Assignment.objects.filter(departments__icontains=intern.department).order_by("-created_at")
	return render(
		request,
		"intern/dashboard.html",
		{"form": form, "tasks": tasks, "today": date.today(), "assignments": assignments},
	)


@login_required
@csrf_exempt
def task_create(request: HttpRequest) -> HttpResponse:
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		messages.error(request, "Your account is not configured as an intern. Please contact admin.")
		return redirect("login")

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
@csrf_exempt
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


@csrf_exempt
def logout_view(request: HttpRequest) -> HttpResponse:
	# Explicit GET-based logout
	auth_logout(request)
	return redirect("login")


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


# Staff login endpoint (for staff/superusers)
@csrf_exempt
def staff_login(request: HttpRequest) -> HttpResponse:
	if request.method == "POST":
		username_input = request.POST.get("username", "").strip()
		password = request.POST.get("password", "")
		# Allow login using either Django username or email
		auth_username = username_input
		if "@" in username_input:
			try:
				matched_user = User.objects.get(email__iexact=username_input)
				auth_username = matched_user.username
			except User.DoesNotExist:
				pass
		user = authenticate(request, username=auth_username, password=password)
		if user is not None and user.is_staff:
			login(request, user)
			return redirect("staff_dashboard")
		messages.error(request, "Invalid credentials or you don't have staff privileges.")
		return render(request, "auth/staff_login.html", status=401)
	return render(request, "auth/staff_login.html")


# Staff dashboard - view all interns and create new ones
@login_required
@user_passes_test(is_staff_user)
def staff_dashboard(request: HttpRequest) -> HttpResponse:
	# Intern create form handling
	create_form = InternSignupForm(request.POST or None)
	if request.method == "POST" and "create_intern" in request.POST and create_form.is_valid():
		name = create_form.cleaned_data["name"]
		email = create_form.cleaned_data["email"]
		password = create_form.cleaned_data["password"]
		department = create_form.cleaned_data["department"]
		# Create auth user (username = email)
		user = User.objects.create_user(username=email, email=email, password=password)
		# Split name if possible
		if name:
			parts = name.split(" ")
			user.first_name = parts[0]
			user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
			user.save(update_fields=["first_name", "last_name"])
		# Create Intern profile
		Intern.objects.create(name=name, email=email, password=password, department=department, user=user)
		messages.success(request, "Intern account created.")
		return redirect("staff_dashboard")

	# Staff create form handling (separate submit button)
	staff_form = StaffSignupForm(request.POST or None)
	if request.method == "POST" and "create_staff" in request.POST and staff_form.is_valid():
		sname = staff_form.cleaned_data["name"]
		semail = staff_form.cleaned_data["email"]
		spassword = staff_form.cleaned_data["password"]
		sdepartment = staff_form.cleaned_data["department"]
		sposition = staff_form.cleaned_data["position"]
		is_super = staff_form.cleaned_data.get("is_superuser")
		# create auth user with staff/admin flags
		suser = User.objects.create_user(username=semail, email=semail, password=spassword)
		suser.is_staff = True
		if is_super:
			suser.is_superuser = True
		suser.save(update_fields=["is_staff", "is_superuser"])
		# create Staff model entry
		Staff.objects.create(name=sname, department=sdepartment, position=sposition)
		messages.success(request, "Staff account created.")
		return redirect("staff_dashboard")

	interns = Intern.objects.select_related("user").annotate(
		total_tasks=Count("tasks"),
		pending_tasks=Count("tasks", filter=Q(tasks__status=TaskStatus.PENDING)),
		resolved_tasks=Count("tasks", filter=Q(tasks__status=TaskStatus.RESOLVED)),
		latest_task_date=Max("tasks__date"),
	).order_by("-total_tasks")
	
	# Calculate totals
	total_tasks_all = sum(i.total_tasks for i in interns)
	total_pending_all = sum(i.pending_tasks for i in interns)
	total_resolved_all = sum(i.resolved_tasks for i in interns)
	
	return render(request, "superuser/dashboard.html", {
		"interns": interns,
		"total_tasks_all": total_tasks_all,
		"total_pending_all": total_pending_all,
		"total_resolved_all": total_resolved_all,
		"create_form": create_form,
	})


@login_required
@user_passes_test(is_staff_user)
def staff_create_staff(request: HttpRequest) -> HttpResponse:
	form = StaffSignupForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		sname = form.cleaned_data["name"]
		semail = form.cleaned_data["email"]
		spassword = form.cleaned_data["password"]
		sdepartment = form.cleaned_data["department"]
		sposition = form.cleaned_data["position"]
		is_super = form.cleaned_data.get("is_superuser")
		# create auth user with staff/admin flags
		suser = User.objects.create_user(username=semail, email=semail, password=spassword)
		suser.is_staff = True
		if is_super:
			suser.is_superuser = True
		suser.save()
		# create Staff model entry and optionally link to the user in future
		Staff.objects.create(name=sname, department=sdepartment, position=sposition)
		messages.success(request, "Staff account created.")
		return redirect("staff_dashboard")

	return render(request, "superuser/create_staff.html", {"staff_form": form})


# Superuser: list all users
@login_required
@user_passes_test(is_superuser)
def superuser_users(request: HttpRequest) -> HttpResponse:
	users = User.objects.all().order_by("username")
	return render(request, "superuser/users_list.html", {"users": users})


# Superuser: edit user and linked profile
@login_required
@user_passes_test(is_superuser)
def superuser_user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
	user_obj = get_object_or_404(User, id=user_id)
	intern = None
	staff_obj = None
	try:
		intern = user_obj.intern_profile
	except Intern.DoesNotExist:
		intern = None
	# find Staff by email or name - Staff isn't linked to User in current model
	staff_qs = Staff.objects.filter(name=user_obj.get_full_name())
	if not staff_qs.exists():
		staff_qs = Staff.objects.filter(department__iexact="")  # empty queryset
	staff_obj = staff_qs.first() if staff_qs.exists() else None

	if request.method == "POST":
		user_form = SuperuserUserForm(request.POST, instance=user_obj)
		intern_form = InternProfileForm(request.POST, instance=intern) if intern else None
		staff_form = StaffProfileForm(request.POST, instance=staff_obj) if staff_obj else None

		if "save_profile" in request.POST and intern_form and intern_form.is_valid():
			intern_form.save()
			messages.success(request, "Intern profile updated.")
			return redirect("superuser_user_edit", user_id=user_obj.id)
		if "save_profile" in request.POST and staff_form and staff_form.is_valid():
			staff_form.save()
			messages.success(request, "Staff profile updated.")
			return redirect("superuser_user_edit", user_id=user_obj.id)

		if user_form.is_valid():
			u = user_form.save(commit=False)
			# ensure username stays in sync with email
			u.username = u.email
			new_pw = user_form.cleaned_data.get("new_password")
			if new_pw:
				u.set_password(new_pw)
			u.save()
			messages.success(request, "User updated.")
			return redirect("superuser_users")
		else:
			messages.error(request, "Please correct the errors below.")
	else:
		user_form = SuperuserUserForm(instance=user_obj)
		intern_form = InternProfileForm(instance=intern) if intern else None
		staff_form = StaffProfileForm(instance=staff_obj) if staff_obj else None

	return render(request, "superuser/user_edit.html", {"user_form": user_form, "intern_form": intern_form, "staff_form": staff_form, "user_obj": user_obj})


# Individual intern detail view (staff)
@login_required
@user_passes_test(is_staff_user)
def staff_intern_detail(request: HttpRequest, intern_id: int) -> HttpResponse:
	intern = get_object_or_404(Intern, id=intern_id)
	tasks = intern.tasks.all().order_by("-date", "-created_at")
	
	# Calculate stats
	total_tasks = tasks.count()
	pending = tasks.filter(status=TaskStatus.PENDING).count()
	resolved = tasks.filter(status=TaskStatus.RESOLVED).count()
	
	# Get tasks by date for analytics
	from django.db.models.functions import TruncDay
	tasks_by_date = (
		tasks.annotate(day=TruncDay("created_at"))
		.values("day")
		.annotate(count=Count("id"))
		.order_by("day")
	)
	
	chart_labels = [str(row["day"]) for row in tasks_by_date]
	chart_data = [row["count"] for row in tasks_by_date]
	
	context = {
		"intern": intern,
		"tasks": tasks,
		"total_tasks": total_tasks,
		"pending": pending,
		"resolved": resolved,
		"chart_labels": chart_labels,
		"chart_data": chart_data,
		"password_form": PasswordResetForm(),
		"show_password_modal": False,
	}
	return render(request, "superuser/intern_detail.html", context)


# Reset intern password (staff only)
@login_required
@user_passes_test(is_staff_user)
@csrf_exempt
def staff_reset_intern_password(request: HttpRequest, intern_id: int) -> HttpResponse:
	import secrets
	import string
	
	intern = get_object_or_404(Intern, id=intern_id)
	
	if not intern.user:
		messages.error(request, "This intern does not have a user account linked.")
		return redirect("staff_intern_detail", intern_id=intern_id)
	
	if request.method == "POST":
		form = PasswordResetForm(request.POST)
		if form.is_valid():
			auto_generate = form.cleaned_data.get("auto_generate")
			custom_password = form.cleaned_data.get("custom_password")
			
			if auto_generate:
				# Generate a secure random password
				alphabet = string.ascii_letters + string.digits
				new_password = ''.join(secrets.choice(alphabet) for i in range(12))
			else:
				new_password = custom_password
			
			# Update the Django User password
			intern.user.set_password(new_password)
			intern.user.save()
			
			# Also update the Intern model's password field (for consistency)
			intern.password = new_password
			intern.save()
			
			messages.success(request, f"Password reset successfully! New password: {new_password}")
			return redirect("staff_intern_detail", intern_id=intern_id)
		else:
			messages.error(request, "Please correct the errors below.")
	else:
		form = PasswordResetForm()
	
	# Re-fetch intern data for the detail page
	tasks = intern.tasks.all().order_by("-date", "-created_at")
	total_tasks = tasks.count()
	pending = tasks.filter(status=TaskStatus.PENDING).count()
	resolved = tasks.filter(status=TaskStatus.RESOLVED).count()
	
	from django.db.models.functions import TruncDay
	tasks_by_date = (
		tasks.annotate(day=TruncDay("created_at"))
		.values("day")
		.annotate(count=Count("id"))
		.order_by("day")
	)
	
	chart_labels = [str(row["day"]) for row in tasks_by_date]
	chart_data = [row["count"] for row in tasks_by_date]
	
	return render(request, "superuser/intern_detail.html", {
		"intern": intern,
		"tasks": tasks,
		"total_tasks": total_tasks,
		"pending": pending,
		"resolved": resolved,
		"chart_labels": chart_labels,
		"chart_data": chart_data,
		"password_form": form,
		"show_password_modal": True,
	})


# Compare interns performance (staff)
@login_required
@user_passes_test(is_staff_user)
def staff_compare(request: HttpRequest) -> HttpResponse:
	intern_ids = request.GET.getlist("interns")
	interns = Intern.objects.filter(id__in=intern_ids) if intern_ids else Intern.objects.none()
	
	comparison_data = []
	for intern in interns:
		tasks = intern.tasks.all()
		# Use deterministic ordering when picking first/latest task dates
		latest_task = tasks.order_by("-date").first()
		first_task = tasks.order_by("date").first()
		comparison_data.append({
			"intern": intern,
			"total": tasks.count(),
			"pending": tasks.filter(status=TaskStatus.PENDING).count(),
			"resolved": tasks.filter(status=TaskStatus.RESOLVED).count(),
			"latest": latest_task.date if latest_task else None,
			"first": first_task.date if first_task else None,
		})
	
	all_interns = Intern.objects.all().order_by("name")
	
	return render(request, "superuser/compare.html", {
		"comparison_data": comparison_data,
		"all_interns": all_interns,
		"selected_ids": [int(i) for i in intern_ids] if intern_ids else [],
	})


# Staff: view and create assignments
@login_required
@user_passes_test(is_staff_user)
def staff_assignments(request: HttpRequest) -> HttpResponse:
	staff_form = None

# Intern submits an assignment result
@login_required
def assignment_submit(request: HttpRequest, assignment_id: int) -> HttpResponse:
	assignment = get_object_or_404(Assignment, id=assignment_id)
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		messages.error(request, "Your account is not configured as an intern. Please contact admin.")
		return redirect("login")

	# ensure this assignment is for the intern's department
	if intern.department not in assignment.get_departments_list():
		messages.error(request, "You are not eligible to submit for this assignment.")
		return redirect("intern_dashboard")

	if request.method == "POST":
		form = SubmissionForm(request.POST, request.FILES)
		if form.is_valid():
			sub = form.save(commit=False)
			sub.assignment = assignment
			sub.intern = intern
			sub.save()
			messages.success(request, "Submission received.")
			return redirect("intern_dashboard")
		else:
			messages.error(request, "Please correct the errors below.")
	else:
		form = SubmissionForm()

	return render(request, "intern/assignment_submit.html", {"form": form, "assignment": assignment})


# Edit assignment (staff only)
@login_required
@user_passes_test(is_staff_user)
def staff_assignment_edit(request: HttpRequest, assignment_id: int) -> HttpResponse:
	assignment = get_object_or_404(Assignment, id=assignment_id)
	if request.method == "POST":
		form = AssignmentForm(request.POST, instance=assignment)
		if form.is_valid():
			a = form.save(commit=False)
			a.departments = form.cleaned_data.get("departments")
			a.save()
			messages.success(request, "Assignment updated.")
			return redirect("staff_assignments")
		else:
			messages.error(request, "Please correct the errors below.")
	else:
		# convert departments CSV to list for form initial
		initial = {"departments": assignment.get_departments_list(), "due_date": assignment.due_date}
		form = AssignmentForm(instance=assignment, initial=initial)
	return render(request, "superuser/assignments.html", {"form": form, "assignments": [assignment], "editing": True})


# Delete assignment (staff only)
@login_required
@user_passes_test(is_staff_user)
def staff_assignment_delete(request: HttpRequest, assignment_id: int) -> HttpResponse:
	assignment = get_object_or_404(Assignment, id=assignment_id)
	if request.method == "POST":
		assignment.delete()
		messages.success(request, "Assignment deleted.")
		return redirect("staff_assignments")
	return render(request, "superuser/assignment_confirm_delete.html", {"assignment": assignment})


# Staff: view all submissions or submissions for an assignment
@login_required
@user_passes_test(is_staff_user)
def staff_submissions(request: HttpRequest) -> HttpResponse:
	assignment_id = request.GET.get("assignment_id")
	qs = Submission.objects.select_related("intern", "assignment").all()
	if assignment_id:
		qs = qs.filter(assignment_id=assignment_id)
	submissions = qs.order_by("-submitted_at")
	assignments = Assignment.objects.all()
	try:
		selected_assignment = int(assignment_id) if assignment_id else None
	except (TypeError, ValueError):
		selected_assignment = None
	return render(request, "superuser/submissions.html", {"submissions": submissions, "assignments": assignments, "selected_assignment": selected_assignment})


# Staff: view single submission and mark reviewed
@login_required
@user_passes_test(is_staff_user)
def staff_submission_detail(request: HttpRequest, submission_id: int) -> HttpResponse:
	sub = get_object_or_404(Submission, id=submission_id)
	if request.method == "POST":
		# toggle reviewed and save notes
		action = request.POST.get("action")
		if action == "mark_reviewed":
			sub.reviewed = True
			sub.review_notes = request.POST.get("review_notes", "")
			sub.save()
			messages.success(request, "Submission marked as reviewed.")
		elif action == "unmark_reviewed":
			sub.reviewed = False
			sub.review_notes = request.POST.get("review_notes", "")
			sub.save()
			messages.success(request, "Submission unmarked as reviewed.")
		return redirect("staff_submission_detail", submission_id=sub.id)
	return render(request, "superuser/submission_detail.html", {"submission": sub})



@login_required
def intern_analytics(request: HttpRequest) -> HttpResponse:
	# Ensure the logged-in user has an Intern profile
	try:
		intern = request.user.intern_profile
	except Intern.DoesNotExist:
		messages.error(request, "Your account is not configured as an intern. Please contact admin.")
		return redirect("login")

	period = (request.GET.get("period") or "week").lower()
	valid_periods = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}
	if period not in valid_periods:
		period = "week"

	qs = Task.objects.filter(intern=intern)

	# Determine truncation function and default window size
	trunc_fn = valid_periods[period]
	annotated = (
		qs.annotate(bucket=trunc_fn("created_at"))
		.values("bucket")
		.annotate(count=Count("id"))
		.order_by("bucket")
	)

	labels: list[str] = []
	data: list[int] = []
	for row in annotated:
		labels.append(row["bucket"].strftime("%Y-%m-%d"))
		data.append(row["count"])

	context = {
		"period": period,
		"labels": labels,
		"data": data,
	}
	return render(request, "intern/analytics.html", context)

