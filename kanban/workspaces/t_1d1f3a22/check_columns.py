import pandas as pd
cols = pd.read_csv('/home/pebynn/quant/backtest_momentum.csv', nrows=1).columns.tolist()
print('Columns:', cols)
