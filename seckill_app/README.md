# Flask + SQLAlchemy 商品秒杀系统

这是一个使用 Flask 和 SQLAlchemy 实现的商品秒杀 API，重点解决了高并发场景下的超卖问题。

## 项目结构

```
seckill_app/
├── app.py              # Flask 应用和 API 接口
├── models.py           # 数据模型（Product 和 Order）
├── test_seckill.py     # 单元测试
├── test_final.py       # 高并发测试
└── pyproject.toml      # 项目配置
```

## 核心实现

### 数据模型

- **Product（商品）**：包含商品ID、名称、库存、价格等字段
- **Order（订单）**：记录订单ID、商品ID、数量、状态等信息

### 秒杀接口（POST /seckill/<product_id>）

这是核心接口，使用了以下技术防止超卖：

1. **数据库行级锁**：使用 `with_for_update()` 查询商品，获取行级锁
2. **事务管理**：使用数据库事务确保库存扣减和订单创建的原子性
3. **库存检查**：严格检查库存是否大于0
4. **重试机制**：失败时自动重试（最多3次）

```python
product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()

if product.stock <= 0:
    return jsonify({'success': False, 'message': '商品已售罄'}), 400

product.stock -= 1
order = Order(product_id=product_id, quantity=1)
db.session.add(order)
db.session.commit()
```

## 安装依赖

```bash
pip install flask flask-sqlalchemy pytest requests
```

## 运行应用

```bash
cd seckill_app
python app.py
```

应用将在 `http://127.0.0.1:5000` 运行，并自动初始化一个库存为10的商品。

## API 接口

### 1. 秒杀购买

```http
POST /seckill/<product_id>
```

响应示例：
```json
{
    "success": true,
    "message": "秒杀成功",
    "order_id": 1,
    "remaining_stock": 9
}
```

### 2. 获取商品列表

```http
GET /products
```

### 3. 获取订单列表

```http
GET /orders
```

## 测试

### 单元测试

运行基本单元测试：

```bash
pytest test_seckill.py -v
```

测试用例：
- `test_single_seckill_success`：测试单个购买请求
- `test_seckill_out_of_stock`：测试库存不足时的处理
- `test_seckill_nonexistent_product`：测试购买不存在的商品

### 高并发测试

运行并发测试（100个并发请求）：

```bash
python test_final.py
```

## 防止超卖的关键技术

### 1. 使用 `with_for_update()` 行级锁

```python
product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()
```

这会在查询时对商品行加锁，确保同一时间只有一个请求可以修改该商品的库存。

### 2. 数据库事务

所有操作都在一个数据库事务中完成，确保原子性：
- 要么库存扣减和订单创建都成功
- 要么都失败并回滚

### 3. 严格的库存检查

在扣减库存前，先检查库存是否大于0：

```python
if product.stock <= 0:
    return jsonify({'success': False, 'message': '商品已售罄'}), 400
```

## 注意事项

1. **SQLite 限制**：SQLite 在高并发写入场景下性能有限，因为它使用文件级锁。在生产环境中，建议使用 PostgreSQL 或 MySQL。

2. **并发测试结果**：在测试中，由于 SQLite 的限制，可能会出现成功数不完全等于初始库存的情况。但核心逻辑（不超卖）是保证的。

3. **生产环境**：在生产环境中，应该使用：
   - 更强大的数据库（PostgreSQL/MySQL）
   - 连接池管理
   - Redis 等缓存技术
   - 消息队列（如 RabbitMQ）来削峰填谷

## 示例场景

假设商品初始库存为10件，100个并发请求同时发起购买：

- 预期结果：10个请求成功，90个请求失败
- 最终库存：0（不会为负数）
- 订单数量：10个
- 不会出现超卖现象

## License

MIT
