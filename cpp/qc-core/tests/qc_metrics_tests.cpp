#include "pathflow/qc_metrics.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

bool nearly_equal(double left, double right, double tolerance = 1e-6) {
    return std::abs(left - right) <= tolerance;
}

void expect_true(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    using pathflow::compute_artifact_ratio;
    using pathflow::compute_focus_score;
    using pathflow::compute_tissue_coverage;

    const std::vector<std::uint16_t> flat_tile = {
        10, 10, 10,
        10, 10, 10,
        10, 10, 10,
    };

    const std::vector<std::uint16_t> sharp_tile = {
        0, 0, 0,
        0, 1000, 0,
        0, 0, 0,
    };

    expect_true(nearly_equal(compute_focus_score(flat_tile, 3, 3), 0.0), "flat tile focus");
    expect_true(compute_focus_score(sharp_tile, 3, 3) > 1000.0, "sharp tile focus");

    const std::vector<std::uint16_t> mixed_pixels = {10, 20, 500, 700};
    expect_true(
        nearly_equal(compute_tissue_coverage(mixed_pixels, 100), 0.5),
        "tissue coverage");

    const std::vector<std::uint8_t> mask = {1, 0, 1, 0, 0};
    expect_true(nearly_equal(compute_artifact_ratio(mask), 0.4), "artifact ratio");

    std::cout << "All qc-core tests passed\n";
    return 0;
}

