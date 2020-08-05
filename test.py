import pandas as pd
import matplotlib.pyplot as plt


mylist = [[1, 2000], [2, 1500], [3, 800]]
df = pd.DataFrame(mylist, columns = ['x', 'y'], dtype = float)
print(df)
print(df.dtypes)

df.plot(x = 'x', y = 'y')