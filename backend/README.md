# Backend (Python)

`backend/` содержит текущий Python-код: `LinkedInClient/`, `PostAnalyzer/`, `Storage/`, а также `run_demo.py`, который:

- логинится в LinkedIn (Playwright)
- сохраняет cookies и найденные посты в Supabase (`linkedin_accounts`, `feed_posts`)
- анализирует релевантность постов через LLM

## Установка зависимостей (editable)

Из корня репозитория:

```bash
cd backend
python3 -m pip install -e LinkedInClient -e PostAnalyzer -e Storage
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

```bash
cd backend
python run_demo.py --limit 10
```

