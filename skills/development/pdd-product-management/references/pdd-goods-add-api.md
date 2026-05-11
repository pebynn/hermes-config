# pdd.goods.add API 参数详解

> 来源: 蜂巢开放平台文档(2025-08-14更新) + v兔电商知识库 + 多源交叉验证
> 完整调研: ~/research-skill-graph/projects/pdd-listing-official-2026-05/

## 请求信息

- **方法**: POST
- **URL**: https://gw-api.pinduoduo.com/api/router
- **测试环境**: https://open-api.pinduoduo.com/sandbox
- **公共参数**: type, client_id, access_token, timestamp, data_type, sign

## 签名算法

```python
import hashlib

def sign_pdd(params, client_secret):
    clean = {k: v for k, v in params.items() if v is not None and k != 'sign'}
    sorted_str = ''.join([f"{k}{v}" for k, v in sorted(clean.items())])
    sign_str = client_secret + sorted_str + client_secret
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
```

## 核心业务参数

```json
{
  "goods_name": "商品标题(≤30汉字=60字符)",
  "cat_id": 1234,
  "goods_type": "1",
  "country_id": "10",
  "is_onsale": 1,
  "is_pre_sale": false,
  "is_refundable": true,
  "is_folt": true,
  "second_hand": false,
  "market_price": 29900,
  "price": 15900,
  "multi_price": 14900,
  "quantity": 500,
  "limit_quantity": 999,
  "weight": 100,
  "goods_desc": "<p>商品详情HTML</p>",
  "image_url": "https://img.pddpic.com/xxx.jpg",
  "carousel_gallery": ["url1", "url2"],
  "detail_gallery": ["url1", "url2"],
  "cost_template_id": "运费模板ID",
  "shipment_limit_second": "86400",
  "two_pieces_discount": 95,
  "sku_properties": [{
    "template_pid": 96688,
    "template_module_id": 22326,
    "ref_pid": 310,
    "pid": 5,
    "value": "",
    "value_unit": ""
  }],
  "sku_list": [{
    "id": 0,
    "is_onsale": 1,
    "price": 15900,
    "multi_price": 14900,
    "quantity": 200,
    "limit_quantity": 0,
    "weight": 0,
    "out_sku_sn": "SKU001",
    "thumb_url": "https://img.pddpic.com/sku1.jpg",
    "spec_id_list": "[765,767]",
    "spec": [
      {"parent_id": 1216, "parent_name": "颜色", "spec_id": 765, "spec_name": "酒红"},
      {"parent_id": 1217, "parent_name": "尺码", "spec_id": 767, "spec_name": "XL"}
    ],
    "sku_srv_templates": ""
  }]
}
```

## 价格单位

所有价格字段单位为**分**：
- 100 = ¥1.00
- 15900 = ¥159.00
- 29900 = ¥299.00

## 关键规则

### SKU规则
- 父规格类型 ≤ 4种（中老年女装用2种：颜色+尺码）
- 子规格值总数 ≤ 44个
- spec_id_list必须按笛卡尔积展开
- 单买价 ≥ 拼单价 + 100分（1元）
- SKU间价差 ≤ 20%（否则搜索屏蔽7天+扣保证金1000元）

### 图片规则
- 轮播图≤10张, ≥480px, ≤1M, 宽高相等
- 详情图: 宽高比>1:3, 宽≥480px, ≤1M
- SKU缩略图: 1:1, ≥480px, ≤1M
- 视频(部分类目): ≤60s, 16:9/1:1/3:4, ≤300M

### 库存规则
- 单SKU库存 ≤ 2亿
- 至少一个SKU为上架状态
- 图片空间总容量限5G

## 成功响应

```json
{
  "code": 0,
  "data": {
    "goods_commit_id": 164489173095,
    "goods_id": 794029426838,
    "matched_spu_id": null,
    "request_id": "17549067735883097"
  },
  "message": "ok"
}
```

## 草稿模式（替代方案）

如果 pdd.goods.add 不可用或需要先预览：
```
pdd.goods.edit.goods.commit → 保存草稿
pdd.goods.submit.goods.commit → 提交草稿上架
pdd.goods.commit.detail.get → 查看草稿详情
pdd.goods.commit.status.get → 查询审核状态
```

## 类目ID获取流程

```
pdd.goods.authorization.cats → 商家可发布类目列表
pdd.goods.cats.get(parent_cat_id=0) → 一级类目
pdd.goods.cats.get(parent_cat_id=一级ID) → 二级类目
pdd.goods.cats.get(parent_cat_id=二级ID) → 三级(叶子)类目
pdd.goods.cat.rule.get(cat_id=叶子ID) → 确认发布规则
```

## OAuth 2.0 流程

```
1. 注册开发者 → 创建应用 → client_id + client_secret
2. 引导商家访问授权URL
3. 回调返回 authorization_code (10分钟有效)
4. pdd.pop.auth.token.create → access_token (24h) + refresh_token
5. access_token过期 → refresh_token刷新
```
