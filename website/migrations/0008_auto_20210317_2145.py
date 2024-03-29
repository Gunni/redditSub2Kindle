# Generated by Django 3.1.5 on 2021-03-17 21:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0007_auto_20210317_2123'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='author',
            options={'ordering': ['username']},
        ),
        migrations.AlterModelOptions(
            name='story',
            options={'ordering': ['title_fragment']},
        ),
        migrations.AlterUniqueTogether(
            name='author',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='story',
            unique_together={('author', 'subreddit', 'title_fragment')},
        ),
        migrations.RemoveField(
            model_name='author',
            name='subreddit',
        ),
        migrations.RemoveField(
            model_name='author',
            name='title_fragment',
        ),
    ]
