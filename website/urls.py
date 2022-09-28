from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
	path('', views.get_list_of_subscriptions, name='index'),
	path('get_all_authors/', views.get_all_authors, name='get_all_authors'),
	#path('author/<int:author_id>', views.author, name='author'),
	path('all/', views.get_all_posts_of_all_subscriptions, name='all'),
	path('<int:story_id>/', views.get_list_of_subscription_posts, name='detail'),
	path('vote/<slug:vote_id>', views.vote, name='vote'),
	path('download_ebook/<slug:post_id>/', views.download_ebook, name='download_ebook'),
	path('textbook', views.textbook, name='textbook'),
	path('bookify', views.bookify, name='bookify'),
	path('get_n_chapter_as_ebook/<int:story_id>/', views.get_n_chapter_as_ebook, name='get_n_chapter_as_ebook'),
	path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.png'))),

	path('nuke_cache/', views.nuke_cache, name='nuke_cache'),
	path('nuke_cache/<int:story_id>/', views.nuke_cache, name='nuke_cache'),
]
