import os
import sys

sys.path.append(os.path.join(os.getcwd(), "ExhaustiveVsLocalSearch_App"))

import game_logic as gl


def test_seeding_is_reproducible():
    print("1. Same code -> identical landscapes...")
    seed_a = gl.code_to_seed("CLASS01")
    seed_b = gl.code_to_seed("class01")  # case-insensitive
    rounds_a = gl.generate_all_rounds(seed_a)
    rounds_b = gl.generate_all_rounds(seed_b)
    assert rounds_a == rounds_b
    print("   - Reproducible across case and repeated calls.")

    print("2. Different code -> different landscapes...")
    seed_c = gl.code_to_seed("CLASS02")
    rounds_c = gl.generate_all_rounds(seed_c)
    assert rounds_c != rounds_a
    print("   - Distinct seeds diverge as expected.")


def test_round_shapes_and_growth():
    print("3. Round sizes match the growing x-axis...")
    rounds = gl.generate_all_rounds(gl.code_to_seed("SHAPES"))
    assert len(rounds) == len(gl.ROUND_XMAX)
    for ys, xmax in zip(rounds, gl.ROUND_XMAX):
        assert len(ys) == xmax + 1
        assert all(y >= 0 for y in ys)
    assert gl.ROUND_XMAX == sorted(gl.ROUND_XMAX)  # strictly non-decreasing x-axis
    print(f"   - Sizes: {[len(r) for r in rounds]} match xmax+1 for {gl.ROUND_XMAX}.")


def test_local_minima_includes_global_min():
    print("4. Global minimum is always among the local minima...")
    for code in ["A1", "B2", "C3"]:
        for ys in gl.generate_all_rounds(gl.code_to_seed(code)):
            global_idx = min(range(len(ys)), key=lambda i: ys[i])
            assert global_idx in gl.local_minima_indices(ys)
    print("   - Holds across sampled seeds/rounds.")


def test_is_improving():
    print("5. is_improving is strict minimization...")
    assert gl.is_improving(1.0, 2.0) is True
    assert gl.is_improving(2.0, 2.0) is False
    assert gl.is_improving(2.0, 1.0) is False
    print("   - Strict '<' semantics confirmed.")


def test_score_round_exhaustive_is_fixed_baseline():
    print("6. Exhaustive-equivalent scoring (all points evaluated) is a fixed baseline...")
    ys = [3.0, 1.0, 0.0, 2.0, 4.0]
    result = gl.score_round(found_y=min(ys), ys=ys, evaluations=len(ys))
    assert result["quality"] == 1.0
    assert result["efficiency"] == 0.0
    assert result["score"] == round(1000 * gl.QUALITY_WEIGHT) == 650
    print(f"   - score={result['score']} (quality=1.0, efficiency=0.0), matches the app's documented baseline.")


def test_score_round_rewards_efficient_success():
    print("7. Finding the optimum with few evaluations beats exhaustive's baseline...")
    ys = [3.0, 1.0, 0.0, 2.0, 4.0]
    efficient = gl.score_round(found_y=0.0, ys=ys, evaluations=2)
    baseline = round(1000 * gl.QUALITY_WEIGHT)
    assert efficient["score"] > baseline
    print(f"   - efficient score={efficient['score']} > baseline={baseline}.")


def test_score_round_penalizes_getting_trapped():
    print("8. Landing on a poor local optimum scores below the exhaustive baseline...")
    ys = [3.0, 1.0, 0.0, 2.0, 4.0]
    trapped = gl.score_round(found_y=4.0, ys=ys, evaluations=2)  # stuck at the worst point (global max)
    baseline = round(1000 * gl.QUALITY_WEIGHT)
    assert trapped["quality"] == 0.0
    assert trapped["score"] < baseline
    print(f"   - trapped score={trapped['score']} < baseline={baseline}.")


def test_neighbor_xs_basic_and_boundaries():
    print("9. neighbor_xs: n=1 matches the original left/right neighborhood...")
    assert gl.neighbor_xs(5, 1, 20) == [4, 6]
    assert gl.neighbor_xs(0, 1, 20) == [1]  # no left neighbor at the boundary
    assert gl.neighbor_xs(20, 1, 20) == [19]  # no right neighbor at the boundary
    print("   - Matches.")

    print("10. neighbor_xs: n=2 widens the neighborhood on each side...")
    assert gl.neighbor_xs(5, 2, 20) == [3, 4, 6, 7]
    assert gl.neighbor_xs(1, 2, 20) == [0, 2, 3]  # clipped at the left boundary
    assert gl.neighbor_xs(19, 2, 20) == [17, 18, 20]  # clipped at the right boundary
    print("   - Clips correctly at both boundaries.")

    print("11. neighbor_xs never includes the current position itself...")
    for n in gl.NEIGHBORHOOD_CHOICES:
        for x in range(0, 21):
            assert x not in gl.neighbor_xs(x, n, 20)
    print("   - Confirmed across all neighborhood sizes and positions.")


if __name__ == "__main__":
    test_seeding_is_reproducible()
    test_round_shapes_and_growth()
    test_local_minima_includes_global_min()
    test_is_improving()
    test_score_round_exhaustive_is_fixed_baseline()
    test_score_round_rewards_efficient_success()
    test_score_round_penalizes_getting_trapped()
    test_neighbor_xs_basic_and_boundaries()
    print("\nAll game_logic tests passed.")
