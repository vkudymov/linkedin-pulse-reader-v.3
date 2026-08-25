# Frontend (Next.js)

## Требования

- Node.js \(рекомендуется LTS\)

## Настройка окружения

1. Скопировать пример и заполнить ключи Supabase:

```bash
cp .env.local.example .env.local
```

2. Взять значения в Supabase Dashboard → Project Settings → API:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Запуск

```bash
npm install
npm run dev
```

Открыть `http://localhost:3000`.

## Что делает UI

- `/register` — регистрация пользователя (Supabase Auth, email+password)
- `/login` — вход
- `/posts` — просмотр `feed_posts` из Supabase для текущего пользователя (через RLS)

Данные загружает python-воркер из `worker/run_post_search.py`.

## Логи

- **Коротко в консоль**: одна строка вида `[ERROR] scope message`.
- **Файл** (только на сервере): `frontend/log/app-YYYY-MM-DD.log`.

Если видите `Missing required env var: NEXT_PUBLIC_SUPABASE_URL`, то в логе будет строка вида:

```
[ERROR] env.getEnv NEXT_PUBLIC_SUPABASE_URL missing
```

Что делать:

1. Проверьте `frontend/.env.local`.
2. Полностью перезапустите dev-сервер (`Ctrl+C`, затем `npm run dev`).
