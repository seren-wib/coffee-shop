"""Test data builders for orders (STP 1.2). Rows are inserted directly, not through services."""

from itertools import count

from orders.models import Order, OrderItem, OrderStatus, Payment, PaymentStatus

_seq = count(1)


def make_order(user, option, quantity=1, status=OrderStatus.PENDING, **fields):
    n = next(_seq)
    price = option.price
    total = price * quantity
    fee = 0 if total >= 30000 else 3000
    order = Order.objects.create(
        order_id=fields.pop("order_id", f"ORD-20261130-{n:03d}"),
        user=user,
        order_status=status,
        total_product_amt=total,
        shipping_fee=fee,
        final_payment_amt=total + fee,
        recipient_name="받는사람",
        recipient_phone="010-1111-2222",
        shipping_address="(28644) 충북 청주시 서원구 충대로 1",
        **fields,
    )
    OrderItem.objects.create(
        order=order,
        option=option,
        product_name=option.product.name,
        weight_size=option.weight_size,
        grind_type=option.grind_type,
        order_price=price,
        quantity=quantity,
    )
    return order


def make_payment(order, attempt=1, status=PaymentStatus.READY, **fields):
    return Payment.objects.create(
        order=order,
        pg_order_id=f"{order.order_id}-P{attempt}",
        payment_status=status,
        paid_amount=order.final_payment_amt,
        **fields,
    )
