# Remnashop Architecture Notes for Rain VPN

This repository is the Telegram bot backend for Rain VPN. It is a fork of
Remnashop, integrated with RemnaWave through `remnapy`, with local Rain-specific
extensions for the web personal cabinet, node traffic quota, Moy Nalog
receipts, personal discounts, and referral milestones.

## Runtime Shape

- Main HTTP app: `src/__main__.py` builds FastAPI, aiogram `Dispatcher`, Dishka
  DI container, and registers FastAPI plus aiogram integrations.
- App lifecycle: `src/lifespan.py` initializes the event bus, default payment
  gateways, settings, Telegram webhook, bot commands, RemnaWave connectivity
  checks, startup/shutdown notifications, and cleanup.
- Web layer: `src/web/app.py` creates FastAPI without public docs, adds CORS,
  registers routers, and mounts Telegram webhook handling.
- Bot state: aiogram FSM is stored in Redis via `src/telegram/dispatcher.py`.
- Background jobs: Taskiq uses Redis streams via
  `src/infrastructure/taskiq/broker.py`; worker/scheduler entry points are
  `src/infrastructure/taskiq/worker.py` and `src/infrastructure/taskiq/scheduler.py`.
- Docker: `docker-compose.yml` runs Postgres, Valkey/Redis, web app, Taskiq
  worker, and scheduler. `docker-entrypoint.sh` syncs assets/translations,
  patches `remnapy`, runs Alembic migrations, then starts uvicorn.

## Layering

- `src/core`: configuration, constants, enums, exceptions, logger, generic
  helpers.
- `src/application`: business layer. DTOs, protocol interfaces, permission
  policy, events, services, and use cases live here.
- `src/infrastructure`: adapters for database, Redis, RemnaWave SDK, payment
  gateways, event bus, Taskiq, cryptography, redirects, and translation.
- `src/telegram`: aiogram/aiogram-dialog presentation layer: routers, dialogs,
  handlers, getters, middlewares, widgets, keyboards, states.
- `src/web`: FastAPI endpoints for Telegram, payment webhooks, RemnaWave
  webhooks, and Rain internal API.
- `assets`: Fluent translations and banner images. Russian translations are
  actively customized for Rain. User-facing text belongs here: button labels,
  menu titles, descriptions, notifications, event texts, and similar copy must
  be referenced from code by i18n keys instead of being hardcoded in feature
  modules.

The intended dependency direction is:

`telegram/web/taskiq -> application use cases/services -> application protocols -> infrastructure adapters`.

Use cases should depend on application protocols such as `UserDao`,
`SubscriptionDao`, `Remnawave`, `Notifier`, and `UnitOfWork`, not directly on
SQLAlchemy or aiogram, unless the existing use case already does so.

## Dependency Injection

- DI is Dishka-based. Container factories are in `src/infrastructure/di/ioc.py`.
- Provider groups live in `src/infrastructure/di/providers`.
- App and worker containers share most providers. aiogram gets
  `AiogramProvider` and `I18nAiogramProvider`; Taskiq gets `I18nTaskiqProvider`.
- Use cases are registered centrally in `UseCasesProvider`, collecting
  `*_USE_CASES` tuples from each feature package.
- DAO interfaces are in `src/application/common/dao`; implementations are in
  `src/infrastructure/database/dao`.
- DTO/model conversion is handled with Adaptix `Retort` and `ConversionRetort`
  in `src/infrastructure/di/providers/retort.py`.

## Main User Flows

### Telegram Update Flow

1. Telegram sends POST to `/api/v1/telegram`.
2. `TelegramWebhookEndpoint` verifies `X-Telegram-Bot-Api-Secret-Token`.
3. The update is scheduled with `dispatcher.feed_update`.
4. Middlewares run:
   - `AccessMiddleware`: blocks maintenance, invite-only, disabled payment,
     registration-disabled, and blocked users.
   - `UserMiddleware`: creates or refreshes local user from Telegram.
   - `RulesMiddleware` and `ChannelMiddleware`: enforce configured access
     requirements.
   - `ThrottlingMiddleware`: short per-user throttle.
   - `ErrorMiddleware`: redirects to menu, notifies user/support, publishes
     error events.
5. Routers/dialogs process the interaction.

### Subscription Purchase Flow

1. Dialog starts in `src/telegram/routers/subscription`.
2. User selects purchase type, plan, duration, payment gateway.
3. `CreatePayment` creates a `TransactionDto` and calls the selected gateway.
4. Payment gateway webhook hits `/api/v1/payments/{gateway_type}`.
5. Webhook schedules `handle_payment_transaction_task`.
6. `ProcessPayment` marks transaction status and dispatches:
   - normal plan: `PurchaseSubscription`;
   - node traffic reset: `PurchaseTrafficReset`;
   - test/free payment: direct handling.
7. `PurchaseSubscription` creates/updates RemnaWave user, updates local
   subscription, resets one-time `purchase_discount`, redirects user to success
   or failure, and assigns referral rewards after paid purchases.

### Trial/Free Flow

- Telegram trial uses `ActivateTrialSubscription`.
- Rain internal API free activation uses `ActivateFreePlan`, a silent variant
  without Telegram redirects or admin events.

### RemnaWave Webhook Flow

1. RemnaWave sends POST to `/api/v1/remnawave`.
2. `WebhookUtility.parse_webhook` validates body/header signature using
   `REMNAWAVE_WEBHOOK_SECRET`.
3. `RemnaWebhookService` handles:
   - user created/modified: sync local user/subscription;
   - user status events: sync and publish subscription notifications;
   - device events: publish device notifications;
   - node events: publish node status/traffic notifications.

### Internal Rain Web API

`src/web/endpoints/internal.py` exposes `/api/v1/internal/*`, protected by
`X-Internal-Key` matching `APP_WEB_API_KEY` from environment.

It supports the Rain web cabinet:

- user lookup/create/delete/migrate;
- current subscription lookup and manual add-days/free activation;
- plan and gateway listing;
- transaction history;
- referral stats;
- node listing;
- personal discount updates;
- node quota lookup;
- web payment creation with external `return_url`.

This endpoint is a major Rain-specific integration point and should be treated
as part of the public contract with `web-rain`.

## Data Model

SQLAlchemy models live in `src/infrastructure/database/models`; migrations are
in `src/infrastructure/database/migrations/versions`.

Core tables:

- `users`: Telegram identity, role, language, referral code, discounts, points,
  trial flag, current subscription pointer, block flags, paid referral counter.
- `subscriptions`: local snapshot of RemnaWave user, plan snapshot, limits,
  squads, status, URL, expiration.
- `plans`, `plan_durations`, `plan_prices`: sellable plans and prices per
  duration/currency.
- `transactions`: payment ID, user, status, gateway, purchase type, pricing,
  currency, plan snapshot.
- `settings`: JSONB access, requirements, notifications, referral, menu config.
- `payment_gateways`: active gateway configs, encrypted sensitive settings.
- `referrals`, `referral_rewards`: referral graph and issued/pending rewards.
- `broadcasts`, `broadcast_messages`: admin broadcast lifecycle.
- `user_node_quota`: Rain-specific node traffic quota state.

Postgres JSONB snapshots are used intentionally for settings, transaction
pricing/plan snapshots, and subscription plan snapshots. Adaptix handles most
DTO conversion.

## RemnaWave Integration

- Provider: `src/infrastructure/di/providers/remnawave.py`.
- Protocol: `src/application/common/remnawave.py`.
- Implementation: `src/infrastructure/services/remnawave.py`.
- SDK: `remnapy==2.7.0` from git source.

The app builds RemnaWave users from local user/profile plus either a
`PlanSnapshotDto` or `SubscriptionDto`. Local RemnaWave usernames use
`rs_{telegram_id}`. Important operations include create/update/delete user,
sync from panel, sync from bot, reset traffic, revoke subscription, device
deletion, and squad updates.

## Payment Gateways

Gateway types are in `PaymentGatewayType`. Implementations live in
`src/infrastructure/payment_gateways`.

Supported gateways:

- Telegram Stars
- YooKassa
- YooMoney
- Cryptomus
- Heleket
- CryptoPay
- FreeKassa
- MulenPay
- PayMaster
- Platega
- Robokassa
- UrlPay
- Wata

`CreateDefaultPaymentGateway` creates missing gateway rows at startup. Gateway
instances are cached by `PaymentGatewaysProvider` and recreated when gateway
data changes.

## Events and Notifications

- Event bus: `src/infrastructure/services/event_bus.py`.
- Decorator: `@on_event(...)`.
- Event classes: `src/application/events`.
- Main listener: `NotificationService`.
- Receipt listener: `NalogReceiptsService`.

Event publication is asynchronous: event bus creates background tasks and
resolves handlers from Dishka request scopes. Shutdown waits for background
event tasks.

Notifications use Fluent translation keys and `MessagePayloadDto`. Admin/user
notification toggles are stored in `settings.notifications`.

## Taskiq Jobs

Scheduled/background tasks live in `src/infrastructure/taskiq/tasks`.

- `payments.py`: payment transaction processing, old pending transaction
  cancellation.
- `broadcast.py`: send/delete broadcasts, clear old broadcasts.
- `importer.py`: import XUI users and sync users from panel.
- `notifications.py`: notify waitlisted users when payments are restored.
- `update.py`: check upstream Remnashop releases through GitHub API.
- `receipts.py`: call Moy Nalog receipt service.
- `node_traffic.py`: hourly quota enforcement and monthly reset for monitored nodes
  nodes.

Taskiq worker command in compose imports tasks with pattern
`src/infrastructure/taskiq/tasks/*.py`.

## Rain-Specific Features

- Internal cabinet API in `src/web/endpoints/internal.py`.
- Node quota:
  - config in `src/core/config/node_quota.py`;
  - model/DAO/DTO for `user_node_quota`;
  - hourly/monthly Taskiq jobs;
  - purchase type `TRAFFIC_RESET`;
  - subscription dialog traffic-reset flow;
  - admin user-profile controls.
- Referral milestones:
  - config in `src/core/config/referral_milestones.py`;
  - `paid_referrals_count` on user;
  - milestone discounts via `CheckReferralMilestone`.
- Personal and one-time purchase discounts:
  - fields on user;
  - `PricingService` chooses max discount capped at 100%;
  - purchase discount is reset after successful subscription purchase.
- Moy Nalog receipts:
  - config fields on `AppConfig`;
  - receipt queued after RUB non-trial purchase events.
- `UrlPay` gateway and web payment return URL support.

## Local Development Notes

- Python target is 3.12.
- Dependency manager is `uv`; lock file is `uv.lock`.
- There is no `tests` directory currently.
- `git status` may need `git -c safe.directory=F:/dev/Rain/remnashop ...`
  because Windows reports dubious ownership.
- Commits and pushes must use the repository owner's GitHub identity only. Do
  not add `Co-authored-by` trailers for Codex/OpenAI or otherwise mark AI
  co-authorship in commits.
- Do not read or print `.env` unless explicitly needed; it contains production
  secrets.
- Current known local dirty file when this note was created:
  `assets/translations/ru/events.ftl`.

## Change Guidelines

- For business behavior, add or adjust an application use case first, then wire
  it into Telegram, web, or Taskiq adapters.
- For persistent data, update model, DTO, DAO protocol/implementation, Adaptix
  conversion if needed, and add an Alembic migration.
- For Telegram UI, keep dialog state in `src/telegram/states.py`; put display
  data in getters and side effects in handlers.
- For admin actions, check `Permission` and `ROLE_PERMISSIONS`.
- For user-visible text, update Fluent files under `assets/translations`. Do
  not hardcode button names, descriptions, notifications, or menu copy in
  handlers, getters, use cases, or web endpoints unless it is a truly internal
  technical string.
- For background behavior, prefer Taskiq tasks and keep long work out of webhook
  handlers.
- For RemnaWave state changes, keep local DB and panel sync paths explicit:
  local DB changes go through DAO/UoW; panel changes go through `Remnawave`
  protocol or SDK when the wrapper lacks an operation.
