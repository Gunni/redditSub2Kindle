# Generated by Django 3.1.5 on 2021-02-16 01:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
    ]
