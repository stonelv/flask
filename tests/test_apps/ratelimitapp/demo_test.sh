#!/bin/bash

# 速率限制装饰器演示脚本
echo "========================================"
echo "Flask 自定义速率限制装饰器演示"
echo "========================================"
echo ""

echo "1. 查看 API 列表:"
curl -s http://127.0.0.1:5000/ | jq .
echo ""

echo "2. 测试 /api/limited 端点（10次/分钟）:"
echo "   前10次请求应该成功..."
for i in {1..10}; do
    response=$(curl -s http://127.0.0.1:5000/api/limited | jq -r '.count')
    echo "   请求 $i: 成功 (当前计数: $response)"
done
echo ""

echo "3. 第11次请求应该被限制:"
echo "   请求 11:"
curl -i http://127.0.0.1:5000/api/limited
echo ""
echo ""

echo "4. 测试 /api/unlimited 端点（无限制）:"
echo "   连续请求 3 次..."
for i in {1..3}; do
    curl -s http://127.0.0.1:5000/api/unlimited | jq .
    echo ""
done

echo "========================================"
echo "演示完成！"
echo "========================================"
echo ""
echo "提示:"
echo "- 受限端点将在 1 分钟后自动重置计数"
echo "- 不同 IP 地址的计数是独立的"
echo "- 可以根据需要调整 max_requests 和 window_seconds 参数"
