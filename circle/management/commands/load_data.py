"""
Management command: load the anonymized Phase 1 CSVs into the database.

Usage:
    python manage.py load_data                 # (re)load customers + transactions
    python manage.py load_data --skip-if-exists  # no-op if data already present
    python manage.py load_data --data-dir path/  # override the data directory

Idempotent: rows are written with update_or_create, so running it repeatedly
will not create duplicates. If the data/ files are missing the command logs a
warning and exits cleanly (so it never breaks the Render build).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from circle.models import Customer, Transaction


def _parse_dt(value) -> dt.datetime | None:
    """Parse a CSV timestamp into an aware datetime (or None when blank)."""
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    py = ts.to_pydatetime()
    if timezone.is_naive(py):
        return timezone.make_aware(py, timezone.get_current_timezone())
    return py


def _as_bool(value) -> bool:
    """Coerce CSV truthy values (True/true/1/yes) into a real bool."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "t"}


class Command(BaseCommand):
    help = "Load anonymized customers and transactions from data/*.csv."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--skip-if-exists",
            action="store_true",
            help="Skip loading if the database already contains customers.",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default=str(settings.BASE_DIR / "data"),
            help="Directory containing the CSV files (default: <project>/data).",
        )

    def _find(self, name: str, data_dir: Path) -> Path | None:
        """Locate a data file in data_dir (preferred) or the repo root."""
        for base in (data_dir, settings.BASE_DIR):
            candidate = base / name
            if candidate.exists():
                return candidate
        return None

    def handle(self, *args, **options) -> None:
        data_dir = Path(options["data_dir"])

        if options["skip_if_exists"] and Customer.objects.exists():
            self.stdout.write(
                self.style.WARNING("Customers already present; skipping load.")
            )
            return

        customers_csv = self._find("customers.csv", data_dir)
        transactions_csv = self._find("transactions.csv", data_dir)

        if customers_csv is None or transactions_csv is None:
            self.stdout.write(
                self.style.WARNING(
                    f"Data files not found in {data_dir} or {settings.BASE_DIR} "
                    "(need customers.csv and transactions.csv). Nothing loaded."
                )
            )
            return

        n_customers = self._load_customers(customers_csv)
        n_transactions = self._load_transactions(transactions_csv)

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {n_customers} customers, {n_transactions} transactions"
            )
        )

    @db_transaction.atomic
    def _load_customers(self, path: Path) -> int:
        """Upsert Customer rows from customers.csv."""
        df = pd.read_csv(path)
        count = 0
        for row in df.to_dict(orient="records"):
            Customer.objects.update_or_create(
                customer_id_hash=str(row["customer_id_hash"]),
                defaults={
                    "customer_code": str(row["customer_code"]),
                    "membership_tier": str(row.get("membership_tier", "bronze")).lower(),
                    "current_points": int(row.get("current_points", 0) or 0),
                    "total_points_earned": int(row.get("total_points_earned", 0) or 0),
                    "total_points_redeemed": int(
                        row.get("total_points_redeemed", 0) or 0
                    ),
                    "created_at": _parse_dt(row.get("created_at"))
                    or timezone.now(),
                    "updated_at": _parse_dt(row.get("updated_at")) or timezone.now(),
                },
            )
            count += 1
        return count

    @db_transaction.atomic
    def _load_transactions(self, path: Path) -> int:
        """Upsert Transaction rows from transactions.csv (skips orphans)."""
        df = pd.read_csv(path)
        known = set(Customer.objects.values_list("customer_id_hash", flat=True))
        count = 0
        skipped = 0
        for row in df.to_dict(orient="records"):
            cust_hash = str(row["customer_id_hash"])
            if cust_hash not in known:
                skipped += 1
                continue

            price = row.get("drink_price_jod")
            category = row.get("drink_category")
            Transaction.objects.update_or_create(
                id=str(row["id"]),
                defaults={
                    "customer_id": cust_hash,
                    "transaction_type": str(row["transaction_type"]).lower(),
                    "earn_source": str(row.get("earn_source") or "")[:50],
                    "points": int(row.get("points", 0) or 0),
                    "is_drink_purchase": _as_bool(row.get("is_drink_purchase")),
                    "drink_category": (
                        None if pd.isna(category) else str(category)[:50]
                    ),
                    "drink_price_jod": (None if pd.isna(price) else float(price)),
                    "created_at": _parse_dt(row.get("created_at")) or timezone.now(),
                    "expires_at": _parse_dt(row.get("expires_at")),
                },
            )
            count += 1

        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {skipped} transactions referencing unknown customers."
                )
            )
        return count
