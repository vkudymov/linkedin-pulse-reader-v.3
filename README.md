# LinkedIn Pulse Reader (Monorepo)

Репозиторий разделён на две части:

- `frontend/` — Next.js UI (регистрация/вход, просмотр найденных постов)
- `worker/` — Python worker (сбор постов, запись в Supabase, анализ через LLM)

## Быстрый старт

### 1) Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### 2) Worker

```bash
cd worker
python3 -m pip install -e LinkedInClient -e PostAnalyzer -e Storage
python run_demo.py --limit 10
```

## Supabase

Схема БД находится в `worker/supabase/migrations/`.

### Личный кабинет

- Таблица профиля пользователя: `public.user_profiles`
- Аватары: Supabase Storage bucket `avatars`
- Страница: `/account`
