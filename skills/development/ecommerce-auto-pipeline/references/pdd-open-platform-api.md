# PDD 开放平台 API 商品发布

> 来源：蜂巢开放文档 + 阿里云开发者社区 + v-tool 电商工具
> 提取日期：2026-05-03

## 核心接口

### pdd.goods.add — 商品新增

**请求**: POST `https://gw-api.pinduoduo.com/api/router`

**关键参数**（价格单位：分）:

| 参数 | 类型 | 说明 |
|------|------|------|
| `goods_name` | String | 商品标题 |
| `cat_id` | Int | 叶子类目ID（从 pdd.goods.cats.get 获取） |
| `carousel_gallery` | String[] | 轮播图URL数组 |
| `detail_gallery` | String[] | 详情图URL数组 |
| `sku_list` | Object[] | SKU列表，含 quantity/price/multi_price/spec |
| `market_price` | Int | 市场参考价（分） |
| `cost_template_id` | String | 运费模板ID |
| `is_onsale` | Int | 0=仓库 1=上架 |
| `is_refundable` | Boolean | 支持7天无理由 |
| `country_id` | String | 国家地区，"1"=中国 |

**返回**: `{goods_id, goods_commit_id}`

### 完整发布流程

```
1. pdd.goods.cats.get(parent_cat_id) → 逐级下钻获取叶子类目ID
2. pdd.goods.image.upload → 上传图片获取URL  
3. pdd.goods.spec.get / pdd.goods.spec.id.get → 获取规格ID
4. pdd.goods.cat.rule.get → 获取类目发布规则（必填属性/标品）
5. pdd.goods.add → 创建商品
   或 pdd.goods.edit.goods.commit → 存草稿
      pdd.goods.submit.goods.commit → 提交草稿
```

### 签名算法

```python
import hashlib
def sign(params, client_secret):
    sorted_items = sorted(params.items())
    raw = client_secret + ''.join(f'{k}{v}' for k,v in sorted_items) + client_secret
    return hashlib.md5(raw.encode('utf-8')).hexdigest().upper()
```

### 认证

- OAuth 2.0: `client_id` + `client_secret` → `access_token`（24h有效期）
- 获取流程：注册开发者 → 创建应用 → 商家授权 → 回调获取code → 换取token

## 注册步骤

1. `https://open.pinduoduo.com` → 注册开发者
2. 创建"商家后台系统"类型应用
3. 申请"商品发布权限"权限包
4. 获取 `client_id` + `client_secret`
5. 商家在 `mms.pinduoduo.com` 授权应用
6. 回调获取 `authorization_code` → 换取 `access_token`

## PDD API 客户端

`~/PDD/pdd_api_client.py` — 完整的Python API客户端，支持：
- 类目查询 (`--action cats`)
- 图片上传 (`--action upload --image path`)
- 商品发布 (`--action publish --listing listing.json --cat-id XXX`)

使用前需设置凭证：
```bash
python3 ~/PDD/pdd_api_client.py --set-client-id xxx
python3 ~/PDD/pdd_api_client.py --set-client-secret xxx
python3 ~/PDD/pdd_api_client.py --set-access-token xxx
```

## 局限

- 需要ISV审核（1-3工作日）
- 部分接口需部署在拼多多云内（额外¥2500/年）
- API创建的商品审核可能比后台创建的更严格
- access_token 24h过期，需定时刷新
