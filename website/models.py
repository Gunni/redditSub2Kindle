import praw
from django.db import models

# Create your models here.
class Author(models.Model):
	username = models.CharField(max_length=200)
	enabled = models.BooleanField(default=True)

	constraints = [
		models.UniqueConstraint(fields=['username'], name='username must be unique')
	]

	def __str__(self):
		return f'/u/{self.username}'

	def __getitem__(self, item):
		reddit = praw.Reddit()

		if item == 'username':
			return reddit.user(self.username)

		return super().__getitem__(item)

	class Meta:
		ordering = ['username']

class Story(models.Model):
	author = models.ForeignKey(Author, on_delete=models.CASCADE)
	subreddit = models.CharField(max_length=200)
	title_fragment = models.CharField(max_length=200)

	enabled = models.BooleanField(default=True)

	constraints = [
		models.UniqueConstraint(fields=['author', 'subreddit', 'title_fragment'], name='`username+subreddit+title fragment` must all be unique')
	]

	def __str__(self):
		return f'{self.title_fragment}'

	class Meta:
		unique_together = [
			['author', 'subreddit', 'title_fragment'],
		]

		ordering = ['title_fragment']
