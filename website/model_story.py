from django.db import models
from .model_author import Author


class Story(models.Model):
	objects = None
	author = models.ForeignKey(Author, on_delete=models.CASCADE)
	subreddit = models.CharField(max_length=200)
	title_fragment = models.CharField(max_length=200)
	is_regex = models.BooleanField(default=False)
	is_fuzzy = models.BooleanField(default=True)
	fuzzy_ratio = models.IntegerField(default=80)

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
