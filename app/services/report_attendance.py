"""Decimal leave-day arithmetic for weekly report attendance items.

Manual report fields are shared string fields; retain their existing format.
"""
from decimal import Decimal, InvalidOperation, localcontext


def _days(value, label):
    if value is None or str(value).strip() == '':
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        raise ValueError(f'{label}는 0 이상의 숫자로 입력해주세요.')
    if not number.is_finite() or number < 0:
        raise ValueError(f'{label}는 0 이상의 숫자로 입력해주세요.')
    return number


def attendance_remaining(accrued, used):
    a, b = _days(accrued, '발생일수'), _days(used, '총사용일수')
    if a is None or b is None:
        return None
    with localcontext() as context:
        integer_places = max(0, a.adjusted(), b.adjusted()) + 1
        decimal_places = max(0, -a.as_tuple().exponent, -b.as_tuple().exponent)
        context.prec = integer_places + decimal_places + 1
        remaining = a - b
    if remaining == 0:
        return '0'
    text = format(remaining, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text
