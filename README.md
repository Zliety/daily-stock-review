# 每日A股复盘AI智能体
基于GitHub Actions + 中国电信息壤Token + Server酱实现的全自动股市复盘工具。

## ✨ 核心功能
- 🕒 每天15:05自动运行，无需打开电脑
- 📊 自动采集大盘、板块、北向资金、新闻数据
- 🤖 AI智能分析市场走势和板块热点
- 📱 生成专业复盘报告并推送到微信
- 🔄 多模型自动切换，保证稳定性

## 💰 运行成本
- 大模型：约5-10元/月（中国电信息壤Token，10元=250万Token）
- 其他：0元（GitHub Actions和Server酱免费版足够使用）

## 🚀 部署步骤
1. 注册GitHub、天翼云、Server酱账号
2. 在GitHub仓库Settings→Secrets中添加：
   - `TIANYI_API_KEY`：天翼云息壤Token API Key
   - `SERVER_CHAN_KEY`：Server酱SendKey
3. 手动触发一次工作流测试运行
4. 等待每天15:05自动接收复盘报告

## ⚠️ 免责声明
本工具仅用于学习和交流，所有分析内容均由AI自动生成，不构成任何投资建议。股市有风险，投资需谨慎。