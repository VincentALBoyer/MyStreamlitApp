import os
os.environ.pop("SSLKEYLOGFILE", None)

import time

import pandas as pd
import streamlit as st

import game_logic as gl
import plotting as pl

st.set_page_config(page_title="GA Word Game", page_icon="\U0001f9ec", layout="wide")

CONCEPTS = [
    (
        "Gene, Chromosome & Fitness",
        "A **gene** is one letter; a **chromosome** is a full candidate word. **Fitness** "
        "counts letters that are correct *and* in the right position - there's no partial "
        "credit for a right letter in the wrong slot, so the population only learns from "
        "that single number each round.",
    ),
    (
        "Selection: Choosing Parents",
        "Selection decides which individuals get to reproduce. Always picking the two "
        "fittest narrows the gene pool fast; occasionally breeding a weaker individual "
        "keeps letters in play that might matter later.",
    ),
    (
        "Crossover",
        "Single-point crossover cuts both parents at the same position and swaps tails, so "
        "each child blends letters from both parents. Where you cut controls how much of "
        "each parent survives into the children.",
    ),
    (
        "Mutation",
        "Mutation randomly replaces a gene (letter) in a child. It's the GA's only source of "
        "brand-new genetic material - without it, the population can only ever recombine "
        "letters already present in the initial population. Mutating more genes explores "
        "further from the parents, but also destroys more of what crossover just built.",
    ),
    (
        "Survivor Selection & Elitism",
        "After breeding, you choose who survives into the next generation. Keeping only the "
        "best (elitism) locks in progress fast but can lose diversity; keeping weaker "
        "individuals too preserves diversity at the cost of slower convergence.",
    ),
    (
        "Why does population size matter?",
        "A larger population explores more of the search space per generation (more "
        "diversity) but costs more fitness evaluations per round - the same "
        "quality-vs-cost trade-off you saw with search strategies.",
    ),
]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "phase": "setup",
        "hidden_word": "",
        "word_length": 6,
        "pop_size": 6,
        "rng": None,
        "population": [],
        "round_idx": 0,
        "offspring": [],
        "history": [],
        "total_evaluations": 0,
        "found": False,
        "winning_word": None,
        "found_generation": None,
        "stopped_manually": False,
        "start_time": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def start_game(word: str, pop_size: int, code: str):
    rng = gl.make_rng(code)
    population = gl.random_population(pop_size, len(word), rng)
    stats = gl.population_stats(population, word)

    st.session_state.update({
        "hidden_word": word,
        "word_length": len(word),
        "pop_size": pop_size,
        "rng": rng,
        "population": population,
        "round_idx": 0,
        "offspring": [],
        "history": [{"generation": 0, "best": stats["best"], "avg": stats["avg"]}],
        "total_evaluations": pop_size,
        "found": False,
        "winning_word": None,
        "found_generation": None,
        "stopped_manually": False,
        "start_time": time.time(),
        "phase": "breeding",
    })

    winner = next((w for w in population if gl.fitness(w, word) == len(word)), None)
    if winner:
        st.session_state.found = True
        st.session_state.winning_word = winner
        st.session_state.found_generation = 0
        st.session_state.phase = "finished"


def stop_game():
    st.session_state.stopped_manually = True
    st.session_state.phase = "finished"


def toggle_parent(i: int, order_key: str):
    """Toggles population member `i` in/out of the parent selection, tracked
    in click order so a 3rd pick can auto-drop the oldest one."""
    order = st.session_state.get(order_key, [])
    if i in order:
        order.remove(i)
    else:
        order.append(i)
        if len(order) > 2:
            order.pop(0)
    st.session_state[order_key] = order


def randomize_mutation(key: str, length: int):
    """Rolls each gene independently with probability 1/length - matching
    the classic recommendation of mutating about one letter per child on
    average, while occasionally landing on 0 or several."""
    rng = st.session_state.rng
    p = 1.0 / length
    st.session_state[key] = [i for i in range(length) if rng.random() < p]


def commit_pair(a_idx: int, b_idx: int, cut: int, mutate_positions1: list, mutate_positions2: list):
    hidden = st.session_state.hidden_word
    rng = st.session_state.rng
    pop = st.session_state.population
    child1, child2 = gl.crossover(pop[a_idx], pop[b_idx], cut)

    for pos in sorted(mutate_positions1):
        child1 = gl.mutate(child1, pos, rng)
    for pos in sorted(mutate_positions2):
        child2 = gl.mutate(child2, pos, rng)

    for word, mutated in ((child1, set(mutate_positions1)), (child2, set(mutate_positions2))):
        st.session_state.offspring.append({
            "word": word, "fitness": gl.fitness(word, hidden), "mutated": mutated,
        })
    st.session_state.total_evaluations += 2

    gen = st.session_state.round_idx + 1
    winner = next((o for o in st.session_state.offspring if o["fitness"] == st.session_state.word_length), None)
    if winner:
        fits = [o["fitness"] for o in st.session_state.offspring]
        st.session_state.history.append({"generation": gen, "best": max(fits), "avg": sum(fits) / len(fits)})
        st.session_state.found = True
        st.session_state.winning_word = winner["word"]
        st.session_state.found_generation = gen
        st.session_state.phase = "finished"
    elif len(st.session_state.offspring) >= st.session_state.pop_size:
        st.session_state.phase = "selection"


def undo_last_pair():
    st.session_state.offspring = st.session_state.offspring[:-2]
    st.session_state.total_evaluations -= 2


def auto_select_best():
    hidden = st.session_state.hidden_word
    round_idx = st.session_state.round_idx
    pop_size = st.session_state.pop_size

    # source rank 0 = offspring, 1 = population - sorting on it after fitness
    # means offspring wins any fitness tie at the pop_size cutoff.
    candidates = [(f"selpop_{round_idx}_{i}", gl.fitness(w, hidden), 1) for i, w in enumerate(st.session_state.population)]
    candidates += [(f"seloff_{round_idx}_{i}", o["fitness"], 0) for i, o in enumerate(st.session_state.offspring)]
    candidates.sort(key=lambda t: (-t[1], t[2]))
    keep = {k for k, _, _ in candidates[:pop_size]}
    for k, _, _ in candidates:
        st.session_state[k] = k in keep


def clear_selection():
    round_idx = st.session_state.round_idx
    for i in range(len(st.session_state.population)):
        st.session_state[f"selpop_{round_idx}_{i}"] = False
    for i in range(len(st.session_state.offspring)):
        st.session_state[f"seloff_{round_idx}_{i}"] = False


def confirm_selection(chosen_words: list):
    hidden = st.session_state.hidden_word
    gen = st.session_state.round_idx + 1
    fits = [gl.fitness(w, hidden) for w in chosen_words]
    st.session_state.history.append({"generation": gen, "best": max(fits), "avg": sum(fits) / len(fits)})
    st.session_state.population = sorted(chosen_words, key=lambda w: -gl.fitness(w, hidden))
    st.session_state.round_idx = gen
    st.session_state.offspring = []
    st.session_state.phase = "breeding"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def word_tiles_html(word: str, cut=None, mutated=None, size=32) -> str:
    """Renders `word` as a row of Wordle-style letter tiles. `cut` draws a
    divider after that many letters (for the crossover workspace); `mutated`
    highlights gene positions changed by mutation."""
    mutated = mutated or set()
    parts = []
    for i, ch in enumerate(word):
        if i in mutated:
            style = "background:#eb6834;color:#fff;border:2px solid #eb6834;"
        else:
            style = "background:transparent;color:inherit;border:2px solid #2a78d6;"
        parts.append(
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:{size}px;height:{size}px;margin:1px;border-radius:5px;font-weight:700;'
            f'font-family:ui-monospace,Consolas,monospace;font-size:{int(size * 0.48)}px;'
            f'vertical-align:middle;{style}">{ch}</span>'
        )
        if cut is not None and i == cut - 1:
            parts.append(
                f'<span style="display:inline-block;width:3px;height:{size}px;'
                f'background:#c3c2b7;margin:0 5px;vertical-align:middle;border-radius:2px;"></span>'
            )
    return '<span style="white-space:nowrap;">' + "".join(parts) + "</span>"


def render_status_bar():
    L = st.session_state.word_length
    gen = st.session_state.round_idx + 1
    label = "Breeding offspring" if st.session_state.phase == "breeding" else "Selecting survivors"

    cols = st.columns([2.2, 1, 1, 1])
    cols[0].subheader(f"Generation {gen} — {label}")
    cols[1].metric("Population size", st.session_state.pop_size)
    cols[2].metric("Target fitness", L)
    cols[3].metric("Elapsed", f"{time.time() - st.session_state.start_time:.0f}s")
    st.divider()


def render_setup():
    st.title("\U0001f9ec GA Word Game")
    st.caption("A hands-on Genetic Algorithm minigame for IN2041 - Metaheuristics")
    st.markdown(
        "Enter a secret word below. You'll then run a tiny genetic algorithm **by hand**: pick "
        "parents, choose where to cut for crossover, and decide which gene to mutate, evolving "
        "a population of random words until one matches. Fitness is just the number of letters "
        "correct **and in the right position** - no other hints are given, just like the "
        "in-class activity."
    )

    raw_word = st.text_input(
        "Hidden word (kept secret - shown as dots)", type="password", max_chars=gl.MAX_WORD_LEN,
        help=f"Letters only, {gl.MIN_WORD_LEN}-{gl.MAX_WORD_LEN} letters (e.g. PLANET).",
    )
    pop_size = st.radio(
        "Population size (kept even for clean parent pairing)", gl.POP_SIZE_CHOICES, index=1, horizontal=True,
    )
    code = st.text_input(
        "Random seed / class code (optional)", value="", placeholder="Leave blank for a random start population",
        help="Use the same code as a classmate to start from the exact same random population.",
    )

    if st.button("▶ Start Game", type="primary"):
        word = gl.clean_hidden_word(raw_word)
        if not (gl.MIN_WORD_LEN <= len(word) <= gl.MAX_WORD_LEN):
            st.error(f"Enter a hidden word between {gl.MIN_WORD_LEN} and {gl.MAX_WORD_LEN} letters (letters only).")
        else:
            start_game(word, pop_size, code)
            st.rerun()


def render_breeding():
    hidden = st.session_state.hidden_word
    L = st.session_state.word_length
    pop = st.session_state.population
    offspring = st.session_state.offspring
    pop_size = st.session_state.pop_size
    round_idx = st.session_state.round_idx
    pair_no = len(offspring) // 2

    left, right = st.columns([0.42, 0.58])

    order_key = f"parent_order_{round_idx}_{pair_no}"
    selected_parents = st.session_state.get(order_key, [])

    with left:
        st.markdown("**Current Population**")
        st.caption("Click a member's M# to select it as a parent.")
        for i, w in enumerate(pop):
            fit = gl.fitness(w, hidden)
            c0, c1, c2 = st.columns([0.16, 0.56, 0.28])
            is_selected = i in selected_parents
            if c0.button(
                f"M{i + 1}", key=f"parent_btn_{round_idx}_{pair_no}_{i}",
                type="primary" if is_selected else "secondary", width="stretch",
            ):
                toggle_parent(i, order_key)
                st.rerun()
            c1.markdown(word_tiles_html(w, size=26), unsafe_allow_html=True)
            c2.markdown(f"Fitness **{fit}/{L}**")

        st.caption(f"Offspring created: {len(offspring)} / {pop_size}")
        st.progress(len(offspring) / pop_size)

        if offspring:
            st.markdown("**Offspring pool so far**")
            for i, o in enumerate(offspring):
                c1, c2 = st.columns([0.72, 0.28])
                c1.markdown(f"**C{i + 1}** &nbsp; " + word_tiles_html(o["word"], mutated=o["mutated"], size=26), unsafe_allow_html=True)
                c2.markdown(f"Fitness **{o['fitness']}/{L}**")
            if st.button("↺ Undo last pair"):
                undo_last_pair()
                st.rerun()

    with right:
        st.markdown("**Breeding Workspace**")

        if len(selected_parents) < 2:
            st.info("← Click 2 members in the population list to select them as parents.")
            return

        a_idx, b_idx = sorted(selected_parents)
        cut = st.slider(
            "Crossover cut position", 1, L - 1, L // 2, key=f"cutpos_{round_idx}_{pair_no}",
            help="Child 1 takes letters 1..cut from Parent A then the rest from Parent B. Child 2 gets the opposite split.",
        )
        child1, child2 = gl.crossover(pop[a_idx], pop[b_idx], cut)

        st.caption(f"Crossing M{a_idx + 1} × M{b_idx + 1} at cut position {cut}")
        st.markdown("A &nbsp; " + word_tiles_html(pop[a_idx], cut=cut, size=22), unsafe_allow_html=True)
        st.markdown("B &nbsp; " + word_tiles_html(pop[b_idx], cut=cut, size=22), unsafe_allow_html=True)

        randomize_help = "Randomly decide which genes mutate (each gene has an independent ~1/N chance)."
        mc1, mc2 = st.columns(2)
        with mc1:
            f1a, f1b = st.columns([0.72, 0.28])
            f1a.markdown(f"Child 1 &nbsp; fitness **{gl.fitness(child1, hidden)}/{L}**")
            mut1_key = f"mut1_pills_{round_idx}_{pair_no}"
            if f1b.button("\U0001f3b2", key=f"rand1_{round_idx}_{pair_no}", help=randomize_help, width="stretch"):
                randomize_mutation(mut1_key, L)
                st.rerun()
            mut_pos1 = st.pills(
                "Click letters to mutate (optional, any number)", list(range(L)), selection_mode="multi",
                format_func=lambda i, w=child1: w[i], key=mut1_key,
            ) or []
        with mc2:
            f2a, f2b = st.columns([0.72, 0.28])
            f2a.markdown(f"Child 2 &nbsp; fitness **{gl.fitness(child2, hidden)}/{L}**")
            mut2_key = f"mut2_pills_{round_idx}_{pair_no}"
            if f2b.button("\U0001f3b2", key=f"rand2_{round_idx}_{pair_no}", help=randomize_help, width="stretch"):
                randomize_mutation(mut2_key, L)
                st.rerun()
            mut_pos2 = st.pills(
                "Click letters to mutate (optional, any number)", list(range(L)), selection_mode="multi",
                format_func=lambda i, w=child2: w[i], key=mut2_key,
            ) or []
        st.caption("Fitness shown is before mutation - clicked (or 🎲 randomized) letters are replaced with a random new one once added.")

        if st.button("✅ Add to offspring pool", type="primary"):
            commit_pair(a_idx, b_idx, cut, mut_pos1, mut_pos2)
            st.rerun()


def render_selection():
    hidden = st.session_state.hidden_word
    L = st.session_state.word_length
    pop = st.session_state.population
    offspring = st.session_state.offspring
    pop_size = st.session_state.pop_size
    round_idx = st.session_state.round_idx

    st.info(f"Offspring pool complete! Select exactly **{pop_size}** individuals to carry into the next generation.")

    left, right = st.columns(2)
    pop_checked = []
    with left:
        st.markdown("**Current Population**")
        for i, w in enumerate(pop):
            fit = gl.fitness(w, hidden)
            c1, c2, c3 = st.columns([0.12, 0.58, 0.3])
            checked = c1.checkbox("keep", key=f"selpop_{round_idx}_{i}", label_visibility="collapsed")
            c2.markdown(f"**M{i + 1}** &nbsp; " + word_tiles_html(w, size=22), unsafe_allow_html=True)
            c3.markdown(f"**{fit}/{L}**")
            pop_checked.append(checked)

    off_checked = []
    with right:
        st.markdown("**Offspring**")
        for i, o in enumerate(offspring):
            c1, c2, c3 = st.columns([0.12, 0.58, 0.3])
            checked = c1.checkbox("keep", key=f"seloff_{round_idx}_{i}", label_visibility="collapsed")
            c2.markdown(f"**C{i + 1}** &nbsp; " + word_tiles_html(o["word"], size=22), unsafe_allow_html=True)
            c3.markdown(f"**{o['fitness']}/{L}**")
            off_checked.append(checked)

    n_selected = sum(pop_checked) + sum(off_checked)
    status_fn = st.success if n_selected == pop_size else st.warning
    status_fn(f"Selected: {n_selected} / {pop_size}")

    bcols = st.columns(3)
    bcols[0].button(f"⭐ Auto-select best {pop_size}", on_click=auto_select_best, width="stretch")
    bcols[1].button("✖ Clear selection", on_click=clear_selection, width="stretch")
    if bcols[2].button("✅ Confirm & start next round", type="primary", disabled=n_selected != pop_size, width="stretch"):
        chosen = [w for w, c in zip(pop, pop_checked) if c] + [o["word"] for o, c in zip(offspring, off_checked) if c]
        confirm_selection(chosen)
        st.rerun()


def render_finished():
    hidden = st.session_state.hidden_word
    L = st.session_state.word_length

    if st.session_state.found:
        st.success(f"\U0001f389 Found the hidden word **{hidden}** in generation {st.session_state.found_generation}!")
        st.balloons()
    else:
        st.info(f"Game stopped. The hidden word was **{hidden}**.")

    best_ever = max(h["best"] for h in st.session_state.history)
    generations_played = st.session_state.found_generation if st.session_state.found else st.session_state.round_idx
    elapsed = time.time() - st.session_state.start_time

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Generations played", generations_played)
    c2.metric("Best fitness reached", f"{best_ever} / {L}")
    c3.metric("Individuals evaluated", st.session_state.total_evaluations)
    c4.metric("Total time", f"{elapsed:.0f}s")

    st.plotly_chart(pl.build_fitness_chart(st.session_state.history, L), width="stretch", key="fitness_chart")

    df = pd.DataFrame(st.session_state.history)
    df.columns = ["Generation", "Best fitness", "Average fitness"]
    df["Average fitness"] = df["Average fitness"].round(2)
    st.dataframe(df, width="stretch", hide_index=True)

    b1, b2 = st.columns(2)
    if b1.button("\U0001f501 Play Again (same word)", width="stretch"):
        start_game(hidden, st.session_state.pop_size, "")
        st.rerun()
    if b2.button("\U0001f195 New Game", width="stretch"):
        st.session_state.phase = "setup"
        st.rerun()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
init_state()

with st.sidebar:
    st.markdown("### \U0001f9ec GA Word Game")
    if st.session_state.phase != "setup":
        st.divider()
        st.metric("Best fitness so far", f"{max(h['best'] for h in st.session_state.history)} / {st.session_state.word_length}")
        if st.session_state.phase in ("breeding", "selection"):
            if st.button("⏹ Stop Game", width="stretch"):
                stop_game()
                st.rerun()
        else:
            if st.button("↺ New Game", width="stretch"):
                st.session_state.phase = "setup"
                st.rerun()
    st.divider()
    st.markdown("### \U0001f4d8 GA Concepts")
    st.caption("Click any topic for a quick explanation.")
    for title, body in CONCEPTS:
        with st.expander(title):
            st.markdown(body)

if st.session_state.phase == "setup":
    render_setup()
elif st.session_state.phase == "breeding":
    render_status_bar()
    render_breeding()
elif st.session_state.phase == "selection":
    render_status_bar()
    render_selection()
elif st.session_state.phase == "finished":
    render_finished()
