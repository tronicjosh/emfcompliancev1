#ifndef ANTENNA_H
#define ANTENNA_H

#include "Types.h"
#include "Vector3.h"
#include "RadiationPattern.h"
#include <memory>
#include <string>

namespace emf {

class Antenna {
public:
    // Construct from configuration
    explicit Antenna(const AntennaConfig& config);

    // Getters
    const std::string& get_id() const { return id_; }
    double get_frequency_mhz() const { return frequency_mhz_; }
    double get_eirp_watts() const { return eirp_watts_; }
    const Vector3& get_position() const { return position_; }

    // Calculate E-field magnitude at a point (V/m)
    // E = sqrt(30 * EIRP * G) / r  (far-field approximation)
    double calculate_e_field(const Vector3& point) const;

    // Calculate power density at a point (W/m²)
    // S = EIRP * G / (4 * pi * r²)
    double calculate_power_density(const Vector3& point) const;

    // Get the gain in the direction of the point
    double get_gain_towards(const Vector3& point) const;

private:
    // Transform point from global to antenna-local coordinates
    // Returns direction vector in antenna's reference frame
    Vector3 to_local_direction(const Vector3& point) const;

    // Get azimuth and elevation angles to a point (in antenna's frame)
    void get_angles_to_point(const Vector3& point, double& azimuth_deg, double& elevation_deg) const;

    std::string id_;
    double frequency_mhz_;
    double eirp_watts_;
    Vector3 position_;
    double azimuth_deg_;   // Antenna pointing direction (rotation around Z)
    double tilt_deg_;      // Mechanical downtilt (rotation around local Y)

    std::unique_ptr<IRadiationPattern> pattern_;
};

} // namespace emf

#endif // ANTENNA_H
