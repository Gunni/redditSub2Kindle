import praw
from django.db import models
from django.db.models.functions import Lower
from django.forms import ModelForm


class AuthorOrderManager(models.Manager):
	def get_queryset(self):
		return super().get_queryset().order_by(Lower('username'))


class Author(models.Model):
	username = models.CharField(max_length=200)
	enabled = models.BooleanField(default=True)

	constraints = [
		models.UniqueConstraint(fields=['username'], name='username must be unique')
	]

	ordered_objects = AuthorOrderManager()

	def __str__(self):
		return self.username

	def __getitem__(self, item):
		reddit = praw.Reddit()

		if item == 'username':
			return reddit.user(self.username)

		return super().__getitem__(item)

	class Meta:
		ordering = ['username']


class AuthorForm(ModelForm):
	class Meta:
		model = Author
		fields = ['username', 'enabled']
