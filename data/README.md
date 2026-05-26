# Data directory

Place the anonymized Phase 1 CSVs and Phase 2 enrichment files here. They are
**not** committed by default — drop them in locally, then run
`python manage.py load_data` and the two training scripts.

## Files expected

### `customers.csv` (149 rows)
`customer_id_hash`, `customer_code`, `membership_tier` (bronze/silver/gold),
`current_points`, `total_points_earned`, `total_points_redeemed`,
`created_at`, `updated_at`, `coffee_adventure_level`

### `transactions.csv` (1,000 rows)
`id`, `customer_id_hash`, `transaction_type` (earn/redeem), `earn_source`,
`points`, `is_drink_purchase`, `drink_category`, `drink_price_jod`,
`reward_id`, `created_at`, `expires_at`, `notes`, `role`

### `rewards.csv`, `redemptions.csv`, `menu.csv`
Present for completeness; the app models only customers and transactions.

### Phase 2 enrichment (needed for the volume model)
- `weather_amman.json` — 261 days of Amman weather. Either the raw Open-Meteo
  response (`{"daily": {"time": [...], "temperature_2m_max": [...], ...}}`) or a
  list/dict of records with `date`, `temperature_2m_max`, `temperature_2m_min`,
  `precipitation_sum`.
- `coffee_prices_scraped.csv` — `month`, `arabica_usd_per_lb` (9 rows).

## Which files each step needs

| Step | Needs |
|------|-------|
| `load_data` | `customers.csv`, `transactions.csv` |
| `train_tier_model.py` | `customers.csv`, `transactions.csv` |
| `train_volume_model.py` | `transactions.csv`, `weather_amman.json`, `coffee_prices_scraped.csv` |
