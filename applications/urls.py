from django.urls import path
from .views import *

urlpatterns = [
	path('<pk>', ApplicationRetrieveView.as_view(), name='application'),
	path('apply/', ApplicationView.as_view(), name='apply'),
	path('list/', ApplicationListView.as_view(), name='list'),
	path('display/', DisplayView.as_view(), name='box-display'),
	path('shortlist/<pk>', ApplicationUpdateView.as_view(), name='shortlist'),
	path('jobs/', JobApplicationsView.as_view(), name='applications_per_job'),
	path('count/', ApplicationsCountView.as_view(), name='applications_in_a_month'),
]