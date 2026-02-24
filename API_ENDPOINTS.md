# TeamSync API 端点汇总

## 基础信息

- **基础URL**: `http://localhost:8000/api`
- **认证方式**: JWT Bearer Token
- **请求头**: `Authorization: Bearer <access_token>`

---

## 认证模块 (Auth)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/auth/register/` | 用户注册 | 公开 |
| POST | `/auth/login/` | 用户登录 | 公开 |
| POST | `/auth/logout/` | 用户登出 | 登录 |
| POST | `/auth/refresh/` | Token 刷新 | 公开 |
| GET | `/auth/me/` | 当前用户信息 | 登录 |
| PATCH | `/auth/me/update/` | 更新当前用户 | 登录 |
| GET | `/auth/visitor/status/` | 访客状态 | 登录 |

### 注册请求示例
```json
POST /api/auth/register/
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "password123",
  "password_confirm": "password123",
  "join_type": "create",
  "team_name": "研发团队"
}
```

### 登录请求示例
```json
POST /api/auth/login/
{
  "username": "zhangsan",
  "password": "password123"
}
```

---

## 团队管理 (Team)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/team/members/` | 成员列表 | 管理员 |
| POST | `/team/invite/` | 邀请成员 | 管理员 |
| GET | `/team/check-user/` | 检查用户是否可邀请 | 管理员 |
| PATCH | `/team/members/{id}/role/` | 修改角色 | 管理员 |
| DELETE | `/team/members/{id}/` | 移除成员 | 管理员 |

### 邀请成员

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名或邮箱 |
| role | string | 否 | 角色，可选 `team_admin` 或 `member`，默认为 `member` |

**角色枚举：**
- `team_admin` - 团队管理员
- `member` - 普通成员（默认）

**请求示例：**
```json
POST /api/team/invite/
{
  "username": "lisi",
  "role": "member"
}
```

**响应示例：**
```json
{
  "code": 200,
  "message": "邀请成功",
  "data": {
    "user_id": 2,
    "username": "lisi",
    "role": "member",
    "invited_at": "2026-02-12T10:30:00Z"
  }
}
```

**错误码：**
- `400` - 用户不存在，请先注册账号
- `400` - 该用户已是团队成员
- `409` - 该用户已被邀请

### 检查用户是否可邀请

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 要检查的用户名 |

**请求示例：**
```
GET /api/team/check-user/?username=lisi
```

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "exists": true,
    "available": false,
    "message": "用户已在团队中"
  }
}
```

**状态组合说明：**

| exists | available | 含义 |
|--------|-----------|------|
| false | false | 用户不存在，无法邀请 |
| true | true | 用户存在且不在团队中，可以邀请 |
| true | false | 用户存在但已在团队中，无法邀请 |

### 修改成员角色

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| role | string | 是 | 新角色，`team_admin` 或 `member` |

**限制：**
- 不能修改自己的角色（防止团队无人管理）

**请求示例：**
```json
PATCH /api/team/members/5/role/
{
  "role": "team_admin"
}
```

**错误码：**
- `400` - 该用户不属于您的团队
- `400` - 不能修改自己的角色

---

## 项目管理 (Projects)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/projects/` | 项目列表 | 团队成员 |
| POST | `/projects/create/` | 创建项目 | 管理员 |
| GET | `/projects/{id}/` | 项目详情 | 团队成员 |
| PATCH | `/projects/{id}/update/` | 更新项目 | 管理员 |
| PATCH | `/projects/{id}/archive/` | 归档项目 | 管理员 |
| PATCH | `/projects/{id}/unarchive/` | 取消归档 | 管理员 |
| DELETE | `/projects/{id}/delete/` | 删除项目 | 超管 |
| GET | `/projects/{id}/progress/` | 项目进度 | 管理员 |
| PUT | `/projects/{id}/members/` | 更新成员 | 管理员 |

### 创建项目请求示例
```json
POST /api/projects/create/
{
  "title": "电商平台重构",
  "description": "对现有电商平台进行技术重构",
  "status": "planning",
  "start_date": "2026-02-15",
  "end_date": "2026-03-15",
  "member_ids": [1, 2, 3]
}
```

### 查询参数
- `status`: 状态过滤 (planning, pending, in_progress, completed)
- `is_archived`: 是否包含归档项目 (true/false)
- `search`: 标题搜索

---

## 任务管理 (Tasks)

### 全局任务视图（跨项目）

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/tasks/kanban/` | 全局看板数据 | 团队成员 |
| GET | `/tasks/list/` | 全局任务列表 | 团队成员 |
| GET | `/tasks/gantt/` | 全局甘特图数据 | 团队成员 |
| GET | `/tasks/calendar/` | 全局日历数据 | 团队成员 |

### 项目任务管理

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/tasks/project/{project_id}/` | 任务列表 | 团队成员 |
| POST | `/tasks/project/{project_id}/create/` | 创建主任务 | 管理员 |
| GET | `/tasks/{id}/` | 任务详情 | 团队成员 |
| PATCH | `/tasks/{id}/update/` | 更新任务 | 负责人/管理员 |
| PATCH | `/tasks/{id}/status/` | 更新状态 | 负责人/管理员 |
| DELETE | `/tasks/{id}/delete/` | 删除任务 | 超管 |
| GET | `/tasks/{id}/history/` | 变更历史 | 团队成员 |
| POST | `/tasks/{id}/subtasks/` | 创建子任务 | 负责人 |
| GET | `/tasks/project/{project_id}/progress/` | 任务统计 | 管理员 |

---

### 全局看板数据

**GET** `/tasks/kanban/`

> 权限：所有团队成员
> 数据范围：管理员返回所有任务，成员返回自己的任务

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | integer | 否 | 项目过滤，不传则显示所有项目 |
| assignee | string | 否 | me(我的), all(全部)，默认 all |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "columns": [
      {
        "id": "planning",
        "title": "规划中",
        "color": "#94A3B8",
        "tasks": [
          {
            "id": 5,
            "title": "技术选型",
            "priority": "high",
            "assignee": {"id": 1, "username": "zhangsan"},
            "project": {"id": 1, "title": "电商平台重构"},
            "end_date": "2026-02-20",
            "normal_flag": "normal"
          }
        ]
      }
    ]
  }
}
```

---

### 全局任务列表

**GET** `/tasks/list/`

> 权限：所有团队成员
> 数据范围：管理员返回所有任务，成员返回自己的任务

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | integer | 否 | 项目过滤 |
| status | string | 否 | 状态过滤，多个用逗号分隔 |
| priority | string | 否 | 优先级过滤 |
| assignee | string | 否 | me(我的), all(全部) |
| search | string | 否 | 标题搜索 |
| sort_by | string | 否 | 排序字段: created_at, end_date, priority |
| sort_order | string | 否 | 排序方向: asc, desc |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 20 |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "API设计",
        "status": "in_progress",
        "priority": "high",
        "level": 1,
        "assignee": {"id": 1, "username": "zhangsan"},
        "project": {"id": 1, "title": "电商平台重构"},
        "start_date": "2026-02-01",
        "end_date": "2026-02-10",
        "normal_flag": "normal",
        "created_at": "2026-02-01T08:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 50,
      "total_pages": 3
    }
  }
}
```

---

### 全局甘特图数据

**GET** `/tasks/gantt/`

> 权限：所有团队成员
> 数据范围：管理员返回所有主任务，成员返回自己的主任务

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | integer | 否 | 项目过滤 |
| start_date | date | 否 | 开始日期范围 |
| end_date | date | 否 | 结束日期范围 |
| view_mode | string | 否 | 视图模式: day(默认), week, month |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "view_mode": "day",
    "date_range": {
      "start": "2026-02-01",
      "end": "2026-02-28"
    },
    "tasks": [
      {
        "id": 1,
        "title": "需求分析",
        "start": "2026-02-01",
        "end": "2026-02-05",
        "progress": 100,
        "status": "completed",
        "assignee": {"id": 1, "username": "zhangsan"},
        "project": {"id": 1, "title": "电商平台重构"},
        "level": 1,
        "children": []
      }
    ],
    "projects": [
      {"id": 1, "title": "电商平台重构", "color": "#0D9488"},
      {"id": 2, "title": "官网改版", "color": "#0891B2"}
    ]
  }
}
```

---

### 全局日历数据

**GET** `/tasks/calendar/`

> 权限：所有团队成员
> 数据范围：管理员返回所有任务，成员返回自己的任务

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| year | integer | 是 | 年份 |
| month | integer | 是 | 月份 (1-12) |
| project_id | integer | 否 | 项目过滤 |
| assignee | string | 否 | me(我的), all(全部) |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "year": 2026,
    "month": 2,
    "days": [
      {
        "date": "2026-02-01",
        "tasks": [
          {
            "id": 1,
            "title": "需求分析",
            "status": "completed",
            "priority": "high",
            "assignee": {"id": 1, "username": "zhangsan"},
            "project": {"id": 1, "title": "电商平台重构"}
          }
        ]
      }
    ]
  }
}
```

---

### 创建任务请求示例

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| title | string | 是 | 任务标题 |
| description | string | 否 | 任务描述 |
| assignee_id | integer | 是 | 负责人ID |
| priority | string | 否 | 优先级：`urgent`/`high`/`medium`/`low`，默认 `medium` |
| start_date | string | 否 | 开始日期，格式 `YYYY-MM-DD` |
| end_date | string | 否 | 结束日期，格式 `YYYY-MM-DD` |

```json
POST /api/tasks/project/1/create/
{
  "title": "数据库设计",
  "description": "设计系统数据库结构",
  "assignee_id": 2,
  "priority": "high",
  "start_date": "2026-02-10",
  "end_date": "2026-02-15"
}
```

**最小化创建示例（只有必填字段）：**
```json
POST /api/tasks/project/1/create/
{
  "title": "简单任务",
  "assignee_id": 2
}
```

### 创建子任务请求示例

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| title | string | 是 | 子任务标题 |
| description | string | 否 | 子任务描述 |
| priority | string | 否 | 优先级，默认继承父任务 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

```json
POST /api/tasks/5/subtasks/
{
  "title": "用户表设计",
  "description": "设计用户相关表结构",
  "priority": "medium"
}
```

### 任务附件管理

**任务和子任务都可以单独添加附件**，使用以下接口：

#### 1. 获取上传URL
```
POST /api/files/tasks/{task_id}/upload-url/
```

**请求体：**
```json
{
  "file_name": "design.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

**响应：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "upload_url": "https://minio.example.com/...",
    "file_key": "tasks/5/uuid-design.pdf",
    "expires_in": 300
  }
}
```

#### 2. 上传文件到存储
使用返回的 `upload_url` 直接上传文件（PUT 请求）。

#### 3. 确认上传并创建附件记录
```
POST /api/files/tasks/{task_id}/attachments/
```

**请求体：**
```json
{
  "file_key": "tasks/5/uuid-design.pdf",
  "file_name": "design.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

**权限说明：**
- 只有任务负责人或管理员可以上传附件
- 项目归档后无法上传附件

**示例场景：**
- 主任务（ID: 10）添加附件 → `POST /api/files/tasks/10/upload-url/`
- 子任务（ID: 20）添加附件 → `POST /api/files/tasks/20/upload-url/`

### 更新状态请求示例
```json
PATCH /api/tasks/5/status/
{
  "status": "completed"
}
```

### 查询参数
- `view`: 视图类型 (tree, flat)
- `assignee`: 负责人过滤 (me, all, user_id)
- `status`: 状态过滤
- `level`: 层级过滤 (1, 2, 3)
- `search`: 标题搜索

---

## 可视化 (Visualization)

### 项目级视图

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/visualization/projects/{id}/gantt/` | 甘特图 | 团队成员 |
| GET | `/visualization/projects/{id}/kanban/` | 看板 | 团队成员 |
| GET | `/visualization/projects/{id}/calendar/` | 日历 | 团队成员 |

### 全局视图

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/visualization/kanban/` | 全局看板 | 团队成员 |
| GET | `/visualization/gantt/` | 全局甘特图 | 团队成员 |
| GET | `/visualization/calendar/` | 全局日历 | 团队成员 |
| GET | `/visualization/list/` | 全局任务列表 | 团队成员 |

### 甘特图查询参数
- `start_date`: 开始日期范围
- `end_date`: 结束日期范围
- `view_mode`: 视图模式 (day, week, month)

### 看板查询参数
- `assignee`: 负责人过滤 (me, all)

### 日历查询参数
- `year`: 年份
- `month`: 月份 (1-12)
- `assignee`: 负责人过滤 (me, all)

---

## 仪表盘 (Dashboard)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/dashboard/member/` | 成员仪表盘 | 成员 |
| GET | `/dashboard/admin/` | 管理员仪表盘 | 管理员 |

---

## 通知 (Notifications)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/notifications/` | 通知列表 | 登录 |
| PATCH | `/notifications/{id}/read/` | 标记已读 | 登录 |
| PATCH | `/notifications/read-all/` | 全部已读 | 登录 |
| DELETE | `/notifications/{id}/` | 删除通知 | 登录 |

### 查询参数
- `is_read`: 是否已读过滤 (true/false)

---

## 文件管理 (Files)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/files/tasks/{task_id}/upload-url/` | 获取上传URL | 负责人/管理员 |
| POST | `/files/tasks/{task_id}/attachments/` | 确认上传 | 负责人/管理员 |
| GET | `/files/attachments/{id}/download-url/` | 获取下载URL | 负责人/管理员 |
| DELETE | `/files/attachments/{id}/` | 删除附件 | 上传者/管理员 |

### 附件上传流程

附件上传采用**预签名 URL** 方式，分为三步：

#### 第一步：获取上传URL
```
POST /api/files/tasks/{task_id}/upload-url/
```

**说明：**
- `task_id` 可以是主任务ID或子任务ID
- 主任务和子任务都可以独立添加附件

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_name | string | 是 | 文件名，如 `design.pdf` |
| file_type | string | 是 | MIME 类型，如 `application/pdf` |
| file_size | integer | 是 | 文件大小（字节） |

```json
POST /api/files/tasks/5/upload-url/
{
  "file_name": "design.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

**响应：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "upload_url": "https://minio.example.com/...",
    "file_key": "tasks/5/uuid-design.pdf",
    "expires_in": 300
  }
}
```

#### 第二步：上传文件到存储
使用返回的 `upload_url` 直接上传文件：

```bash
curl -X PUT \
  -H "Content-Type: application/pdf" \
  --data-binary @design.pdf \
  "https://minio.example.com/..."
```

#### 第三步：确认上传
```
POST /api/files/tasks/{task_id}/attachments/
```

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_key | string | 是 | 第一步返回的 file_key |
| file_name | string | 是 | 文件名 |
| file_type | string | 是 | MIME 类型 |
| file_size | integer | 是 | 文件大小（字节） |

```json
POST /api/files/tasks/5/attachments/
{
  "file_key": "tasks/5/uuid-design.pdf",
  "file_name": "design.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

**响应：**
```json
{
  "code": 201,
  "message": "附件上传成功",
  "data": {
    "id": 1,
    "file_name": "design.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000,
    "url": "https://minio.example.com/...",
    "uploaded_by": 2,
    "uploaded_by_name": "张三",
    "created_at": "2026-02-12T10:30:00Z"
  }
}
```

### 获取下载URL
```
GET /api/files/attachments/{attachment_id}/download-url/
```

**响应：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "download_url": "https://minio.example.com/...",
    "expires_in": 300
  }
}
```

### 删除附件
```
DELETE /api/files/attachments/{attachment_id}/
```

**权限：** 只有上传者或管理员可以删除

### 使用场景示例

**场景1：给主任务添加附件**
```
POST /api/files/tasks/10/upload-url/   # task_id=10 是主任务
```

**场景2：给子任务添加附件**
```
POST /api/files/tasks/25/upload-url/   # task_id=25 是子任务
```

**注意：**
- 主任务和子任务的附件是独立的
- 子任务删除不会影响父任务的附件
- 任务详情接口会返回该任务的所有附件列表

---

## WebSocket

### 连接地址
```
ws://localhost:8000/ws/notifications/?token=<access_token>
```

### 消息格式

**服务端 → 客户端:**
```json
{
  "type": "notification",
  "data": {
    "id": 1,
    "type": "task_assigned",
    "title": "新任务分配",
    "content": "您被分配了新任务：API设计",
    "task_id": 5,
    "is_read": false,
    "created_at": "2026-02-10T08:44:13Z"
  }
}
```

**客户端 → 服务端:**
```json
{
  "action": "ping"
}
```

---

## 错误码

| 错误码 | 说明 | HTTP状态 |
|--------|------|---------|
| 1001 | 用户名或密码错误 | 401 |
| 1002 | Token已过期 | 401 |
| 1003 | Token无效 | 401 |
| 1004 | 用户未激活 | 403 |
| 2001 | 项目不存在 | 404 |
| 2002 | 项目成员已存在 | 409 |
| 2003 | 项目必须至少有一个成员 | 422 |
| 2004 | 项目已归档 | 422 |
| 2005 | 项目未归档，无法删除 | 422 |
| 3001 | 任务不存在 | 404 |
| 3002 | 任务层级超过限制(最多3层) | 422 |
| 3003 | 无权创建子任务(非负责人) | 403 |
| 3004 | 无权查看任务详情 | 403 |
| 3005 | 存在子任务，无法删除 | 422 |
| 3006 | 任务已归档，无法修改 | 422 |
| 4001 | 用户不存在 | 404 |
| 4002 | 用户已是团队成员 | 409 |
| 4003 | 用户未加入团队 | 403 |
| 5001 | 文件上传失败 | 500 |
| 5002 | 文件类型不支持 | 400 |
| 5003 | 文件大小超过限制 | 400 |
| 5004 | 文件不存在 | 404 |

---

## 数据模型

### 用户角色
- `super_admin`: 超级管理员
- `team_admin`: 团队管理员
- `member`: 团队成员
- `visitor`: 访客

### 项目状态
- `planning`: 规划中
- `pending`: 待处理
- `in_progress`: 进行中
- `completed`: 已完成

### 任务状态
- `planning`: 规划中
- `pending`: 待处理
- `in_progress`: 进行中
- `completed`: 已完成

### 任务优先级
- `urgent`: 紧急
- `high`: 高
- `medium`: 中
- `low`: 低

### 正常标识
- `normal`: 正常
- `overdue`: 已逾期

### 通知类型
- `task_assigned`: 任务分配
- `status_changed`: 状态变更
- `due_reminder`: 截止提醒
- `overdue`: 逾期通知
- `member_invited`: 成员邀请
