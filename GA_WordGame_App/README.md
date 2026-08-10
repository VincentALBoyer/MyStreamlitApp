# GA Word Game

A Streamlit companion for **IN2041 - Metaheuristics**, built around the
*"Genetic Algorithm: The Word Game"* in-class activity
(`GA_WordGame.tex`): discover a hidden word by hand-running a tiny genetic
algorithm - gene = one letter, chromosome = a candidate word.

Two fitness functions are selectable at setup, to illustrate how scoring
design shapes a GA's search:
- **Exact match (classic)** - the slide's original rule: 1 point only for a
  letter in the exact right position. A near-miss word (right letters,
  wrong order) can score 0 - a harsh, deceptive landscape.
- **Partial credit (alphabet distance)** - wrong letters still earn a
  fractional point based on how close they are alphabetically to the
  correct letter, giving the GA a smoother slope to climb. Only a perfect
  match ever reaches the full score.

Unlike the worksheet's slide deck, every GA decision here is made by the
player, not by chance: **you** click the parents, **you** pick the crossover
cut point, and **you** click which letters to mutate (the app rolls the
actual replacement letters). Fitness is computed automatically and is the
only feedback you get - no letter-by-letter hints.

## How it plays

1. **Setup** - type a secret word (kept masked), pick a population size
   (4, 6, or 8 - always even, so parent pairs divide it evenly), and pick a
   scoring method. An initial population of random words is generated.
2. **Breeding** - each round, repeatedly:
   - click **2 members** of the population to select them as parents (a 3rd
     click auto-deselects the oldest pick, keeping the most recent 2),
   - drag the **crossover cut** slider - the 2 children update live,
   - optionally click any number of **letters** on each child to mutate
     (the app rolls the replacement letter for each one you pick),
   - add the pair to the offspring pool - until it matches the population
     size.
3. **Survivor selection** - once the offspring pool is full, choose exactly
   `N` individuals from the combined population + offspring pool to carry
   into the next generation. A "select best N" shortcut is available to
   compare pure elitism against your own manual picks.
4. Repeat until an individual's fitness matches the word length, or stop
   manually at any time.
5. **Report** - reveals the hidden word and plots best/average fitness per
   generation, plus total evaluations and elapsed time.

## Run it

```bash
streamlit run GA_WordGame_App/app.py
```

## Files

- `app.py` - Streamlit UI and game state machine.
- `game_logic.py` - fitness, crossover, mutation, and population generation
  (pure functions, unit-tested in `../test_ga_wordgame_logic.py`).
- `plotting.py` - Plotly fitness-over-generations chart.
