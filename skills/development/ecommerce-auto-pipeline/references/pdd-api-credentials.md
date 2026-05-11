# 拼多多开放平台 API 凭证获取

## 前置条件
- 必须有拼多多商家账号（已开店）
- 商家后台可正常登录

## 获取步骤

### 1. 注册开发者 + 创建应用
1. 打开 https://open.pinduoduo.com
2. 用拼多多商家账号登录
3. 进入「控制台」→ 入驻
4. 选择应用类型：**「商家后台系统」**（自研商家场景）
5. 按指引完成入驻，创建应用

### 2. 获取 client_id 和 client_secret
- 路径：控制台 → 我的应用 → 点击应用名称
- 页面显示 `client_id`（应用ID）和 `client_secret`（应用密钥）
- client_secret 需妥善保管，不泄露

### 3. 获取 access_token（调用接口用）
- 路径：应用详情 → 授权管理
- 配置 pdd 开头店铺账号（店铺账号在商家后台右上角「账号管理」中查看）
- 通过授权接口获取 access_token：参考文档 https://open.pinduoduo.com/application/document/browse?idStr=BD3A776A4D41D5F5

### 4. 接口调用基础
- 鉴权方式：OAuth 2.0，access_token 放在请求参数中
- 签名算法：MD5(所有参数按key排序拼接 + client_secret)
- 网关地址：https://gw-api.pinduoduo.com/api/router

## 需提供给 Agent 的三要素
1. `client_id`
2. `client_secret`
3. `access_token`（或店铺账号用于自动获取）

## 注意事项
- access_token 有有效期，过期需重新授权
- 自研商家可在授权管理页面直接配置店铺账号获取 token
- 不同应用类型（商家后台系统/ERP/跨境）权限不同，选「商家后台系统」覆盖商品/订单/物流/售后
