# 📰 每日新闻汇总 - 飞书 API 版部署指南

## 🚀 5 分钟快速部署

### 第 1 步：创建 GitHub 仓库（1 分钟）

1. 打开 [GitHub](https://github.com/)
2. 创建新仓库：`news-bot`
3. 上传文件：
   - `.github/workflows/daily-news.yml`
   - `news_bot.py`

### 第 2 步：获取飞书应用凭证（3 分钟）

1. **打开飞书开放平台**：https://open.feishu.cn/

2. **创建企业应用**：
   - 点击「企业管理」→「应用开发」
   - 点击「创建企业自建应用」
   - 填写应用名称（如：新闻机器人）
   - 点击「创建」

3. **获取凭证**：
   - 在应用页面，点击「凭证与基础信息」
   - 复制 **App ID** 和 **App Secret**

4. **配置权限**：
   - 点击「权限管理」
   - 搜索并添加以下权限：
     - `im:message` - 发送消息
     - `im:chat` - 访问聊天信息
   - 点击「版本发布」→ 发布应用

5. **获取 Chat ID**：
   - **私聊**：你的飞书用户 ID（就是 `ou_xxxxx` 格式）
   - **群聊**：在群里发送任意消息，然后查看 API 日志获取群 ID

### 第 3 步：配置 GitHub Secrets（1 分钟）

在 GitHub 仓库：
1. Settings → Secrets and variables → Actions
2. 添加以下 3 个 secrets：

| Name | Value |
|------|-------|
| `FEISHU_APP_ID` | 从飞书开放平台复制的 App ID |
| `FEISHU_APP_SECRET` | 从飞书开放平台复制的 App Secret |
| `FEISHU_CHAT_ID` | 你的飞书用户 ID 或群聊 ID |

### 第 4 步：测试运行

1. 在 GitHub 仓库点击 **Actions**
2. 选择 **Daily News Summary**
3. 点击 **Run workflow**
4. 等待 30 秒，检查飞书是否收到消息！

---

## ✅ 完成！

现在你的机器人会：
- ⏰ **每天 10:00（北京时间）自动发送新闻**
- 🎯 也可以手动触发测试

---

## 🔧 自定义新闻源

编辑 `news_bot.py` 中的 `get_news()` 函数，接入实际新闻 API：

### 示例：知乎日报
```python
def get_news():
    url = "https://daily.zhihu.com/api/4/news/latest"
    response = requests.get(url)
    data = response.json()
    
    news_items = []
    for story in data['stories'][:5]:  # 取前 5 条
        news_items.append({
            "title": story['title'],
            "content": story.get('hint', '点击查看详细内容'),
            "url": story['url']
        })
    
    return news_items
```

### 其他新闻源
- 新浪新闻：http://api.sina.cn/sinago/feed.json
- 澎湃新闻：https://www.thepaper.cn/api
- 36 氪：https://36kr.com/api

---

## 📝 修改发送时间

编辑 `.github/workflows/daily-news.yml`：

```yaml
schedule:
  # cron 格式：分 时 日 月 周（UTC 时间）
  # 北京时间 10:00 = UTC 02:00
  - cron: '0 2 * * *'
```

其他时间示例：
- 早上 8:00：`0 0 * * *`
- 晚上 8:00：`0 12 * * *`
- 每 6 小时：`0 */6 * * *`

---

## 🆘 常见问题

**Q: 获取 token 失败？**
A: 检查 App ID 和 App Secret 是否正确，应用是否已发布

**Q: 发送消息失败？**
A: 检查权限是否已添加并发布，Chat ID 是否正确

**Q: Chat ID 怎么获取？**
A: 
- 私聊：你的飞书用户 ID（`ou_xxxxx` 格式）
- 群聊：在群里发消息后查看 API 日志，或联系管理员

**Q: 想换新闻源？**
A: 修改 `news_bot.py` 中的 `get_news()` 函数

---

**祝使用愉快！** 🎉
