"""Empty the tables, then seed one option with the given stock and N members
who each have that option (quantity 1) in their cart. --spare 1 adds a
second option of the same product with stock 100 that nobody orders."""
from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import CartItem, Member, Order, OrderItem, Product, ProductOption


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=10)
        parser.add_argument("--stock", type=int, default=1)
        parser.add_argument("--spare", type=int, default=0)

    def handle(self, *args, users, stock, spare, **options):
        with transaction.atomic():
            for model in (OrderItem, Order, CartItem, ProductOption, Product, Member):
                model.objects.all().delete()
            product = Product.objects.create(name="Spike Blend", base_price=18000)
            option = ProductOption.objects.create(
                product=product,
                weight_size="200g",
                grind_type="WHOLE_BEAN",
                stock_quantity=stock,
            )
            if spare:
                # A second option in stock keeps the product ON_SALE after the
                # first order, so the other orders reach decrease_stock.
                ProductOption.objects.create(
                    product=product, weight_size="500g", grind_type="WHOLE_BEAN",
                    stock_quantity=100,
                )
            for n in range(1, users + 1):
                member = Member.objects.create(id=n, name=f"m{n}")
                CartItem.objects.create(user=member, option=option, quantity=1)
