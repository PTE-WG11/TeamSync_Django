# TeamSync 文件上传使用指南

## 一、上传流程概述

TeamSync 采用**预签名 URL** 方式上传文件，分为三个步骤：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. 获取    │     │  2. 上传    │     │  3. 确认    │
│  上传URL    │────▶│  文件到存储  │────▶│  上传完成   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 为什么使用预签名 URL？

1. **安全性**：后端控制上传权限，生成带过期时间的临时 URL
2. **减轻服务器压力**：文件直接上传到 MinIO/OSS，不经过后端服务器
3. **灵活性**：支持大文件上传，支持断点续传

---

## 二、支持的存储后端

| 存储类型 | 配置项 | 说明 |
|---------|--------|------|
| MinIO | `MINIO_*` | 本地/私有部署，默认启用 |
| 阿里云 OSS | `OSS_*` | 云端存储，需开启 `OSS_ENABLED` |

优先级：根据 `FILE_STORAGE_PRIORITY` 配置决定

---

## 三、接口详解

### 3.1 获取上传 URL

**接口信息**

| 属性 | 值 |
|------|-----|
| URL | `POST /api/files/tasks/{task_id}/upload-url/` |
| 认证 | JWT Bearer Token |
| 权限 | 任务负责人/管理员 |

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_name | string | 是 | 文件名，如 `design.pdf` |
| file_type | string | 是 | MIME 类型，如 `application/pdf` |
| file_size | integer | 是 | 文件大小（字节） |

**请求示例**

```bash
curl -X POST \
  'http://localhost:8000/api/files/tasks/5/upload-url/' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -H 'Content-Type: application/json' \
  -d '{
    "file_name": "design.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000
  }'
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "upload_url": "https://minio.example.com/teamsync/tasks/5/a1b2c3d4.pdf?X-Amz-Algorithm=...",
    "file_key": "tasks/5/a1b2c3d4.pdf",
    "expires_in": 300
  }
}
```

### 3.2 上传文件到存储

使用返回的 `upload_url` 直接上传文件（**PUT 请求**）：

```bash
curl -X PUT \
  -H "Content-Type: application/pdf" \
  --data-binary @/path/to/design.pdf \
  "https://minio.example.com/teamsync/tasks/5/a1b2c3d4.pdf?X-Amz-Algorithm=..."
```

**JavaScript 示例**

```javascript
// 使用原生 fetch
const uploadFile = async (uploadUrl, file) => {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type,
    },
    body: file,
  });
  
  if (response.ok) {
    console.log('上传成功');
    return true;
  } else {
    console.error('上传失败');
    return false;
  }
};

// 使用 Axios
const uploadFileAxios = async (uploadUrl, file) => {
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': file.type,
    },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      );
      console.log(`上传进度: ${percentCompleted}%`);
    },
  });
};
```

### 3.3 确认上传

文件上传成功后，调用此接口保存附件记录到数据库：

**接口信息**

| 属性 | 值 |
|------|-----|
| URL | `POST /api/files/tasks/{task_id}/attachments/` |
| 认证 | JWT Bearer Token |
| 权限 | 任务负责人/管理员 |

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_key | string | 是 | 第一步返回的 file_key |
| file_name | string | 是 | 原始文件名 |
| file_type | string | 是 | MIME 类型 |
| file_size | integer | 是 | 文件大小（字节） |

**请求示例**

```bash
curl -X POST \
  'http://localhost:8000/api/files/tasks/5/attachments/' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -H 'Content-Type: application/json' \
  -d '{
    "file_key": "tasks/5/a1b2c3d4.pdf",
    "file_name": "design.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000
  }'
```

**响应示例**

```json
{
  "code": 201,
  "message": "附件上传成功",
  "data": {
    "id": 1,
    "file_name": "design.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000,
    "url": "https://minio.example.com/teamsync/tasks/5/a1b2c3d4.pdf",
    "uploaded_by": 2,
    "uploaded_by_name": "张三",
    "created_at": "2026-02-12T10:30:00Z"
  }
}
```

---

## 四、完整前端示例

```javascript
class FileUploader {
  constructor(apiBaseUrl, token) {
    this.apiBaseUrl = apiBaseUrl;
    this.token = token;
  }

  // 步骤1: 获取上传URL
  async getUploadUrl(taskId, file) {
    const response = await fetch(
      `${this.apiBaseUrl}/api/files/tasks/${taskId}/upload-url/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_name: file.name,
          file_type: file.type,
          file_size: file.size,
        }),
      }
    );
    
    if (!response.ok) {
      throw new Error('获取上传URL失败');
    }
    
    const result = await response.json();
    return result.data;
  }

  // 步骤2: 上传文件到存储
  async uploadToStorage(uploadUrl, file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded * 100) / event.total);
          onProgress(percent);
        }
      });
      
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          resolve();
        } else {
          reject(new Error(`上传失败: ${xhr.statusText}`));
        }
      });
      
      xhr.addEventListener('error', () => reject(new Error('上传出错')));
      
      xhr.open('PUT', uploadUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  }

  // 步骤3: 确认上传
  async confirmUpload(taskId, fileInfo) {
    const response = await fetch(
      `${this.apiBaseUrl}/api/files/tasks/${taskId}/attachments/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(fileInfo),
      }
    );
    
    if (!response.ok) {
      throw new Error('确认上传失败');
    }
    
    const result = await response.json();
    return result.data;
  }

  // 完整上传流程
  async upload(taskId, file, onProgress) {
    try {
      // 1. 获取上传URL
      const { upload_url, file_key } = await this.getUploadUrl(taskId, file);
      
      // 2. 上传文件
      await this.uploadToStorage(upload_url, file, onProgress);
      
      // 3. 确认上传
      const attachment = await this.confirmUpload(taskId, {
        file_key,
        file_name: file.name,
        file_type: file.type,
        file_size: file.size,
      });
      
      return attachment;
    } catch (error) {
      console.error('上传失败:', error);
      throw error;
    }
  }
}

// 使用示例
const uploader = new FileUploader('http://localhost:8000', 'your-jwt-token');

const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  try {
    const attachment = await uploader.upload(
      5, // taskId
      file,
      (percent) => console.log(`上传进度: ${percent}%`)
    );
    console.log('上传成功:', attachment);
  } catch (error) {
    alert('上传失败: ' + error.message);
  }
});
```

---

## 五、文件限制

| 限制项 | 值 | 说明 |
|--------|-----|------|
| 最大文件大小 | 500MB | 可在 `BaseStorage.MAX_FILE_SIZE` 修改 |
| 上传URL有效期 | 300秒（5分钟） | 过期后需要重新获取 |
| 下载URL有效期 | 300秒（5分钟） | 过期后需要重新获取 |

### 支持的文件类型

| 类型 | 扩展名 |
|------|--------|
| 图片 | .jpg, .jpeg, .png, .gif, .bmp, .webp |
| 文档 | .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt |
| 压缩包 | .zip, .rar, .7z, .tar, .gz |
| 代码 | .py, .js, .html, .css, .json, .xml, .yaml, .yml |

---

## 六、错误码

| 错误码 | HTTP状态 | 说明 |
|--------|---------|------|
| 5001 | 400 | 文件上传失败 |
| 5002 | 400 | 文件类型不支持 |
| 5003 | 400 | 文件大小超过限制 |
| 5004 | 404 | 文件不存在 |
| 3004 | 403 | 无权上传附件 |
| 3006 | 422 | 项目已归档，无法上传 |

---

## 七、下载和删除

### 获取下载 URL

```bash
GET /api/files/attachments/{attachment_id}/download-url/
```

**响应**
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

```bash
DELETE /api/files/attachments/{attachment_id}/
```

**权限**：只有上传者或管理员可以删除

---

## 八、配置说明 (.env)

```bash
# 文件存储优先级: minio 或 oss
FILE_STORAGE_PRIORITY=minio

# MinIO 配置
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=teamsync
MINIO_SECURE=false

# OSS 配置（可选）
OSS_ENABLED=false
OSS_ACCESS_KEY_ID=your-access-key
OSS_ACCESS_KEY_SECRET=your-secret-key
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=teamsync
```

---

## 九、常见问题

### Q1: 为什么上传 URL 会过期？
为了安全考虑，预签名 URL 设置了 5 分钟的有效期，过期后需要重新调用接口获取。

### Q2: 可以上传多个文件吗？
可以，对每个文件重复上述三步流程即可。建议前端使用 Promise.all 并行处理。

### Q3: 如何支持大文件分片上传？
当前实现适用于中小文件（<500MB）。如需支持大文件分片，需要扩展存储服务和前端逻辑。

### Q4: 主任务和子任务的附件是独立的吗？
是的，每个任务（包括子任务）都有独立的附件列表，互不影响。
