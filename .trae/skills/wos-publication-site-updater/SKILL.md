---
name: "wos-publication-site-updater"
description: "Maintain and update WoS publication static site. Invoke when adding new Excel data, regenerating data.js, fixing accordion display, or preparing GitHub Pages deployment."
---

# WoS Publication Site Updater

用于维护本项目的学术论文静态网站，统一处理数据更新、页面校验和部署准备。

## 何时调用

- 用户要求更新新的 WoS 导出数据
- 用户要求修复期刊 / 年份 / 论文三级展示逻辑
- 用户要求检查论文显示不完整、折叠异常、滚动体验问题
- 用户要求准备或校验 GitHub Pages 发布内容

## 输入假设

- 工作目录中存在多个按期刊命名的 `*.xls` 文件
- 目标网页文件为 `index.html`
- 数据文件为 `data.js`，格式为 `const DATA = [...]`
- 核心字段包括：
  - `Source Title`
  - `Publication Year`
  - `Article Title`
  - `Author Full Names`
  - `Abstract`

## 标准执行步骤

1. 审核项目文件结构与现有数据格式
2. 统一字段映射并生成最新 `data.js`
3. 校验年份过滤范围（2015–2025）
4. 校验三级交互逻辑（期刊 → 年份 → 论文）
5. 校验每年文章是否完整展示，避免容器高度截断
6. 校验页面在桌面与移动端的可读性
7. 输出变更摘要与部署说明

## 质量检查清单

- 期刊列表可正常展开到年份
- 年份列表可正常展开到文章
- 单个年份下文章数量与数据一致
- 文章标题、作者、摘要渲染完整
- 页面无明显卡顿、样式重叠或内容裁切
- `index.html` 与 `data.js` 可直接静态打开

## GitHub Pages 准备要求

- 确认存在主页入口文件 `index.html`
- 确认存在 `.nojekyll` 或等效配置（如需要）
- 推送前检查仓库中不包含无关临时文件
- 提供发布后访问路径与回归测试建议

## 输出要求

- 给出本次修改的文件清单
- 给出关键验证结果
- 给出后续可复用的更新步骤
