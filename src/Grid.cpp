#include "Grid.h"
#include <cmath>
#include <algorithm>

namespace emf {

// GridResults implementation
GridResults::GridResults(const GridConfig& config) : config_(config) {}

void GridResults::add_result(const PointResult& result) {
    results_.push_back(result);
}

size_t GridResults::compliant_points() const {
    return std::count_if(results_.begin(), results_.end(),
        [](const PointResult& r) { return r.status == ComplianceStatus::COMPLIANT; });
}

size_t GridResults::marginal_points() const {
    return std::count_if(results_.begin(), results_.end(),
        [](const PointResult& r) { return r.status == ComplianceStatus::MARGINAL; });
}

size_t GridResults::non_compliant_points() const {
    return std::count_if(results_.begin(), results_.end(),
        [](const PointResult& r) { return r.status == ComplianceStatus::NON_COMPLIANT; });
}

double GridResults::max_field_value() const {
    if (results_.empty()) return 0.0;

    auto it = std::max_element(results_.begin(), results_.end(),
        [](const PointResult& a, const PointResult& b) {
            return a.field_value < b.field_value;
        });
    return it->field_value;
}

double GridResults::max_percentage_of_limit() const {
    if (results_.empty()) return 0.0;

    auto it = std::max_element(results_.begin(), results_.end(),
        [](const PointResult& a, const PointResult& b) {
            return a.percentage_of_limit < b.percentage_of_limit;
        });
    return it->percentage_of_limit;
}

// Grid implementation
Grid::Grid(const GridConfig& config) : config_(config) {
    num_x_ = static_cast<int>(std::ceil((config_.x_max - config_.x_min) / config_.resolution)) + 1;
    num_y_ = static_cast<int>(std::ceil((config_.y_max - config_.y_min) / config_.resolution)) + 1;
}

std::vector<Vector3> Grid::get_points() const {
    std::vector<Vector3> points;
    points.reserve(num_x_ * num_y_);

    for (int yi = 0; yi < num_y_; ++yi) {
        for (int xi = 0; xi < num_x_; ++xi) {
            double x = config_.x_min + xi * config_.resolution;
            double y = config_.y_min + yi * config_.resolution;
            points.emplace_back(x, y, config_.z_level);
        }
    }

    return points;
}

void Grid::for_each_point(std::function<void(int, int, const Vector3&)> callback) const {
    for (int yi = 0; yi < num_y_; ++yi) {
        for (int xi = 0; xi < num_x_; ++xi) {
            double x = config_.x_min + xi * config_.resolution;
            double y = config_.y_min + yi * config_.resolution;
            callback(xi, yi, Vector3(x, y, config_.z_level));
        }
    }
}

Vector3 Grid::get_point(int x_idx, int y_idx) const {
    double x = config_.x_min + x_idx * config_.resolution;
    double y = config_.y_min + y_idx * config_.resolution;
    return Vector3(x, y, config_.z_level);
}

} // namespace emf
