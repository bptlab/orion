import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_cell_correlation(row):
    figsize_value = (4,3.75)
    #figsize_value = (15,10)
    fontsize_value = 10
    if row["method"] == "pearson" or row["method"] == "spearman":
        plt.close(2)
        fig, ax = plt.subplots(figsize=figsize_value, num='Correlation Plot')
        plt.title(f"{row['Act_1']} -> {row['Act_2']}: {row['scipy_corr'].round(2)}", fontsize=fontsize_value)
        plt.xlabel(f"Δ{row['measure_1']}", fontsize=fontsize_value)
        plt.ylabel(f"Δ{row['measure_2']}", fontsize=fontsize_value)
        plt.xticks(size=5, wrap=True)
        plt.yticks(size=5)
        plt.scatter(row['values_1'], row['values_2'])   
    elif row["method"] == "cramer":
        plt.close(2)
        pd.crosstab(index=row['values_1'],columns=row['values_2']).plot(kind="bar", figsize=figsize_value, )
        legend = plt.legend(title=f"Δ{row['measure_2']} ", prop={'size': 6}, title_fontsize=6)
        l_texts = [item for item in legend.get_texts()]
        for l_text in l_texts:
            l_text.set_text(l_text.get_text().replace('abnormal ', ''))
        plt.title(f"{row['Act_1']} -> {row['Act_2']}: {row['scipy_corr'].round(2)}", fontsize=fontsize_value)
        plt.xlabel(f"Δ{row['measure_1']}", fontsize=fontsize_value)
        plt.ylabel(f"Δ{row['measure_2']}", fontsize=fontsize_value)
        ax = plt.gca()
        plt.xticks(size=5, wrap=True)
        plt.yticks(size=5)
        plt.setp(ax.get_xticklabels(), rotation=7.5, horizontalalignment='center')
        labels = [item.get_text() for item in ax.get_xticklabels()]
        labels_new = [label.replace('abnormal ', '') for label in labels]
        ax.set_xticklabels(labels_new)
    elif row["method"] == "anova" or row["method"] == "kruskal":
        plt.close(2)
        fig, ax = plt.subplots(figsize=figsize_value, num='Correlation Plot')
        #sns.swarmplot(x='values_1', y='values_2', data=row, dodge=True, palette='viridis')
        plt.title(f"{row['Act_1']} -> {row['Act_2']}: {row['stat'].round(2)}", fontsize=fontsize_value)
        plt.xlabel(f"Δ{row['measure_2']}", fontsize=fontsize_value)
        plt.ylabel(f"Δ{row['measure_1']}", fontsize=fontsize_value)  
        plt.xticks(size=5, wrap=True)
        plt.yticks(size=5)  
        #draw mean(avg) line
        #sns.boxplot(showmeans=True,
        #    meanline=True,
        #    meanprops={'color': 'k', 'ls': '-', 'lw': 2},
        #    medianprops={'visible': False},
        #    whiskerprops={'visible': False},
        #    zorder=10,
        #    x="values_1",
        #    y="values_2",
        #    data=row,
        #    showfliers=False,
        #    showbox=False,
        #    showcaps=False,
        #    ax=ax)
        sns.boxplot(showmeans=False,
            meanline=False,
            #meanprops={'color': 'k', 'ls': '-', 'lw': 2},
            #medianprops={'visible': False},
            #whiskerprops={'visible': False},
            zorder=10,
            x="values_1",
            y="values_2",
            data=row,
            showfliers=False,
            showbox=True,
            showcaps=True,
            ax=ax)
        plt.setp(ax.get_xticklabels(), rotation=7.5, horizontalalignment='center')
        labels = [item.get_text() for item in ax.get_xticklabels()]
        labels_new = [label.replace('abnormal ', '') for label in labels]
        ax.set_xticklabels(labels_new)
