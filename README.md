# TeamSync 后端 API

TeamSync 团队协作管理系统后端 API，基于 Django REST Framework + JWT + MySQL + WebSocket 构建。

## 技术栈

- **框架**: Django 4.2 + Django REST Framework
- **认证**: JWT (djangorestframework-simplejwt)
- **数据库**: MySQL 8.0
- **缓存/消息队列**: Redis
- **实时通信**: Django Channels + WebSocket
- **定时任务**: Celery + Celery Beat
- **文件存储**: MinIO / Aliyun OSS

## 功能模块

### 1. 认证模块 (Auth)
- 用户注册/登录
- JWT Token 刷新
- 用户登出
- 当前用户信息

### 2. 项目管理 (Projects)
- 项目 CRUD
- 项目归档/取消归档
- 项目进度统计
- 项目成员管理

### 3. 任务管理 (Tasks)
- 任务 CRUD
- 子任务层级控制（最多3层）
- 任务状态流转
- 任务变更历史

### 4. 可视化 (Visualization)
- 甘特图数据
- 看板数据
- 日历数据
- 仪表盘

### 5. 成员管理 (Team)
- 团队成员列表
- 邀请成员
- 修改角色
- 移除成员

### 6. 通知 (Notifications)
- 通知列表
- 标记已读
- WebSocket 实时推送

### 7. 文件管理 (Files)
- 预签名 URL 上传
- 文件下载
- MinIO/OSS 支持

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.9+
- MySQL 8.0
- Redis
- MinIO (可选)

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

主要配置项：
```
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=teamsync
DB_USER=root
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=3306
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### 4. 初始化数据库

```bash
python init_db.py
```

或手动执行：
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 5. 启动服务

```bash
# 进入虚拟环境
venv\Scripts\activate
# 启动 Django 开发服务器
python manage.py runserver

# 或启动 ASGI 服务器（支持 WebSocket）
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 启动 Celery Worker
celery -A config worker -l info

# 启动 Celery Beat（定时任务）
celery -A config beat -l info
```

## API 文档

### 认证相关

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/auth/register/` | 用户注册 |
| POST | `/api/auth/login/` | 用户登录 |
| POST | `/api/auth/logout/` | 用户登出 |
| POST | `/api/auth/refresh/` | Token 刷新 |
| GET | `/api/auth/me/` | 当前用户信息 |

### 项目管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/projects/` | 项目列表 |
| POST | `/api/projects/create/` | 创建项目 |
| GET | `/api/projects/{id}/` | 项目详情 |
| PATCH | `/api/projects/{id}/update/` | 更新项目 |
| PATCH | `/api/projects/{id}/archive/` | 归档项目 |
| GET | `/api/projects/{id}/progress/` | 项目进度 |

### 任务管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/tasks/project/{project_id}/` | 任务列表 |
| POST | `/api/tasks/project/{project_id}/create/` | 创建任务 |
| GET | `/api/tasks/{id}/` | 任务详情 |
| PATCH | `/api/tasks/{id}/update/` | 更新任务 |
| PATCH | `/api/tasks/{id}/status/` | 更新状态 |
| POST | `/api/tasks/{id}/subtasks/` | 创建子任务 |
| GET | `/api/tasks/{id}/history/` | 变更历史 |

### 可视化

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/visualization/projects/{id}/gantt/` | 甘特图数据 |
| GET | `/api/visualization/projects/{id}/kanban/` | 看板数据 |
| GET | `/api/visualization/projects/{id}/calendar/` | 日历数据 |
| GET | `/api/visualization/kanban/` | 全局看板 |
| GET | `/api/visualization/gantt/` | 全局甘特图 |

### 仪表盘

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/dashboard/member/` | 成员仪表盘 |
| GET | `/api/dashboard/admin/` | 管理员仪表盘 |

## WebSocket

连接地址: `ws://localhost:8000/ws/notifications/`

需要在 query parameter 中传递 token:
```
ws://localhost:8000/ws/notifications/?token=<access_token>
```

## 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| check_overdue_tasks | 每天 00:01 | 检查逾期任务 |
| send_due_reminders | 每天 07:00 | 发送截止提醒 |

## 角色权限

| 角色 | 权限 |
|------|------|
| 超级管理员 | 所有权限 |
| 团队管理员 | 项目管理、任务管理、成员管理 |
| 团队成员 | 查看项目、编辑自己的任务 |
| 访客 | 等待邀请，无操作权限 |

## 开发规范

### 响应格式

成功响应：
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

错误响应：
```json
{
  "code": 400,
  "message": "错误描述",
  "errors": {
    "field_name": ["错误详情"]
  }
}
```

### 分页格式

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

## 测试

```bash
# 运行测试
python manage.py test

# 运行特定应用测试
python manage.py test apps.accounts
python manage.py test apps.projects
python manage.py test apps.tasks
```

## 部署

### 生产环境配置

1. 修改 `.env` 文件：
```
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com
```

2. 收集静态文件：
```bash
python manage.py collectstatic
```

3. 使用 Gunicorn + Daphne：
```bash
# HTTP
gunicorn config.wsgi:application -b 0.0.0.0:8000

# WebSocket
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```

## 许可证

MIT License
