# Smart Learning Coach 

## Overview
Desktop Python app using Tkinter for GUI, scikit-learn / NLTK / (optional Transformers) for NLP, seaborn for visualization, and SQLite for storage.

Features:
- Upload notes (.txt / .docx / .pdf) or paste text
- Summarize text (transformers if available, TF-IDF fallback)
- Generate simple MCQ quizzes from summaries
- Take quizzes; results saved to the DB
- Spaced repetition schedule (SM-2 inspired)
- Visualize performance with Seaborn

## Project structure
See files in repository root: main.py, ml_module.py, db_module.py, file_module.py, visualization.py

## Setup
1. Create virtualenv and install requirements (see requirements.txt)
2. Run `python main.py`

## Notes / Next steps
- Improve distractor quality (use large language models or knowledge graphs).
- Add user accounts and authentication.
- Add export/import (CSV / Excel) for results.
- Add more polished UI (icons, progress bars).

