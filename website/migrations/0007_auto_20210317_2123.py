# Generated by Django 3.1.5 on 2021-03-17 21:23

from django.db import migrations

def move_subscriptions_to_stories(apps, schema_editor):
	# We can't import the models directly as it may be a newer
	# version than this migration expects. We use the historical version.
	Author = apps.get_model('website', 'Author')
	Story  = apps.get_model('website', 'Story')

	for author in Author.objects.all():
		story = Story()

		story.author         = author
		story.subreddit      = author.subreddit
		story.title_fragment = author.title_fragment
		story.enabled        = author.enabled

		story.save()

class Migration(migrations.Migration):

	dependencies = [
		('website', '0006_story'),
	]

	operations = [
		migrations.RunPython(move_subscriptions_to_stories),
	]
