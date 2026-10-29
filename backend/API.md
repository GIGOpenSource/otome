# Uivsbe API 文档

> 在线 Swagger 文档：http://127.0.0.1:8088/api/docs/  
> OpenAPI Schema：http://127.0.0.1:8088/api/schema/  
> ReDoc：http://127.0.0.1:8088/api/redoc/

## 基础说明

### 基础路径

```
http://127.0.0.1:8088/api/
```

### 统一响应格式

所有接口 HTTP 状态码均为 `200`，业务状态通过 `code` 字段区分：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| code | 含义 |
|------|------|
| 200  | 成功 |
| 201  | 创建成功 |
| 400  | 请求参数错误或业务校验失败 |
| 404  | 资源不存在 |
| 500  | 服务器错误 |

### 分页

列表接口支持分页，查询参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `currentPage` | 页码 | 1 |
| `pageSize` | 每页条数 | 20（最大 999） |

分页响应 `data` 结构：

```json
{
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  },
  "results": []
}
```

### 认证

需要登录的接口在请求头携带 Token：

```
Authorization: Token <your_token>
```

---

## 用户模块 `/api/users/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/users/send-verify-code/` | 发送邮箱验证码 | 否 |
| POST | `/users/register/` | 用户注册 | 否 |
| POST | `/users/login/` | 用户登录 | 否 |
| POST | `/users/logout/` | 用户登出 | 是 |
| GET  | `/users/` | 用户列表 | 是 |
| GET  | `/users/{id}/` | 用户详情 | 是 |
| POST | `/users/{id}/toggle-status/` | 切换用户状态 | 是 |

### 登录请求示例

```json
POST /api/users/login/
{
  "username": "admin",
  "password": "your_password"
}
```

---

## 管理员模块 `/api/admin/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/admin/send-verify-code/` | 发送邮箱验证码 | 否 |
| POST | `/admin/register/` | 管理员注册 | 否 |
| POST | `/admin/login/` | 管理员登录 | 否 |
| POST | `/admin/reset-password/` | 重置密码 | 否 |
| POST | `/admin/logout/` | 管理员登出 | 是 |
| GET  | `/admin/info/` | 当前管理员信息 | 是 |
| GET  | `/admin/` | 管理员列表 | 是 |

### 管理员用户管理 `/api/admin/users/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/admin/users/` | 用户列表 |
| GET    | `/admin/users/{id}/` | 用户详情 |
| PUT    | `/admin/users/{id}/` | 更新用户 |
| DELETE | `/admin/users/{id}/` | 删除用户 |
| POST   | `/admin/users/{id}/toggle-status/` | 切换状态 |

---

## 商品分类 `/api/product/categories/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/product/categories/` | 分类列表 |
| GET    | `/product/categories/{id}/` | 分类详情 |
| POST   | `/product/categories/` | 创建分类 |
| PUT    | `/product/categories/{id}/` | 更新分类 |
| PATCH  | `/product/categories/{id}/` | 部分更新 |
| DELETE | `/product/categories/{id}/` | 删除分类 |

### 列表查询参数

| 参数 | 说明 |
|------|------|
| `name` | 分类名称（模糊搜索） |
| `status` | 状态：`1` 启用，`0` 禁用 |
| `parent` | 父分类 ID；不传则返回**顶级分类**；`parent=all` 返回**全部分类**（不分页） |

### 分类字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 分类 ID |
| `name` | string | 分类名称 |
| `parent` | int \| null | 上级分类 ID，null 为一级分类 |
| `sort_order` | int | 排序权重 |
| `status` | int | 1 启用 / 0 禁用 |
| `children_count` | int | 子分类数量（只读） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 创建示例

```json
POST /api/product/categories/
{
  "name": "瓷砖",
  "parent": null,
  "sort_order": 0,
  "status": 1
}
```

> 删除限制：存在子分类或关联商品时无法删除。

---

## 商家管理 `/api/product/merchants/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/product/merchants/` | 商家列表 |
| GET    | `/product/merchants/{id}/` | 商家详情 |
| POST   | `/product/merchants/` | 创建商家 |
| PUT    | `/product/merchants/{id}/` | 更新商家 |
| PATCH  | `/product/merchants/{id}/` | 部分更新 |
| DELETE | `/product/merchants/{id}/` | 删除商家 |
| POST   | `/product/merchants/{id}/create-account/` | 为商家创建登录账号 |

### 列表查询参数

`name`、`region`、`level`（1-5）、`status`、`main_category`

---

## 商品管理 `/api/product/products/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/product/products/` | 商品列表 |
| GET    | `/product/products/{id}/` | 商品详情 |
| POST   | `/product/products/` | 创建商品 |
| PUT    | `/product/products/{id}/` | 更新商品 |
| PATCH  | `/product/products/{id}/` | 部分更新 |
| DELETE | `/product/products/{id}/` | 删除商品 |

### 列表查询参数

`name`、`category`、`merchant`、`status`、`material`、`min_price`、`max_price`、`ordering`

---

## 标签管理 `/api/tags/tags/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/tags/tags/` | 标签列表 |
| GET    | `/tags/tags/{id}/` | 标签详情 |
| POST   | `/tags/tags/` | 创建标签 |
| PUT    | `/tags/tags/{id}/` | 更新标签 |
| PATCH  | `/tags/tags/{id}/` | 部分更新 |
| DELETE | `/tags/tags/{id}/` | 删除标签 |

### 列表查询参数

| 参数 | 说明 |
|------|------|
| `name` | 标签名称（模糊搜索） |
| `category` | 所属分类 ID |

### 标签字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 标签 ID |
| `name` | string | 标签名称（全局唯一） |
| `category` | int \| null | 关联分类 ID |
| `category_name` | string | 分类名称（只读） |
| `created_at` | datetime | 创建时间 |

---

## 商圈组管理 `/api/merchant-manage/district-groups/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/merchant-manage/district-groups/` | 商圈组列表 |
| GET    | `/merchant-manage/district-groups/{id}/` | 详情 |
| POST   | `/merchant-manage/district-groups/` | 创建 |
| PUT    | `/merchant-manage/district-groups/{id}/` | 更新 |
| PATCH  | `/merchant-manage/district-groups/{id}/` | 部分更新 |
| DELETE | `/merchant-manage/district-groups/{id}/` | 删除 |
| POST   | `/merchant-manage/district-groups/{id}/add-merchant/` | 添加商家 |
| POST   | `/merchant-manage/district-groups/{id}/remove-merchant/` | 移除商家 |

---

## 商家入驻申请 `/api/merchant-manage/merchant-applications/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/merchant-manage/merchant-applications/` | 申请列表 |
| GET  | `/merchant-manage/merchant-applications/{id}/` | 申请详情 |
| POST | `/merchant-manage/merchant-applications/{id}/approve/` | 审批通过 |
| POST | `/merchant-manage/merchant-applications/{id}/reject/` | 审批拒绝 |

---

## 推广码管理 `/api/promotion/promotion-codes/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/promotion/promotion-codes/` | 推广码列表 |
| POST | `/promotion/promotion-codes/` | 创建推广码 |
| PUT  | `/promotion/promotion-codes/{id}/` | 更新 |
| DELETE | `/promotion/promotion-codes/{id}/` | 删除 |
| POST | `/promotion/promotion-codes/{id}/toggle-status/` | 切换状态 |

---

## 咨询管理 `/api/inquiry/inquiries/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/inquiry/inquiries/` | 咨询列表 |
| GET  | `/inquiry/inquiries/{id}/` | 咨询详情 |
| POST | `/inquiry/inquiries/{id}/mark-processed/` | 标记已处理 |
| POST | `/inquiry/inquiries/{id}/close/` | 关闭咨询 |

---

## 消息聊天 `/api/chat/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/chat/conversations/` | 会话列表 |
| POST | `/chat/conversations/start/` | 发起会话 |
| POST | `/chat/conversations/{id}/read/` | 标记已读 |
| GET  | `/chat/messages/` | 消息列表 |
| POST | `/chat/messages/` | 发送消息 |

---

## 系统管理 `/api/system/`

### 品牌 `/api/system/brands/`

标准 CRUD。

### 系统配置 `/api/system/system-configs/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/system/system-configs/` | 配置列表 |
| PUT  | `/system/system-configs/{id}/` | 更新配置 |
| POST | `/system/system-configs/batch-update/` | 批量更新 |

### 采购需求 `/api/system/procurement-requirements/`

标准 CRUD + `update-status` 操作。

---

## 前端对接说明

### 管理端（admin）

- 代理配置：`/api` → `http://127.0.0.1:8088`
- API 封装：`admin/src/services/adminApi.ts`
- Token 存储：`localStorage.admin_token`

### 分类接口使用建议

| 场景 | 调用方式 |
|------|----------|
| 分类树（顶级列表） | `GET /product/categories/` |
| 展开子分类 | `GET /product/categories/?parent={id}` |
| 下拉选择（全部） | `GET /product/categories/?parent=all` |

### 列表数据提取

后端分页列表返回 `{ pagination, results }`，前端需从 `response.data.data.results` 取数组；`parent=all` 时 `data` 直接为数组。

---

*文档生成时间：2026-06-09 | 对应 Swagger UI：/api/docs/*
