from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

import aiohttp

from src.application.dto.ad_link import AdLinkComparisonItemDto, AdLinkDailyClickDto, AdLinkStatsDto

QUICKCHART_URL = "https://quickchart.io/chart"

_COLORS = [
    "rgba(54, 162, 235, 0.85)",
    "rgba(75, 192, 192, 0.85)",
    "rgba(255, 206, 86, 0.85)",
    "rgba(255, 99, 132, 0.85)",
    "rgba(153, 102, 255, 0.85)",
    "rgba(255, 159, 64, 0.85)",
]


async def render_chart(config: dict, width: int = 700, height: int = 400) -> bytes:
    payload = {
        "chart": config,
        "width": width,
        "height": height,
        "backgroundColor": "white",
        "format": "png",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(QUICKCHART_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            return await resp.read()


def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m")


def build_daily_clicks_chart(name: str, days_data: list[AdLinkDailyClickDto]) -> dict:
    labels = [_fmt_date(d.day) for d in days_data]
    values = [d.unique_clicks for d in days_data]
    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Уник. пользователей",
                    "data": values,
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "backgroundColor": "rgba(54, 162, 235, 0.15)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 4,
                }
            ],
        },
        "options": {
            "title": {"display": True, "text": f"Тренд кликов: {name}", "fontSize": 16},
            "scales": {
                "yAxes": [{"ticks": {"beginAtZero": True, "precision": 0}}]
            },
            "legend": {"position": "bottom"},
        },
    }


def build_funnel_chart(name: str, stats: AdLinkStatsDto) -> dict:
    labels = ["Уник. пользователей", "Получили бонус", "Пробный период", "Оплатили"]
    values = [stats.unique_clicks, stats.bonus_issued_count, stats.trial_count, stats.paid_count]
    colors = ["rgba(54, 162, 235, 0.85)", "rgba(75, 192, 192, 0.85)",
              "rgba(255, 206, 86, 0.85)", "rgba(75, 192, 100, 0.85)"]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Пользователей",
                    "data": values,
                    "backgroundColor": colors,
                }
            ],
        },
        "options": {
            "title": {"display": True, "text": f"Воронка конверсии: {name}", "fontSize": 16},
            "legend": {"display": False},
            "scales": {
                "yAxes": [{"ticks": {"beginAtZero": True, "precision": 0}}]
            },
        },
    }


def build_comparison_chart(
    items: list[AdLinkComparisonItemDto],
    metric: str,
) -> dict:
    sorted_items = sorted(items, key=lambda x: _metric_value(x, metric), reverse=True)
    labels = [i.name[:20] for i in sorted_items]
    values = [float(_metric_value(i, metric)) for i in sorted_items]
    colors = [_COLORS[idx % len(_COLORS)] for idx in range(len(sorted_items))]

    metric_label = {
        "revenue": "Выручка, ₽",
        "conversion": "Конверсия, %",
        "clicks": "Уник. пользователей",
    }.get(metric, metric)

    return {
        "type": "horizontalBar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": metric_label,
                    "data": values,
                    "backgroundColor": colors,
                }
            ],
        },
        "options": {
            "title": {
                "display": True,
                "text": f"Сравнение кампаний — {metric_label}",
                "fontSize": 16,
            },
            "legend": {"display": False},
            "scales": {
                "xAxes": [{"ticks": {"beginAtZero": True}}]
            },
        },
    }


def _metric_value(item: AdLinkComparisonItemDto, metric: str) -> float | Decimal:
    if metric == "revenue":
        return item.revenue_rub
    if metric == "conversion":
        return item.conversion_pct
    return float(item.unique_clicks)


def mini_bar(value: float, max_value: float, width: int = 8) -> str:
    if max_value <= 0:
        return "░" * width
    filled = round(value / max_value * width)
    return "▓" * filled + "░" * (width - filled)
