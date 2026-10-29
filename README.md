# Otome

乙女视觉小说服务。后台配置故事、角色、素材和剧情，玩家从故事编码对应的地址进入游戏。

## 目录

- `backend`：Django 接口
- `frontend/admin`：后台页面
- `frontend/game-client`：玩家页面
- `deploy`：容器启动脚本和部署说明
- `.env.example`：环境变量示例

数据库账号、对象存储密钥、后台初始密码和证书都不在仓库里。使用前把 `.env.example` 复制为 `.env`，再填入自己的值。

## 本地启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
python manage.py migrate --settings=uivsbe_backend.settings.pro
python manage.py runserver 8001 --settings=uivsbe_backend.settings.pro
```

## 本地启动页面

后台：

```powershell
cd frontend\admin
npm install
npm run dev
```

玩家页：

```powershell
cd frontend\game-client
npm install
$env:UNI_INPUT_DIR = (Get-Location).Path
npm run dev:h5
```

开发时接口走本机 `http://127.0.0.1:8001`。

## 部署

用 Docker 部署时见 [deploy/部署.md](deploy/部署.md)。
