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
python run_post_search.py --limit 10
```

### 3) Worker API (для запуска поиска из UI)

Если вы хотите запускать поиск постов кнопкой из интерфейса (`/prompts`), нужно поднять worker API:

```bash
cd worker
uvicorn pulse_api.main:app --app-dir api/src --reload --host 127.0.0.1 --port 8000
```

## Supabase

Схема БД находится в `worker/supabase/migrations/`.

### Личный кабинет

- Таблица профиля пользователя: `public.user_profiles`
- Аватары: Supabase Storage bucket `avatars`
- Страница: `/account`

### Промпты (поиск и комментарии)

В личном кабинете (`/account`) пользователь может настроить промпты, которые используются для:

- отбора релевантных постов (обязательный `search_prompt`)
- генерации комментариев (опциональный `comment_prompt`)

Важно: промпт поиска должен содержать маркер `<<<POST_TEXT>>>`. Если `search_prompt` не заполнен,
worker **не будет запускать анализ** до тех пор, пока вы не сохраните промпт.

Миграция для добавления колонок:
- `worker/supabase/migrations/20260805180200_user_profile_prompts.sql`
