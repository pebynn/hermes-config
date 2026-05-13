#!/usr/bin/env python3
import pandas as pd

df = pd.read_parquet("/home/pebynn/quant/cache/sina_kline_2025_2026.parquet")
print("Shape:", df.shape)
print("Columns:", list(df.columns))
print("Dtypes:")
print(df.dtypes)
print()
print("First 2 rows:")
print(df.head(2).to_string())
print()
print("Sample stock codes:", df["code"].unique()[:5])
print("Date range:", df["date"].min(), "->", df["date"].max())
