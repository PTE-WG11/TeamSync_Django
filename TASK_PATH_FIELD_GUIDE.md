# 任务 Path 字段详解

## 一、Path 字段是什么？

`path` 是任务模型中的一个**路径枚举字段**，用于记录任务在层级结构中的完整路径。

```python
path = models.CharField(
    _('路径'),
    max_length=255,
    blank=True,
    default='',
    help_text=_('路径枚举，如 /1/12/34')
)
```

---

## 二、Path 的作用

### 1. 标识任务层级关系

| 任务类型 | level | path 值 | 说明 |
|---------|-------|---------|------|
| 主任务 | 1 | `''` (空字符串) | 没有父任务 |
| 子任务 | 2 | `'/1'` | 父任务是 ID=1 的主任务 |
| 孙任务 | 3 | `'/1/12'` | 祖父是 ID=1，父亲是 ID=12 |

### 2. 快速查询祖先和后代

```python
# 获取所有祖先任务（上级任务）
task.get_ancestors()  # 返回 QuerySet

# 获取所有后代任务（下级任务）
task.get_descendants()  # 返回 QuerySet
```

---

## 三、Path 的生成逻辑

### 3.1 创建主任务时

```python
# 主任务没有父任务，path 为空
task = Task.objects.create(
    title='主任务',
    level=1,
    parent=None,
    path='',  # 空字符串
    ...
)
```

### 3.2 创建子任务时

```python
# 通过 create_subtask 方法自动计算 path
subtask = parent_task.create_subtask(title='子任务')
```

**内部逻辑：**

```python
def create_subtask(self, **kwargs):
    """创建子任务时自动设置 path"""
    kwargs['path'] = self.full_path  # 使用父任务的 full_path
    return Task.objects.create(**kwargs)

@property
def full_path(self):
    """获取包含自身的完整路径"""
    if self.path:
        return f"{self.path}/{self.id}"  # 如: /1/12
    return str(self.id)  # 主任务返回: "1"
```

### 3.3 路径构建示例

```
创建主任务 (ID=1)
    ├── path = ''
    ├── full_path = '1'
    │
    └── 创建子任务 (ID=12)
            ├── path = '/1'          (继承父任务的 full_path)
            ├── full_path = '/1/12'
            │
            └── 创建孙任务 (ID=34)
                    ├── path = '/1/12'       (继承父任务的 full_path)
                    └── full_path = '/1/12/34'
```

---

## 四、Path 的应用场景

### 4.1 查询所有子任务

```python
# 获取主任务 (ID=1) 的所有后代任务
task = Task.objects.get(id=1)
descendants = task.get_descendants()
# SQL: SELECT * FROM tasks WHERE path LIKE '/1%'
```

### 4.2 查询所有上级任务

```python
# 获取孙任务 (ID=34) 的所有祖先任务
task = Task.objects.get(id=34)
ancestors = task.get_ancestors()
# 解析 path='/1/12' → 查询 ID in [1, 12]
```

### 4.3 删除任务时级联处理

```python
# 删除主任务时，由于设置了 on_delete=models.CASCADE
# 所有子任务会自动被删除（Django ORM 处理）
```

### 4.4 树形结构展示

```python
def to_tree_dict(self):
    """转换为树形字典"""
    data = {
        'id': self.id,
        'title': self.title,
        'level': self.level,
        'path': self.path,  # 前端可根据 path 渲染缩进
        'children': [...]
    }
```

---

## 五、相关方法对比

| 方法/属性 | 返回值示例 | 说明 |
|-----------|-----------|------|
| `task.path` | `'/1/12'` | 不包含自身的祖先路径 |
| `task.full_path` | `'/1/12/34'` | 包含自身的完整路径 |
| `task.get_ancestors()` | QuerySet | 所有上级任务 |
| `task.get_descendants()` | QuerySet | 所有下级任务 |
| `task.parent` | Task 对象 | 直接父任务 |
| `task.children` | RelatedManager | 直接子任务 |

---

## 六、数据库索引优化

```python
class Meta:
    indexes = [
        models.Index(fields=['path']),  # 为 path 字段创建索引
    ]
```

**为什么需要索引？**

```python
# 查询所有后代时使用了 startswith 查询
task.get_descendants()  # SQL: path LIKE '/1/12%'
# 索引可以加速这种前缀匹配查询
```

---

## 七、完整示例

```python
# 创建任务层级
project = Project.objects.get(id=1)

# 1. 创建主任务
main_task = Task.objects.create(
    project=project,
    title='前端开发',
    level=1,
    parent=None,
    path='',
    assignee=user
)
# main_task.path = ''
# main_task.full_path = '1'

# 2. 创建子任务
sub_task = main_task.create_subtask(title='登录页面')
# sub_task.path = '/1'
# sub_task.full_path = '/1/2'

# 3. 创建孙任务
grand_task = sub_task.create_subtask(title='表单验证')
# grand_task.path = '/1/2'
# grand_task.full_path = '/1/2/3'

# 4. 查询祖先
ancestors = grand_task.get_ancestors()
# 返回: [主任务(ID=1), 子任务(ID=2)]

# 5. 查询后代
descendants = main_task.get_descendants()
# 返回: [子任务(ID=2), 孙任务(ID=3)]
```

---

## 八、总结

| 特性 | 说明 |
|------|------|
| **本质** | 存储任务的层级关系，类似文件系统的路径 |
| **格式** | `/祖先ID/父ID` 的形式，以 `/` 分隔 |
| **主任务** | path 为空字符串 `''` |
| **作用** | 快速查询祖先和后代任务 |
| **索引** | 已添加数据库索引优化查询性能 |
| **最大层级** | 3层（主任务→子任务→孙任务）|

Path 字段是**物化路径 (Materialized Path)** 模式的实现，是处理树形结构数据的高效方式。
