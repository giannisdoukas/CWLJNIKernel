from random import random

import matplotlib.pyplot as plt
import pandas as pd

if __name__ == '__main__':
    lines = 100
    columns = 2
    x = pd.Series([random() for _ in range(lines)])
    y = pd.Series([i for i in range(lines)])
    fig, ax = plt.subplots()
    ax.plot(y, x)
    ax.grid()

    fig.savefig("test.png")
