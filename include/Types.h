#ifndef TYPES_H
#define TYPES_H

#include <string>
#include <vector>

namespace emf {

// Exposure category as per ICNIRP guidelines
enum class ExposureCategory {
    GENERAL_PUBLIC,
    OCCUPATIONAL
};

// Field quantity for calculations
enum class FieldQuantity {
    ELECTRIC_FIELD,    // V/m
    POWER_DENSITY      // W/m²
};

// Compliance assessment result
enum class ComplianceStatus {
    COMPLIANT,         // Below limit
    MARGINAL,          // 80-100% of limit (warning zone)
    NON_COMPLIANT      // Exceeds limit
};

// Result for a single calculation point
struct PointResult {
    double x;                      // Position X (m)
    double y;                      // Position Y (m)
    double z;                      // Position Z (m)
    double field_value;            // E-field (V/m) or power density (W/m²)
    double limit;                  // Applicable limit at this frequency
    double percentage_of_limit;    // field_value / limit * 100
    ComplianceStatus status;       // Compliance assessment
};

// Antenna orientation
struct Orientation {
    double azimuth_deg;   // Rotation in horizontal plane (0 = +X axis)
    double tilt_deg;      // Mechanical downtilt (negative = down)
};

// Position in 3D space
struct Position {
    double x;
    double y;
    double z;
};

// Configuration for a single antenna
struct AntennaConfig {
    std::string id;               // Unique identifier
    std::string pattern_file;     // Path to MSI/PLN/CSV pattern file
    double frequency_mhz;         // Operating frequency
    double power_eirp_watts;      // EIRP in watts
    Position position;            // Antenna location
    Orientation orientation;      // Pointing direction
};

// Grid configuration
struct GridConfig {
    double x_min;
    double x_max;
    double y_min;
    double y_max;
    double z_level;      // Height of calculation plane
    double resolution;   // Grid spacing in meters
};

// Compliance configuration
struct ComplianceConfig {
    std::string standard;         // ICNIRP_2020, FCC, ICASA
    ExposureCategory category;    // general_public or occupational
};

// Full simulation configuration
struct SimulationConfig {
    std::string name;
    GridConfig grid;
    ComplianceConfig compliance;
    std::vector<AntennaConfig> antennas;
};

// Helper to convert ComplianceStatus to string
inline std::string to_string(ComplianceStatus status) {
    switch (status) {
        case ComplianceStatus::COMPLIANT: return "COMPLIANT";
        case ComplianceStatus::MARGINAL: return "MARGINAL";
        case ComplianceStatus::NON_COMPLIANT: return "NON_COMPLIANT";
        default: return "UNKNOWN";
    }
}

// Helper to convert ExposureCategory to string
inline std::string to_string(ExposureCategory category) {
    switch (category) {
        case ExposureCategory::GENERAL_PUBLIC: return "general_public";
        case ExposureCategory::OCCUPATIONAL: return "occupational";
        default: return "unknown";
    }
}

// Helper to parse ExposureCategory from string
inline ExposureCategory parse_exposure_category(const std::string& str) {
    if (str == "occupational" || str == "OCCUPATIONAL") {
        return ExposureCategory::OCCUPATIONAL;
    }
    return ExposureCategory::GENERAL_PUBLIC;
}

} // namespace emf

#endif // TYPES_H
