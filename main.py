import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from file_module import read_text_from_path
from ml_module import Summarizer, QuizGenerator, SpacedRepetitionScheduler
from db_module import Database
from visualization import Visualization

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
os.makedirs(MODELS_DIR, exist_ok=True)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize modules
db = Database(os.path.join(PROJECT_ROOT, "data", "slc.db"))
summarizer = Summarizer(models_dir=MODELS_DIR)
quizgen = QuizGenerator()
scheduler = SpacedRepetitionScheduler(db)
viz = Visualization(db)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Learning Coach")
        self.geometry("1000x650")
        self.configure(bg="white")
        self.resizable(True, True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="white", foreground="black", font=("Segoe UI", 10))
        style.configure("TNotebook.Tab", padding=[10, 5])

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_upload = ttk.Frame(notebook)
        self.tab_quiz = ttk.Frame(notebook)
        self.tab_dashboard = ttk.Frame(notebook)
        self.tab_settings = ttk.Frame(notebook)

        notebook.add(self.tab_upload, text="Notes & Summaries")
        notebook.add(self.tab_quiz, text="Quizzes")
        notebook.add(self.tab_dashboard, text="Dashboard")
        notebook.add(self.tab_settings, text="Settings")

        self._build_upload_tab()
        self._build_quiz_tab()
        self._build_dashboard_tab()
        self._build_settings_tab()

        self.loaded_text = ""
        self.current_topic = ""

    def _build_upload_tab(self):
        frame = self.tab_upload

        left = ttk.Frame(frame, padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Upload Notes").pack(anchor=tk.W)
        ttk.Button(left, text="Select file (.txt/.docx/.pdf)", command=self._on_upload).pack(fill=tk.X, pady=5)

        ttk.Label(left, text="Or paste text below:").pack(anchor=tk.W, pady=(10, 0))
        self.txt_paste = tk.Text(left, width=45, height=15, bg="white", fg="black", wrap=tk.WORD)
        self.txt_paste.pack(pady=5)

        ttk.Label(left, text="Topic name:").pack(anchor=tk.W)
        self.entry_topic = ttk.Entry(left)
        self.entry_topic.pack(fill=tk.X, pady=3)

        ttk.Button(left, text="Summarize & Save", command=self._on_summarize).pack(fill=tk.X, pady=5)
        ttk.Button(left, text="Generate Quiz from Summary", command=self._on_generate_quiz).pack(fill=tk.X, pady=5)

        right = ttk.Frame(frame, padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        ttk.Label(right, text="Summary / Notes Preview").pack(anchor=tk.W)
        self.txt_summary = tk.Text(right, wrap=tk.WORD, bg="white", fg="black")
        self.txt_summary.pack(fill=tk.BOTH, expand=True)

    def _build_quiz_tab(self):
        frame = self.tab_quiz
        top = ttk.Frame(frame, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Available Topics:").pack(side=tk.LEFT)
        self.combo_topics = ttk.Combobox(top, values=db.get_all_topics(), state="readonly", width=50)
        self.combo_topics.pack(side=tk.LEFT, padx=5)
        self.combo_topics.bind("<<ComboboxSelected>>", lambda e: self._on_topic_selected())

        ttk.Button(top, text="Refresh Topics", command=self._refresh_topics).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Start Quiz", command=self._on_start_quiz).pack(side=tk.RIGHT)

        self.quiz_frame = ttk.Frame(frame, padding=10)
        self.quiz_frame.pack(fill=tk.BOTH, expand=True)

    def _build_dashboard_tab(self):
        frame = self.tab_dashboard
        top = ttk.Frame(frame, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(top, text="Show Performance Chart", command=self._show_performance).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Show Forgetfulness Trend", command=self._show_forgetfulness).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Show Topic Breakdown", command=self._show_topic_breakdown).pack(side=tk.LEFT, padx=5)
        self.viz_canvas = ttk.Frame(frame, padding=10)
        self.viz_canvas.pack(fill=tk.BOTH, expand=True)

    def _build_settings_tab(self):
        frame = self.tab_settings
        ttk.Label(frame, text="Settings / Debug").pack(anchor=tk.W, padx=10, pady=10)
        ttk.Button(frame, text="Run DB Integrity Check", command=self._db_check).pack(anchor=tk.W, padx=10, pady=5)

    def _on_upload(self):
        path = filedialog.askopenfilename(
            filetypes=[("All supported", "*.txt *.docx *.pdf"), ("Text files", "*.txt"), ("Word", "*.docx"), ("PDF", "*.pdf")]
        )
        if not path:
            return
        try:
            text = read_text_from_path(path)
            self.txt_paste.delete("1.0", tk.END)
            self.txt_paste.insert(tk.END, text)
            messagebox.showinfo("Loaded", f"Loaded {os.path.basename(path)} (length {len(text)} chars)")
        except Exception as e:
            messagebox.showerror("Error reading file", str(e))

    def _on_summarize(self):
        topic = self.entry_topic.get().strip()
        text = self.txt_paste.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No text", "Please paste or upload notes before summarizing.")
            return
        if not topic:
            messagebox.showwarning("No topic", "Please enter a topic name.")
            return

        def job():
            try:
                self._set_status("Summarizing...")
                summary = summarizer.summarize(text)
                self.txt_summary.delete("1.0", tk.END)
                self.txt_summary.insert(tk.END, summary)
                db.insert_or_update_note(topic, text, summary)
                self._set_status("Saved summary to DB.")
                self._refresh_topics()
            except Exception as e:
                messagebox.showerror("Summarization error", str(e))
            finally:
                self._set_status("Ready")

        threading.Thread(target=job, daemon=True).start()

    def _on_generate_quiz(self):
        topic = self.entry_topic.get().strip()
        if not topic:
            messagebox.showwarning("No topic", "Please enter/select a topic name first.")
            return
        note = db.get_note_by_topic(topic)
        if not note:
            messagebox.showwarning("No notes", "No saved note for this topic. Please summarize/save first.")
            return

        def job():
            try:
                self._set_status("Generating quiz...")
                summary = note["summary"]
                q_items = quizgen.generate_mcq_from_text(summary, num_questions=5)
                db.save_quiz(topic, q_items)
                messagebox.showinfo("Quiz Generated", f"Generated {len(q_items)} questions for topic '{topic}'.")
                self._set_status("Quiz saved to DB.")
                self._refresh_topics()
            except Exception as e:
                messagebox.showerror("Quiz generation error", str(e))
            finally:
                self._set_status("Ready")

        threading.Thread(target=job, daemon=True).start()

    def _refresh_topics(self):
        topics = db.get_all_topics()
        self.combo_topics['values'] = topics
        if topics:
            self.combo_topics.current(0)

    def _on_topic_selected(self):
        sel = self.combo_topics.get()
        self.entry_topic.delete(0, tk.END)
        self.entry_topic.insert(0, sel)
        note = db.get_note_by_topic(sel)
        if note:
            self.txt_summary.delete("1.0", tk.END)
            self.txt_summary.insert(tk.END, note["summary"])

    def _on_start_quiz(self):
        topic = self.combo_topics.get()
        if not topic:
            messagebox.showwarning("Choose topic", "Please select a topic.")
            return
        quiz_items = db.get_quiz_for_topic(topic)
        if not quiz_items:
            messagebox.showwarning("No quiz", "No generated quiz for this topic. Generate one first.")
            return

        for child in self.quiz_frame.winfo_children():
            child.destroy()

        ttk.Label(self.quiz_frame, text=f"Quiz: {topic}", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W)
        q_vars = []
        for i, q in enumerate(quiz_items):
            frame = ttk.Frame(self.quiz_frame)
            frame.pack(anchor=tk.W, pady=5, fill=tk.X)
            ttk.Label(frame, text=f"{i + 1}. {q['question']}", wraplength=900).pack(anchor=tk.W)
            var = tk.StringVar(value="")
            q_vars.append((var, q))
            for opt in q['options']:
                ttk.Radiobutton(frame, text=opt, value=opt, variable=var).pack(anchor=tk.W)

        def submit():
            score = 0
            results = []
            for var, q in q_vars:
                sel = var.get()
                correct = q["answer"]
                is_correct = (sel == correct)
                results.append({"question": q["question"], "selected": sel, "correct": correct, "is_correct": is_correct})
                if is_correct:
                    score += 1

            db.save_quiz_result(topic, results, score)
            scheduler.update_schedule_after_quiz(topic, score)
            messagebox.showinfo("Result", f"You scored {score} / {len(q_vars)}")
            self._refresh_topics()
            self._show_quiz_results(results)

        ttk.Button(self.quiz_frame, text="Submit", command=submit).pack(pady=10)

    def _show_quiz_results(self, results):
        win = tk.Toplevel(self)
        win.title("Quiz Results")
        text = tk.Text(win, width=80, height=25, bg="white", fg="black", wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        for r in results:
            text.insert(tk.END, f"Q: {r['question']}\nYour: {r['selected']}\nCorrect: {r['correct']}\n\n")

    def _show_performance(self):
        try:
            fig = viz.plot_performance_over_time()
            viz.show_figure_in_toplevel(self, fig, title="Performance Over Time")
        except Exception as e:
            messagebox.showerror("Visualization error", str(e))

    def _show_forgetfulness(self):
        try:
            fig = viz.plot_forgetfulness_trend()
            viz.show_figure_in_toplevel(self, fig, title="Forgetfulness Trend")
        except Exception as e:
            messagebox.showerror("Visualization error", str(e))

    def _show_topic_breakdown(self):
        try:
            fig = viz.plot_topic_strengths()
            viz.show_figure_in_toplevel(self, fig, title="Topic Strengths")
        except Exception as e:
            messagebox.showerror("Visualization error", str(e))

    def _db_check(self):
        ok, msg = db.run_integrity_check()
        messagebox.showinfo("DB Integrity", f"OK: {ok}\n{msg}")

    def _set_status(self, msg):
        self.title(f"Smart Learning Coach — {msg}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
