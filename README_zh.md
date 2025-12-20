# Fanbox 关注用户更新监听（Python 版本）

## 功能概述

- **创作背景**
  - 你是否也有和我一样，fanbox作者偷偷在最后几天更新而没看到赞助内容！亦或者因为繁忙的工作或者学业忘记查看？
  - 该工具通过python3编写，依赖**requests（爬虫）**和**onepush（通知推送）**，你可以轻松追踪fanbox赞助者（关注者的更新内容也可以！只需在配置文件里配置）。
- **工具优点**
  - 多语言支持
  - 低配置，开箱即用
  - 除了赞助者，可额外选择监控关注者，并配置最小监听金额
  - 支持设置代理端口，符合国情
- **监听对象**: 
  - 你在 Fanbox 上「正在赞助」的创作者（默认启用）
  - 你「关注」的创作者（可选，通过配置开启）
- **实现方式**: 
  - 调用 `post.listSupporting` 接口检测赞助的创作者
  - 如果开启关注者检测，调用 `creator.listFollowing` 获取关注列表，然后对每个关注者调用 `post.listCreator` 检测更新
  - 对比每个创作者最新一条投稿的 `id`，发现变化就输出"有新投稿"的提示并发送 Bark 通知
- **认证方式**: 复用浏览器里的登录 Cookie（和本仓库的浏览器扩展一致，依赖 Cookie 身份）。

**我也是在gayhub上看不到相关项目才是自己研发的，如果这对你有帮助，请给我点个star吧~**

---

## 安装依赖

在仓库根目录执行：

```bash
pip install -r fanbox_monitor/requirements.txt
```

（或者你可以只安装 `requests` 和 `onepush`：`pip install requests onepush`）

---

## 配置 cookie

1. 登录 `https://www.fanbox.cc/` ，确保能看到"正在赞助"的页面。
2. 打开浏览器开发者工具 → Network（网络）面板。
3. 刷新页面，随便点一个 `帖子链接` 或其他 fanbox 接口请求。
4. 在请求的 **Request Headers** 中找到 `Cookie`，复制整段值。
5. 在仓库根目录创建 `fanbox_monitor_config.json`，内容示例：

```json
{
  "cookie": "这里粘贴你复制的整段 Cookie 字符串",
  "limit": 50,
  "state_file": "fanbox_monitor_state.json",
  "bark_key": "你的 Bark 推送 key（可选，用于手机推送）",
  "bark_group": "可选的 Bark 分组名称，默认：Fanbox更新跟踪",
  "check_following": false,
  "min_fee_required": 0,
  "creators_file": "fanbox_monitor_creators.json",
  "proxy": "http://172.17.0.1:7890"
}
```

### 配置项说明

- **limit**: 每次从"正在赞助"列表或单个创作者获取的帖子数量，默认 50 即可。
- **state_file**: 用来保存"每个创作者最新一条投稿 id"的本地 JSON 文件。状态文件会区分赞助和关注两种类型。
- **bark_key**: 如果填写，会在发现新投稿时通过 onepush 的 Bark 通知你。通知会使用创作者的头像作为图标。
- **bark_group**: Bark 的分组名称，用来在 Bark 客户端里对通知进行分类，不填则使用默认值 `Fanbox更新跟踪`。
- **check_following**: 是否同时检测关注的创作者（不仅仅是赞助的）。设置为 `true` 时，会获取你的关注列表并检测每个关注者的新投稿。默认 `false`。
- **min_fee_required**: 默认最小收费金额（日元）。当某个创作者没有单独配置时，使用此值作为默认值。设置为 `0` 表示不限制（所有投稿都会通知）。
- **creators_file**: 保存赞助者和关注者列表的文件名。脚本会在每次检测后自动更新此文件，包含所有赞助者和关注者的 ID、名称和头像 URL。
- **proxy**: HTTP 代理地址（可选）。如果需要通过代理访问 Fanbox API，可以设置此字段，例如 `"http://172.17.0.1:7890"`。不设置则不使用代理。

### 为每个作者单独配置最小监听金额

脚本会自动检测所有赞助者和关注者，并在配置文件中为每个作者创建最小监听金额配置。你只需要在配置文件中修改 `creator_min_fees` 字段即可：

```json
{
  "cookie": "你的 Cookie",
  "limit": 50,
  "state_file": "fanbox_monitor_state.json",
  "bark_key": "你的 Bark key",
  "bark_group": "Fanbox更新跟踪",
  "check_following": true,
  "min_fee_required": 0,
  "creators_file": "fanbox_monitor_creators.json",
  "proxy": "http://172.17.0.1:7890",
  "creator_min_fees": {
    "creator_id_1": 500,
    "creator_id_2": 0,
    "creator_id_3": 1000
  }
}
```

- **creator_min_fees**: 每个创作者的最小监听金额配置（键为创作者 ID，值为最小金额，单位：日元）
  - 脚本会在首次检测到某个创作者时，自动将其添加到配置文件中，默认值为 `0`（不限制）
  - 你只需要修改对应创作者 ID 的值即可
  - 如果某个创作者没有在此配置中，会使用 `min_fee_required` 作为默认值
  - **注意**：你不需要手动查找创作者 ID，脚本会自动检测并写入配置文件，你只需要修改数值即可

---

## 运行方式

在仓库根目录执行（或把整个 `fanbox_monitor` 文件夹单独拷出来，在其内部执行也可以）：

```bash
cd fanbox_monitor
python monitor.py
```

运行后脚本只执行**一次检测**，适合由外部定时器（计划任务 / cron 等）定期调用：

- 当检测到某个创作者有新投稿时：
  - 在终端打印：`[NEW] 赞助/关注 - 创作者名称 (ID) 有新投稿：标题 (id=xxx, 发布于 时间)`
  - 如果配置了 `bark_key`，会同时通过 Bark 推送到你的手机：
    - **赞助的创作者**：标题为 `你赞助的{作者名称}有更新！`
    - **关注的创作者**：标题为 `你关注的{作者名称}有更新！`
    - 通知会使用创作者的头像作为图标
    - 点击通知可打开对应 Fanbox 投稿页面

- 状态文件会区分赞助和关注两种类型，使用 `supporting:creator_id` 和 `following:creator_id` 作为 key 存储。

- 再次运行时会从 `state_file` 里读取上次记录的各创作者最新投稿 id，只提示**之后的新投稿**。

- 每个创作者都可以单独配置最小监听金额（在配置文件的 `creator_min_fees` 字段中）。脚本会在首次检测到某个创作者时，自动将其添加到配置文件中，默认值为 `0`（不限制）。你只需要修改对应创作者 ID 的值即可。如果某个创作者没有单独配置，会使用 `min_fee_required` 作为默认值。

- 每次检测后，脚本会自动将赞助者和关注者列表保存到 `creators_file` 配置的文件中，方便查看你正在监听的所有创作者。

- 如果运行时发生错误且配置了 `bark_key`，会发送错误通知到你的手机。

---

## 语言支持

脚本支持多语言。默认语言根据系统语言环境自动检测。你也可以在配置文件中手动设置语言：

```json
{
  "language": "zh"
}
```

支持的语言：
- `en` - English（英语）
- `zh` - 简体中文
- `zh-tw` - 繁体中文
- `ja` - 日本語
- `ko` - 한국어

---

## 错误处理

如果脚本运行时发生错误（网络连接失败、API 请求失败、解析错误等），且配置了 `bark_key`，会自动发送错误通知到你的手机：

- 标题：`Fanbox 监听器运行错误`
- 内容：具体的错误信息（例如：`检测时发生错误: HTTP error 403 Forbidden`）
- 分组：使用配置的 `bark_group`（默认：`Fanbox更新跟踪`）

**注意**：只有在配置了 `bark_key` 的情况下才会发送错误通知。如果没有配置 `bark_key`，错误信息只会打印到终端。

