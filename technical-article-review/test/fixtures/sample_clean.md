# 正常文章

这是一篇技术文章，描述了一个具体的实现方案。

核心机制是事件驱动架构，在 Kubernetes 环境下，我们通过 Prometheus 监控验证了效果。

局限是延迟敏感场景下可能出现超时，当出现网络抖动时，建议切换到同步调用。

## 代码示例

```bash
kubectl apply -f deployment.yaml
```

以上命令会创建部署。
