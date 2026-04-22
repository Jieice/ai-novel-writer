# AI检测平台API参考文档

## 概述

本文档汇总了各AI检测平台的API调用方式和限制说明。

---

## 1. ZeroGPT

### 基本信息
- **官网**: https://www.zerogpt.com/
- **免费额度**: 无限制
- **支持语言**: 多语言（包括中文）
- **检测速度**: 快

### API调用

**端点**: `https://api.zerogpt.com/api/detect/detectText`

**请求方法**: POST

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
    "text": "要检测的文本内容",
    "language": "zh"
}
```

**响应示例**:
```json
{
    "data": {
        "isAI": 0.45,
        "text": "检测的文本...",
        "language": "zh"
    }
}
```

### 注意事项
- 无需API Key
- 建议调用间隔：1秒以上
- 文本长度建议：100-5000字符

---

## 2. Writer.com AI Detector

### 基本信息
- **官网**: https://writer.com/ai-content-detector/
- **免费额度**: 每日有限制
- **支持语言**: 英文为主
- **检测速度**: 快

### API调用

**端点**: `https://api.writer.com/v1/detect/ai`

**请求方法**: POST

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
    "text": "要检测的文本内容"
}
```

**响应示例**:
```json
{
    "score": 0.38,
    "status": "success"
}
```

### 注意事项
- 无需API Key
- 每日检测次数有限
- 对英文文本效果更好

---

## 3. Sapling AI Detector

### 基本信息
- **官网**: https://sapling.ai/ai-content-detector
- **开发者**: MIT
- **免费额度**: 有免费额度
- **准确度**: 高

### API调用

**端点**: `https://api.sapling.ai/api/v1/aidetect`

**请求方法**: POST

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
    "text": "要检测的文本内容"
}
```

**响应示例**:
```json
{
    "ai_score": 0.52,
    "status": "success"
}
```

### 注意事项
- MIT出品，学术背景可靠
- 支持长文本检测
- 建议注册获取更好的服务

---

## 4. Content at Scale

### 基本信息
- **官网**: https://contentatscale.ai/ai-content-detector/
- **免费额度**: 每日有限制
- **特点**: 详细分析

### API调用

**端点**: `https://api.contentatscale.ai/api/v1/detect`

**请求方法**: POST

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
    "text": "要检测的文本内容"
}
```

**响应示例**:
```json
{
    "score": 0.41,
    "analysis": {
        "sentence_count": 15,
        "word_count": 200
    }
}
```

### 注意事项
- 提供详细的句子级分析
- 支持长文本
- 建议调用间隔：2秒以上

---

## 5. GPTZero

### 基本信息
- **官网**: https://gptzero.me/
- **免费额度**: 每月有限免费额度
- **专业度**: 高
- **特点**: 学术界认可

### API调用

**端点**: `https://api.gptzero.me/v2/predict/text`

**请求方法**: POST

**请求头**:
```
Content-Type: application/json
x-api-key: YOUR_API_KEY
```

**请求体**:
```json
{
    "document": "要检测的文本内容"
}
```

**响应示例**:
```json
{
    "documents": [
        {
            "completely_generated_prob": 0.65,
            "average_generated_prob": 0.58,
            "sentences": [...]
        }
    ]
}
```

### 注意事项
- **需要API Key**
- 免费额度：每月有限次数
- 提供句子级别的详细分析
- 学术论文常用

### 获取API Key
1. 访问 https://gptzero.me/
2. 注册账户
3. 在 Dashboard 获取 API Key

---

## 6. Originality.ai

### 基本信息
- **官网**: https://originality.ai/
- **免费额度**: 新用户免费试用
- **准确度**: 高
- **特点**: 专业级检测

### API调用

**端点**: `https://api.originality.ai/api/v1/scan/ai`

**请求方法**: POST

**请求头**:
```
Content-Type: application/json
X-API-KEY: YOUR_API_KEY
```

**请求体**:
```json
{
    "content": "要检测的文本内容"
}
```

### 注意事项
- **需要API Key**
- 新用户有免费试用额度
- 专业级检测，准确度高
- 付费后无限制使用

---

## 7. 朱雀AI（国内）

### 基本信息
- **官网**: 腾讯云平台
- **开发者**: 腾讯
- **特点**: 中文优化
- **免费额度**: 有

### 使用方式
- 通过腾讯云控制台使用
- 需要腾讯云账户
- 对中文内容检测效果好

### 注意事项
- 国内访问速度快
- 中文检测优化
- 需要腾讯云账户

---

## 调用限制汇总

| 平台 | 免费额度 | 需要Key | 调用间隔建议 |
|------|----------|---------|--------------|
| ZeroGPT | 无限制 | 否 | 1秒 |
| Writer | 每日限制 | 否 | 2秒 |
| Sapling | 有额度 | 否 | 1秒 |
| ContentScale | 每日限制 | 否 | 2秒 |
| GPTZero | 每月限制 | 是 | 1秒 |
| Originality | 新用户试用 | 是 | 1秒 |
| 朱雀AI | 有额度 | 是 | 1秒 |

---

## 最佳实践

### 1. 多平台对比
建议使用至少3个平台进行检测，取平均值作为参考。

### 2. 文本长度
- 最短：100字符
- 推荐：500-3000字符
- 最长：部分平台支持10000+字符

### 3. 调用频率
- 避免短时间内大量请求
- 建议间隔1-2秒
- 使用队列管理批量检测

### 4. 结果解读
- 不同平台算法不同，结果会有差异
- 关注趋势而非绝对数值
- 结合人工判断综合评估

---

## 错误处理

### 常见错误

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 429 | 请求过于频繁 | 增加调用间隔 |
| 401 | API Key无效 | 检查Key是否正确 |
| 400 | 请求格式错误 | 检查请求体格式 |
| 500 | 服务器错误 | 稍后重试 |

### 重试策略
```python
import time

def detect_with_retry(detector, text, max_retries=3):
    for i in range(max_retries):
        try:
            result = detector.detect(text)
            if result.get('status') == 'success':
                return result
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(2 ** i)  # 指数退避
            else:
                return {'error': str(e)}
    return {'error': 'Max retries exceeded'}
```
