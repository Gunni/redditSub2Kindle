# Generated by Django 3.1.5 on 2021-03-20 03:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0008_auto_20210317_2145'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='is_regex',
            field=models.BooleanField(default=False),
        ),
    ]