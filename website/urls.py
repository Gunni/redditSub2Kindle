from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import path
from django.views.generic import RedirectView

from . import views

base = ''

urlpatterns = [
	path(f'{base}', views.index, name='index'),
	path(f'{base}authors/', views.authors, name='authors'),
	path(f'{base}author/<int:author_id>', views.author, name='author'),
	path(f'{base}all/', views.all, name='all'),
	path(f'{base}<int:story_id>/', views.detail, name='detail'),
	path(f'{base}vote/<slug:vote_id>', views.vote, name='vote'),
	path(f'{base}download_ebook/<slug:post_id>/', views.download_ebook, name='download_ebook'),
	path(f'{base}direct/', views.direct, name='direct'),
	path(f'{base}get_all/<int:story_id>/', views.get_all, name='get_all'),
	path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.png'))),
]
