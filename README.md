# Discord Activity Sender

## 免责声明

Discord 官方文档中明确表示**不支持 Self-Bot 的使用**，违反使用条款可能导致账号被封禁。使用本项目意味着您知晓并承担账号封禁的风险。

## 如何使用

### 准备运行环境

```bash
# 安装依赖库
pipenv install
# 进入虚拟环境
pipenv shell
```

### 添加环境变量

复制 `.env.example` 粘贴为 `.env`，修改环境变量；或使用 Docker 部署时，复制 `docker-compose.example.yml` 粘贴为 `docker-compose.yml`，修改配置项 `environment`：

- `DISCORD_TOKEN`：子账户的 `authorization` 令牌。您可以在 HTTP 请求头中找到它。**请千万不要设置为自己主账号的令牌**。
- `DISCORD_CHANNEL_ID`：子账户与主账户的私聊频道编号。您可以在相关的 HTTP 请求地址中找到它，例如：`https://discord.com/api/v9/channels/{DISCORD_CHANNEL_ID}/messages`。

可选环境变量：

- `DISCORD_ACTIVITY_CACHE_DURATION`：活动状态信息缓存时间，单位“秒”。默认值为 `30` 秒。
- `PORT`：服务运行的端口号。默认为 `28800` 端口。

### 运行应用

启动服务：

```bash
python main.py
```

可用接口如下：

- `localhost:28800/`：检查服务是否正在运行中。
- `localhost:28800/me`：检查子账号的登录状态。
- `localhost:28800/activity`：获取主账号的活动状态信息。

## 贡献代码

在提交前自动格式化代码：

```bash
# 安装完整的依赖库
pipenv install --dev
# 进入虚拟环境
pipenv shell
# 注册 commit 钩子
pre-commit install
# 监听代码更改并自动重启服务
python main.py
```
