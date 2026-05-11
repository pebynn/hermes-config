---
name: database-schema-designer
description: 从需求设计关系型数据库Schema — 自动生成迁移(Drizzle/Prisma/TypeORM/Alembic)、TypeScript/Python类型、种子数据、RLS策略、索引策略、ERD图
version: "1.0.0"
author: "seaworld008"
source: "Commonly-used-high-value-skills"
tags: ["database", "schema", "design", "migration", "prisma"]
created_at: "2026-03-18"
updated_at: "2026-03-20"
---
# Database Schema Designer

从需求设计关系型数据库 Schema，自动生成迁移代码、类型定义、种子数据和 RLS 策略。

## 核心能力

- **Schema 设计** — 需求→表/关系/约束
- **迁移生成** — Drizzle / Prisma / TypeORM / Alembic
- **类型生成** — TypeScript interfaces / Python dataclasses/Pydantic
- **RLS 策略** — 多租户行级安全
- **索引策略** — 复合/部分/覆盖索引
- **种子数据** — Faker 生成真实测试数据
- **ERD 图** — Mermaid 格式

## 设计流程

### 1. 需求→实体提取
例："用户可以创建项目，项目有任务，任务可打标签，任务可分配给用户，需要审计日志"
→ User, Project, Task, Label, TaskLabel(junction), TaskAssignment, AuditLog

### 2. 识别关系
User 1──* Project, Project 1──* Task, Task *──* Label (via TaskLabel)

### 3. 添加横切关注点
- **多租户**：tenant-scoped 表加 `organization_id`
- **软删除**：加 `deleted_at TIMESTAMPTZ`
- **审计追踪**：`created_by`, `updated_by`, `created_at`, `updated_at`
- **版本控制**：`version INTEGER` 乐观锁

## 输出示例

### Prisma
```prisma
model Task {
  id          String   @id @default(cuid())
  projectId   String   @map("project_id")
  title       String
  status      TaskStatus @default(TODO)
  deletedAt   DateTime? @map("deleted_at")
  project     Project  @relation(fields: [projectId], references: [id])
  @@index([projectId, status])
  @@map("tasks")
}
```

### Drizzle (TypeScript)
```typescript
export const tasks = pgTable('tasks', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  projectId: text('project_id').notNull(),
  title: varchar('title', { length: 500 }).notNull(),
  deletedAt: timestamp('deleted_at'),
})
```

## 触发场景

- 新功能需要数据库表
- 审查 Schema 性能/规范化问题
- 为现有 Schema 添加多租户
- 规划破坏性 Schema 迁移

## 边界

- 不部署迁移到生产环境
- 不进行实际数据迁移
- 不处理 NoSQL 数据库设计