import os
import random
import math
from typing import List, Dict, Any
from datetime import datetime, timedelta

# NLP and ML
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

# Ensure NLTK data
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True) # Dependency for tokenization
nltk.download('averaged_perceptron_tagger_eng', quiet=True) # For POS tagging
nltk.download('stopwords', quiet=True) # For summarizer/quizzer
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
from nltk.corpus import stopwords

class Summarizer:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir

    def summarize(self, text: str, max_sentences: int = 6) -> str:
        text = text.strip()
        if not text:
            return ""
        sents = sent_tokenize(text)
        if len(sents) <= max_sentences:
            return " ".join(sents)
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

class QuizGenerator:
    def __init__(self):
        self.stopwords = set(stopwords.words('english'))

    def _clean_option_list(self, options):
        """
        Normalize options: remove duplicates case-insensitive and maintain capitalized formatting.
        """
        seen = set()
        cleaned = []
        for o in options:
            if not isinstance(o, str):
                continue
            norm = o.strip()
            if not norm:
                continue
            key = norm.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(norm.capitalize())
        return cleaned

    def _get_distractors_simple(self, answer, text, n=3):
        words = [w for w in set(word_tokenize(text)) if w.isalpha() and w.lower() not in self.stopwords and w.lower() != answer.lower()]
        random.shuffle(words)
        return [w.capitalize() for w in words[:n]]

    def generate_mcq_from_text(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Generate contextual MCQs from summary text.
        This is an extractive approach (no heavy LLMs) and tries to pick meaningful nouns as answers.
        """
        text = text.strip()
        if not text:
            return []
        sents = sent_tokenize(text)
        # filter sentences with enough content
        sents = [s for s in sents if len(word_tokenize(s)) > 6]
        if not sents:
            return []
        random.shuffle(sents)
        questions = []
        used_answers = set()
        for sent in sents:
            # find candidate answer nouns
            tokens = word_tokenize(sent)
            tags = nltk.pos_tag(tokens)
            nouns = [w for w, pos in tags if pos.startswith("NN") and w.isalpha() and w.lower() not in self.stopwords]
            if not nouns:
                continue
            # pick the most informative noun (longest)
            nouns = sorted(nouns, key=lambda x: -len(x))
            answer = nouns[0]
            if answer.lower() in used_answers:
                continue
            used_answers.add(answer.lower())
            question_text = sent.replace(answer, "_____")
            distractors = self._get_distractors_simple(answer, text, n=6)
            # ensure answer not in distractors
            distractors = [d for d in distractors if d.lower() != answer.lower()]
            options = [answer] + distractors[:3]
            options = self._clean_option_list(options)
            if answer.capitalize() not in options:
                options.append(answer.capitalize())
            # final dedupe and trim
            options = options[:4]
            random.shuffle(options)
            questions.append({"question": question_text, "answer": answer.capitalize(), "options": options})
            if len(questions) >= num_questions:
                break

        # fallback: simple blanks if not enough
        i = 0
        while len(questions) < num_questions and i < len(sents):
            sent = sents[i]
            words = [w for w in word_tokenize(sent) if w.isalpha()]
            if len(words) > 3:
                idx = len(words)//2
                ans = words[idx]
                q = sent.replace(ans, "_____")
                opts = self._get_distractors_simple(ans, text, n=6)[:3] + [ans]
                opts = self._clean_option_list(opts)
                random.shuffle(opts)
                questions.append({"question": q, "answer": ans.capitalize(), "options": opts[:4]})
            i += 1

        return questions[:num_questions]

class SpacedRepetitionScheduler:
    def __init__(self, db):
        self.db = db

    def update_schedule_after_quiz(self, topic: str, score: float, max_score: float = 5.0):
        # map raw score to quality 0-5
        try:
            quality = int(round(min(max_score, score) / max_score * 5))
        except Exception:
            quality = 0
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
            if s.get('next_review_date'):
                d = datetime.fromisoformat(s['next_review_date'])
                delta = (d.date() - datetime.utcnow().date()).days
                if delta <= days:
                    out.append(s)
        return out
