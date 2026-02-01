#include "FieldSolver.h"
#include "Compliance.h"
#include <cmath>
#include <stdexcept>

namespace emf {

namespace {
    constexpr double PI = 3.14159265358979323846;
    constexpr double DEG_TO_RAD = PI / 180.0;
}

FieldSolver::FieldSolver() {}

void FieldSolver::add_antenna(std::unique_ptr<Antenna> antenna) {
    antennas_.push_back(std::move(antenna));
}

void FieldSolver::add_antenna(const AntennaConfig& config) {
    antennas_.push_back(std::make_unique<Antenna>(config));
}

double FieldSolver::calculate_total_power_density(const Vector3& point) const {
    double total_s = 0.0;

    for (const auto& antenna : antennas_) {
        total_s += antenna->calculate_power_density(point);
    }

    return total_s;
}

double FieldSolver::calculate_total_e_field(const Vector3& point) const {
    double total_s = calculate_total_power_density(point);

    // E = sqrt(η * S) where η = 377 Ω
    return std::sqrt(ETA_0 * total_s);
}

GridResults FieldSolver::solve(const Grid& grid, const Compliance& compliance) const {
    GridResults results(grid.get_config());

    // Get the frequency for limit lookup (use first antenna's frequency)
    // For multi-frequency scenarios, this would need to be more sophisticated
    double frequency_mhz = 0.0;
    if (!antennas_.empty()) {
        frequency_mhz = antennas_[0]->get_frequency_mhz();
    }

    grid.for_each_point([&](int /*xi*/, int /*yi*/, const Vector3& point) {
        PointResult result;
        result.x = point.x;
        result.y = point.y;
        result.z = point.z;

        // Calculate cumulative E-field
        result.field_value = calculate_total_e_field(point);

        // Get applicable limit
        result.limit = compliance.get_e_field_limit(frequency_mhz);

        // Calculate percentage of limit
        result.percentage_of_limit = (result.field_value / result.limit) * 100.0;

        // Determine compliance status
        if (result.percentage_of_limit >= 100.0) {
            result.status = ComplianceStatus::NON_COMPLIANT;
        } else if (result.percentage_of_limit >= 80.0) {
            result.status = ComplianceStatus::MARGINAL;
        } else {
            result.status = ComplianceStatus::COMPLIANT;
        }

        results.add_result(result);
    });

    return results;
}

double FieldSolver::find_compliance_boundary(const std::string& antenna_id,
                                              const Compliance& compliance,
                                              double direction_azimuth_deg) const {
    // Find the specified antenna
    const Antenna* target = nullptr;
    for (const auto& antenna : antennas_) {
        if (antenna->get_id() == antenna_id) {
            target = antenna.get();
            break;
        }
    }

    if (!target) {
        throw std::runtime_error("Antenna not found: " + antenna_id);
    }

    // Get limit for this antenna's frequency
    double limit = compliance.get_e_field_limit(target->get_frequency_mhz());

    // Binary search for compliance boundary
    // Start with search range from 1m to 1000m
    double min_dist = 1.0;
    double max_dist = 1000.0;

    // Direction unit vector in XY plane
    double az_rad = direction_azimuth_deg * DEG_TO_RAD;
    Vector3 direction(std::cos(az_rad), std::sin(az_rad), 0);

    // First check if we're already compliant at min distance
    Vector3 pos = target->get_position();
    Vector3 test_point = pos + direction * min_dist;
    test_point.z = 1.5;  // Typical evaluation height

    double e_field = calculate_total_e_field(test_point);
    if (e_field <= limit) {
        return min_dist;
    }

    // Check if we're still non-compliant at max distance
    test_point = pos + direction * max_dist;
    test_point.z = 1.5;
    e_field = calculate_total_e_field(test_point);
    if (e_field > limit) {
        return max_dist;  // Boundary is beyond search range
    }

    // Binary search
    while (max_dist - min_dist > 0.1) {  // 10cm precision
        double mid_dist = (min_dist + max_dist) / 2.0;
        test_point = pos + direction * mid_dist;
        test_point.z = 1.5;

        e_field = calculate_total_e_field(test_point);

        if (e_field > limit) {
            min_dist = mid_dist;
        } else {
            max_dist = mid_dist;
        }
    }

    return (min_dist + max_dist) / 2.0;
}

std::map<std::string, double> FieldSolver::find_all_compliance_boundaries(
    const Compliance& compliance) const {

    std::map<std::string, double> boundaries;

    for (const auto& antenna : antennas_) {
        // Find boundary in the direction of maximum gain (azimuth = 0 in antenna frame)
        double boundary = find_compliance_boundary(antenna->get_id(), compliance, 0.0);
        boundaries[antenna->get_id()] = boundary;
    }

    return boundaries;
}

} // namespace emf
