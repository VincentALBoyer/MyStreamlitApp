import os
import sys

sys.path.append(os.path.join(os.getcwd(), "GA_WordGame_App"))

import game_logic as gl


def test_seeding_is_reproducible():
    print("1. Same code -> identical initial populations...")
    rng_a = gl.make_rng("CLASS01")
    rng_b = gl.make_rng("class01")  # case-insensitive
    pop_a = gl.random_population(6, 6, rng_a)
    pop_b = gl.random_population(6, 6, rng_b)
    assert pop_a == pop_b
    print("   - Reproducible across case and repeated calls.")

    print("2. Different code -> different populations...")
    rng_c = gl.make_rng("CLASS02")
    pop_c = gl.random_population(6, 6, rng_c)
    assert pop_c != pop_a
    print("   - Distinct seeds diverge as expected.")

    print("3. Blank code -> unpredictable (not reproducible on purpose)...")
    rng_d1 = gl.make_rng("")
    rng_d2 = gl.make_rng("")
    pop_d1 = gl.random_population(6, 6, rng_d1)
    pop_d2 = gl.random_population(6, 6, rng_d2)
    assert pop_d1 != pop_d2  # astronomically unlikely to collide by chance
    print("   - Blank code yields independent random populations.")


def test_clean_hidden_word():
    print("4. clean_hidden_word strips non-letters and uppercases...")
    assert gl.clean_hidden_word("planet") == "PLANET"
    assert gl.clean_hidden_word(" Pla-Net9! ") == "PLANET"
    assert gl.clean_hidden_word("") == ""
    print("   - Matches expected cleaning behavior.")


def test_fitness_counts_position_matches_only():
    print("5. fitness counts letters correct AND in position (slide's example)...")
    assert gl.fitness("PLANET", "PLANET") == 6
    assert gl.fitness("PLAZET", "PLANET") == 5  # matches the slide's worked example
    assert gl.fitness("TENALP", "PLANET") == 0  # right letters, all wrong positions
    print("   - Matches the slide's worked example exactly.")


def test_crossover_swaps_tails_and_preserves_length():
    print("6. crossover produces complementary children of the same length...")
    a, b = "AAAAAA", "BBBBBB"
    c1, c2 = gl.crossover(a, b, 2)
    assert c1 == "AABBBB"
    assert c2 == "BBAAAA"
    assert len(c1) == len(c2) == len(a)
    print(f"   - cut=2 -> child1={c1}, child2={c2}.")

    print("7. Every crossover cut point is reachable and reversible...")
    for cut in range(1, len(a)):
        c1, c2 = gl.crossover(a, b, cut)
        # Swapping the same cut again on the children recovers the original parents.
        back1, back2 = gl.crossover(c1, c2, cut)
        assert (back1, back2) == (a, b)
    print("   - All cuts round-trip correctly.")


def test_mutate_always_changes_the_letter():
    print("8. mutate always replaces the letter with a *different* one...")
    rng = gl.make_rng("MUTATE-TEST")
    word = "PLANET"
    for pos in range(len(word)):
        mutated = gl.mutate(word, pos, rng)
        assert len(mutated) == len(word)
        assert mutated[pos] != word[pos]
        assert mutated[:pos] + mutated[pos + 1:] == word[:pos] + word[pos + 1:]
    print("   - Every position mutates to a strictly different letter, rest unchanged.")


def test_population_stats():
    print("9. population_stats reports best/avg fitness correctly...")
    words = ["PLANET", "PLAZET", "ZZZZZZ"]
    hidden = "PLANET"
    stats = gl.population_stats(words, hidden)
    assert stats["fits"] == [6, 5, 0]
    assert stats["best"] == 6
    assert abs(stats["avg"] - (6 + 5 + 0) / 3) < 1e-9
    print(f"   - best={stats['best']}, avg={stats['avg']:.2f} as expected.")


def test_random_individual_and_population_shapes():
    print("10. random_individual/random_population respect length and alphabet...")
    rng = gl.make_rng("SHAPES")
    ind = gl.random_individual(8, rng)
    assert len(ind) == 8
    assert all(c in gl.ALPHABET for c in ind)

    pop = gl.random_population(6, 6, rng)
    assert len(pop) == 6
    assert all(len(w) == 6 for w in pop)
    print("   - Lengths and alphabet constraints hold.")


if __name__ == "__main__":
    test_seeding_is_reproducible()
    test_clean_hidden_word()
    test_fitness_counts_position_matches_only()
    test_crossover_swaps_tails_and_preserves_length()
    test_mutate_always_changes_the_letter()
    test_population_stats()
    test_random_individual_and_population_shapes()
    print("\nAll game_logic tests passed.")
