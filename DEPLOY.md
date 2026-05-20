# Деплой на Railway

## 1. Создать аккаунт
- Зайти на https://railway.app
- Зарегистрироваться через GitHub (нужен GitHub аккаунт)

## 2. Загрузить код на GitHub
- Создать новый репозиторий на github.com (например `vegalibr-kp`)
- Инициализировать git в папке `webapp` и запушить:

```
cd "D:\ПРОЕКТ КЛАУД\webapp"
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/ТВОЙ_ЛОГИН/vegalibr-kp.git
git push -u origin main
```

## 3. Создать проект на Railway
- На dashboard.railway.app → New Project → Deploy from GitHub
- Выбрать репозиторий `vegalibr-kp`
- Railway автоматически обнаружит `Procfile` и запустит

## 4. Задать переменные окружения
В Railway → твой проект → Variables → добавить:

| Переменная | Значение |
|---|---|
| `APP_PASSWORD` | твой пароль (например `Vega2025!`) |
| `SECRET_KEY` | любая случайная строка (например `x7k2m9p4`) |

## 5. Готово!
Railway выдаст адрес вида `https://vegalibr-kp.up.railway.app`
Открываешь → вводишь пароль → загружаешь Excel → скачиваешь Word КП.

## Обновление
При изменении кода — просто делаешь `git push`, Railway автоматически переразворачивает.

## Сменить пароль
В Railway → Variables → изменить `APP_PASSWORD` → Save → приложение перезапускается автоматически.
