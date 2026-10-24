-- Восстановление трёх платежей, стёртых слиянием аккаунтов при привязке Telegram.
--
-- Основание: разбор тикета #QCPX3MQU (документ поддержки, в репозиторий не входит).
-- Данные взяты из API ЮKassa утилитой scripts/reconcile_yookassa.py (24.10.2026):
-- id, время создания и проведения, сумма. Владелец — настоящий аккаунт, в
-- который слился виртуальный; соответствие «платёж — виртуальный аккаунт»
-- подтверждено логом бота («Created transaction … for user [USER:<id>…]»):
--   324c1dec… — виртуальный 830 → users.id 857
--   3265e9bf… — виртуальный 867 → users.id 261
--   326b7844… — виртуальный 876 → users.id 264
-- Ники и telegram_id намеренно не приводятся: файл лежит в репозитории.
--
-- Дни никому не доначисляются: все трое их получили при слиянии. Возвращается
-- только запись о платеже — по ней поддержка подтверждает оплату, и по ней же
-- сверка со шлюзом перестаёт находить расхождение.
--
-- Тип покупки NEW — так в описании счёта в ЮKassa («Purchase of …»). Скидки не
-- было: списано ровно по прайсу (Solo 30 дней — 200, 180 дней — 960). Снимок
-- тарифа — тот, что действовал в эти даты: список сквадов у всех транзакций
-- Solo с 20.09 по 23.10 одинаковый. created_at и updated_at — время создания и
-- проведения в ЮKassa, а не время восстановления.
--
-- Повторный запуск ничего не меняет: строка с тем же payment_id пропускается.
-- Чеки «Мой налог» по этим платежам были выпущены в момент оплаты (статус
-- SENT), их восстанавливать не нужно.

BEGIN;

INSERT INTO transactions (
    payment_id, status, is_test, purchase_type, gateway_type, pricing, currency,
    plan_snapshot, created_at, updated_at, user_id, gateway_display_name,
    payment_method, is_gift
)
SELECT
    -- Приведения к enum явные: на неявное приведение строки в INSERT ... SELECT
    -- на денежной таблице полагаться не стоит.
    v.payment_id::uuid, 'COMPLETED'::transaction_status, false, 'NEW'::purchase_type,
    'YOOKASSA'::payment_gateway_type, v.pricing::jsonb, 'RUB'::currency,
    v.snapshot::jsonb, v.created_at::timestamptz, v.captured_at::timestamptz, v.user_id,
    NULL, NULL, false
FROM (VALUES
    (
        '324c1dec-000f-5001-9000-1f973f043e19',
        '{"final_amount": "200", "original_amount": "200.00", "discount_percent": 0}',
        '{"id": 2, "tag": null, "name": "Solo", "type": "DEVICES", "duration": 30, "is_trial": false, "device_limit": 2, "traffic_limit": 0, "external_squad": null, "internal_squads": ["c0534f03-e7e1-4449-be25-ab523ef80b02", "3d8c6c83-0c04-479e-a478-90636d057944"], "traffic_limit_strategy": "NO_RESET"}',
        '2026-09-28T06:33:16.642Z', '2026-09-28T06:33:39.177Z', 857
    ),
    (
        '3265e9bf-000f-5000-b000-13231918fbe1',
        '{"final_amount": "200", "original_amount": "200.00", "discount_percent": 0}',
        '{"id": 2, "tag": null, "name": "Solo", "type": "DEVICES", "duration": 30, "is_trial": false, "device_limit": 2, "traffic_limit": 0, "external_squad": null, "internal_squads": ["c0534f03-e7e1-4449-be25-ab523ef80b02", "3d8c6c83-0c04-479e-a478-90636d057944"], "traffic_limit_strategy": "NO_RESET"}',
        '2026-10-17T20:09:35.623Z', '2026-10-17T20:10:56.757Z', 261
    ),
    (
        '326b7844-000f-5001-8000-11475f100843',
        '{"final_amount": "960", "original_amount": "960.00", "discount_percent": 0}',
        '{"id": 2, "tag": null, "name": "Solo", "type": "DEVICES", "duration": 180, "is_trial": false, "device_limit": 2, "traffic_limit": 0, "external_squad": null, "internal_squads": ["c0534f03-e7e1-4449-be25-ab523ef80b02", "3d8c6c83-0c04-479e-a478-90636d057944"], "traffic_limit_strategy": "NO_RESET"}',
        '2026-10-22T01:19:00.228Z', '2026-10-22T01:28:45.734Z', 264
    )
) AS v(payment_id, pricing, snapshot, created_at, captured_at, user_id)
WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = v.user_id)
  AND NOT EXISTS (SELECT 1 FROM transactions t WHERE t.payment_id = v.payment_id::uuid)
RETURNING id, payment_id, user_id, created_at, (pricing->>'final_amount') AS amount;

COMMIT;
