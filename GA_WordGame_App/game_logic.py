"""Pure game logic for the GA Word Game minigame.

Mirrors the "Genetic Algorithm: The Word Game" in-class activity from
IN2041 (GA_WordGame.tex): discover a hidden word by hand-running a tiny
genetic algorithm - gene = one letter, chromosome = a candidate word,
fitness = letters correct AND in the right position.

Every random choice (initial population, mutated letters) is driven by an
explicit random.Random instance so a game can be reproduced from a shared
code, same convention as the other minigames in this repo.
"""

import hashlib
import random
import string

ALPHABET = string.ascii_uppercase

POP_SIZE_CHOICES = [4, 6, 8]  # kept even so parent pairs divide the population evenly
MIN_WORD_LEN = 4
MAX_WORD_LEN = 8


def new_game_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def code_to_seed(code: str) -> int:
    """Deterministic seed from a share code, so the same code always
    regenerates the same initial population."""
    digest = hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def make_rng(code: str) -> random.Random:
    """A fresh, explicit RNG - seeded from `code` if given, otherwise
    unpredictable (mirrors random.Random() default)."""
    code = (code or "").strip()
    return random.Random(code_to_seed(code)) if code else random.Random()


def clean_hidden_word(raw: str) -> str:
    """Keeps letters only, uppercased - strips anything a player might
    accidentally type (spaces, punctuation, digits)."""
    return "".join(ch for ch in raw.upper() if ch.isalpha())


def random_individual(length: int, rng: random.Random) -> str:
    return "".join(rng.choice(ALPHABET) for _ in range(length))


def random_population(size: int, length: int, rng: random.Random) -> list:
    return [random_individual(length, rng) for _ in range(size)]


def fitness(word: str, hidden: str) -> int:
    """Letters correct AND in the right position - the slide's fitness
    function. No credit for a correct letter in the wrong slot."""
    return sum(1 for a, b in zip(word, hidden) if a == b)


def crossover(parent_a: str, parent_b: str, cut: int) -> tuple:
    """Single-point crossover: cut is how many letters child 1 takes from
    parent A's head (1 <= cut <= len-1) before swapping tails."""
    child1 = parent_a[:cut] + parent_b[cut:]
    child2 = parent_b[:cut] + parent_a[cut:]
    return child1, child2


def mutate(word: str, position: int, rng: random.Random) -> str:
    """Replaces the letter at `position` with a different random letter."""
    current = word[position]
    new_letter = rng.choice([c for c in ALPHABET if c != current])
    return word[:position] + new_letter + word[position + 1:]


def population_stats(words: list, hidden: str) -> dict:
    fits = [fitness(w, hidden) for w in words]
    return {"best": max(fits), "avg": sum(fits) / len(fits), "fits": fits}
