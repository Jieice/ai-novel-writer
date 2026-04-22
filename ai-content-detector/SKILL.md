---
name: ai-content-detector
description: "AI内容检测技能，辅助使用多个免费平台进行AI率检测并多方对比。触发关键词：AI检测、AI率、检测AI、AI内容检测、查AI、AI生成检测。功能：文本预处理、平台指南、结果汇总、综合报告生成。支持ZeroGPT、Writer、Content at Scale、Sapling等免费检测工具。"
---

# AI内容检测技能

## 概述

本技能辅助用户使用多个免费AI检测平台，对文本内容进行AI生成概率检测，并提供多方对比分析报告。

**注意**：大多数免费AI检测平台没有公开API，需要通过Web界面使用。本技能提供文本预处理、平台指南和结果汇总功能。

## 支持的检测平台

### 免费无需注册的平台

| 平台 | 网址 | 特点 |
|------|------|------|
| **ZeroGPT** | https://www.zerogpt.com/ | 免费无限制，支持中文 |
| **Writer.com** | https://writer.com/ai-content-detector/ | 简洁易用，结果直观 |
| **Content at Scale** | https://contentatscale.ai/ai-content-detector/ | 详细分析，支持长文本 |
| **Sapling** | https://sapling.ai/ai-content-detector | MIT出品，准确度高 |

### 需要注册的平台

| 平台 | 网址 | 特点 |
|------|------|------|
| **GPTZero** | https://gptzero.me/ | 专业检测，学术界认可，免费额度 |
| **朱雀AI** | 腾讯云平台 | 中文优化，国内访问快 |

## 使用流程

### 方式一：直接使用（推荐）

```
用户：检测这段文本的AI率

[粘贴文本内容]

Claude：
1. 预处理文本（清理格式标记）
2. 提供检测平台链接
3. 指导用户在各平台检测
4. 记录并汇总结果
5. 生成综合报告
```

### 方式二：使用脚本辅助

```bash
# 显示平台使用指南
python scripts/detect_ai.py --guide

# 预处理文本文件
python scripts/detect_ai.py --file "文件路径" --preprocess

# 交互式记录检测结果
python scripts/detect_ai.py --record
```

## 检测流程详解

### 步骤1：文本预处理

自动清理以下格式标记：
- Markdown标题（# ## ###）
- 加粗/斜体（** *）
- 链接（[text](url)）
- 代码块（`code`）

### 步骤2：文本分割

对于长文本（>2000字符），自动分割为多个部分：
- 保持段落完整性
- 每部分独立检测
- 综合计算平均AI率

### 步骤3：多平台检测

访问各检测平台，粘贴文本进行检测：

```
推荐检测顺序：
1. ZeroGPT（快速，支持中文）
2. Writer（简洁直观）
3. Sapling（准确度高）
4. Content at Scale（详细分析）
```

### 步骤4：结果汇总

记录各平台检测结果，生成综合报告：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI内容检测报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 平台 | AI概率 | 人类概率 | 备注 |
|------|--------|----------|------|
| ZeroGPT | 45% | 55% | - |
| Writer | 38% | 62% | - |
| Sapling | 52% | 48% | - |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
平均AI率: 45%
综合判定: 中等
建议: 文本存在混合特征，建议进一步优化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 结果解读

### AI概率等级

| 概率范围 | 等级 | 说明 | 建议 |
|----------|------|------|------|
| 0-20% | 极低 | 高度人类写作特征 | 无需处理 |
| 20-40% | 低 | 较多人类写作特征 | 可选优化 |
| 40-60% | 中等 | 混合特征 | 建议优化 |
| 60-80% | 高 | 较多AI特征 | 需要优化 |
| 80-100% | 极高 | 高度AI特征 | 强烈建议降重 |

### 多平台对比分析

当各平台结果差异较大时（>20%），可能原因：
1. 文本类型特殊（如对话、诗歌）
2. 文本经过人工修改
3. 不同平台算法侧重不同

## 脚本使用说明

### detect_ai.py 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--guide` | 显示平台使用指南 | `python detect_ai.py --guide` |
| `--file` | 指定检测文件 | `python detect_ai.py --file chapter.md` |
| `--text` | 直接输入文本 | `python detect_ai.py --text "文本内容"` |
| `--preprocess` | 预处理文本 | `python detect_ai.py --file x.md --preprocess` |
| `--record` | 交互式记录结果 | `python detect_ai.py --record` |
| `--max-length` | 分割最大长度 | `--max-length 1500` |

## 注意事项

1. **文本长度**：建议500-3000字符，过短可能不准确
2. **多平台对比**：使用至少3个平台，取平均值
3. **结果参考**：检测结果仅供参考，不同平台算法有差异
4. **中文优化**：中文文本优先使用ZeroGPT或朱雀AI

## 与小说创作技能联动

本技能可与 `novel-assistant` 技能配合使用：

```
1. novel-assistant 创作章节
2. ai-content-detector 检测AI率
3. novel-assistant 降重优化
4. ai-content-detector 再次检测验证
```

## 快速开始示例

```
用户：检测第二章的AI率

Claude：好的，我来帮你检测第二章的AI率。

首先预处理文本...

文本长度: 3231 字符
已分割为 3 部分

请访问以下平台进行检测：

1. ZeroGPT: https://www.zerogpt.com/
   - 复制第1部分文本
   - 粘贴检测
   - 记录AI率

2. Writer: https://writer.com/ai-content-detector/
   - 同上操作

3. Sapling: https://sapling.ai/ai-content-detector
   - 同上操作

检测完成后，告诉我各平台的结果，我帮你生成综合报告。

用户：ZeroGPT 42%, Writer 38%, Sapling 45%

Claude：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI内容检测报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 平台 | AI概率 | 人类概率 |
|------|--------|----------|
| ZeroGPT | 42% | 58% |
| Writer | 38% | 62% |
| Sapling | 45% | 55% |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
平均AI率: 41.67%
综合判定: 低
建议: 文本具有较多人类写作特征，可选择性优化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 参考文档

- [references/api_docs.md](references/api_docs.md) - 各平台详细信息
- [references/rate_limits.md](references/rate_limits.md) - 使用限制说明
