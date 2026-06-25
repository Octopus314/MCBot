Experimental branch that tries out llm integration to implement conditional muting.

## 命令

### 基础功能
| 命令 | 说明 |
|------|------|
| `/help` | 展示帮助信息 |
| `/ls` | 查询服务器内玩家 |
| `/iam <name>` | 设置关联的 Minecraft ID |
| `/whoami` | 查询关联的 Minecraft ID |
| `/connect` | 重连 RCON（服务器挂了以后） |
| `/llm <消息>` | 向 LLM 提问（简短回答） |

### 管理员功能
| 命令 | 说明 |
|------|------|
| `/ban @用户 [分钟]` | 禁言用户，默认 60 分钟 |
| `/unban @用户` | 解除禁言 |
| `/mute` | 全体禁言 |
| `/unmute` | 解除全体禁言 |
| `/kick @用户` | 踢出用户 |

管理员权限通过 `config.py` 中的 `SUPERUSERS` 配置。

### 自动禁言（LLM）
Bot 会定时检查群内消息，通过 LLM 判断目标用户是否发送了应该禁言的内容，满足置信度阈值后自动禁言并回复原因。
