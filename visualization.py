import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime

import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="darkgrid", rc={
    "axes.facecolor": "#1e1e1e",
    "figure.facecolor": "#1e1e1e",
    "axes.labelcolor": "white",
    "text.color": "white",
    "xtick.color": "white",
    "ytick.color": "white",
    "grid.color": "#3c3f41"
})

class Visualization:
    def __init__(self, db):
        self.db = db

    def plot_performance_over_time(self):
        # gather all quiz_results
        conn = self.db
        rows = []
        c = conn._conn.cursor()
        c.execute("SELECT topic, score, taken_at FROM quiz_results ORDER BY taken_at ASC")
        for r in c.fetchall():
            rows.append({"topic": r[0], "score": float(r[1]), "taken_at": datetime.fromisoformat(r[2])})
        if not rows:
            fig, ax = plt.subplots(figsize=(8,4))
            ax.text(0.5,0.5,"No quiz results yet", ha='center', va='center')
            return fig
        df = pd.DataFrame(rows)
        fig, ax = plt.subplots(figsize=(10,5))
        sns.lineplot(data=df, x="taken_at", y="score", marker="o", ax=ax)
        ax.set_title("Performance Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Score")
        plt.tight_layout()
        return fig

    def plot_forgetfulness_trend(self):
        # naive: compute average score per day and plot decreasing trend
        c = self.db._conn.cursor()
        c.execute("SELECT taken_at, score FROM quiz_results")
        rows = []
        for r in c.fetchall():
            dt = datetime.fromisoformat(r[0]).date()
            rows.append({"date": dt, "score": float(r[1])})
        if not rows:
            fig, ax = plt.subplots(figsize=(8,4))
            ax.text(0.5,0.5,"No quiz results yet", ha='center', va='center')
            return fig
        df = pd.DataFrame(rows)
        daily = df.groupby("date").mean().reset_index()
        fig, ax = plt.subplots(figsize=(10,5))
        sns.barplot(data=daily, x="date", y="score", ax=ax)
        ax.set_title("Daily Average Score (forgetfulness proxy)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Avg Score")
        plt.xticks(rotation=30)
        plt.tight_layout()
        return fig

    def plot_topic_strengths(self):
        c = self.db._conn.cursor()
        c.execute("SELECT topic, score FROM quiz_results")
        rows = []
        for r in c.fetchall():
            rows.append({"topic": r[0], "score": float(r[1])})
        if not rows:
            fig, ax = plt.subplots(figsize=(8,4))
            ax.text(0.5,0.5,"No quiz results yet", ha='center', va='center')
            return fig
        df = pd.DataFrame(rows)
        topic_mean = df.groupby("topic").mean().reset_index()
        fig, ax = plt.subplots(figsize=(10,5))
        sns.barplot(data=topic_mean, x="score", y="topic", ax=ax)
        ax.set_title("Average Score by Topic")
        ax.set_xlabel("Avg Score")
        ax.set_ylabel("Topic")
        plt.tight_layout()
        return fig

    def show_figure_in_toplevel(self, root_tk, fig, title="Chart"):
        # create Toplevel and embed matplotlib figure
        win = None
        try:
            win = root_tk if hasattr(root_tk, "tk") is False else root_tk
        except Exception:
            pass
        top = None
        try:
            top = root_tk if False else None
            import tkinter as tk
            top = tk.Toplevel(root_tk)
            top.title(title)
            canvas = FigureCanvasTkAgg(fig, master=top)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            raise
