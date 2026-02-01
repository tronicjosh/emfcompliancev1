#ifndef FIELD_SOLVER_H
#define FIELD_SOLVER_H

#include "Types.h"
#include "Vector3.h"
#include "Antenna.h"
#include "Grid.h"
#include <vector>
#include <memory>
#include <map>

namespace emf {

// Forward declaration
class Compliance;

// Solves for cumulative EMF exposure from multiple antennas
class FieldSolver {
public:
    FieldSolver();

    // Add an antenna to the solver
    void add_antenna(std::unique_ptr<Antenna> antenna);
    void add_antenna(const AntennaConfig& config);

    // Get number of antennas
    size_t num_antennas() const { return antennas_.size(); }

    // Calculate total power density at a point (W/m²)
    // Non-coherent summation: S_total = Σ S_i
    double calculate_total_power_density(const Vector3& point) const;

    // Calculate equivalent E-field from total power density (V/m)
    // E = sqrt(η * S) where η = 377 Ω (free-space impedance)
    double calculate_total_e_field(const Vector3& point) const;

    // Solve for entire grid
    // Returns grid results with field values and compliance status
    GridResults solve(const Grid& grid, const Compliance& compliance) const;

    // Find compliance boundary distance for a specific antenna
    // Uses binary search from antenna position
    // Returns distance in meters where field drops below limit
    double find_compliance_boundary(const std::string& antenna_id,
                                    const Compliance& compliance,
                                    double direction_azimuth_deg = 0.0) const;

    // Find compliance boundaries for all antennas
    std::map<std::string, double> find_all_compliance_boundaries(
        const Compliance& compliance) const;

private:
    // Free-space impedance (ohms)
    static constexpr double ETA_0 = 377.0;

    std::vector<std::unique_ptr<Antenna>> antennas_;
};

} // namespace emf

#endif // FIELD_SOLVER_H
