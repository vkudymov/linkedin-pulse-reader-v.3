# Backend (Python)

`backend/` содержит текущий Python-код: `LinkedInClient/`, `PostAnalyzer/`, `Storage/`, а также `run_demo.py`, который:

- логинится в LinkedIn (Playwright)
- сохраняет cookies и найденные посты в Supabase (`linkedin_accounts`, `feed_posts`)
- анализирует релевантность постов через LLM

## Установка зависимостей (editable)

Из корня репозитория:

```bash
cd backend
python3 -m pip install -e LinkedInClient -e PostAnalyzer -e Storage -e api
```

## Переменные окружения

Создайте `backend/.env` (не коммитится). Минимальный набор для Supabase worker:

```bash
SUPABASE_URL="https://<project-ref>.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="<service-role>"
STORAGE_USER_ID="<auth.users.id>"
STORAGE_ACCOUNT_LABEL="default"
```

Важно: `STORAGE_USER_ID` должен совпадать с `auth.users.id`, который вы создали через фронтенд (`/register`). Тогда записи будут принадлежать этому пользователю и будут видны ему в UI.

## Запуск

### Demo-скрипт (worker-пайплайн)

```bash
cd backend
python run_demo.py --limit 10
```

### HTTP API для LinkedIn login (backend only)

API поднимает интерактивный Playwright Chromium и сохраняет cookies в Supabase `linkedin_accounts` для **текущего пользователя** (определяется по Supabase JWT).

Дополнительно к переменным выше:

```bash
SUPABASE_ANON_KEY="<anon-key>"          # для проверки Bearer JWT через Supabase Auth
LINKEDIN_AUTH_TIMEOUT_MS="300000"      # 5 минут на OAuth/2FA/checkpoint
PLAYWRIGHT_CHANNEL="chrome"           # помогает для Google/Apple (если установлен Chrome)
PLAYWRIGHT_USER_DATA_DIR="./.playwright-profile"  # persistent Chrome profile (важно для Google)
API_HOST="127.0.0.1"
API_PORT="8000"
```

Если Google показывает ошибку вида “This browser or app may not be secure”, обычно помогает:
- `PLAYWRIGHT_CHANNEL="chrome"`
- `PLAYWRIGHT_USER_DATA_DIR` (persistent профиль)

Чтобы начать “с чистого листа”, остановите API и удалите папку профиля (по умолчанию `backend/.playwright-profile/`), затем запустите API снова.

Запуск:

```bash
cd backend
uvicorn pulse_api.main:app --app-dir api/src --reload --host 127.0.0.1 --port 8000
```

Эндпоинты:
- `POST /v1/linkedin/login` — старт login-сессии (`email` / `google` / `apple`)
- `GET /v1/linkedin/login/{session_id}` — статус (polling)
- `DELETE /v1/linkedin/login/{session_id}` — отмена (best-effort, закрывает браузер через cancel flag)

Пример (вместо `$SUPABASE_ACCESS_TOKEN` используйте access token текущего пользователя Supabase):

```bash
curl -X POST "http://127.0.0.1:8000/v1/linkedin/login" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"method":"google","label":"default"}'
```

Email/phone + password (best-effort автозаполнение; при 2FA/checkpoint нужно будет доделать руками в том же окне):

```bash
curl -X POST "http://127.0.0.1:8000/v1/linkedin/login" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"method":"email","identifier":"user@example.com","password":"secret","label":"default"}'
```

Apple ID:

```bash
curl -X POST "http://127.0.0.1:8000/v1/linkedin/login" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"method":"apple","label":"default"}'
```

