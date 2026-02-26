# Generated manually on 2026-02-25
# Change start_date and end_date from DateField to DateTimeField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_alter_task_assignee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='开始时间'),
        ),
        migrations.AlterField(
            model_name='task',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='截止时间'),
        ),
    ]
