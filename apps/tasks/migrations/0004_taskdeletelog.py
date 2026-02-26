# Generated manually on 2026-02-25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0003_alter_task_dates'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskDeleteLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_task_id', models.IntegerField(db_index=True, verbose_name='原任务ID')),
                ('title', models.CharField(max_length=200, verbose_name='任务标题')),
                ('description', models.TextField(blank=True, default='', verbose_name='任务描述')),
                ('project_id', models.IntegerField(db_index=True, verbose_name='项目ID')),
                ('project_title', models.CharField(blank=True, max_length=100, verbose_name='项目标题')),
                ('assignee_id', models.IntegerField(blank=True, null=True, verbose_name='负责人ID')),
                ('assignee_name', models.CharField(blank=True, max_length=150, verbose_name='负责人名称')),
                ('status', models.CharField(max_length=20, verbose_name='状态')),
                ('priority', models.CharField(max_length=20, verbose_name='优先级')),
                ('level', models.PositiveSmallIntegerField(default=1, verbose_name='层级')),
                ('parent_id', models.IntegerField(blank=True, null=True, verbose_name='父任务ID')),
                ('path', models.CharField(blank=True, default='', max_length=255, verbose_name='路径')),
                ('start_date', models.DateTimeField(blank=True, null=True, verbose_name='开始时间')),
                ('end_date', models.DateTimeField(blank=True, null=True, verbose_name='截止时间')),
                ('created_by_id', models.IntegerField(blank=True, null=True, verbose_name='创建者ID')),
                ('created_by_name', models.CharField(blank=True, max_length=150, verbose_name='创建者名称')),
                ('original_created_at', models.DateTimeField(null=True, blank=True, verbose_name='原创建时间')),
                ('deleted_by_name', models.CharField(blank=True, max_length=150, verbose_name='删除人名称')),
                ('deleted_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='删除时间')),
                ('deletion_reason', models.TextField(blank=True, default='', verbose_name='删除原因')),
                ('task_data_json', models.JSONField(blank=True, null=True, verbose_name='任务完整数据')),
                ('deleted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_tasks', to=settings.AUTH_USER_MODEL, verbose_name='删除人')),
            ],
            options={
                'verbose_name': '任务删除日志',
                'verbose_name_plural': '任务删除日志',
                'db_table': 'task_delete_logs',
                'ordering': ['-deleted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='taskdeletelog',
            index=models.Index(fields=['project_id', 'deleted_at'], name='task_delete_project_id_idx'),
        ),
        migrations.AddIndex(
            model_name='taskdeletelog',
            index=models.Index(fields=['deleted_by', 'deleted_at'], name='task_delete_deleted_by_idx'),
        ),
    ]
