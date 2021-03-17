# Generated by Django 3.1.5 on 2021-02-16 01:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0002_subscription_enabled'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='subscription',
            options={'ordering': ['title_fragment']},
        ),
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together={('username', 'subreddit', 'title_fragment')},
        ),
    ]
