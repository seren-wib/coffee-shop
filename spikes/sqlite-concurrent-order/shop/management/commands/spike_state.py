"""Print the state after a round as one JSON line."""
import json

from django.core.management.base import BaseCommand
from django.db import connection

from shop.models import CartItem, Order, OrderItem, Product, ProductOption


class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute("PRAGMA journal_mode")
            journal_mode = cur.fetchone()[0]
        self.stdout.write(
            json.dumps(
                {
                    "stock_quantity": ProductOption.objects.order_by("id").first().stock_quantity,
                    "sales_status": Product.objects.get().sales_status,
                    "orders": Order.objects.count(),
                    "order_items": OrderItem.objects.count(),
                    "cart_items": CartItem.objects.count(),
                    "journal_mode": journal_mode,
                }
            )
        )
