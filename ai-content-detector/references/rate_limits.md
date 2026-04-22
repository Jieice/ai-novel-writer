# API调用限制说明

## 概述

各AI检测平台均有不同的调用限制，本文档详细说明各平台的限制情况及应对策略。

---

## 各平台限制详情

### ZeroGPT

| 限制项 | 说明 |
|--------|------|
| 每日请求次数 | 无明确限制 |
| 单次文本长度 | 建议5000字符以内 |
| 并发请求 | 不建议并发 |
| IP限制 | 同一IP高频请求可能被限制 |

**建议策略**:
- 调用间隔：1-2秒
- 批量检测时使用队列
- 避免短时间内大量请求

---

### Writer.com

| 限制项 | 说明 |
|--------|------|
| 每日请求次数 | 约50-100次（未注册） |
| 单次文本长度 | 1500字符 |
| 注册用户 | 更高额度 |

**建议策略**:
- 优先用于关键内容检测
- 注册账户获取更高额度
- 调用间隔：2秒以上

---

### Sapling

| 限制项 | 说明 |
|--------|------|
| 免费额度 | 每月2000次 |
| 单次文本长度 | 无明确限制 |
| 注册用户 | 更高额度 |

**建议策略**:
- 注册免费账户
- 合理分配月度额度
- 调用间隔：1秒

---

### Content at Scale

| 限制项 | 说明 |
|--------|------|
| 每日请求次数 | 约25次（免费） |
| 单次文本长度 | 支持长文本 |
| 付费用户 | 无限制 |

**建议策略**:
- 用于重要内容检测
- 调用间隔：2秒以上
- 考虑付费升级

---

### GPTZero

| 限制项 | 免费版 | 付费版 |
|--------|--------|--------|
| 每月请求次数 | 100次 | 无限制 |
| 单次文本长度 | 5000字符 | 50000字符 |
| 批量检测 | 不支持 | 支持 |

**建议策略**:
- 合理规划月度额度
- 优先用于学术论文检测
- 考虑付费升级

---

### Originality.ai

| 限制项 | 说明 |
|--------|------|
| 新用户试用 | $1试用额度 |
| 付费模式 | 按字数计费 |
| 单次文本长度 | 无限制 |

**建议策略**:
- 新用户可免费试用
- 适合专业用户
- 按需付费

---

## 调用频率管理

### 推荐配置

```python
# 各平台推荐调用间隔（秒）
RECOMMENDED_DELAYS = {
    'zerogpt': 1.0,
    'writer': 2.0,
    'sapling': 1.0,
    'contentscale': 2.0,
    'gptzero': 1.0,
    'originality': 1.0
}

# 每日推荐调用次数
DAILY_LIMITS = {
    'zerogpt': 100,
    'writer': 50,
    'sapling': 100,
    'contentscale': 25,
    'gptzero': 100,  # 月度限制
    'originality': 10
}
```

### 队列管理示例

```python
import time
from collections import deque

class APIRateLimiter:
    def __init__(self, calls_per_minute=30):
        self.calls_per_minute = calls_per_minute
        self.calls = deque()
    
    def wait_if_needed(self):
        now = time.time()
        while self.calls and self.calls[0] < now - 60:
            self.calls.popleft()
        
        if len(self.calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.calls[0])
            time.sleep(sleep_time)
        
        self.calls.append(now)
```

---

## 错误代码处理

### HTTP状态码

| 状态码 | 含义 | 处理方式 |
|--------|------|----------|
| 200 | 成功 | 正常处理 |
| 400 | 请求错误 | 检查请求格式 |
| 401 | 未授权 | 检查API Key |
| 403 | 禁止访问 | 检查权限 |
| 429 | 请求过多 | 等待后重试 |
| 500 | 服务器错误 | 稍后重试 |
| 503 | 服务不可用 | 稍后重试 |

### 重试策略

```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

---

## 最佳实践建议

### 1. 批量检测策略

```
1. 将待检测文本分组（每组5-10个）
2. 使用队列逐个检测
3. 记录已使用额度
4. 遇到限制时暂停，稍后继续
```

### 2. 额度管理

```
1. 每日记录各平台使用次数
2. 设置使用阈值警告
3. 优先使用免费额度高的平台
4. 重要内容使用付费平台
```

### 3. 错误处理

```
1. 捕获所有异常
2. 记录错误日志
3. 实现自动重试
4. 提供降级方案
```

---

## 常见问题

### Q: 为什么不同平台结果差异大？

A: 各平台使用不同的检测算法和训练数据，侧重点不同。建议：
- 使用多个平台对比
- 关注趋势而非绝对值
- 结合人工判断

### Q: 如何提高检测准确度？

A: 建议：
- 确保文本长度足够（>500字符）
- 使用多个平台对比
- 选择适合文本类型的平台
- 考虑文本语言选择对应优化的平台

### Q: 遇到429错误怎么办？

A: 
- 立即停止请求
- 等待至少60秒
- 增加调用间隔
- 考虑更换平台

---

## 更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-04-19 | 初始版本 |
