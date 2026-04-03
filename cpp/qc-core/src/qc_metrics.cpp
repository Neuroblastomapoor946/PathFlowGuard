#include "pathflow/qc_metrics.hpp"

#include <cmath>
#include <stdexcept>

namespace {

std::size_t index_for(std::size_t x, std::size_t y, std::size_t width) {
    return (y * width) + x;
}

}  // namespace

namespace pathflow {

double compute_focus_score(
    const std::vector<std::uint16_t>& pixels,
    std::size_t width,
    std::size_t height) {
    if (width == 0 || height == 0 || pixels.size() != width * height) {
        throw std::invalid_argument("pixels must match width * height");
    }

    if (width < 3 || height < 3) {
        return 0.0;
    }

    double total_response = 0.0;
    std::size_t sample_count = 0;

    for (std::size_t y = 1; y < height - 1; ++y) {
        for (std::size_t x = 1; x < width - 1; ++x) {
            const auto center = static_cast<double>(pixels[index_for(x, y, width)]);
            const auto north = static_cast<double>(pixels[index_for(x, y - 1, width)]);
            const auto south = static_cast<double>(pixels[index_for(x, y + 1, width)]);
            const auto east = static_cast<double>(pixels[index_for(x + 1, y, width)]);
            const auto west = static_cast<double>(pixels[index_for(x - 1, y, width)]);
            const auto laplacian = std::abs((4.0 * center) - north - south - east - west);
            total_response += laplacian;
            ++sample_count;
        }
    }

    return total_response / static_cast<double>(sample_count);
}

double compute_tissue_coverage(
    const std::vector<std::uint16_t>& pixels,
    std::uint16_t threshold) {
    if (pixels.empty()) {
        return 0.0;
    }

    std::size_t tissue_pixels = 0;
    for (const auto pixel : pixels) {
        if (pixel < threshold) {
            ++tissue_pixels;
        }
    }

    return static_cast<double>(tissue_pixels) / static_cast<double>(pixels.size());
}

double compute_artifact_ratio(const std::vector<std::uint8_t>& artifact_mask) {
    if (artifact_mask.empty()) {
        return 0.0;
    }

    std::size_t artifact_pixels = 0;
    for (const auto value : artifact_mask) {
        if (value != 0U) {
            ++artifact_pixels;
        }
    }

    return static_cast<double>(artifact_pixels) / static_cast<double>(artifact_mask.size());
}

}  // namespace pathflow

