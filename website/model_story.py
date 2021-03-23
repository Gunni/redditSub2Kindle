from django.db import models
from .model_author import Author


class Story(models.Model):
	author = models.ForeignKey(Author, on_delete=models.CASCADE)
	subreddit = models.CharField(max_length=200)
	title_fragment = models.CharField(max_length=200)
	is_regex = models.BooleanField(default=False)

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
