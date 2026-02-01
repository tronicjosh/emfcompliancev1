#include "Antenna.h"
#include <cmath>
#include <stdexcept>

namespace emf {

namespace {
    constexpr double PI = 3.14159265358979323846;
    constexpr double DEG_TO_RAD = PI / 180.0;
    constexpr double RAD_TO_DEG = 180.0 / PI;
}

Antenna::Antenna(const AntennaConfig& config)
    : id_(config.id),
      frequency_mhz_(config.frequency_mhz),
      eirp_watts_(config.power_eirp_watts),
      position_(config.position.x, config.position.y, config.position.z),
      azimuth_deg_(config.orientation.azimuth_deg),
      tilt_deg_(config.orientation.tilt_deg) {

    // Load or create radiation pattern
    if (config.pattern_file.empty() || config.pattern_file == "isotropic") {
        pattern_ = create_isotropic_pattern();
    } else {
        pattern_ = create_pattern(config.pattern_file);
    }

    if (!pattern_) {
        throw std::runtime_error("Failed to create radiation pattern for antenna: " + id_);
    }
}

Vector3 Antenna::to_local_direction(const Vector3& point) const {
    // Get vector from antenna to point
    Vector3 to_point = point - position_;

    // Rotate by negative azimuth (bring antenna pointing direction to +X)
    Vector3 rotated = to_point.rotate_around_z(-azimuth_deg_ * DEG_TO_RAD);

    // Rotate by negative tilt (bring horizontal plane to XY)
    rotated = rotated.rotate_around_y(-tilt_deg_ * DEG_TO_RAD);

    return rotated;
}

void Antenna::get_angles_to_point(const Vector3& point, double& azimuth_deg, double& elevation_deg) const {
    Vector3 local_dir = to_local_direction(point);

    // Convert to spherical coordinates
    double azimuth_rad, elevation_rad;
    local_dir.to_spherical(azimuth_rad, elevation_rad);

    azimuth_deg = azimuth_rad * RAD_TO_DEG;
    elevation_deg = elevation_rad * RAD_TO_DEG;

    // Normalize azimuth to 0-360
    while (azimuth_deg < 0) azimuth_deg += 360;
    while (azimuth_deg >= 360) azimuth_deg -= 360;
}

double Antenna::get_gain_towards(const Vector3& point) const {
    double az_deg, el_deg;
    get_angles_to_point(point, az_deg, el_deg);
    return pattern_->get_gain_linear(az_deg, el_deg);
}

double Antenna::calculate_e_field(const Vector3& point) const {
    Vector3 to_point = point - position_;
    double distance = to_point.magnitude();

    if (distance < 0.1) {
        // Avoid singularity at antenna location
        distance = 0.1;
    }

    // Get gain in direction of point
    double gain = get_gain_towards(point);

    // E-field magnitude: E = sqrt(30 * EIRP * G) / r
    // Where EIRP is in watts, G is linear gain, r is in meters
    // Result is in V/m
    double e_field = std::sqrt(30.0 * eirp_watts_ * gain) / distance;

    return e_field;
}

double Antenna::calculate_power_density(const Vector3& point) const {
    Vector3 to_point = point - position_;
    double distance = to_point.magnitude();

    if (distance < 0.1) {
        distance = 0.1;
    }

    double gain = get_gain_towards(point);

    // Power density: S = EIRP * G / (4 * pi * r²)
    // Where EIRP is in watts, G is linear gain, r is in meters
    // Result is in W/m²
    double power_density = (eirp_watts_ * gain) / (4.0 * PI * distance * distance);

    return power_density;
}

} // namespace emf
