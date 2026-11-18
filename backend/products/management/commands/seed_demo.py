"""Demo data for NFR-1 ~ NFR-3 measurements and the demo (SDD 4.9.3).

Orders are inserted directly, not through order services, but keep DR-12 ~ DR-15:
snapshot prices, the shipping fee rule, totals, and stock taken for live orders.
"""

import random
import secrets
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from orders.models import (
    Courier,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from products import services
from products.models import GrindType, Product, RoastLevel, WeightSize
from products.origins import ORIGINS
from users.models import Role, User, UserAddress

SEOUL = ZoneInfo("Asia/Seoul")
FREE_SHIPPING_FROM = 30000
SHIPPING_FEE = 3000

VARIETIES = ["게이샤", "버번", "카투라", "티피카", "SL28", "파카마라", "카투아이"]
PROCESSES = ["워시드", "내추럴", "허니"]
NOTES = ["자스민", "레몬", "베리", "초콜릿", "캐러멜", "견과", "복숭아", "흑설탕"]
SIZE_EXTRA = {WeightSize.G200: 0, WeightSize.G500: 12000, WeightSize.KG1: 26000}
COMBOS = [(w, g) for w in WeightSize.values for g in GrindType.values]
FAMILY = ["김", "이", "박", "최", "정", "강", "조", "윤"]
GIVEN = ["민준", "서연", "도윤", "지우", "하준", "서윤", "지호", "하은"]
STREETS = [
    "충북 청주시 서원구 충대로 1",
    "서울 마포구 월드컵북로 21",
    "부산 해운대구 센텀중앙로 55",
    "대전 유성구 대학로 99",
]
CANCEL_REASONS = ["단순 변심", "주소 변경", "다른 원두로 다시 주문"]
PAID_STATES = [OrderStatus.PAID, OrderStatus.PREPARING]
METHODS = [PaymentMethod.CARD, PaymentMethod.EASY_PAY, PaymentMethod.TRANSFER]


class Command(BaseCommand):
    help = "Insert demo products, members and orders (NFR-3)."

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=100)
        parser.add_argument("--members", type=int, default=50)
        parser.add_argument("--orders", type=int, default=500)
        parser.add_argument("--seed", type=int, default=20261130)
        parser.add_argument(
            "--force", action="store_true", help="Run even when DEBUG is off."
        )

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("DEBUG is off. Add --force to seed this database.")
        if (
            Product.objects.exists()
            or Order.objects.exists()
            or User.objects.filter(role=Role.MEMBER).exists()
        ):
            raise CommandError("The database already has data. Seed an empty one.")

        self.rng = random.Random(opts["seed"])
        self.now = timezone.now()
        password = secrets.token_urlsafe(9)
        with transaction.atomic():
            products = self._products(opts["products"])
            members = self._members(opts["members"], password)
            self._orders(opts["orders"], members, products)
            self._stop_some(products)

        self.stdout.write(
            f"Seeded {opts['products']} products, {opts['members']} members, "
            f"{opts['orders']} orders."
        )
        self.stdout.write(
            f"Member password (shown once): {password}  e.g. demo001@example.com"
        )

    # Products

    def _products(self, n):
        rng = self.rng
        products = []
        for i in range(n):
            origin = rng.choice(ORIGINS)
            product = Product.objects.create(
                name=f"{origin} {rng.choice(VARIETIES)} {rng.choice(PROCESSES)}",
                origin=origin,
                roast_level=rng.choice(RoastLevel.values),
                base_price=rng.randrange(12000, 30001, 500),
                tasting_notes=", ".join(rng.sample(NOTES, rng.randint(2, 3))),
                description=f"시연용 원두 {i + 1}번입니다.",
            )
            for weight, grind in rng.sample(COMBOS, rng.randint(1, 9)):
                stock = 0 if rng.random() < 0.1 else rng.randint(5, 60)
                services.add_option(
                    product.pk, weight, grind, SIZE_EXTRA[weight], stock
                )
            products.append(product)
        return products

    def _stop_some(self, products):
        for product in self.rng.sample(products, len(products) // 20):
            services.stop_sales(product.pk)

    # Members

    def _members(self, n, password):
        rng = self.rng
        hashed = make_password(password)  # hash once, not once per member
        members = []
        for i in range(n):
            user = User(
                email=f"demo{i + 1:03d}@example.com",
                user_name=rng.choice(FAMILY) + rng.choice(GIVEN),
                phone_number=f"010-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
                role=Role.MEMBER,
                privacy_agreed_at=self.now,  # same as sign-up (FR-58)
            )
            user.password = hashed
            user.save()
            addresses = [
                UserAddress.objects.create(
                    user=user,
                    recipient_name=user.user_name,
                    recipient_phone=user.phone_number,
                    zipcode=f"{rng.randint(10000, 63999)}",
                    base_address=rng.choice(STREETS),
                    detail_address=f"{rng.randint(101, 120)}동 {rng.randint(101, 1504)}호",
                    is_default=(k == 0),
                )
                for k in range(rng.randint(1, 3))
            ]
            members.append((user, addresses))
        return members

    # Orders

    def _orders(self, n, members, products):
        rng = self.rng
        statuses = [OrderStatus.values[i % 7] for i in range(n)]
        rng.shuffle(statuses)
        times = sorted(
            self.now - timedelta(days=rng.randint(0, 29), seconds=rng.randint(0, 86399))
            for _ in range(n)
        )
        stock = {}
        for product in products:
            for option in product.options.select_related("product").order_by(
                "option_id"
            ):
                stock[option.pk] = [option, option.stock_quantity]
        per_day = {}
        for status, created in zip(statuses, times):
            day = created.astimezone(SEOUL).strftime("%Y%m%d")
            per_day[day] = per_day.get(day, 0) + 1
            if per_day[day] > 999:
                raise CommandError("More than 999 orders on one day (DR-11).")
            order_id = f"ORD-{day}-{per_day[day]:03d}"
            user, addresses = rng.choice(members)
            self._order(order_id, status, created, user, rng.choice(addresses), stock)

    def _pick_items(self, stock, live):
        rng = self.rng
        candidates = [k for k, (_, left) in stock.items() if left >= 1 or not live]
        if not candidates:
            raise CommandError("Ran out of stock. Use fewer orders or more products.")
        count = min(len(candidates), rng.randint(1, 3))
        picked = []
        for option_id in rng.sample(candidates, count):
            option, left = stock[option_id]
            quantity = rng.randint(1, 3)
            if live:
                quantity = min(quantity, left)
            picked.append((option, quantity))
        return picked

    def _order(self, order_id, status, created, user, address, stock):
        rng = self.rng
        live = status != OrderStatus.CANCELLED  # cancelled orders gave stock back
        items = self._pick_items(stock, live)
        total = sum(option.price * quantity for option, quantity in items)
        fee = 0 if total >= FREE_SHIPPING_FROM else SHIPPING_FEE

        fields = {}
        if status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            fields.update(
                courier_code=rng.choice(Courier.values),
                tracking_number=f"{rng.randint(10**11, 10**12 - 1)}",
                shipped_at=min(created + timedelta(hours=20), self.now),
            )
        if status == OrderStatus.DELIVERED:
            fields["delivered_at"] = min(created + timedelta(days=2), self.now)
        if status in (OrderStatus.CANCEL_REQUESTED, OrderStatus.CANCELLED):
            fields.update(
                status_before_cancel=rng.choice(PAID_STATES),
                cancel_reason=rng.choice(CANCEL_REASONS),
            )

        order = Order.objects.create(
            order_id=order_id,
            user=user,
            order_status=status,
            total_product_amt=total,
            shipping_fee=fee,
            final_payment_amt=total + fee,
            recipient_name=address.recipient_name,
            recipient_phone=address.recipient_phone,
            shipping_address=(
                f"({address.zipcode}) {address.base_address} {address.detail_address}"
            ),
            **fields,
        )
        Order.objects.filter(pk=order_id).update(created_at=created)
        for option, quantity in items:
            OrderItem.objects.create(
                order=order,
                option=option,
                product_name=option.product.name,
                weight_size=option.weight_size,
                grind_type=option.grind_type,
                order_price=option.price,
                quantity=quantity,
            )
            if live:
                services.decrease_stock(option.pk, quantity)
                stock[option.pk][1] -= quantity
        self._payment(order, status, created)

    def _payment(self, order, status, created):
        if status == OrderStatus.PENDING:
            payment_status, approved_at, method = PaymentStatus.READY, None, None
        else:
            payment_status = (
                PaymentStatus.CANCELLED
                if status == OrderStatus.CANCELLED
                else PaymentStatus.SUCCESS
            )
            approved_at = created + timedelta(minutes=1)
            method = self.rng.choice(METHODS)
        payment = Payment.objects.create(
            order=order,
            pg_order_id=f"{order.order_id}-P1",
            pg_tid=None if approved_at is None else f"seed-{order.order_id}",
            payment_method=method,
            payment_status=payment_status,
            paid_amount=order.final_payment_amt,
            approved_at=approved_at,
        )
        Payment.objects.filter(pk=payment.pk).update(requested_at=created)
