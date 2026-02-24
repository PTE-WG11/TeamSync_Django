# TeamSync 后端项目总结

## 项目概述

TeamSync 团队协作管理系统后端 API，基于 Django REST Framework + JWT + MySQL + WebSocket 构建。

---

## 项目结构

```
teamsync_backend/
├── apps/                          # 应用模块
│   ├── accounts/                  # 用户认证与团队管理
│   │   ├── models.py              # User, Team, TeamInvitation 模型
│   │   ├── views.py               # 认证、用户、团队视图
│   │   ├── serializers.py         # 序列化器
│   │   ├── urls.py                # 认证路由
│   │   ├── team_urls.py           # 团队管理路由
│   │   ├── admin.py               # 后台管理配置
│   │   ├── tests.py               # 单元测试
│   │   └── apps.py                # 应用配置
│   │
│   ├── projects/                  # 项目管理
│   │   ├── models.py              # Project, ProjectMember 模型
│   │   ├── views.py               # 项目 CRUD 视图
│   │   ├── serializers.py         # 序列化器
│   │   ├── urls.py                # 路由配置
│   │   ├── admin.py               # 后台管理配置
│   │   └── apps.py                # 应用配置
│   │
│   ├── tasks/                     # 任务管理
│   │   ├── models.py              # Task, TaskHistory, TaskAttachment 模型
│   │   ├── views.py               # 任务 CRUD 视图
│   │   ├── serializers.py         # 序列化器
│   │   ├── urls.py                # 路由配置
│   │   ├── tasks.py               # Celery 定时任务
│   │   ├── admin.py               # 后台管理配置
│   │   └── apps.py                # 应用配置
│   │
│   ├── notifications/             # 通知系统
│   │   ├── models.py              # Notification 模型
│   │   ├── views.py               # 通知视图
│   │   ├── services.py            # 通知服务
│   │   ├── consumers.py           # WebSocket 消费者
│   │   ├── routing.py             # WebSocket 路由
│   │   ├── serializers.py         # 序列化器
│   │   ├── urls.py                # 路由配置
│   │   ├── admin.py               # 后台管理配置
│   │   └── apps.py                # 应用配置
│   │
│   ├── files/                     # 文件管理
│   │   ├── storage.py             # MinIO/OSS 存储服务
│   │   ├── views.py               # 文件上传/下载视图
│   │   ├── urls.py                # 路由配置
│   │   └── apps.py                # 应用配置
│   │
│   └── visualization/             # 数据可视化
│       ├── views.py               # 甘特图/看板/日历视图
│       ├── dashboard_views.py     # 仪表盘视图
│       ├── urls.py                # 路由配置
│       ├── dashboard_urls.py      # 仪表盘路由
│       └── apps.py                # 应用配置
│
├── config/                        # 项目配置
│   ├── settings.py                # Django 设置
│   ├── urls.py                    # 主路由配置
│   ├── wsgi.py                    # WSGI 配置
│   ├── asgi.py                    # ASGI 配置 (WebSocket)
│   ├── celery.py                  # Celery 配置
│   ├── pagination.py              # 自定义分页
│   ├── renderers.py               # 自定义渲染器
│   ├── permissions.py             # 自定义权限
│   └── exceptions.py              # 自定义异常
│
├── media/                         # 媒体文件目录
├── static/                        # 静态文件目录
├── manage.py                      # Django 管理脚本
├── init_db.py                     # 数据库初始化脚本
├── start.sh                       # 启动脚本
├── requirements.txt               # Python 依赖
├── Dockerfile                     # Docker 镜像配置
├── docker-compose.yml             # Docker Compose 配置
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git 忽略配置
├── README.md                      # 项目说明
├── API_ENDPOINTS.md               # API 端点文档
└── PROJECT_SUMMARY.md             # 项目总结
```

---

## 核心功能

### 1. 认证模块
- ✅ JWT Token 认证 (Access/Refresh)
- ✅ 用户注册/登录/登出
- ✅ 角色权限控制 (超级管理员/团队管理员/成员/访客)
- ✅ 当前用户信息获取

### 2. 团队管理
- ✅ 团队成员列表
- ✅ 邀请成员 (输入用户名/邮箱)
- ✅ 修改成员角色
- ✅ 移除成员

### 3. 项目管理
- ✅ 项目 CRUD
- ✅ 项目归档/取消归档
- ✅ 项目进度统计
- ✅ 项目成员管理
- ✅ 硬删除 (仅超级管理员)

### 4. 任务管理
- ✅ 任务 CRUD
- ✅ 子任务层级控制 (最多3层)
- ✅ 任务状态流转
- ✅ 任务变更历史
- ✅ 权限脱敏 (成员只能查看自己的任务详情)

### 5. 可视化
- ✅ 甘特图数据
- ✅ 看板数据
- ✅ 日历数据
- ✅ 成员仪表盘
- ✅ 管理员仪表盘

### 6. 通知系统
- ✅ 通知持久化存储
- ✅ WebSocket 实时推送
- ✅ 通知类型: 任务分配、状态变更、截止提醒、逾期通知

### 7. 文件管理
- ✅ MinIO 预签名 URL 上传
- ✅ Aliyun OSS 支持 (可切换)
- ✅ 文件下载
- ✅ 文件删除权限控制

### 8. 定时任务
- ✅ 每日 00:01 检查逾期任务
- ✅ 每日 07:00 发送截止提醒

---

## API 端点统计

| 模块 | 端点数量 |
|------|---------|
| 认证 | 7 |
| 团队管理 | 5 |
| 项目管理 | 9 |
| 任务管理 | 9 |
| 可视化 | 7 |
| 仪表盘 | 2 |
| 通知 | 4 |
| 文件管理 | 4 |
| **总计** | **46** |

---

## 数据模型

### 用户相关
- **User**: 用户模型 (扩展 Django AbstractUser)
- **Team**: 团队模型
- **TeamInvitation**: 团队邀请记录

### 项目相关
- **Project**: 项目模型
- **ProjectMember**: 项目成员关系

### 任务相关
- **Task**: 任务模型 (支持层级结构)
- **TaskHistory**: 任务变更历史
- **TaskAttachment**: 任务附件

### 通知相关
- **Notification**: 通知模型

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Django 4.2 + DRF |
| 认证 | JWT (djangorestframework-simplejwt) |
| 数据库 | MySQL 8.0 |
| 缓存/消息队列 | Redis |
| 实时通信 | Django Channels + WebSocket |
| 定时任务 | Celery + Celery Beat |
| 文件存储 | MinIO / Aliyun OSS |
| 部署 | Docker + Docker Compose |

---

## 快速启动

### 方式一: 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 初始化数据库
python init_db.py

# 4. 启动服务
python manage.py runserver
```

### 方式二: Docker

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 创建超级管理员
docker-compose exec web python manage.py createsuperuser
```

---

## 开发规范

### 响应格式

成功响应:
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

错误响应:
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

---

## 文件统计

- **Python 文件**: 50+
- **总代码行数**: 约 8000+ 行
- **API 端点**: 46 个
- **数据模型**: 10 个

---

## 后续建议

1. **测试覆盖**
   - 编写更多单元测试
   - 添加集成测试
   - 配置 CI/CD

2. **性能优化**
   - 添加缓存层 (Redis)
   - 数据库查询优化
   - 分页优化

3. **安全加固**
   - 添加请求限流
   - 配置 HTTPS
   - 添加审计日志

4. **监控运维**
   - 添加日志收集
   - 配置监控告警
   - 添加健康检查

---

## 联系方式

如有问题或建议，请联系开发团队。
