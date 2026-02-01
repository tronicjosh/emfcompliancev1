#ifndef GRID_H
#define GRID_H

#include "Types.h"
#include "Vector3.h"
#include <vector>
#include <functional>

namespace emf {

// Stores results for a calculation grid
class GridResults {
public:
    GridResults(const GridConfig& config);

    // Add a point result
    void add_result(const PointResult& result);

    // Get all results
    const std::vector<PointResult>& get_results() const { return results_; }

    // Get grid configuration
    const GridConfig& get_config() const { return config_; }

    // Statistics
    size_t total_points() const { return results_.size(); }
    size_t compliant_points() const;
    size_t marginal_points() const;
    size_t non_compliant_points() const;
    double max_field_value() const;
    double max_percentage_of_limit() const;

private:
    GridConfig config_;
    std::vector<PointResult> results_;
};

// 2D calculation grid at a fixed Z level
class Grid {
public:
    explicit Grid(const GridConfig& config);

    // Get grid configuration
    const GridConfig& get_config() const { return config_; }

    // Get all grid points
    std::vector<Vector3> get_points() const;

    // Get grid dimensions
    int get_num_x() const { return num_x_; }
    int get_num_y() const { return num_y_; }
    int total_points() const { return num_x_ * num_y_; }

    // Iterate over all points with callback
    // Callback receives (x_index, y_index, point)
    void for_each_point(std::function<void(int, int, const Vector3&)> callback) const;

    // Get point at specific indices
    Vector3 get_point(int x_idx, int y_idx) const;

private:
    GridConfig config_;
    int num_x_;
    int num_y_;
};

} // namespace emf

#endif // GRID_H
