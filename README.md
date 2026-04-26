# MS Bottleneck Detector — v2 Monorepo

Инструмент автоматического обнаружения узких мест в микросервисных системах.

## Структура

```
ms-bn-detector/
├── backend/    # Flask + SQLAlchemy + SQLite
└── frontend/   # React + Vite + Recharts
```

## Запуск

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt

# Запуск (из папки backend/)
python main.py
# или явно указать БД:
python main.py --db sqlite:///bottleneck.db --port 5000
```

> **Важно:** запускать `python main.py` нужно именно из папки `backend/`,  
> либо через `python -m` из корня: `python -m backend.main`

### Frontend

Сначала убедись что npm актуальный — ошибка `cb() never called` означает npm 6.x:

```bash
# Обновить npm
npm install -g npm@latest

# Затем
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Альтернативно через yarn (если npm не обновляется):

```bash
npm install -g yarn
cd frontend
yarn install
yarn dev
```

Фронт проксирует `/api` → `localhost:5000` через Vite — CORS не нужен.

## API

### Проекты

```
GET    /api/projects                     — список проектов
POST   /api/projects                     — создать проект
         body: { name, description, format }
GET    /api/projects/<id>                — детали проекта
DELETE /api/projects/<id>                — удалить проект

POST   /api/projects/<id>/load           — загрузить логи (создаёт снапшот)
         body: { path: "resources/alibaba/" }

GET    /api/projects/<id>/edges          — рёбра с фильтрами + пагинация
         ?severity=critical|warning|ok
         ?rpc_type=http|rpc
         ?service=mc-1
         ?min_p95_growth=2.0
         ?sort_by=p95_growth|records_amount|severity|source
         ?page=1&page_size=50

GET    /api/projects/<id>/snapshots      — история загрузок
GET    /api/projects/<id>/analyse/<edge> — детальный анализ ребра
```

### Legacy (обратная совместимость)

```
POST /api/load
GET  /api/edges
GET  /api/analyse/<edge>
```

Инструмент автоматического обнаружения узких мест в микросервисных системах.

## Структура

```
ms-bn-detector/
├── backend/    # Flask + SQLAlchemy + SQLite
└── frontend/   # React + Vite + Recharts
```

## Запуск

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py --db sqlite:///bottleneck.db --port 5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Фронт проксирует `/api` → `localhost:5000` через Vite.

## API

### Проекты

```
GET    /api/projects                     — список проектов
POST   /api/projects                     — создать проект
         body: { name, description, format }
GET    /api/projects/<id>                — детали проекта
DELETE /api/projects/<id>                — удалить проект

POST   /api/projects/<id>/load           — загрузить логи (создаёт снапшот)
         body: { path: "resources/alibaba/" }

GET    /api/projects/<id>/edges          — рёбра с фильтрами + пагинация
         ?severity=critical|warning|ok
         ?rpc_type=http|rpc
         ?service=mc-1
         ?min_p95_growth=2.0
         ?sort_by=p95_growth|records_amount|severity|source
         ?page=1&page_size=50

GET    /api/projects/<id>/snapshots      — история загрузок
GET    /api/projects/<id>/analyse/<edge> — детальный анализ ребра
```

### Legacy (обратная совместимость)

```
POST /api/load
GET  /api/edges
GET  /api/analyse/<edge>
```
