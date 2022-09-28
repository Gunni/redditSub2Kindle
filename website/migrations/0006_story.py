# Generated by Django 3.1.5 on 2021-03-17 21:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0005_auto_20210317_2112'),
    ]

    operations = [
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.author')),
                ('subreddit', models.CharField(max_length=200)),
                ('title_fragment', models.CharField(max_length=200)),
                ('enabled', models.BooleanField(default=True)),
            ],
        ),
    ]
