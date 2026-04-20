event-error =
    .general =
    #ErrorEvent

    <b>🔅 Событие: Произошла ошибка!</b>

    { frg-build-info }
    
    { $telegram_id -> 
    [0] { space }
    *[HAS]
    { hdr-user }
    { frg-user-info }
    }

    { hdr-error }
    <blockquote>
    { $error }
    </blockquote>

    .remnawave-version =
    #RemnawaveVersionWarningEvent

    <b>⚠️ Событие: Возможная несовместимость с Remnawave!</b>

    <blockquote>
    Версия панели <b>{ $panel_version }</b> выше протестированной версии <b>{ $max_version }</b>. Некоторые функции бота могут работать некорректно.
    </blockquote>

    { frg-build-info }
    
    .remnawave =
    #RemnawaveErrorEvent

    <b>🔅 Событие: Ошибка при подключении к Remnawave!</b>

    <blockquote>
    Без активного подключения корректная работа бота невозможна!
    </blockquote>

    { frg-build-info }

    { hdr-error }
    <blockquote>
    { $error }
    </blockquote>

    .webhook =
    #ErrorEvent

    <b>🔅 Событие: Зафиксирована ошибка вебхука!</b>

    { hdr-error }
    <blockquote>
    { $error }
    </blockquote>


event-bot =
    .startup =
    #BotStartupEvent

    <b>🔅 Событие: Бот запущен!</b>

    { frg-build-info }

    <b>🔓 Доступность:</b>
    <blockquote>
    • <b>Режим</b>: { access-mode }
    • <b>Платежи</b>: { $payments_allowed ->
    [0] запрещены
    *[1] разрешены
    }
    • <b>Регистрация</b>: { $registration_allowed ->
    [0] запрещена
    *[1] разрешена
    }
    </blockquote>

    .shutdown =
    #BotShutdownEvent

    <b>🔅 Событие: Бот остановлен!</b>

    { frg-build-info }

    <blockquote>
    • <b>Аптайм</b>: { $uptime }
    </blockquote>

    .update =
    #BotUpdateEvent

    <b>🔅 Событие: Обнаружено обновление Rain VPN!</b>

    <b>📑 Версии:</b>
    <blockquote>
    • <b>Текущая</b>: { $local_version }
    • <b>Последняя</b>: { $remote_version }
    </blockquote>


event-user =
    .registered =
    #UserRegisteredEvent

    <b>🔅 Событие: Новый пользователь!</b>

    { hdr-user }
    { frg-user-info }

    { $referrer_telegram_id ->
    [0] { empty }
    *[HAS]
    <b>🤝 Пригласитель:</b>
    <blockquote>
    • <b>ID</b>: <code>{ NUMBER($referrer_telegram_id, useGrouping: 0) }</code>
    • <b>Имя</b>: { $referrer_name } { $referrer_username -> 
        [0] { empty }
        *[HAS] (<a href="tg://user?id={ $referrer_telegram_id }">@{ $referrer_username }</a>)
    }
    </blockquote>
    }

    .first-connected =
    #UserFirstConnectionEvent

    <b>🔅 Событие: Первое подключение пользователя!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-subscription }
    { frg-subscription-details }

    .device-added =
    #UserDeviceAddedEvent

    <b>🔅 Событие: Пользователь добавил новое устройство!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-hwid }
    { frg-user-hwid }

    .device-deleted =
    #UserDeviceDeletedEvent

    <b>🔅 Событие: Пользователь удалил устройство!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-hwid }
    { frg-user-hwid }
    

event-subscription =
    .trial =
    #SubscriptionTrialEvent

    <b>🔅 Событие: Получение пробной подписки!</b>

    { hdr-user }
    { frg-user-info }
    
    { hdr-plan }
    { frg-plan-snapshot }
    
    .new =
    #SubscriptionNewEvent

    <b>🔅 Событие: Покупка подписки!</b>

    { hdr-payment }
    { frg-payment-info }

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot }

    .renew =
    #SubscriptionRenewEvent

    <b>🔅 Событие: Продление подписки!</b>
    
    { hdr-payment }
    { frg-payment-info }

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot }

    .change =
    #SubscriptionChangeEvent

    <b>🔅 Событие: Изменение подписки!</b>

    { hdr-payment }
    { frg-payment-info }

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot-comparison }

    .expiring =
    { $value ->
    [1]
    { $is_trial ->
    [0]
    ⚠️ <b>Подписка истекает завтра!</b>

    Продлите сейчас — иначе VPN перестанет работать.
    *[1]
    ⚠️ <b>Пробный период заканчивается завтра!</b>

    Оформите подписку, чтобы не потерять доступ к сервису.
    }
    [2]
    { $is_trial ->
    [0]
    ⏰ <b>Подписка заканчивается послезавтра.</b>

    Продлите заранее, чтобы не потерять доступ.
    *[1]
    ⏰ <b>Пробный период заканчивается послезавтра.</b>

    Оформите подписку заранее, чтобы не прерывать доступ.
    }
    *[other]
    { $is_trial ->
    [0]
    📅 <b>Напоминание: подписка закончится через { unit-day }.</b>

    Продлите заранее, чтобы не терять доступ к сервису.
    *[1]
    📅 <b>Напоминание: пробный период закончится через { unit-day }.</b>

    Оформите подписку, чтобы продолжить пользоваться VPN.
    }
    }

    .expired =
    { $is_trial ->
    [0]
    ⛔ <b>Подписка истекла — VPN не работает.</b>

    Продлите подписку, чтобы восстановить доступ.
    *[1]
    ⛔ <b>Пробный период завершён — VPN не работает.</b>

    Оформите подписку, чтобы продолжить пользоваться сервисом.
    }

    .expired-ago =
    { $is_trial ->
    [0]
    ⛔ <b>Подписка истекла { unit-day } назад.</b>

    VPN по-прежнему не работает. Оформите продление, когда будете готовы.
    *[1]
    ⛔ <b>Пробный период закончился { unit-day } назад.</b>

    Оформите подписку в любой момент — доступ восстановится сразу.
    }

    .limited =
    { $is_trial ->
    [0]
    ⛔ <b>Трафик исчерпан — VPN приостановлен.</b>

    { $traffic_strategy ->
    [NO_RESET] Продлите подписку, чтобы сбросить счётчик и продолжить работу.
    *[RESET] Трафик восстановится через { $reset_time }. Или продлите подписку, чтобы сбросить прямо сейчас.
    }
    *[1]
    ⛔ <b>Трафик пробного периода исчерпан.</b>

    { $traffic_strategy ->
    [NO_RESET] Оформите подписку, чтобы продолжить пользоваться сервисом.
    *[RESET] Трафик восстановится через { $reset_time }. Оформите подписку для неограниченного доступа.
    }
    }

    .revoked =
    #SubscriptionRevokedEvent

    <b>🔅 Событие: Пользователь перевыпустил подписку!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-subscription }
    { frg-subscription-details }


event-node =
    .connection-lost =
    #NodeConnectionLostEvent
    
    <b>🔅 Событие: Соединение с узлом потеряно!</b>

    { hdr-node }
    { frg-node-info }

    .connection-restored =
    #NodeConnectionRestoredEvent

    <b>🔅 Событие: Cоединение с узлом восстановлено!</b>

    { hdr-node }
    { frg-node-info }

    .traffic-reached =
    #NodeTrafficReachedEvent

    <b>🔅 Событие: Узел достиг порога лимита трафика!</b>

    { hdr-node }
    { frg-node-info }


event-referral =
    .attached =
    <b>🤝 Новый реферал</b>

    <blockquote>
    Пользователь <b>{ $name }</b> зарегистрировался по вашей реферальной ссылке. Вознаграждение будет начислено после совершения первой оплаты.
    </blockquote>

    .reward =
    <b>✅ Начислено вознаграждение</b>

    <blockquote>
    Пользователь <b>{ $name }</b> совершил оплату. Вам начислено: <b>{ $value } { $reward_type ->
    [POINTS] { $value ->
        [one] балл
        [few] балла
        *[more] баллов
        }

    <i>Перейдите в раздел «Пригласить», чтобы узнать о доступных наградах и способах их использования.</i>
    [EXTRA_DAYS] доп. { $value ->
        [one] день
        [few] дня
        *[more] дней
        } </b> к подписке.
    *[OTHER] { $reward_type }
    }
    </blockquote>

    .reward-failed =
    <b>⚠️ Не удалось начислить вознаграждение</b>

    <blockquote>
    Пользователь <b>{ $name }</b> совершил оплату, однако начисление невозможно: <b>у вас нет активной подписки</b>, к которой можно добавить { $value } { $reward_type ->
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

    <i>Оформите подписку, чтобы получать вознаграждения за приглашённых пользователей.</i>
    </blockquote>

event-remnashop-welcome =
    <b>🌧️ Rain VPN v{ $version }</b>

    Добро пожаловать в панель управления Rain VPN! Бот успешно запущен и готов к работе.

    🚀 <i>Настройте платёжные системы и планы в разделе «Панель управления», чтобы начать принимать клиентов.</i>