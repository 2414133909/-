# 问卷星快填

> 自动识别并随机填写 [问卷星](https://www.wjx.cn/) 问卷，支持批量提交。

---

## 功能特性

| 题型 | 说明 |
|------|------|
| 单选题 | 随机选择一个选项 |
| 多选题 | 随机勾选 1~N 个选项 |
| 填空 / 简答 | 填入随机中文短语 |
| 量表 / 评分 | 随机点击刻度 |
| 矩阵单选 | 每行随机选一列 |
| 矩阵多选 | 每行随机勾选若干列 |
| 下拉题 | 随机选择一个有效选项 |

- 基于 **Playwright + Chromium**，支持无头或可见浏览器模式
- 可配置**填写次数**及每次提交后的**等待间隔**
- 模拟随机停顿，降低被风控识别的概率

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 运行

```bash
# 填写一次
python main.py https://www.wjx.cn/vm/xxxxxxx.aspx

# 填写 5 次，每次间隔 3 秒
python main.py https://www.wjx.cn/vm/xxxxxxx.aspx --count 5 --interval 3

# 显示浏览器窗口（便于调试）
python main.py https://www.wjx.cn/vm/xxxxxxx.aspx --show
```

### 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | — | 必填 | 问卷星问卷链接 |
| `--count` | `-n` | `1` | 填写次数 |
| `--interval` | `-i` | `2.0` | 每次提交后等待秒数 |
| `--show` | — | 关闭 | 显示浏览器窗口 |

---

## 在代码中使用

```python
from wjx_filler import fill_once, fill_batch

# 填写一次，返回是否成功
ok = fill_once("https://www.wjx.cn/vm/xxxxxxx.aspx")

# 批量填写，返回成功次数
count = fill_batch("https://www.wjx.cn/vm/xxxxxxx.aspx", count=10, interval=3)
print(f"成功提交 {count} 次")
```

---

## 运行测试

```bash
python -m unittest discover -s tests -v
```

---

## 注意事项

- 本工具仅供学习研究，请勿用于任何违反问卷星服务条款或法律法规的用途。
- 过于频繁的提交可能导致 IP 被封禁，请合理控制 `--count` 与 `--interval`。
