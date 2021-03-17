from django.urls import path

from . import views

base = ''

urlpatterns = [
	path(f'{base}', views.index, name='index'),
	path(f'{base}all/', views.all, name='all'),
	path(f'{base}<int:story_id>/', views.detail, name='detail'),
	path(f'{base}vote/<slug:vote_id>', views.vote, name='vote'),
	path(f'{base}download/<slug:post_id>/', views.download, name='download'),
	path(f'{base}direct/', views.direct, name='direct'),
]
