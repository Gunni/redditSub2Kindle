from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Author, Story

class AuthorAdmin(admin.ModelAdmin):
	list_display = ('username', 'enabled')

admin.site.register(Author, AuthorAdmin)

class StoryAdmin(admin.ModelAdmin):
	list_display = ('author', 'subreddit', 'title_fragment', 'is_regex', 'enabled')

admin.site.register(Story, StoryAdmin)
