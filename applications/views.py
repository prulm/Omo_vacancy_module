from django.shortcuts import render
from django.core.mail import EmailMessage
from django.db.models import Count
from django.utils import timezone
from django.db.models.functions import TruncDay
from rest_framework import permissions
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from jobs.permissions import *
from .serializers import ApplicationSerializer, ApplicationListSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, timedelta
from rest_framework import status
from .models import Application
from accounts.models import *
from recruit_screenings.models import Screening
from jobs.models import Job
from django.conf import settings

class ApplicationView(CreateAPIView):
	permission_classes = (permissions.IsAuthenticated, IsRecruit)
	serializer_class = ApplicationSerializer

	def perform_create(self, serializer):
		instance = serializer.save()
		subject = 'Application Submitted'
		message = f'Your application for {instance.job.title} position has been submitted successfully.\
		 \nOur team will review your application and get back to you shortly.\n\
		 \nRegards,\nOmo Bank Recruitment Team'
		to_email = instance.user.email
		email = EmailMessage(subject, message, to=[to_email])
		email.send()

class ApplicationUpdateView(UpdateAPIView):
	permission_classes = (permissions.IsAuthenticated, IsHRUser)
	serializer_class = ApplicationSerializer
	queryset = Application.objects.all()

class ApplicationListView(ListAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = ApplicationListSerializer
	
	def get_queryset(self):
		param = self.request.query_params.get("Type")
		if (self.request.user.user_type.lower() == 'recruit'):
			return Application.objects.filter(user=self.request.user)
		elif (self.request.user.user_type.lower() == 'department user'):
			department = self.request.user.departmentuser.department
			if (param == 'Application'):
				return Application.objects.filter(job__department=department).order_by('application_date')
			else:
				return Application.objects.filter(job__department=department)\
				.filter(is_candidate=True).order_by('application_date')
		else:
			if (param == 'Candidate'):
				return Application.objects.filter(is_candidate=True).order_by('application_date')
			elif (param == 'Shortlist'):
				return Application.objects.filter(is_shortlisted=True).order_by('application_date')
			return Application.objects.all().order_by('application_date')

class ApplicationRetrieveView(RetrieveAPIView):
	permission_classes = (permissions.IsAuthenticated, IsStaff)
	serializer_class = ApplicationListSerializer
	queryset = Application.objects.all()

class DisplayView(APIView):
	permission_classes = (permissions.IsAuthenticated, )
	def get(self,*args,**kwargs):
		if self.request.user.user_type.lower()=="department user":
			department = self.request.user.departmentuser.department
			end = datetime.now()
			start = end - timedelta(days=7)
			third = end + timedelta(days=3)
			new_application = Application.objects.filter(job__department=department)\
			.filter(application_date__range=[start, end]).count()
			new_candidates= Application.objects.filter(job__department=department)\
			.filter(application_date__range=[start, end]).filter(is_candidate=True).count()
			invited_for_screening=Screening.objects.filter(application__job__department=department)\
			.filter(screening_type='Test').filter(schedule__range=[end, third]).count()
			invited_for_interview=Screening.objects.filter(application__job__department=department)\
			.filter(screening_type='Interview').filter(schedule__range=[end, third]).count()
			dict = {
			"New applications": {"New applications": new_application,
			"link": "/applications"
			},
			"New candidates": {"New candidates": new_candidates,
			"link": "/candidates"
			},
			"Upcoming test": {"Upcoming test": invited_for_screening,
			"link": "/applications"
			},
			"Upcoming interview": {"Upcoming interview": invited_for_interview,
			"link": "/applications"
			}
			}
			return Response(dict,status=status.HTTP_200_OK)
		elif self.request.user.user_type.lower()=="hr user":
			end = datetime.now()
			start = end - timedelta(days=7)
			third = end + timedelta(days=3)
			new_application = Application.objects.filter(application_date__range=[start, end]).count()
			new_candidates = Application.objects.filter(application_date__range=[start, end])\
			.filter(is_candidate=True).count()
			invited_for_screening = Screening.objects.filter(screening_type='Test')\
			.filter(schedule__range=[end, third]).count()
			invited_for_interview = Screening.objects.filter(screening_type='Interview')\
			.filter(schedule__range=[end, third]).count()
			dict = {
			"New applications": {"New applications": new_application,
			"link": "/applications"
			},
			"New candidates": {"New candidates": new_candidates,
			"link": "/candidates"
			},
			"Upcoming test": {"Upcoming test": invited_for_screening,
			"link": "/calendar"
			},
			"Upcoming interview": {"Upcoming interview": invited_for_interview,
			"link": "/calendar"
			}
			}
			return Response(dict, status=status.HTTP_200_OK)

		ongoing_applications=Application.objects.filter(user=self.request.user).filter(is_candidate=False).count()
		end = datetime.now()
		start = end - timedelta(days=7)
		third = end + timedelta(days=3)
		new_jobs = Job.objects.filter(date_created__range=[start, end]).count()
		candidate_for = Application.objects.filter(user=self.request.user).filter(is_candidate=True).count()
		upcoming_screening = Screening.objects.filter(application__user=self.request.user)\
		.filter(schedule__range=[end, third]).count()
		dict = {
		"New jobs": {"New jobs": new_jobs,
		"link": "/jobs"
		},
		"Candidate for": {"Candidate for": candidate_for,
		"link": "/applications"
		},
		"Ongoing applications": {"Ongoing applications": ongoing_applications,
		"link": "/applications"
		},
		"Upcoming screening": {"Upcoming screening": upcoming_screening,
		"link": "/calendar"
		}
		}
		return Response(dict,status=status.HTTP_200_OK)

class JobApplicationsView(APIView):
	permission_classes = (permissions.IsAuthenticated, IsStaff)
	def get(self, request, format=None):
		jobs = Job.objects.filter(is_published=True).annotate(num_applications=Count('application'))
		job_list = []
		for job in jobs:
			job_list.append({
				'id': job.id,
				'name': job.title,
				'value': job.num_applications
			})
		job_list = [job for job in job_list if job['value'] > 0]
		return Response(job_list, status=status.HTTP_200_OK)

class ApplicationsCountView(APIView):
	permission_classes = (permissions.IsAuthenticated, IsStaff)
	def get(self, request):
		today = timezone.now()
		start_date = today - timezone.timedelta(days=30)
		applications = Application.objects.filter(
			application_date__gte=start_date
		).annotate(
			day=TruncDay('application_date')
		).values('day').annotate(
			applications=Count('id')
		).order_by('day')
		return Response(applications, status=status.HTTP_200_OK)