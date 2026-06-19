# Это единственный файл переводов в вашем volume — он имеет наивысший приоритет.
# Встроенные переводы бота лежат в образе (assets.default/) и всегда актуальны;
# обновления бота их не трогают, а этот файл остается вашим.

# Этот файл служит для двух целей:
#
# 1. Переопределение встроенных переводов.
#    Чтобы изменить любой стандартный ключ — скопируйте его сюда со своим текстом.
#    Значение отсюда перекроет встроенное (assets.default/), остальные ключи берутся из бота.
#
# 2. Собственные переводы, которых нет в стандартном наборе.
#    Например: дополнительные кнопки меню, названия планов и т.п.
#    Используйте ключ вместо текста (например, в названии плана).
#    Чтобы не пересекаться со встроенными ключами, давайте им префикс custom-.

# Ключи должны быть уникальными. Подробная документация по переводам: assets/README.md.

# Максимальная длина перевода:
# Для использования в кнопках — 32 символа.
# Для использования в сообщениях — 1024 символа.

# ============================================================
# КАСТОМНЫЕ КЛЮЧИ МЕНЮ
# ============================================================

custom-menu-link1 = 1️⃣ Первая кнопка
custom-menu-link2 = 2️⃣ Вторая кнопка

# ============================================================
# СИСТЕМНЫЕ МЕТКИ
# ============================================================

# Метка squad для импортированных пользователей
IMPORTED = 🔄 Импортирован

# ============================================================
# НАЗВАНИЯ И ОПИСАНИЯ ПЛАНОВ Rain VPN
# ============================================================

Free = 🌧️ Free | Бесплатный
Solo = 👤 Solo | 2 устройства
Duo = 👥 Duo | 4 устройства
Family = 👨‍👩‍👧 Family | 6 устройств
Team = 🏢 Team | 10 устройств

plan-desc-free = Бесплатный доступ, чтобы спокойно проверить сервис в реальных условиях.
plan-desc-solo = Безлимитный VPN для личного использования. Подключай свои устройства и пользуйся без ограничений.
plan-desc-duo = Расширенный тариф для двух пользователей или нескольких устройств.
plan-desc-family = Оптимально для всей семьи.
plan-desc-team = Для команды или проекта. Один тариф — много устройств.

# ============================================================
# КНОПКИ МЕНЮ (ПЕРЕОПРЕДЕЛЕНИЯ)
# ============================================================

# Главное меню — Rain VPN брендирование
btn-menu =
    .trial = 🌧️ ПОПРОБОВАТЬ БЕСПЛАТНО
    .trial-paid = 🌧️ ПОПРОБОВАТЬ ЗА { $trial_price }
    .connect = ⚡ Подключиться
    .connect-reserve = 🔗 Подключиться (резерв)
    .devices = 📱 Мои устройства
    .subscription = 💎 Подписка
    .invite = 🤝 Пригласить друга
    .support = 💬 Поддержка
    .web-cabinet = 🌐 Личный кабинет
    .dashboard = ⚙️ Панель управления
    .proxy = 👀 Прокси для друга

    .connect-not-available =
    ⚠️ { $status ->
    [LIMITED] ПРЕВЫШЕН ЛИМИТ ТРАФИКА
    [EXPIRED] ПОДПИСКА ИСТЕКЛА
    *[OTHER] ПОДПИСКА НЕ АКТИВНА
    } ⚠️

# Кастомные кнопки пользовательского меню
btn-how-connect = 🤷‍♂️ Как подключиться?
btn-proxy = 👀 Поделиться Mtproxy
btn-proxy-share = 📩 Отправить в Telegram
btn-proxy-copy = 📋 Скопировать ссылку

# ============================================================
# КНОПКИ АДМИН-ПАНЕЛИ: node-quota (наши кастомные атрибуты)
# Upstream btn-user не содержит этих атрибутов.
# ============================================================

btn-user =
    .discount = 💸 Скидка
    .discount-personal = 👤 Персональная скидка
    .discount-purchase = 🎟 На следующую покупку
    .points = 💎 Баллы
    .statistics = 📊 Статистика
    .referrals = 👪 Рефералы
    .message = 📩 Сообщение
    .role = 👮‍♂️ Роль
    .transactions = 🧾 Транзакции
    .give-access = 🔑 Доступ к планам
    .current-subscription = 💳 Текущая подписка
    .subscription-traffic-limit = 🌐 Лимит трафика
    .subscription-device-limit = 📱 Лимит устройств
    .subscription-expire-time = ⏳ Время истечения
    .subscription-squads = 🔗 Сквады
    .subscription-traffic-reset = 🔄 Сбросить трафик
    .subscription-devices = 🗒️ Список устройств
    .node-quota = 🔴 Сервер для 4G/LTE
    .node-quota-reset = 🔄 Сбросить счётчик
    .node-quota-restrict = 🚫 Ограничить доступ
    .node-quota-unrestrict = ✅ Снять ограничение
    .node-quota-test-notify = 📨 Тест уведомления
    .subscription-url = 📋 Скопировать ссылку
    .subscription-delete = ❌ Удалить
    .subscription-reissue = ♻️ Перевыпустить
    .message-preview = 👀 Предпросмотр
    .message-confirm = ✅ Отправить
    .referral-reset = 🔄 Сбросить реф. ссылку
    .sync = 🌀 Синхронизировать
    .sync-remnawave = 🌊 Использовать данные Remnawave
    .sync-remnashop = 🛍 Использовать данные Remnashop
    .give-subscription = 🎁 Выдать подписку
    .subscription-internal-squads = ⏺️ Внутренние сквады
    .subscription-external-squads = ⏹️ Внешний сквад

    .allowed-plan-choice = { $selected ->
    [1] 🔘
    *[0] ⚪
    } { $plan_name }

    .subscription-active-toggle = { $is_active ->
    [1] 🔴 Выключить
    *[0] 🟢 Включить
    }

    .transaction = { $status ->
    [PENDING] 🕓
    [COMPLETED] ✅
    [CANCELED] ❌
    [REFUNDED] 💸
    [FAILED] ⚠️
    *[OTHER] { $status }
    } { $created_at } · { gateway-type }

    .trial-toggle = { $is_trial_available ->
    [1] 🧪 Пробник: доступен
    *[0] 🧪 Пробник: не доступен
    }

    .block = { $is_blocked ->
    [1] 🔓 Разблокировать
    *[0] 🔒 Заблокировать
    }

# ============================================================
# ФРАГМЕНТЫ: ПЕРЕОПРЕДЕЛЕНИЯ СТАНДАРТНЫХ КЛЮЧЕЙ
# ============================================================

# frg-user переопределён: добавлен блок реферального статуса Rain (тиры)
# и убрано поле email (только ID, как в брендированной версии)
frg-user =
    <blockquote>
    • <b>ID</b>: <code>{ NUMBER($telegram_id, useGrouping: 0) }</code>
    • <b>Имя</b>: { $name }
    { $referral_tier ->
    [1] • <b>Статус</b>: ☁️ Облако
    [2] • <b>Статус</b>: 🌩️ Туча
    [3] • <b>Статус</b>: 🌧️ Дождь
    [4] • <b>Статус</b>: ⛈️ Шторм
    *[0] { "" }
    }
    { $show_personal_discount ->
    [1] • <b>Персональная скидка</b>: { $personal_discount }%
    *[0] { "" }
    }
    { $show_purchase_discount ->
    [1] • <b>Скидка на покупку</b>: { $purchase_discount }%
    *[0] { "" }
    }
    </blockquote>

# ============================================================
# СООБЩЕНИЯ: ПЕРЕОПРЕДЕЛЕНИЯ СТАНДАРТНЫХ КЛЮЧЕЙ
# ============================================================

# frg-subscription: явно определён здесь для надёжности (также есть в utils.ftl из assets.default)
frg-subscription =
    <blockquote>
    • <b>Лимит трафика</b>: { $traffic_limit }
    • <b>Лимит устройств</b>: { $device_limit }
    • <b>Осталось</b>: { $expire_time }
    </blockquote>

# msg-subscription-main переопределён: добавлен блок node-quota
# (upstream версия — просто однострочный текст "<b>💳 Подписка</b>")
msg-subscription-main =
    <b>💳 Подписка</b>

    { $has_current_subscription ->
    [1] { frg-subscription }
    *[0] { "" }
    }

    { $node_quota_enabled ->
    [1]
    <b>🔴 Сервер для 4G/LTE:</b>
    <blockquote>
    { $node_quota_is_restricted ->
    [1] • 🚫 Доступ ограничен до 1-го числа следующего месяца
    *[0]
    • <b>Использовано</b>: { $node_quota_used_gb } / { $node_quota_limit_gb } ГБ
    • <b>Свободно</b>: { $node_quota_free_gb } ГБ
    }
    </blockquote>
    *[0] { "" }
    }

# msg-menu-invite переопределён: Rain VPN брендинг + таблица тиров реферальной программы
msg-menu-invite =
    <b>🤝 Реферальная программа</b>

    Приглашайте пользователей по вашей уникальной ссылке и получайте { $reward_type ->
        [POINTS] <b>баллы</b> — обменивайте на дни доступа или подписку
        [EXTRA_DAYS] <b>бесплатные дни</b> к вашей текущей подписке
        *[OTHER] { $reward_type }
    }.

    <b>📊 Ваша статистика:</b>
    <blockquote>
    • Приглашено пользователей: { $referrals }
    • Оплат по вашей ссылке: { $payments }
    { $reward_type ->
    [POINTS] • Баллов на счёте: { $points }
    *[EXTRA_DAYS] { "" }
    }
    </blockquote>

    <b>🏆 Статус и персональная скидка:</b>
    <blockquote>
    За каждого приглашённого, кто оформит подписку, вы получаете постоянную скидку на все тарифы:

    • ☁️ Облако — <b>5%</b> (1 чел.)
    • 🌩️ Туча — <b>10%</b> (3 чел.)
    • 🌧️ Дождь — <b>15%</b> (5 чел.)
    • ⛈️ Шторм — <b>25%</b> (10 чел.)

    { $referral_tier ->
    [0] Ваш статус: пока не получен.
    [1] Ваш статус: ☁️ Облако — скидка <b>{ $personal_discount }%</b>
    [2] Ваш статус: 🌩️ Туча — скидка <b>{ $personal_discount }%</b>
    [3] Ваш статус: 🌧️ Дождь — скидка <b>{ $personal_discount }%</b>
    *[4] Ваш статус: ⛈️ Шторм — скидка <b>{ $personal_discount }%</b>
    }
    </blockquote>

# msg-menu-invite-about переопределён: Rain VPN брендинг
msg-menu-invite-about =
    <b>💡 Условия программы</b>

    <b>Условие начисления:</b>
    <blockquote>
    { $accrual_strategy ->
    [ON_FIRST_PAYMENT] Вознаграждение начисляется однократно — за первую оплату подписки приглашённым пользователем.
    [ON_EACH_PAYMENT] Вознаграждение начисляется за каждую оплату или продление подписки приглашённым пользователем.
    *[OTHER] { $accrual_strategy }
    }
    </blockquote>

    <b>Размер вознаграждения:</b>
    <blockquote>
    { $max_level ->
    [1] За приглашённых: { $reward_level_1 }
    *[MORE]
    { $identical_reward ->
    [0]
    • Уровень 1 (ваши приглашённые): { $reward_level_1 }
    • Уровень 2 (приглашённые ваших друзей): { $reward_level_2 }
    *[1]
    За все уровни: { $reward_level_1 }
    }
    }

    { $reward_strategy_type ->
    [AMOUNT] { $reward_type ->
        [POINTS] { "" }
        [EXTRA_DAYS] <i>Дополнительные дни начисляются к вашей текущей подписке.</i>
        *[OTHER] { $reward_type }
    }
    [PERCENT] { $reward_type ->
        [POINTS] <i>Процент рассчитывается от стоимости подписки приглашённого.</i>
        [EXTRA_DAYS] <i>Процент рассчитывается от длительности подписки приглашённого.</i>
        *[OTHER] { $reward_type }
    }
    *[OTHER] { $reward_strategy_type }
    }
    </blockquote>

# msg-menu-proxy: страница "Поделиться Mtproxy" (кастомная, нет в upstream)
msg-menu-proxy =
    📡 <b>Помоги другу войти в Telegram</b>

    Заблокирован Telegram? Скинь эту ссылку — нажмёт один раз и подключится, без VPN-приложений.

    • <b>Отправить в Telegram</b> — если у него уже есть доступ (через прокси или VPN)
    • <b>Другой мессенджер</b> — скопируй ссылку и отправь через любой другой рабочий мессенджер

# ============================================================
# СООБЩЕНИЯ: КАСТОМНЫЕ КЛЮЧИ (НЕ СУЩЕСТВУЮТ В UPSTREAM)
# ============================================================

# Окно администратора: просмотр квоты 4G/LTE конкретного пользователя
msg-user-node-quota =
    <b>🔴 Сервер для 4G/LTE</b>

    <blockquote>
    • <b>Нода</b>: 🇷🇺🔴 4G/LTE | Не для Wi-Fi
    • <b>Лимит</b>: { $node_quota_limit_gb } ГБ / мес
    • <b>Использовано</b>: { $node_quota_used_gb } ГБ ({ $node_quota_pct }%)
    • <b>Свободно</b>: { $node_quota_free_gb } ГБ
    • <b>Период</b>: с { $period_start }
    • <b>Статус</b>: { $is_restricted ->
    [1] 🚫 Ограничен
    *[0] ✅ Активен
    }
    { $restricted_at ->
    [0] { "" }
    *[HAS] • <b>Ограничен с</b>: { $restricted_at }
    }
    </blockquote>

# Диалог платного сброса трафика 4G/LTE (пользователь)
msg-subscription-traffic-reset-confirm =
    <b>🔴 Сброс трафика 4G/LTE</b>

    Сбросьте счётчик использованного трафика на сервере 4G/LTE.

    <b>Использовано:</b> { $tr_used_gb } из { $tr_limit_gb } ГБ ({ $tr_used_pct }%)
    <b>Свободно:</b> { $tr_free_gb } ГБ

    { $tr_show_warning ->
    [1]
    ⚠️ <b>У вас ещё остался неизрасходованный трафик.</b> Сброс счётчика выгоден только при исчерпании лимита. Платёж будет списан в любом случае.

    *[0] { "" }
    }<b>Стоимость:</b> { $price } ₽

    После успешной оплаты счётчик будет немедленно обнулён, и вы снова получите доступ к полному лимиту.

    { $tr_url_has ->
    [1] ✅ Платёж создан. Нажмите кнопку ниже для оплаты.
    *[0] Выберите способ оплаты:
    }

# ============================================================
# УВЕДОМЛЕНИЯ: КАСТОМНЫЕ КЛЮЧИ (НЕ СУЩЕСТВУЮТ В UPSTREAM)
# ============================================================

# Уведомления системы квоты трафика 4G/LTE
ntf-node-quota =
    .reset-purchased = ✅ <i>Счётчик трафика 4G/LTE успешно сброшен!</i>

    .reset-purchased-system =
        💳 <b>Платный сброс трафика 4G/LTE</b>

        Пользователь: <code>{ $telegram_id }</code> ({ $name }, @{ $username })
        Сумма: <b>{ $price } ₽</b>
        Сброшено трафика: <b>{ $used_gb } ГБ</b>
        Был ограничен: { $was_restricted ->
            [1] да
            *[0] нет
        }

    .reset-by-admin-system =
        🛠 <b>Сброс трафика 4G/LTE администратором</b>

        Администратор: <code>{ $admin_telegram_id }</code> ({ $admin_name })
        Пользователь: <code>{ $target_telegram_id }</code> ({ $target_name }, @{ $target_username })
        Сброшено трафика: <b>{ $used_gb } ГБ</b>
        Был ограничен: { $was_restricted ->
            [1] да
            *[0] нет
        }

    .warn =
        ⚠️ Вы использовали <b>{ $used_gb } ГБ</b> из <b>{ $limit_gb } ГБ</b> месячного лимита на сервере для 4G/LTE.

        При достижении 100% доступ к этому серверу будет ограничен до конца месяца.

    .limited =
        🚫 Ваш месячный лимит на сервере для 4G/LTE (<b>{ $limit_gb } ГБ</b>) исчерпан.

        Доступ к серверу будет восстановлен 1-го числа следующего месяца.{ $reset_price ->
            [0] { "" }
            *[other]  Вы также можете <b>сбросить счётчик досрочно</b> за { $reset_price } ₽ в разделе «Подписка».
        }

# ============================================================
# РЕКЛАМНЫЕ ССЫЛКИ: КНОПКИ (ОТСУТСТВУЮТ В UPSTREAM 0.8.0)
# ============================================================

btn-advertising =
    .create = ➕ Создать ссылку
    .toggle-active = { $is_active ->
    [1] 🔴 Деактивировать
    *[0] 🟢 Активировать
    }
    .edit-name = ✏️ Название
    .bonus-points = 🎯 Баллы: { $bonus_points }
    .bonus-days = 📅 Дней: { $bonus_days }
    .bonus-discount = 💸 Скидка: { $bonus_discount_pct }%
    .delete = 🗑 Удалить
    .delete-confirm = ✅ Подтвердить удаление
    .promo = ✉️ Promo-сообщение
    .promo-edit-text = ✏️ Изменить текст
    .promo-photo = { $promo_has_photo ->
    [1] 📷 Изменить фото
    *[0] 📷 Добавить фото
    }
    .promo-remove-photo = 🗑 Удалить фото
    .promo-add-button = ➕ Добавить кнопку
    .promo-use-ad-url = 🔗 Использовать ссылку бота
    .promo-preview = 👁 Отправить мне превью
    .promo-style-default = ⚪ Обычная
    .promo-style-primary = 🔵 Синяя
    .promo-style-success = 🟢 Зелёная
    .promo-style-danger = 🔴 Красная
    .analytics = 📊 Аналитика
    .analytics-period-7 = { $is_active_7 ->
    [1] ● 7 дней
    *[0] ○ 7 дней
    }
    .analytics-period-30 = { $is_active_30 ->
    [1] ● 30 дней
    *[0] ○ 30 дней
    }
    .analytics-period-0 = { $is_active_0 ->
    [1] ● Всё время
    *[0] ○ Всё время
    }
    .analytics-trend = 📈 Тренд кликов
    .analytics-funnel = 📊 Воронка
    .comparison = 📊 Сравнить
    .comparison-sort-revenue = { $is_sort_revenue ->
    [1] ● Выручка
    *[0] ○ Выручка
    }
    .comparison-sort-conversion = { $is_sort_conversion ->
    [1] ● Конверсия
    *[0] ○ Конверсия
    }
    .comparison-sort-clicks = { $is_sort_clicks ->
    [1] ● Клики
    *[0] ○ Клики
    }
    .comparison-chart = 📊 График

# ============================================================
# РЕКЛАМНЫЕ ССЫЛКИ: СООБЩЕНИЯ (ОТСУТСТВУЮТ В UPSTREAM 0.8.0)
# ============================================================

msg-advertising-list =
    🎯 <b>Рекламные ссылки</b>

    { $count ->
    [0] Ссылок пока нет. Создайте первую.
    *[other] Всего ссылок: <b>{ $count }</b>
    }

msg-advertising-view =
    🎯 <b>{ $name }</b>  { $is_active ->
    [1] ✅ Активна
    *[0] ❌ Неактивна
    }
    Код: <code>{ $code }</code>
    Ссылка: <code>{ $deep_link }</code>

    <b>Бонусы при переходе:</b>
    • Баллы: <b>{ $bonus_points }</b>
    • Дней: <b>{ $bonus_days }</b>
    • Скидка: <b>{ $bonus_discount_pct }%</b>

    <b>Аналитика:</b>
    • Переходов: <b>{ $clicks_count }</b>
    • Уник. пользователей: <b>{ $unique_clicks }</b>
    • Получили бонус: <b>{ $bonus_issued_count }</b>
    • Активировали пробный: <b>{ $trial_count }</b>
    • Оплатили: <b>{ $paid_count }</b>
    • Выручка: <b>{ $revenue_rub } ₽</b>

msg-advertising-create-name =
    ✏️ Введите название ссылки (для вашего удобства):

msg-advertising-create-code =
    🔗 Введите код ссылки (только буквы и цифры, без пробелов):

    <i>Название: { $create_name }</i>

msg-advertising-edit-name =
    ✏️ Введите новое название:

msg-advertising-edit-bonus-points =
    🎯 Введите количество баллов (0 — без бонуса):

msg-advertising-edit-bonus-days =
    📅 Введите количество дней (0 — без бонуса):

msg-advertising-edit-bonus-discount =
    💸 Введите размер скидки % от 0 до 100 (0 — без скидки):

msg-advertising-confirm-delete =
    ⚠️ Удалить ссылку <b>{ $delete_name }</b>?

    Вся аналитика будет потеряна.

msg-advertising-promo =
    ✉️ <b>Promo-сообщение</b> — { $name }
    Отправить: введите <code>@vpnrain_bot { $inline_query }</code> в любом чате

    <b>Фото:</b> { $promo_has_photo ->
    [1] ✅ Загружено
    *[0] ❌ Нет
    }
    <b>Текст:</b>
    { $promo_text_preview }

    <b>Кнопки:</b>
    { $promo_buttons_info }

msg-advertising-promo-edit-text =
    ✏️ Введите текст promo-сообщения (поддерживается HTML):

msg-advertising-promo-edit-photo =
    📷 Отправьте фото для promo-сообщения.

    { $promo_has_photo ->
    [1] <i>Текущее фото будет заменено.</i>
    *[0] { "" }
    }

msg-advertising-promo-button-label =
    ✏️ Введите текст кнопки (до 100 символов):

    <i>Можно использовать эмодзи, например: 🟢 Попробовать</i>

msg-advertising-promo-button-url =
    🔗 Введите URL для кнопки <b>{ $new_btn_label }</b>:

    <i>Должен начинаться с https://
    Или нажмите кнопку ниже, чтобы использовать ссылку бота.</i>

msg-advertising-promo-button-style =
    🎨 Выберите цвет кнопки <b>{ $new_btn_label }</b>:

msg-advertising-analytics =
    📊 <b>Аналитика — { $name }</b>

    { $period_days ->
    [0] Период: <b>Всё время</b>
    *[other] Период: <b>{ $period_days } дней</b>
    }

    • Уник. пользователей: <b>{ $unique_clicks }</b>
    • Получили бонус: <b>{ $bonus_issued_count }</b>
    • Активировали пробный: <b>{ $trial_count }</b>
    • Оплатили: <b>{ $paid_count }</b>
    • Выручка: <b>{ $revenue_rub } ₽</b>
    • Конверсия: <b>{ $conversion_pct }%</b>

msg-advertising-comparison =
    📊 <b>Сравнение кампаний</b>  ({ $count } ссылок)

    { $comparison_text }

# ============================================================
# РЕФЕРАЛЬНАЯ СИСТЕМА: СОБЫТИЯ
# Переопределён полностью, чтобы добавить атрибут .milestone
# ============================================================

event-referral =
    .attached =
    <b>🎉 Вы пригласили друга!</b>

    <blockquote>
    Пользователь <b>{ $name }</b> присоединился по вашей пригласительной ссылке! Чтобы получить награду, убедитесь, что он совершит покупку подписки.
    </blockquote>

    .reward =
    <b>💰 Вам начислена награда!</b>

    <blockquote>
    Пользователь <b>{ $name }</b> совершил платеж. Вы получили { $reward_type ->
    [POINTS] <b>{ $value } { $value ->
        [one] балл
        [few] балла
        *[more] баллов
        }</b>

    <i>Для использования баллов перейдите в раздел "Пригласить" в боте, чтобы узнать о доступных наградах и способах их использования.</i>
    [EXTRA_DAYS] <b>{ $value } доп. { $value ->
        [one] день
        [few] дня
        *[more] дней
        }</b> к вашей подписке!
    *[OTHER] <b>{ $value } { $reward_type }</b>
    }
    </blockquote>

    .reward-failed =
    <b>❌ Не получилось выдать награду!</b>

    <blockquote>
    Пользователь <b>{ $name }</b> совершил платеж, но мы не смогли начислить вам вознаграждение из-за того что <b>у вас нет купленной подписки</b>, к которой можно было бы добавить { $value } { $reward_type ->
    [POINTS] { $value ->
        [one] балл
        [few] балла
        *[more] баллов
        }
    [EXTRA_DAYS] доп. { $value ->
        [one] день
        [few] дня
        *[more] дней
        }
    *[OTHER] { $reward_type }
    }.

    <i>Купите подписку, чтобы получать бонусы за приглашенных друзей!</i>
    </blockquote>

    .milestone =
    <b>🏆 Новый уровень реферальной программы!</b>

    <blockquote>
    Вы достигли <b>{ $tier } уровня</b>!
    Оплативших рефералов: <b>{ $paid_referrals_count }</b>
    Персональная скидка: <b>{ $discount }%</b>
    </blockquote>

# Уведомления рекламных ссылок
ntf-ad =
    .bonus-received =
        🎁 <b>Вам начислен бонус за переход по рекламной ссылке!</b>
        { $bonus_points ->
        [0] { "" }
        *[other]
         • +{ $bonus_points } баллов
        }{ $bonus_days ->
        [0] { "" }
        *[other]
         • +{ $bonus_days } дней к подписке
        }{ $bonus_discount_pct ->
        [0] { "" }
        *[other]
         • Скидка { $bonus_discount_pct }% на следующую покупку
        }

    .code-invalid = ⚠️ <i>Рекламная ссылка не найдена или недоступна.</i>
