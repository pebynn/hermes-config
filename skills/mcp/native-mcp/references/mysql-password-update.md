# MySQL MCP 密码更新流程

## 场景

MySQL `stock` 用户密码变更后，MCP MySQL server 连不上。关键陷阱：

1. **MCP stdio 传输不支持 `${ENV_VAR}` 展开** — `args` 数组直接传给子进程，无 shell 求值。`mysql://stock:${MYSQL_PASSWORD}@localhost` 会被当作字面量。
2. **`systemctl restart` 不会清理旧 MCP 子进程** — 旧进程残留，继续用旧密码。

## 正确流程

### Step 1: 重置 MySQL 密码

```bash
sudo mysql -e "ALTER USER 'stock'@'localhost' IDENTIFIED BY '新密码'"
# 验证
mysql -u stock -p'新密码' -e "SELECT 1"
```

### Step 2: 更新 config.yaml

```yaml
mcp_servers:
  mysql:
    command: "npx"
    args: ["-y", "@berthojoris/mcp-mysql-server", "mysql://stock:新密码@localhost:3306/stock_kline"]
```

**绝对不能用 `${VAR}`**，必须是明文。

### Step 3: 杀旧进程 + 重启 gateway

```bash
# 第一步：杀干净所有 mcp-mysql 残留进程
pkill -f 'mcp-mysql'

# 第二步：重启 gateway（后台，避免阻塞当前会话）
systemctl --user restart hermes-gateway.service &

# 第三步：等 40 秒让 gateway 重建 MCP 连接
sleep 40

# 第四步：验证新进程用新密码
ps aux | grep mcp-mysql | grep -v grep
# 确认进程已重建，然后测试
```

### Step 4: 测试

当前会话中 `mcp_mysql_test_connection`，如果报 `ClosedResourceError` 或 `unreachable`，再等 10 秒重试。

## 已知问题

- 终端输出会自动遮蔽 `***`，导致看起来像是占位符。用 `xxd` 或 `cat -A` 查看真实内容。
- Gateway 重启后 MCP 服务器重建有 ~30-40s 延迟。
- 多个 mcp-mysql 进程是正常的（npm exec → sh → node 三层），杀的时候 `pkill -f` 一次全清。
