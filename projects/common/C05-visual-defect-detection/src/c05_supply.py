"""Ingredient traceability and supply insights for C05.

A meal is only as good as what went into it. When a tray looks wrong or
children fall ill, the first questions are: which ingredient lots were used,
where did they come from, how long were they on the road, how warm were they
on arrival, and what did they cost. This module records every delivered lot
and answers those questions for any kitchen and meal date.

Design rules:

1. Deterministic checks first. Arrival temperature, transit time, use-by date,
   stock cover, price against a reference and delivery punctuality are plain
   comparisons that cite the lots behind them. They work with no model.
2. Gemini explains and prioritises. It turns the checks into a short brief with
   actions, may only cite lots and suppliers that exist, and never declares
   food safe. If the model is unavailable the deterministic insights stand.
3. Food safety outranks cost. Insights are ordered safety → stock → cost →
   logistics, and the cheapest supplier is never recommended on price alone.

The reference prices and the demo data are synthetic. In production the
reference would come from a public price feed such as Bapanas' Panel Harga
Pangan, and suppliers from the kitchen's purchasing records.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from fastapi import HTTPException, Request

import c05_claims

WIB = timezone(timedelta(hours=7))
KITCHENS = {'KITCHEN-A', 'KITCHEN-B'}
WINDOW_DAYS = 7
CHILLED_MAX_C = 5.0
LATE_GRACE_MIN = 30
PRICE_HIGH = 0.15   # >15 % above reference
PRICE_LOW = 0.20    # >20 % below reference: check grade and handling
PRICE_RISE = 0.10   # >10 % rise across the window
LOW_COVER_DAYS = 1.5
LOCAL_KM = 50

# category, unit, whether it must travel chilled, transit limit in minutes
# (None for shelf-stable goods), the synthetic reference price per unit, and
# whether it is kept in stock (fresh items are bought for the day and used up).
INGREDIENTS = {
    'rice': {'label': 'Rice', 'category': 'carbohydrate', 'unit': 'kg', 'chilled': False, 'max_transit': None, 'ref': 14000, 'stocked': True},
    'chicken': {'label': 'Chicken', 'category': 'protein', 'unit': 'kg', 'chilled': True, 'max_transit': 240, 'ref': 38000},
    'fish': {'label': 'Fish', 'category': 'protein', 'unit': 'kg', 'chilled': True, 'max_transit': 240, 'ref': 42000},
    'eggs': {'label': 'Eggs', 'category': 'protein', 'unit': 'kg', 'chilled': False, 'max_transit': 480, 'ref': 29000},
    'tempeh': {'label': 'Tempeh', 'category': 'protein', 'unit': 'kg', 'chilled': False, 'max_transit': 180, 'ref': 16000},
    'spinach': {'label': 'Spinach', 'category': 'vegetable', 'unit': 'kg', 'chilled': False, 'max_transit': 360, 'ref': 12000},
    'carrot': {'label': 'Carrot', 'category': 'vegetable', 'unit': 'kg', 'chilled': False, 'max_transit': 720, 'ref': 14000},
    'cabbage': {'label': 'Cabbage', 'category': 'vegetable', 'unit': 'kg', 'chilled': False, 'max_transit': 720, 'ref': 9000},
    'banana': {'label': 'Banana', 'category': 'fruit', 'unit': 'kg', 'chilled': False, 'max_transit': 720, 'ref': 15000},
    'cooking_oil': {'label': 'Cooking oil', 'category': 'other', 'unit': 'L', 'chilled': False, 'max_transit': None, 'ref': 18000, 'stocked': True},
}

CATEGORY_ORDER = {'food_safety': 0, 'stock': 1, 'cost': 2, 'logistics': 3, 'supplier': 4}
SEVERITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}


class SupplyInvalid(ValueError):
    pass


# --------------------------------------------------------------------- helpers

def _dt(value, field) -> datetime:
    if not isinstance(value, str) or not value:
        raise SupplyInvalid(f'{field} is required')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise SupplyInvalid(f'{field} must be an ISO date-time') from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=WIB)


def _day(value: str) -> date:
    return _dt(value, 'date').astimezone(WIB).date()


def idr(value: float) -> str:
    return 'Rp' + f'{value:,.0f}'.replace(',', '.')


def _pct(value: float) -> int:
    return round(value * 100)


def transit_minutes(lot: dict) -> int:
    return round((_dt(lot['received_at'], 'received_at') - _dt(lot['dispatched_at'], 'dispatched_at')).total_seconds() / 60)


def _used(lot: dict) -> float:
    return sum(u['qty'] for u in lot.get('used_in', []))


def normalize_lot(payload: dict, suppliers: dict[str, dict]) -> dict:
    """Validate a delivery recorded at the kitchen door."""
    kitchen = payload.get('kitchen_id')
    if kitchen not in KITCHENS:
        raise SupplyInvalid('Unknown kitchen')
    ingredient = payload.get('ingredient')
    if ingredient not in INGREDIENTS:
        raise SupplyInvalid('Unknown ingredient')
    supplier_id = payload.get('supplier_id')
    if supplier_id not in suppliers:
        raise SupplyInvalid('Unknown supplier')
    try:
        qty = float(payload.get('quantity'))
        price = float(payload.get('unit_price'))
    except (TypeError, ValueError):
        raise SupplyInvalid('quantity and unit_price must be numbers') from None
    if not 0 < qty <= 10000:
        raise SupplyInvalid('quantity must be between 0 and 10000')
    if not 0 < price <= 10_000_000:
        raise SupplyInvalid('unit_price must be positive')
    dispatched = _dt(payload.get('dispatched_at'), 'dispatched_at')
    received = _dt(payload.get('received_at'), 'received_at')
    if dispatched > received:
        raise SupplyInvalid('dispatched_at must be before received_at')
    if (received - dispatched) > timedelta(days=3):
        raise SupplyInvalid('Transit longer than 3 days; check the times')
    temp = payload.get('arrival_temp_c')
    if temp in ('', None):
        temp = None
    else:
        try:
            temp = float(temp)
        except (TypeError, ValueError):
            raise SupplyInvalid('arrival_temp_c must be a number') from None
        if not -30 <= temp <= 60:
            raise SupplyInvalid('arrival_temp_c is out of range')
    if INGREDIENTS[ingredient]['chilled'] and temp is None:
        raise SupplyInvalid(f"{INGREDIENTS[ingredient]['label']} must travel chilled; record the arrival temperature")
    status = payload.get('receiving_status', 'ACCEPTED')
    if status not in {'ACCEPTED', 'REJECTED'}:
        raise SupplyInvalid('receiving_status must be ACCEPTED or REJECTED')
    use_by = payload.get('use_by')
    try:
        use_by = date.fromisoformat(str(use_by)).isoformat()
    except ValueError:
        raise SupplyInvalid('use_by must be a date (YYYY-MM-DD)') from None
    promised = payload.get('promised_at') or None
    if promised:
        promised = _dt(promised, 'promised_at').isoformat()
    return {
        'lot_id': payload.get('lot_id') or f'LOT-{uuid.uuid4().hex[:8].upper()}',
        'kitchen_id': kitchen, 'ingredient': ingredient, 'supplier_id': supplier_id,
        'quantity': qty, 'unit': INGREDIENTS[ingredient]['unit'], 'unit_price': price,
        'dispatched_at': dispatched.isoformat(), 'received_at': received.isoformat(), 'promised_at': promised,
        'arrival_temp_c': temp, 'use_by': use_by, 'receiving_status': status,
        'receiving_note': str(payload.get('receiving_note') or '')[:300],
        'used_in': list(payload.get('used_in') or []),
    }


# ------------------------------------------------------------------- checking

def lot_flags(lot: dict, supplier: dict, today: date) -> list[dict]:
    """Deterministic checks for one lot. Each flag says why and what to do."""
    spec = INGREDIENTS[lot['ingredient']]
    name = spec['label']
    flags: list[dict] = []
    used_dates = sorted({u['meal_date'] for u in lot.get('used_in', [])})
    stock = round(lot['quantity'] - _used(lot), 1) if lot['receiving_status'] == 'ACCEPTED' else 0
    minutes = transit_minutes(lot)

    def flag(code, category, severity, title, detail, action):
        flags.append({'code': code, 'category': category, 'severity': severity, 'title': title,
                      'detail': detail, 'action': action})

    served = f" Used in meals on {', '.join(used_dates)}." if used_dates else ''
    if lot['receiving_status'] == 'REJECTED' and used_dates:
        flag('REJECTED_BUT_USED', 'food_safety', 'high', f'A rejected {name.lower()} lot was used in meals',
             f"Lot {lot['lot_id']} was rejected at receiving but appears in meal records.{served}",
             'Stop using it now and review the records with the supervisor.')
    if spec['chilled'] and lot['arrival_temp_c'] is not None and lot['arrival_temp_c'] > CHILLED_MAX_C:
        flag('TEMP_ABOVE_LIMIT', 'food_safety', 'high',
             f"{name} arrived at {lot['arrival_temp_c']:g}°C (limit {CHILLED_MAX_C:g}°C)",
             f"Lot {lot['lot_id']} from {supplier['name']}, {supplier['distance_km']} km away.{served}",
             'Hold any remaining stock, ask the supplier for cold-chain records, and check meals made from this lot.')
    if spec['chilled'] and not supplier.get('cold_chain'):
        flag('NO_COLD_CHAIN', 'food_safety', 'medium', f"{supplier['name']} ships {name.lower()} without cold transport",
             f"Lot {lot['lot_id']} travelled {minutes // 60} h {minutes % 60} min unchilled.",
             'Require chilled transport, or move this item to a certified supplier with a cold chain.')
    if spec['max_transit'] and minutes > spec['max_transit']:
        flag('LONG_TRANSIT', 'logistics', 'high' if spec['chilled'] else 'medium',
             f"{name} spent {minutes / 60:.1f} h on the road (limit {spec['max_transit'] / 60:g} h)",
             f"Lot {lot['lot_id']} from {supplier['location']} ({supplier['distance_km']} km).",
             'Source closer, or agree an earlier dispatch with chilled transport.')
    use_by = date.fromisoformat(lot['use_by'])
    if stock > 0 and use_by < today:
        flag('EXPIRED_IN_STOCK', 'food_safety', 'high', f"{stock:g} {lot['unit']} of {name.lower()} is past its use-by date",
             f"Lot {lot['lot_id']}, use by {lot['use_by']}.", 'Do not cook it. Discard and record the waste.')
    elif stock > 0 and use_by <= today + timedelta(days=1):
        flag('NEAR_EXPIRY', 'stock', 'medium', f"{stock:g} {lot['unit']} of {name.lower()} must be used by {lot['use_by']}",
             f"Lot {lot['lot_id']} from {supplier['name']}.", 'Use it first in the next menu, or record it as waste.')
    gap = lot['unit_price'] / spec['ref'] - 1
    if lot['receiving_status'] == 'ACCEPTED' and gap > PRICE_HIGH:
        extra = (lot['unit_price'] - spec['ref']) * lot['quantity']
        flag('PRICE_ABOVE_REFERENCE', 'cost', 'medium', f"{name} costs {_pct(gap)}% above the reference price",
             f"{idr(lot['unit_price'])}/{lot['unit']} vs reference {idr(spec['ref'])}/{lot['unit']} on lot "
             f"{lot['lot_id']}; {idr(extra)} extra on this delivery.",
             'Ask another supplier for a quote or renegotiate before the next order.')
    elif lot['receiving_status'] == 'ACCEPTED' and gap < -PRICE_LOW:
        flag('PRICE_BELOW_REFERENCE', 'food_safety', 'medium', f"{name} is {_pct(-gap)}% cheaper than the reference price",
             f"{idr(lot['unit_price'])}/{lot['unit']} vs reference {idr(spec['ref'])}/{lot['unit']} on lot {lot['lot_id']}.",
             'Unusually cheap stock can mean a lower grade or poor handling. Check grade and origin at receiving.')
    if lot.get('promised_at'):
        late = round((_dt(lot['received_at'], 'received_at') - _dt(lot['promised_at'], 'promised_at')).total_seconds() / 60)
        if late > LATE_GRACE_MIN:
            flag('LATE_DELIVERY', 'logistics', 'low', f"{supplier['name']} delivered {late} min late",
                 f"Lot {lot['lot_id']} ({name.lower()}).", 'Late deliveries cut prep time. Agree a delivery window.')
    return flags


def _in_window(lot: dict, today: date) -> bool:
    return today - timedelta(days=WINDOW_DAYS - 1) <= _day(lot['received_at']) <= today


def analyze(kitchen_id: str, lots: list[dict], suppliers: dict[str, dict], batches: list[dict], today: date) -> dict:
    """KPIs, ranked insights, supplier scorecard and stock cover for one kitchen."""
    mine = [l for l in lots if l['kitchen_id'] == kitchen_id]
    recent = [l for l in mine if _in_window(l, today)]
    accepted = [l for l in recent if l['receiving_status'] == 'ACCEPTED']
    my_batches = [b for b in batches if b['kitchen_id'] == kitchen_id
                  and today - timedelta(days=WINDOW_DAYS - 1) <= date.fromisoformat(b['meal_date']) <= today]
    portions = sum(b['portions'] for b in my_batches)

    insights: list[dict] = []
    lot_view = []
    for lot in sorted(mine, key=lambda l: l['received_at'], reverse=True):
        sup = suppliers[lot['supplier_id']]
        flags = lot_flags(lot, sup, today)
        for f in flags:
            insights.append({**f, 'lot_ids': [lot['lot_id']], 'supplier_ids': [lot['supplier_id']],
                             'meal_dates': sorted({u['meal_date'] for u in lot.get('used_in', [])})})
        if _in_window(lot, today) or (lot['quantity'] - _used(lot) > 0 and lot['receiving_status'] == 'ACCEPTED'):
            lot_view.append(_lot_row(lot, sup, flags))

    # Stock cover per ingredient: what is on the shelf vs average daily use.
    stock = []
    usage: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for lot in mine:
        for u in lot.get('used_in', []):
            usage[lot['ingredient']][u['meal_date']] += u['qty']
    for ing in sorted({l['ingredient'] for l in mine}):
        on_hand = [l for l in mine if l['ingredient'] == ing and l['receiving_status'] == 'ACCEPTED'
                   and l['quantity'] - _used(l) > 0 and date.fromisoformat(l['use_by']) >= today]
        qty = round(sum(l['quantity'] - _used(l) for l in on_hand), 1)
        days = sorted(usage[ing])[-3:]
        daily = round(sum(usage[ing][d] for d in days) / len(days), 1) if days else 0
        stocked = INGREDIENTS[ing].get('stocked', False)
        cover = round(qty / daily, 1) if daily and stocked else None
        value = sum((l['quantity'] - _used(l)) * l['unit_price'] for l in on_hand)
        row = {'ingredient': ing, 'label': INGREDIENTS[ing]['label'], 'unit': INGREDIENTS[ing]['unit'],
               'on_hand': qty, 'daily_use': daily, 'days_cover': cover, 'value_idr': round(value),
               'fresh_daily': not stocked}
        stock.append(row)
        if cover is not None and cover < LOW_COVER_DAYS:
            insights.append({'code': 'LOW_STOCK', 'category': 'stock', 'severity': 'high' if cover < 1 else 'medium',
                             'title': f"{row['label']}: about {cover:g} day(s) of stock left",
                             'detail': f"{qty:g} {row['unit']} on hand, about {daily:g} {row['unit']} used per day.",
                             'action': 'Reorder today so the next menu is not cut short.',
                             'lot_ids': [l['lot_id'] for l in on_hand],
                             'supplier_ids': sorted({l['supplier_id'] for l in on_hand}), 'meal_dates': []})

    # Price trend per ingredient across the window.
    by_ing: dict[str, list[dict]] = defaultdict(list)
    for lot in sorted(accepted, key=lambda l: l['received_at']):
        by_ing[lot['ingredient']].append(lot)
    trends = []
    for ing, rows in sorted(by_ing.items()):
        first, last = rows[0], rows[-1]
        change = last['unit_price'] / first['unit_price'] - 1
        trends.append({'ingredient': ing, 'label': INGREDIENTS[ing]['label'], 'unit': INGREDIENTS[ing]['unit'],
                       'reference': INGREDIENTS[ing]['ref'], 'latest': last['unit_price'],
                       'points': [{'date': _day(r['received_at']).isoformat(), 'price': r['unit_price']} for r in rows],
                       'change_pct': _pct(change)})
        if len(rows) > 1 and change > PRICE_RISE:
            span = (_day(last['received_at']) - _day(first['received_at'])).days
            insights.append({'code': 'PRICE_RISING', 'category': 'cost', 'severity': 'medium',
                             'title': f"{INGREDIENTS[ing]['label']} price up {_pct(change)}% in {span} days",
                             'detail': f"{idr(first['unit_price'])} → {idr(last['unit_price'])} per {last['unit']}.",
                             'action': 'Lock a price with the supplier, compare quotes, or plan a menu substitute.',
                             'lot_ids': [r['lot_id'] for r in rows],
                             'supplier_ids': sorted({r['supplier_id'] for r in rows}), 'meal_dates': []})

    # Supplier scorecard.
    scorecard = []
    for sid in sorted({l['supplier_id'] for l in recent}):
        sup = suppliers[sid]
        rows = [l for l in recent if l['supplier_id'] == sid]
        promised = [l for l in rows if l.get('promised_at')]
        on_time = [l for l in promised if (_dt(l['received_at'], 'r') - _dt(l['promised_at'], 'p')) <= timedelta(minutes=LATE_GRACE_MIN)]
        temps = [l for l in rows if INGREDIENTS[l['ingredient']]['chilled'] and (l['arrival_temp_c'] or 0) > CHILLED_MAX_C]
        scorecard.append({
            'supplier_id': sid, 'name': sup['name'], 'type': sup['type'], 'location': sup['location'],
            'distance_km': sup['distance_km'], 'cold_chain': sup['cold_chain'], 'certifications': sup['certifications'],
            'ingredients': sorted({INGREDIENTS[l['ingredient']]['label'] for l in rows}),
            'lots': len(rows), 'rejected': sum(1 for l in rows if l['receiving_status'] == 'REJECTED'),
            'spend_idr': round(sum(l['quantity'] * l['unit_price'] for l in rows if l['receiving_status'] == 'ACCEPTED')),
            'avg_transit_min': round(sum(transit_minutes(l) for l in rows) / len(rows)),
            'on_time_pct': _pct(len(on_time) / len(promised)) if promised else None,
            'temp_breaches': len(temps),
            'price_index': round(100 * sum(l['unit_price'] / INGREDIENTS[l['ingredient']]['ref'] for l in rows) / len(rows)),
        })

    spend = sum(l['quantity'] * l['unit_price'] for l in accepted)
    used_cost = sum(u['qty'] * l['unit_price'] for l in mine for u in l.get('used_in', [])
                    if today - timedelta(days=WINDOW_DAYS - 1) <= date.fromisoformat(u['meal_date']) <= today)
    local_spend = sum(l['quantity'] * l['unit_price'] for l in accepted if suppliers[l['supplier_id']]['distance_km'] <= LOCAL_KM)
    perishable = [l for l in recent if INGREDIENTS[l['ingredient']]['max_transit']]
    promised = [l for l in recent if l.get('promised_at')]
    kpis = {
        'window_days': WINDOW_DAYS,
        'lots': len(recent), 'suppliers': len(scorecard), 'portions': portions,
        'spend_idr': round(spend),
        'cost_per_portion_idr': round(used_cost / portions) if portions else None,
        'avg_distance_km': round(sum(suppliers[l['supplier_id']]['distance_km'] * l['quantity'] * l['unit_price']
                                     for l in accepted) / spend) if spend else None,
        'local_share_pct': _pct(local_spend / spend) if spend else None,
        'avg_perishable_transit_min': round(sum(transit_minutes(l) for l in perishable) / len(perishable)) if perishable else None,
        'on_time_pct': _pct(sum(1 for l in promised if (_dt(l['received_at'], 'r') - _dt(l['promised_at'], 'p'))
                                <= timedelta(minutes=LATE_GRACE_MIN)) / len(promised)) if promised else None,
        'stock_value_idr': sum(s['value_idr'] for s in stock),
        'rejected_lots': sum(1 for l in recent if l['receiving_status'] == 'REJECTED'),
    }
    # The same finding on several lots (e.g. every fish delivery runs long) is one insight citing all of them.
    merged: dict[tuple, dict] = {}
    for ins in insights:
        key = (ins['code'], ins['title'])
        if key in merged:
            m = merged[key]
            m['lot_ids'] = sorted(set(m['lot_ids']) | set(ins['lot_ids']))
            m['supplier_ids'] = sorted(set(m['supplier_ids']) | set(ins['supplier_ids']))
            m['meal_dates'] = sorted(set(m['meal_dates']) | set(ins['meal_dates']))
            m['detail'] = f"{len(m['lot_ids'])} lots affected, latest: {ins['detail']}"
        else:
            merged[key] = dict(ins)
    insights = sorted(merged.values(), key=lambda i: (SEVERITY_ORDER[i['severity']], CATEGORY_ORDER[i['category']], i['title']))
    for n, ins in enumerate(insights, start=1):
        ins['insight_id'] = f'INS-{n:02d}'
    return {'kitchen_id': kitchen_id, 'as_of': today.isoformat(), 'kpis': kpis, 'insights': insights,
            'suppliers': scorecard, 'stock': stock, 'price_trends': trends, 'lots': lot_view,
            'reference_note': 'Reference prices and demo records are synthetic. Production would use a public price '
                              'feed (e.g. Bapanas Panel Harga Pangan) and the kitchen\'s purchasing records.'}


def _lot_row(lot: dict, sup: dict, flags: list[dict]) -> dict:
    spec = INGREDIENTS[lot['ingredient']]
    return {**{k: lot[k] for k in ('lot_id', 'kitchen_id', 'ingredient', 'quantity', 'unit', 'unit_price',
                                   'dispatched_at', 'received_at', 'promised_at', 'arrival_temp_c', 'use_by',
                                   'receiving_status', 'receiving_note', 'used_in')},
            'label': spec['label'], 'category': spec['category'], 'chilled': spec['chilled'],
            'reference_price': spec['ref'], 'transit_min': transit_minutes(lot),
            'stock_remaining': round(lot['quantity'] - _used(lot), 1) if lot['receiving_status'] == 'ACCEPTED' else 0,
            'supplier': {k: sup[k] for k in ('supplier_id', 'name', 'type', 'location', 'distance_km',
                                             'cold_chain', 'certifications')},
            'flags': flags}


def trace(kitchen_id: str, meal_date: str, lots: list[dict], suppliers: dict[str, dict], batches: list[dict],
          today: date) -> dict:
    """Which lots, from which suppliers, went into one kitchen's meals on one date."""
    used = []
    for lot in lots:
        if lot['kitchen_id'] != kitchen_id:
            continue
        qty = sum(u['qty'] for u in lot.get('used_in', []) if u['meal_date'] == meal_date)
        if qty:
            sup = suppliers[lot['supplier_id']]
            row = _lot_row(lot, sup, lot_flags(lot, sup, today))
            row['qty_used'] = qty
            used.append(row)
    used.sort(key=lambda r: (min((SEVERITY_ORDER[f['severity']] for f in r['flags']), default=9), r['category']))
    batch = next((b for b in batches if b['kitchen_id'] == kitchen_id and b['meal_date'] == meal_date), None)
    flags = [f for r in used for f in r['flags']]
    return {'kitchen_id': kitchen_id, 'meal_date': meal_date, 'batch': batch, 'lots': used,
            'suppliers': len({r['supplier']['supplier_id'] for r in used}),
            'flags_total': len(flags), 'high_flags': sum(1 for f in flags if f['severity'] == 'high'),
            'max_distance_km': max((r['supplier']['distance_km'] for r in used), default=None)}


# ------------------------------------------------------------------- Gemini

AI_SCHEMA = {
    'type': 'object',
    'properties': {
        'summary': {'type': 'string'},
        'insights': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'category': {'type': 'string', 'enum': list(CATEGORY_ORDER)},
            'title': {'type': 'string'},
            'detail': {'type': 'string'},
            'action': {'type': 'string'},
            'lot_ids': {'type': 'array', 'items': {'type': 'string'}},
            'supplier_ids': {'type': 'array', 'items': {'type': 'string'}},
        }, 'required': ['category', 'title', 'detail', 'action']}},
    },
    'required': ['summary', 'insights'],
}

AI_INSTRUCTIONS = (
    'You are a supply-chain quality analyst for a school-meal kitchen. Using ONLY the data in this request, write '
    'a short brief for the kitchen supervisor: a 2-3 sentence summary, then at most 5 insights ranked by impact. '
    'Food safety comes first (temperature, cold chain, expired stock, unusually cheap protein), then stock, then '
    'cost (price above reference, rising prices, extra spend in rupiah), then logistics (distance, transit time, late '
    'deliveries). Combine related checks into one insight when they share a cause, for example one supplier. '
    'Each insight needs a concrete action. Cite lot_ids and supplier_ids exactly as given; never invent ids, '
    'numbers or suppliers. Never state that food is safe, and never recommend a supplier on price alone. '
    'Plain English, no markdown.'
)


def build_ai_prompt(analysis: dict) -> dict:
    return {
        'instructions': AI_INSTRUCTIONS,
        'kitchen_id': analysis['kitchen_id'], 'as_of': analysis['as_of'], 'kpis': analysis['kpis'],
        'deterministic_insights': [{k: i[k] for k in ('category', 'severity', 'title', 'detail', 'lot_ids', 'supplier_ids')}
                                   for i in analysis['insights'][:25]],
        'suppliers': analysis['suppliers'], 'stock': analysis['stock'],
        'price_trends': [{k: t[k] for k in ('label', 'unit', 'reference', 'latest', 'change_pct')} for t in analysis['price_trends']],
        'lots': [{'lot_id': l['lot_id'], 'ingredient': l['ingredient'], 'supplier_id': l['supplier']['supplier_id'],
                  'qty': l['quantity'], 'unit_price': l['unit_price'], 'reference_price': l['reference_price'],
                  'transit_min': l['transit_min'], 'arrival_temp_c': l['arrival_temp_c'],
                  'received': l['received_at'][:10], 'status': l['receiving_status'],
                  'used_on': sorted({u['meal_date'] for u in l['used_in']})} for l in analysis['lots'][:40]],
    }


def validate_ai(output: dict, lot_ids: set[str], supplier_ids: set[str]) -> dict:
    if not isinstance(output, dict):
        raise SupplyInvalid('Model output is not an object')
    summary = str(output.get('summary') or '').strip()
    if not summary:
        raise SupplyInvalid('Empty summary')
    insights = []
    for item in (output.get('insights') or [])[:5]:
        if not isinstance(item, dict) or item.get('category') not in CATEGORY_ORDER:
            raise SupplyInvalid('Unsupported insight category')
        lots = [str(i) for i in (item.get('lot_ids') or [])]
        sups = [str(i) for i in (item.get('supplier_ids') or [])]
        if not set(lots) <= lot_ids or not set(sups) <= supplier_ids:
            raise SupplyInvalid('Model cited a lot or supplier that is not in the data')
        insights.append({'category': item['category'], 'title': str(item.get('title') or '')[:160],
                         'detail': str(item.get('detail') or '')[:500], 'action': str(item.get('action') or '')[:300],
                         'lot_ids': lots, 'supplier_ids': sups})
    texts = [summary] + [i['detail'] for i in insights]
    if any(re.search(r'\b(is|are) (completely |fully )?safe\b', t, re.I) for t in texts):
        raise SupplyInvalid('Model output declared food safe')
    return {'summary': summary[:900], 'insights': insights}


# ------------------------------------------------------------------ demo data

def demo_supply(today: date) -> tuple[list[dict], list[dict], list[dict]]:
    """A week of deliveries for two kitchens, lined up with the claims demo.

    KITCHEN-A's chicken on D-1 (the day of the claims demo's real outbreak at
    SDN-02, where a parent wrote the chicken "tasted sour") came from a cheap
    distant supplier without a cold chain and arrived warm. Rice is getting
    pricier, cooking oil is nearly out, and some spinach is past its use-by.
    """
    suppliers = [
        {'supplier_id': 'SUP-01', 'name': 'Koperasi Tani Makmur', 'type': 'farmer co-op', 'location': 'Lembang, Bandung Barat',
         'distance_km': 18, 'cold_chain': False, 'certifications': ['Prima 3']},
        {'supplier_id': 'SUP-02', 'name': 'UD Beras Sejahtera', 'type': 'rice mill', 'location': 'Karawang',
         'distance_km': 72, 'cold_chain': False, 'certifications': ['SNI beras']},
        {'supplier_id': 'SUP-03', 'name': 'CV Unggas Murah', 'type': 'poultry trader', 'location': 'Bogor',
         'distance_km': 145, 'cold_chain': False, 'certifications': []},
        {'supplier_id': 'SUP-04', 'name': 'RPU Halal Mitra', 'type': 'poultry abattoir', 'location': 'Cimahi',
         'distance_km': 22, 'cold_chain': True, 'certifications': ['Halal', 'NKV']},
        {'supplier_id': 'SUP-05', 'name': 'Peternakan Telur Jaya', 'type': 'egg farm', 'location': 'Soreang',
         'distance_km': 35, 'cold_chain': False, 'certifications': ['NKV']},
        {'supplier_id': 'SUP-06', 'name': 'Tempe Bu Sari', 'type': 'home producer', 'location': 'Coblong, Bandung',
         'distance_km': 6, 'cold_chain': False, 'certifications': ['PIRT', 'Halal']},
        {'supplier_id': 'SUP-07', 'name': 'Pasar Induk Caringin', 'type': 'wholesale market', 'location': 'Bandung',
         'distance_km': 12, 'cold_chain': False, 'certifications': []},
        {'supplier_id': 'SUP-08', 'name': 'Koperasi Nelayan Pangandaran', 'type': 'fishers co-op', 'location': 'Pangandaran',
         'distance_km': 210, 'cold_chain': True, 'certifications': ['CPIB']},
        {'supplier_id': 'SUP-09', 'name': 'Toko Minyak Sumber Rejeki', 'type': 'distributor', 'location': 'Bandung',
         'distance_km': 9, 'cold_chain': False, 'certifications': ['SNI']},
    ]
    days = [today - timedelta(days=n) for n in range(6, -1, -1)]  # D-6 … D0
    portions = {'KITCHEN-A': 850, 'KITCHEN-B': 560}
    batches = [{'batch_id': f'BATCH-{d:%m%d}', 'kitchen_id': k, 'meal_date': d.isoformat(), 'portions': p}
               for d in days for k, p in portions.items()]
    lots: list[dict] = []

    def at(day: date, hh: int, mm: int = 0) -> str:
        return datetime(day.year, day.month, day.day, hh, mm, tzinfo=WIB).isoformat()

    def add(kitchen, back, ing, sup, qty, price, dispatch, receive, temp=None, shelf=2, use=None,
            status='ACCEPTED', note='', promised=(6, 0)):
        day = today - timedelta(days=back)
        spec = INGREDIENTS[ing]
        lot_id = f"LOT-{kitchen[-1]}{day:%m%d}-{ing[:3].upper()}{sup[-2:]}"
        # Stock used on the day of delivery and the following days until gone.
        used_in = [{'meal_date': (day + timedelta(days=o)).isoformat(), 'batch_id': f'BATCH-{day + timedelta(days=o):%m%d}',
                    'qty': q} for o, q in enumerate(use or [qty]) if q and day + timedelta(days=o) <= today]
        lots.append({'lot_id': lot_id, 'kitchen_id': kitchen, 'ingredient': ing, 'supplier_id': sup,
                     'quantity': qty, 'unit': spec['unit'], 'unit_price': price,
                     'dispatched_at': at(day, *dispatch), 'received_at': at(day, *receive),
                     'promised_at': at(day, *promised) if promised else None,
                     'arrival_temp_c': temp, 'use_by': (day + timedelta(days=shelf)).isoformat(),
                     'receiving_status': status, 'receiving_note': note,
                     'used_in': used_in if status == 'ACCEPTED' else []})

    A, B = 'KITCHEN-A', 'KITCHEN-B'
    # Rice: bulk every three days, price climbing.
    add(A, 6, 'rice', 'SUP-02', 255, 14200, (3, 0), (5, 10), shelf=180, use=[85, 85, 85])
    add(A, 3, 'rice', 'SUP-02', 255, 15400, (3, 0), (5, 20), shelf=180, use=[85, 85, 85])
    add(A, 0, 'rice', 'SUP-02', 255, 16800, (3, 0), (5, 15), shelf=180, use=[85])
    # Protein: chicken and eggs alternate; tempeh every day.
    add(A, 6, 'chicken', 'SUP-04', 60, 38500, (4, 40), (5, 25), temp=3.2, shelf=1, note='Chilled crate, sealed')
    add(A, 5, 'eggs', 'SUP-05', 50, 29500, (4, 30), (5, 30), shelf=10)
    add(A, 4, 'chicken', 'SUP-04', 60, 38000, (4, 45), (5, 30), temp=3.8, shelf=1, note='Chilled crate, sealed')
    add(A, 3, 'eggs', 'SUP-05', 50, 30000, (4, 30), (5, 35), shelf=10)
    add(A, 2, 'chicken', 'SUP-04', 60, 39000, (4, 40), (5, 20), temp=4.1, shelf=1, note='Chilled crate, sealed')
    add(A, 1, 'chicken', 'SUP-03', 60, 29500, (0, 50), (7, 10), temp=11.5, shelf=1,
        note='Usual supplier short; bought from a trader. Looked and smelled normal at receiving.')
    add(A, 0, 'eggs', 'SUP-05', 50, 30500, (4, 30), (5, 40), shelf=10)
    for back in range(6, -1, -1):
        add(A, back, 'tempeh', 'SUP-06', 25, 16000, (5, 0), (5, 25), shelf=2)
    # Vegetables: spinach daily from the co-op, carrots and cabbage from the market.
    for back, left in ((6, 0), (5, 0), (4, 0), (3, 0), (2, 5), (1, 8), (0, 0)):
        add(A, back, 'spinach', 'SUP-01', 30, 11500 + (back % 3) * 300, (4, 0), (5, 45), shelf=1, use=[30 - left])
    for back in (6, 4, 2, 0):
        add(A, back, 'carrot', 'SUP-07', 30, 13500, (4, 30), (5, 50), shelf=7, use=[15, 15])
    add(A, 3, 'cabbage', 'SUP-07', 40, 8500, (4, 30), (6, 50), shelf=4, status='REJECTED',
        note='Wilted outer leaves, about a third rotten. Returned to supplier.', promised=(6, 0))
    add(A, 3, 'cabbage', 'SUP-01', 40, 9500, (8, 0), (8, 40), shelf=4, use=[20, 20], promised=(8, 30))
    # Cooking oil: one delivery six days ago is almost used up.
    add(A, 5, 'cooking_oil', 'SUP-09', 50, 18000, (8, 0), (8, 30), shelf=365, use=[8, 8, 8, 8, 8, 8], promised=(8, 0))
    add(A, 6, 'banana', 'SUP-07', 120, 15500, (4, 30), (6, 5), shelf=5, use=[60, 0, 60], promised=(6, 0))

    # KITCHEN-B: a quieter week; fish travels far but stays chilled.
    add(B, 6, 'rice', 'SUP-02', 170, 14200, (3, 0), (5, 40), shelf=180, use=[56, 56, 56])
    add(B, 3, 'rice', 'SUP-02', 170, 14600, (3, 0), (5, 35), shelf=180, use=[56, 56, 56])
    add(B, 0, 'rice', 'SUP-02', 170, 15000, (3, 0), (5, 30), shelf=180, use=[56])
    for back in (5, 3, 1):
        add(B, back, 'fish', 'SUP-08', 40, 43000, (0, 30), (5, 50), temp=2.8, shelf=1, note='Iced boxes')
    for back in (6, 4, 2, 0):
        add(B, back, 'eggs', 'SUP-05', 35, 29500, (4, 30), (5, 50), shelf=10)
    for back in range(6, -1, -1):
        add(B, back, 'cabbage', 'SUP-07', 25, 9000, (4, 30), (6, 0), shelf=3)
    add(B, 4, 'cooking_oil', 'SUP-09', 40, 18500, (8, 0), (8, 20), shelf=365, use=[5, 5, 5, 5, 5], promised=(8, 0))
    return suppliers, lots, batches


# ---------------------------------------------------------------------- routes

def register(app, store, body: Callable, roles: dict, scope: Callable, actor: Callable, now: Callable):
    """Mount the supply endpoints. Returns agent tools bound to the caller's role.

    `app.state.supply_model` may be replaced by tests with a callable
    `prompt -> dict` so no live provider is needed.
    """
    app.state.supply_model = None

    def _today() -> date:
        return datetime.now(WIB).date()

    def _anchor() -> date:
        """The day the demo week ends on.

        The illness-claims demo puts its real outbreak on its own D-1. When that
        demo is loaded, the supply demo ends on the same day so the outbreak's
        meal traces to the warm chicken; otherwise it ends today.
        """
        served = [s['meal_date'] for s in store.list_kind('service_record') if s['kitchen_id'] == 'KITCHEN-A']
        return date.fromisoformat(max(served)) + timedelta(days=1) if served else _today()

    def _seed(force: bool = False) -> dict:
        anchor = _anchor()
        meta = store.get('supply_meta', 'demo') or {}
        if not force and store.list_kind('supplier') and meta.get('anchor') == anchor.isoformat():
            return {'seeded': False}
        suppliers, lots, batches = demo_supply(anchor)
        # Records from an older seed stay in the store (it has no delete); the
        # `seed` tag hides them so two demo weeks never mix.
        for s in suppliers:
            store.put('supplier', s['supplier_id'], s)
        for l in lots:
            store.put('supply_lot', l['lot_id'], {**l, 'seed': anchor.isoformat()})
        for b in batches:
            store.put('production_batch', f"{b['kitchen_id']}-{b['meal_date']}", {**b, 'seed': anchor.isoformat()})
        store.put('supply_meta', 'demo', {'anchor': anchor.isoformat()})
        return {'seeded': True, 'suppliers': len(suppliers), 'lots': len(lots), 'batches': len(batches), 'synthetic': True}

    def _data():
        _seed()
        current = (store.get('supply_meta', 'demo') or {}).get('anchor')
        suppliers = {s['supplier_id']: s for s in store.list_kind('supplier')}
        lots = [l for l in store.list_kind('supply_lot') if l.get('source') == 'recorded' or l.get('seed') == current]
        return lots, suppliers, [b for b in store.list_kind('production_batch') if b.get('seed') == current]

    def _check(role, kitchen_id):
        if role not in roles:
            raise HTTPException(422, 'Unknown role')
        if kitchen_id not in KITCHENS:
            raise HTTPException(422, 'Unknown kitchen')
        if kitchen_id not in scope(role):
            raise HTTPException(403, 'Kitchen is outside your scope')

    def _overview(kitchen_id: str) -> dict:
        lots, suppliers, batches = _data()
        view = analyze(kitchen_id, lots, suppliers, batches, _today())
        view['ai'] = (store.get('supply_ai', kitchen_id) or {}).get('ai')
        return view

    @app.get('/api/supply/overview')
    async def supply_overview(role: str = 'SUPERVISOR', kitchen_id: str = 'KITCHEN-A'):
        _check(role, kitchen_id)
        return _overview(kitchen_id)

    @app.get('/api/supply/trace')
    async def supply_trace(role: str = 'SUPERVISOR', kitchen_id: str = 'KITCHEN-A', meal_date: str = ''):
        _check(role, kitchen_id)
        try:
            day = date.fromisoformat(meal_date) if meal_date else _today()
        except ValueError:
            raise HTTPException(422, 'meal_date must be YYYY-MM-DD') from None
        lots, suppliers, batches = _data()
        return trace(kitchen_id, day.isoformat(), lots, suppliers, batches, _today())

    @app.get('/api/supply/catalog')
    async def supply_catalog(role: str = 'SUPERVISOR'):
        if role not in roles:
            raise HTTPException(422, 'Unknown role')
        _, suppliers, _ = _data()
        return {'suppliers': sorted(suppliers.values(), key=lambda s: s['supplier_id']),
                'ingredients': [{'ingredient': k, **v} for k, v in INGREDIENTS.items()]}

    @app.post('/api/supply/lots', status_code=201)
    async def record_lot(request: Request):
        payload = await body(request)
        role = payload.get('role')
        _check(role, payload.get('kitchen_id'))
        _, suppliers, _ = _data()
        try:
            lot = normalize_lot({**payload, 'lot_id': None, 'used_in': []}, suppliers)
        except SupplyInvalid as exc:
            raise HTTPException(422, str(exc)) from None
        lot['source'] = 'recorded'  # a real delivery, kept whichever demo week is loaded
        store.put('supply_lot', lot['lot_id'], lot)
        store.append(lot['lot_id'], 'lot_received', {'actor': actor(role), 'status': lot['receiving_status']})
        sup = suppliers[lot['supplier_id']]
        return _lot_row(lot, sup, lot_flags(lot, sup, _today()))

    @app.post('/api/supply/insights')
    async def supply_insights(request: Request):
        payload = await body(request)
        role = payload.get('role')
        kitchen_id = payload.get('kitchen_id', 'KITCHEN-A')
        _check(role, kitchen_id)
        if role not in {'SUPERVISOR', 'ADMIN'}:
            raise HTTPException(403, 'AI insights are available to supervisors and admins')
        lots, suppliers, batches = _data()
        analysis = analyze(kitchen_id, lots, suppliers, batches, _today())
        prompt = build_ai_prompt(analysis)
        lot_ids = {l['lot_id'] for l in lots if l['kitchen_id'] == kitchen_id}
        usage: dict = {}
        try:
            if app.state.supply_model is not None:
                raw = app.state.supply_model(prompt)
                usage = {'provider_called': True, 'model_id': 'TEST_ADAPTER', 'http_status': 200, 'latency_ms': 0}
            else:
                raw, usage = await c05_claims.call_model(prompt, AI_SCHEMA)
            ai = {**validate_ai(raw, lot_ids, set(suppliers)), 'source': 'model',
                  'inference_status': 'INFERENCE_SUCCEEDED', 'error': None}
        except c05_claims.ProviderUnavailable as exc:
            usage = exc.usage
            ai = {'summary': None, 'insights': [], 'source': 'none', 'error': exc.code,
                  'inference_status': 'INFERENCE_FAILED' if usage.get('provider_called') else 'INFERENCE_BLOCKED'}
        except SupplyInvalid as exc:
            ai = {'summary': None, 'insights': [], 'source': 'none', 'inference_status': 'INFERENCE_FAILED',
                  'error': f'invalid_model_output: {exc}'}
        ai.update(model_id=usage.get('model_id'), latency_ms=usage.get('latency_ms'), generated_at=now(),
                  checks_hash=hashlib.sha256(json.dumps([i['title'] for i in analysis['insights']]).encode()).hexdigest()[:12])
        store.put('supply_ai', kitchen_id, {'ai': ai})
        store.append(f'SUPPLY-{kitchen_id}', 'ai_insights', {'actor': actor(role), 'inference_status': ai['inference_status']})
        return {**analysis, 'ai': ai}

    @app.post('/api/supply/demo-seed')
    async def supply_seed(request: Request):
        payload = await body(request)
        if payload.get('role') != 'ADMIN':
            raise HTTPException(403, 'Only ADMIN may reload the demo data')
        return _seed(force=True)

    # ----------------------------------------------------------- agent tools

    def tool_supply_overview(actor_role: str, kitchen_id: str):
        if kitchen_id not in scope(actor_role):
            return {'error': 'outside authorized kitchen scope'}
        view = _overview(kitchen_id)
        return {'kitchen_id': kitchen_id, 'kpis': view['kpis'],
                'top_insights': [{k: i[k] for k in ('severity', 'category', 'title', 'detail', 'action', 'lot_ids')}
                                 for i in view['insights'][:8]],
                'suppliers': [{k: s[k] for k in ('supplier_id', 'name', 'location', 'distance_km', 'on_time_pct',
                                                 'temp_breaches', 'price_index', 'ingredients')} for s in view['suppliers']],
                'stock': view['stock'], 'note': view['reference_note']}

    def tool_trace_meal(actor_role: str, kitchen_id: str, meal_date: str):
        if kitchen_id not in scope(actor_role):
            return {'error': 'outside authorized kitchen scope'}
        lots, suppliers, batches = _data()
        result = trace(kitchen_id, str(meal_date)[:10], lots, suppliers, batches, _today())
        return {**{k: result[k] for k in ('kitchen_id', 'meal_date', 'suppliers', 'flags_total', 'high_flags')},
                'lots': [{'lot_id': r['lot_id'], 'ingredient': r['label'], 'supplier': r['supplier']['name'],
                          'origin': r['supplier']['location'], 'distance_km': r['supplier']['distance_km'],
                          'transit_min': r['transit_min'], 'arrival_temp_c': r['arrival_temp_c'],
                          'qty_used': r['qty_used'], 'flags': [f['title'] for f in r['flags']]} for r in result['lots']]}

    return tool_supply_overview, tool_trace_meal
