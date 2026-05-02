#TODO: add custom

# `Banners`

The `banners` folder contains all banner images.

## Banner configuration

You can configure how banners are displayed in the bot using an environment variable:

* **`BOT_USE_BANNERS`**: Set to true to enable banners, or false to disable them.

## Locale support

The banner system supports **localized versions**. A banner corresponding to the user's **locale** will be loaded for each user. Available locales are defined by the `APP_LOCALES` environment variable.

### How it works:

When loading a banner, the system searches in the following order:

1. `banners/{user_locale}/{page}` — page-specific banner for the user’s locale
2. `banners/{user_locale}/default` — default banner for the user’s locale
3. `banners/{default_locale}/{page}` — page-specific banner for the default locale (`APP_DEFAULT_LOCALE`)
4. `banners/{default_locale}/default` — default banner for the default locale
5. `banners/default` — global fallback

Steps 3–4 handle the case where a user’s locale is not supported — the system falls back to the default locale’s banners before using the global default.

This means:
- To use **one image everywhere** — place a single `banners/default.jpg`.
- To use **one image per locale** — place `banners/{locale}/default.jpg` for each locale.
- To use **per-page images** — place `banners/{locale}/{page}.jpg` for each page and locale.

This ensures that even if a specific banner or locale is not found, some banner will always be displayed, preventing empty or missing images.

## Supported formats

The following file formats are supported, as defined in `/remnashop/src/core/enums.py` as `BannerFormat`:

* **JPG**
* **JPEG**
* **PNG**
* **GIF**
* **WEBP**

## Banner names

Banner filenames must correspond to the following predefined names, specified in `/remnashop/src/core/enums.py` as `BannerName`:

* **`DEFAULT`**: The default banner, used when a specific banner is not found.
* **`MENU`**: The main menu banner.
* **`DEVICES`**: The devices management banner.
* **`DASHBOARD`**: The dashboard banner.
* **`SUBSCRIPTION`**: The subscription banner.
* **`PROMOCODE`**: The promocode banner.
* **`REFERRAL`**: The referral banner.

## Example file structure

```
banners/
├── default.jpg       ← global default (used for all pages and locales as last fallback)
├── ru/
│   ├── default.jpg   ← default for all pages in ru locale
│   ├── menu.jpg      ← page-specific banner for ru locale
│   └── subscription.jpg
└── en/
    ├── default.jpg   ← default for all pages in en locale
    └── menu.jpg
```


# `Translations`

The `translations` folder contains all localization text files.

## Translation configuration

Supported locales are defined in environment variables:

* **`APP_LOCALES`**: A list of supported locales. A full list of available locales can be found in `remnashop/src/core/enums.py` as `Locale`.
* **`APP_DEFAULT_LOCALE`**: The default locale to be used if a user's language preference is not specified or not supported.


## Key naming convention

All translation keys must follow a unified structure:
```
{category}-{scope}-{entity}-{action-or-state}
```

## Components

| Part                | Description                   | Example                                                                            |
| ------------------- | ----------------------------- | ---------------------------------------------------------------------------------- |
| `{category}`        | Top-level type of text        | `btn`, `msg`, `ntf`                                                                |
| `{scope}`           | Logical group or subsystem    | `user`, `plan`, `broadcast`, `gateway`, `subscription`, `access`, `error`, `event` |
| `{entity}`          | Specific object or sub-entity | `content`, `payment`, `link`, `node`                                               |
| `{action-or-state}` | Action or state, in lowercase | `created`, `deleted`, `empty`, `invalid`, `failed`, `not-found`                    |

## Naming rules

1. Use lowercase with hyphens (-) — no underscores or spaces.
2. Follow the order:
    ```
    category → scope → entity → action/state
    ```
    - ✅ ntf-broadcast-content-empty
    - ✅ btn-user-create
    - ✅ msg-plan-deleted-success

    - ❌ ntf-content-empty-broadcast
    - ❌ btn-create-user
    - ❌ msg-plan-success-deleted
3. Actions — past tense verbs (created, updated, deleted, canceled, failed).
4. States — adjectives (empty, invalid, not-found, expired, not-available).
5. Limit to 5 segments maximum.

## Examples keys

| Purpose                               | Key                               |
| ------------------------------------- | --------------------------------- |
| Notification: user expired            | `ntf-user-expired`                |
| Notification: broadcast empty content | `ntf-broadcast-content-empty`     |
| Button: confirm deletion              | `btn-plan-confirm-delete`         |
| Message: plan created successfully    | `msg-plan-created-success`        |
| Notification: gateway test failed     | `ntf-gateway-test-payment-failed` |


# `QR Code Logo`

You can customize the appearance of the generated invitation QR code by adding your logo to the center of the code.

* **Path:** `assets/logo.png`
* **Purpose:** If this file exists, the system will use it as a logo, overlaying it in the center of the generated QR code image for branding purposes.
* **Format:** The logo must be a `PNG` file, preferably with a transparent background.
