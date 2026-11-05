# TLS 证书（仅本机，勿提交真实 .key/.crt）

放到本目录，由 compose 挂载到容器 `/etc/nginx/certs/`。

| 域名 | 证书文件 |
|---|---|
| `caoxi.live` | `jnacaoxi_live.crt` / `jnacaoxi_live.key` |
| `ruxi.ink` | `jnaruxi_ink.crt` / `jnaruxi_ink.key` |
| `caoxi.life` | `jnacaoxi_life.crt` / `jnacaoxi_life.key` |

静态站目录：

- `page/frontend` → 玩家页（三个域名共用）
- `page/admin` → 后台
- `page/agreement` → 协议页（可选）
- `page/file` → ACME / 其它静态文件（可选）
