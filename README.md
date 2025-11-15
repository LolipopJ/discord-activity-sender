# Discord Status Sender

前置准备：

```bash
# 安装依赖库
pipenv install
# 进入虚拟环境
pipenv shell
# 对于开发者，注册 commit 钩子
pre-commit install
```

拷贝 `.env.example` 里的内容，新建 `.env`：

- 修改 `DISCORD_TOKEN` 为 Bot 账户的 `authorization` 令牌。
- 修改 `DISCORD_CHANNEL_ID` 为 Bot 账户与主账户的私聊频道编号。

运行应用：

```bash
python main.py
```
