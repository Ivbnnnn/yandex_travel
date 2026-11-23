# Деплой на VPS

Workflow разворачивает React и FastAPI из `main`. Команды ниже рассчитаны на Ubuntu
24.04 LTS, публичный IPv4 и SSH на `22/tcp`. В примерах замени `203.0.113.10`
на IP своего VPS, а `admin` — на своего пользователя с `sudo`.

## 1. Пользователь и ключ ED25519

На своём ПК в `cmd` создай отдельный ключ для GitHub Actions. На запрос
парольной фразы дважды нажми Enter.

```cmd
if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"
ssh-keygen -t ed25519 -C "github-actions-yandex-travel" -f "%USERPROFILE%\.ssh\yandex_travel_deploy"
type "%USERPROFILE%\.ssh\yandex_travel_deploy.pub"
```

В действующей админской SSH-сессии на VPS создай пользователя и добавь его ключ.
Замени строку `ssh-ed25519 AAAA... github-actions-yandex-travel` полным содержимым файла `.pub`.

```bash
sudo adduser --disabled-password --gecos '' deploy
sudo install -d -m 0700 -o deploy -g deploy /home/deploy/.ssh
printf '%s\n' 'restrict ssh-ed25519 AAAA... github-actions-yandex-travel' \
  | sudo tee -a /home/deploy/.ssh/authorized_keys >/dev/null
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 0600 /home/deploy/.ssh/authorized_keys
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Сверь отпечаток ключа хоста с отпечатком, который показывает SSH при первом
входе. Оставь текущую админскую сессию открытой и проверь из нового окна оба
входа. Для `admin` должен быть настроен отдельный личный ключ.

```cmd
ssh -o IdentitiesOnly=yes -i "%USERPROFILE%\.ssh\yandex_travel_deploy" deploy@203.0.113.10 "id -un"
ssh -o PreferredAuthentications=publickey admin@203.0.113.10
```

Когда оба входа работают, настрой SSH на сервере и проверь эффективные значения.

```bash
sudo tee /etc/ssh/sshd_config.d/00-keys-only.conf >/dev/null <<'EOF'
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
EOF
sudo sshd -t && sudo sshd -T | grep -E '^(pubkeyauthentication|passwordauthentication|kbdinteractiveauthentication|authenticationmethods) '
```

Проверь, что `pubkeyauthentication` имеет значение `yes`,
`authenticationmethods` — `publickey`, а `passwordauthentication` и
`kbdinteractiveauthentication` — `no`. Затем выполни
`sudo sshd -t && sudo systemctl reload ssh` и снова проверь входы в отдельном окне.
Если у тебя уже есть
непривилегированный вход с `sudo`, можно добавить `PermitRootLogin no` в тот же
файл и снова проверить конфигурацию и вход. [Документация OpenSSH в Ubuntu](https://ubuntu.com/server/docs/how-to/security/openssh-server/)

## 2. Docker и firewall

Из админской сессии. Если официальный APT-репозиторий Docker уже подключён,
выполни установку пакетов Docker из последней команды этого блока.

```bash
sudo apt update
sudo apt upgrade
sudo apt install ca-certificates curl uidmap dbus-user-session openssl libcap2-bin ufw unattended-upgrades
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras
```

Если на VPS уже установлен Docker из пакетов Ubuntu, проверь список конфликтующих
пакетов и существующие контейнеры перед переходом на официальный репозиторий.
[Установка Docker на Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

```bash
sudo install -d -m 0700 -o deploy -g deploy /srv/yandex-travel /srv/yandex-travel/releases
sudo loginctl enable-linger deploy
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status
```

В firewall облачного провайдера также разреши входящие `22/tcp` и `80/tcp`.
Порт SSH должен быть доступен из GitHub-hosted runner. Compose публикует только
порт `80` контейнера Nginx. FastAPI и PostgreSQL доступны по внутренней сети
Compose.

В админской сессии разреши RootlessKit привязываться к порту `80`.
После обновления пакета, содержащего RootlessKit, проверь capability через
`getcap "$(command -v rootlesskit)"`. [Привилегированные порты в rootless Docker](https://docs.docker.com/engine/security/rootless/tips/#exposing-privileged-ports)

```bash
sudo setcap cap_net_bind_service=ep "$(command -v rootlesskit)"
```

Подключись по SSH как `deploy` и настрой пользовательский демон Docker. Флаг
`--force` позволяет запустить его рядом с системным демоном Docker. Пользователю
`deploy` достаточно собственной сессии systemd, Docker-контекста `rootless` и
прав на `/srv/yandex-travel`. [Режим rootless](https://docs.docker.com/engine/security/rootless/)

```bash
dockerd-rootless-setuptool.sh install --force
systemctl --user is-active docker
docker --context rootless info --format '{{json .SecurityOptions}}'
docker compose version
```

Если rootless Docker уже настроен, после `setcap` выполни под `deploy`
`systemctl --user restart docker`.

## 3. Настройки приложения и Nginx

Под `deploy` создай файл окружения. Проверь IP перед запуском команд.

```bash
VPS_PUBLIC_IP=203.0.113.10
umask 077
if [ ! -e /srv/yandex-travel/.env.vps ]; then
  cat > /srv/yandex-travel/.env.vps <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
CSRF_SECRET=$(openssl rand -hex 32)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=$(openssl rand -hex 24)
ALLOWED_ORIGINS=["http://$VPS_PUBLIC_IP"]
COOKIE_SECURE=false
SEED_DATA=true
DEMO_PAYMENTS=true
EOF
fi
chmod 0600 /srv/yandex-travel/.env.vps
```

Сайт будет доступен на `http://IP/`, API — на `http://IP/api/v1`, Swagger —
на `http://IP/docs`. Фронтенд и API используют один origin. Для учебного HTTP используй тестовые данные и
уникальные пароли. Параметр `COOKIE_SECURE=false` позволяет браузеру отправлять
cookie по HTTP.

Workflow загрузит `deploy/nginx.conf` вместе с кодом. Compose подключит файл
к контейнеру Nginx в режиме чтения.

```bash
sudo ss -ltnp 'sport = :80'
```

Если порт `80` занимает системный Nginx, который ты установил для этого проекта
по предыдущей инструкции, освободи порт перед деплоем командой
`sudo systemctl disable --now nginx`. Если этот Nginx обслуживает другие сайты,
сначала согласуй перенос их конфигурации. При откате на релиз с системным Nginx
снова запусти его через `sudo systemctl enable --now nginx`.

## 4. GitHub Secrets и первый запуск

В админской сессии VPS выведи строку для `known_hosts`. Это публичный ключ
**сервера**, по которому runner проверяет, к какому VPS подключается.

```bash
VPS_PUBLIC_IP=203.0.113.10
sudo awk -v host="$VPS_PUBLIC_IP" '{print host, $1, $2}' /etc/ssh/ssh_host_ed25519_key.pub
```

В репозитории открой **Settings → Environments → production** и добавь секреты.
Если в репозитории недоступны секреты окружения, добавь их в **Settings →
Secrets and variables → Actions → Repository secrets**. [GitHub Actions Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

| Секрет | Значение |
| --- | --- |
| `VPS_HOST` | Публичный IPv4 VPS |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | Полное содержимое приватного `yandex_travel_deploy`, включая строки `BEGIN` и `END` |
| `VPS_KNOWN_HOSTS` | Строка `IP ssh-ed25519 …` из команды на сервере |

После push в `main` GitHub запустит Ruff, Oxlint и сборку React с проверкой
типов. CI поднимет стек и проверит API, главную страницу, прямой запрос к
`/search` и загрузку JavaScript через Nginx. После успешных проверок workflow
отправит коммит на VPS по SSH, соберёт серверные образы и повторит HTTP-проверки.
Если запуск контейнеров или проверка с VPS завершатся ошибкой, скрипт попробует
поднять предыдущий успешный релиз.
Данные PostgreSQL хранятся в именованном Docker-томе.

С компьютера можно отдельно проверить публичный адрес:

```cmd
curl.exe -fsS http://203.0.113.10/health
```

Для диагностики на VPS используй `docker --context rootless ps` и
`docker --context rootless logs --tail 100 yandex-travel-nginx-1` под `deploy`.
Логи FastAPI находятся в контейнере `yandex-travel-app-1`. Для мониторинга настрой
внешний HTTP-чек `/health` с уведомлениями. Включи автоматические обновления
безопасности и сделай регулярный `pg_dump`, если данные нужно сохранять. Перед очисткой старых
образов и каталогов `releases/` сохрани текущий релиз и версию для отката.
