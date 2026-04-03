#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace pathflow {

double compute_focus_score(
    const std::vector<std::uint16_t>& pixels,
    std::size_t width,
    std::size_t height);

double compute_tissue_coverage(
    const std::vector<std::uint16_t>& pixels,
    std::uint16_t threshold);

double compute_artifact_ratio(const std::vector<std::uint8_t>& artifact_mask);

}  // namespace pathflow

