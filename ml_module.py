import os
import math
import random
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta

# For lightweight summarization
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

# Ensure NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)  # Added for new NLTK versions
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# optional: transformers summarizer
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# persistence
import joblib


# ----------------------------------------------------------------------
# Summarizer Class
# ----------------------------------------------------------------------
class Summarizer:
    def __init__(self, models_dir: str = "models", use_transformers: bool = False):
        self.models_dir = models_dir
        self.use_transformers = use_transformers and TRANSFORMERS_AVAILABLE
        self.tfidf_vectorizer = None

        # if transformer models available and selected, load pipeline lazily
        self._summarizer_pipeline = None
        if self.use_transformers:
            try:
                self._summarizer_pipeline = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
            except Exception:
                self._summarizer_pipeline = None

    def summarize(self, text: str, max_sentences: int = 5) -> str:
        text = text.strip()
        if not text:
            return ""

        # try transformer if available
        if self.use_transformers and self._summarizer_pipeline:
            try:
                if len(text.split()) < 800:
                    out = self._summarizer_pipeline(text, max_length=200, min_length=60, truncation=True)
                    return out[0]['summary_text']
                else:
                    sents = sent_tokenize(text)
                    chunks, chunk = [], ""
                    for s in sents:
                        if len((chunk + " " + s).split()) > 500:
                            chunks.append(chunk)
                            chunk = s
                        else:
                            chunk = chunk + " " + s
                    if chunk:
                        chunks.append(chunk)
                    summaries = []
                    for ch in chunks:
                        out = self._summarizer_pipeline(ch, max_length=120, min_length=30, truncation=True)
                        summaries.append(out[0]['summary_text'])
                    combined = " ".join(summaries)
                    out = self._summarizer_pipeline(combined, max_length=200, min_length=60, truncation=True)
                    return out[0]['summary_text']
            except Exception:
                pass  # fallback to TF-IDF summarizer

        # TF-IDF fallback summarizer
        sents = sent_tokenize(text)
        if len(sents) <= max_sentences:
            return text
        tfidf = TfidfVectorizer(stop_words=stopwords.words('english'))
        try:
            X = tfidf.fit_transform(sents)
            scores = X.sum(axis=1).A1
            ranked = sorted(((i, s, scores[i]) for i, s in enumerate(sents)), key=lambda t: t[2], reverse=True)
            top = sorted(ranked[:max_sentences], key=lambda t: t[0])
            summary = " ".join([t[1] for t in top])
            return summary
        except Exception:
            return " ".join(sents[:max_sentences])


# ----------------------------------------------------------------------
# QuizGenerator Class
# ----------------------------------------------------------------------
import random
import nltk
from nltk.tokenize import sent_tokenize
from transformers import pipeline

# Make sure nltk punkt is available
nltk.download('punkt', quiet=True)

class QuizGenerator:
    def __init__(self):
        # Using a small but context-aware model for question generation
        try:
            self.qg_pipeline = pipeline(
                "text2text-generation",
                model="valhalla/t5-small-qg-prepend",
                tokenizer="valhalla/t5-small-qg-prepend"
            )
        except Exception:
            self.qg_pipeline = None

    def generate_mcq_from_text(self, text, num_questions=5):
        """
        Generates meaningful, topic-aware MCQs from given text.
        """
        if not text or len(text.split()) < 30:
            return []

        # Pick relevant sentences (filter out junk)
        sentences = sent_tokenize(text)
        sentences = [s for s in sentences if 8 < len(s.split()) < 40]
        random.shuffle(sentences)

        questions = []
        used_qs = set()

        if self.qg_pipeline:
            # Model-based QG (if transformer works)
            for sent in sentences[:num_questions]:
                try:
                    result = self.qg_pipeline(f"generate question: {sent}")
                    q_text = result[0]["generated_text"].strip()
                    if q_text and q_text not in used_qs:
                        answer = self._extract_answer(sent)
                        options = self._generate_options(answer, text)
                        questions.append({
                            "question": q_text,
                            "options": options,
                            "answer": answer
                        })
                        used_qs.add(q_text)
                except Exception:
                    continue

        # Fallback if model isn't available
        if not questions:
            for sent in sentences[:num_questions]:
                words = sent.split()
                if len(words) > 6:
                    blank_index = random.randint(2, len(words) - 3)
                    answer = words[blank_index].strip(".,")
                    words[blank_index] = "____"
                    q_text = " ".join(words)
                    options = self._generate_options(answer, text)
                    questions.append({
                        "question": q_text,
                        "options": options,
                        "answer": answer
                    })
        return questions

    def _extract_answer(self, sentence):
        """
        Naive answer extractor (last noun or keyword in sentence).
        """
        tokens = nltk.word_tokenize(sentence)
        pos_tags = nltk.pos_tag(tokens)
        nouns = [word for word, pos in pos_tags if pos.startswith("NN")]
        return nouns[-1] if nouns else tokens[-1]

    def _generate_options(self, correct_answer, text):
        """
        Creates multiple-choice options, ensuring semantic similarity.
        """
        words = list(set([w for w in text.split() if w.isalpha()]))
        distractors = random.sample(words, min(3, len(words))) if len(words) > 3 else []
        distractors = [w for w in distractors if w.lower() != correct_answer.lower()]
        all_opts = [correct_answer] + distractors[:3]
        random.shuffle(all_opts)
        return all_opts



# ----------------------------------------------------------------------
# Spaced Repetition Scheduler
# ----------------------------------------------------------------------
class SpacedRepetitionScheduler:
    """Simple SM-2 inspired scheduler."""
    def __init__(self, db):
        self.db = db

    def update_schedule_after_quiz(self, topic: str, score: float, max_score: float = 5.0):
        quality = int(round(min(5.0, score) / max_score * 5))
        entry = self.db.get_schedule(topic)
        if not entry:
            interval = 1
            easiness = 2.5
            repetition = 0
        else:
            interval = entry['interval_days']
            easiness = entry['easiness']
            repetition = entry['repetition_count']

        if quality < 3:
            repetition = 0
            interval = 1
        else:
            repetition += 1
            if repetition == 1:
                interval = 1
            elif repetition == 2:
                interval = 6
            else:
                interval = int(round(interval * easiness))

        q = quality
        new_e = easiness + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if new_e < 1.3:
            new_e = 1.3
        next_review_date = (datetime.utcnow() + timedelta(days=max(1, interval))).date().isoformat()
        self.db.upsert_schedule(topic, int(interval), float(new_e), int(repetition), next_review_date)

    def get_upcoming_reviews(self, days: int = 7):
        schedules = self.db.get_all_schedules()
        out = []
        for s in schedules:
            if s['next_review_date']:
                d = datetime.fromisoformat(s['next_review_date'])
                delta = (d.date() - datetime.utcnow().date()).days
                if delta <= days:
                    out.append(s)
        return out
