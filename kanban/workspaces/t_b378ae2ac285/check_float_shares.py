#!/home/pebynn/tools/quant_env/bin/python3
import pandas as pd

f = '/home/pebynn/.finquant/cache/shares/float_shares.parquet'
try:
    df = pd.read_parquet(f)
    print('Columns:', list(df.columns))
    print('Shape:', df.shape)
    print('Head:', df.head(3))
    print('Dtypes:', df.dtypes.to_dict())
except Exception as e:
    print(f'Error: {e}')
    import os
    print(f'File size: {os.path.getsize(f)}')
