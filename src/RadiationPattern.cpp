#include "RadiationPattern.h"
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <limits>

namespace emf {

// IRadiationPattern base class
double IRadiationPattern::get_gain_linear(double azimuth_deg, double elevation_deg) const {
    double gain_dbi = get_gain_dbi(azimuth_deg, elevation_deg);
    return std::pow(10.0, gain_dbi / 10.0);
}

// IsotropicPattern
double IsotropicPattern::get_gain_dbi(double /*azimuth_deg*/, double /*elevation_deg*/) const {
    return 0.0;  // 0 dBi everywhere
}

double IsotropicPattern::get_max_gain_dbi() const {
    return 0.0;
}

// MsiPattern
MsiPattern::MsiPattern(const std::string& filepath)
    : frequency_mhz_(0), max_gain_dbi_(0) {
    horizontal_pattern_.resize(360, 0.0);
    vertical_pattern_.resize(360, 0.0);
    load_msi(filepath);
}

void MsiPattern::load_msi(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open MSI file: " + filepath);
    }

    std::string line;
    bool reading_horizontal = false;
    bool reading_vertical = false;
    int h_count = 0;
    int v_count = 0;

    while (std::getline(file, line)) {
        // Trim whitespace
        size_t start = line.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) continue;
        line = line.substr(start);

        // Skip empty lines
        if (line.empty()) continue;

        // Parse header fields
        if (line.find("NAME") == 0) {
            size_t pos = line.find_first_of(" \t");
            if (pos != std::string::npos) {
                name_ = line.substr(pos + 1);
            }
        }
        else if (line.find("FREQUENCY") == 0) {
            std::istringstream iss(line);
            std::string keyword;
            iss >> keyword >> frequency_mhz_;
        }
        else if (line.find("GAIN") == 0) {
            std::istringstream iss(line);
            std::string keyword;
            iss >> keyword >> max_gain_dbi_;
        }
        else if (line.find("HORIZONTAL") == 0) {
            reading_horizontal = true;
            reading_vertical = false;
            h_count = 0;
        }
        else if (line.find("VERTICAL") == 0) {
            reading_horizontal = false;
            reading_vertical = true;
            v_count = 0;
        }
        else if (reading_horizontal || reading_vertical) {
            // Parse angle and gain values
            std::istringstream iss(line);
            double angle, gain;
            if (iss >> angle >> gain) {
                int idx = static_cast<int>(std::round(angle)) % 360;
                if (idx < 0) idx += 360;

                if (reading_horizontal && h_count < 360) {
                    horizontal_pattern_[idx] = gain;
                    h_count++;
                }
                else if (reading_vertical && v_count < 360) {
                    vertical_pattern_[idx] = gain;
                    v_count++;
                }
            }
        }
    }
}

double MsiPattern::interpolate(const std::vector<double>& pattern, double angle_deg) const {
    // Normalize angle to 0-360
    while (angle_deg < 0) angle_deg += 360;
    while (angle_deg >= 360) angle_deg -= 360;

    int idx_low = static_cast<int>(std::floor(angle_deg));
    int idx_high = (idx_low + 1) % 360;
    double frac = angle_deg - idx_low;

    // Linear interpolation
    return pattern[idx_low] * (1.0 - frac) + pattern[idx_high] * frac;
}

double MsiPattern::get_gain_dbi(double azimuth_deg, double elevation_deg) const {
    // MSI format stores relative gain (attenuation from max)
    // Combine horizontal and vertical patterns

    // Get horizontal pattern value (azimuth)
    double h_atten = interpolate(horizontal_pattern_, azimuth_deg);

    // Get vertical pattern value
    // MSI vertical pattern: 0 = horizontal, increases going down
    // Our elevation: positive = up, negative = down
    // Convert: msi_angle = -elevation + 0 (for downtilt=0)
    double v_angle = -elevation_deg;
    while (v_angle < 0) v_angle += 360;
    while (v_angle >= 360) v_angle -= 360;
    double v_atten = interpolate(vertical_pattern_, v_angle);

    // Combine: total attenuation is sum of individual attenuations (in dB)
    // This is an approximation; more accurate would be full 3D pattern
    double total_atten = h_atten + v_atten;

    // Return absolute gain
    return max_gain_dbi_ - total_atten;
}

double MsiPattern::get_max_gain_dbi() const {
    return max_gain_dbi_;
}

// CsvPattern
CsvPattern::CsvPattern(const std::string& filepath)
    : max_gain_dbi_(-std::numeric_limits<double>::infinity()),
      azimuth_step_(1.0), elevation_step_(1.0) {
    load_csv(filepath);
}

void CsvPattern::load_csv(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open CSV pattern file: " + filepath);
    }

    std::string line;
    bool header_skipped = false;

    while (std::getline(file, line)) {
        if (line.empty()) continue;

        // Skip header if present
        if (!header_skipped && (line.find("azimuth") != std::string::npos ||
                                line.find("Azimuth") != std::string::npos ||
                                line.find("AZIMUTH") != std::string::npos)) {
            header_skipped = true;
            continue;
        }

        std::istringstream iss(line);
        std::string token;
        std::vector<double> values;

        while (std::getline(iss, token, ',')) {
            try {
                values.push_back(std::stod(token));
            } catch (...) {
                continue;
            }
        }

        if (values.size() >= 3) {
            int az = static_cast<int>(std::round(values[0]));
            int el = static_cast<int>(std::round(values[1]));
            double gain = values[2];

            gain_map_[{az, el}] = gain;
            if (gain > max_gain_dbi_) {
                max_gain_dbi_ = gain;
            }
        }
    }

    if (gain_map_.empty()) {
        throw std::runtime_error("No valid pattern data in CSV file: " + filepath);
    }
}

double CsvPattern::interpolate_2d(double azimuth_deg, double elevation_deg) const {
    // Round to nearest integer for lookup
    int az = static_cast<int>(std::round(azimuth_deg));
    int el = static_cast<int>(std::round(elevation_deg));

    // Normalize azimuth
    while (az < 0) az += 360;
    while (az >= 360) az -= 360;

    // Clamp elevation
    if (el < -90) el = -90;
    if (el > 90) el = 90;

    auto it = gain_map_.find({az, el});
    if (it != gain_map_.end()) {
        return it->second;
    }

    // If exact match not found, find nearest
    double min_dist = std::numeric_limits<double>::infinity();
    double nearest_gain = 0.0;

    for (const auto& [key, gain] : gain_map_) {
        double az_diff = std::abs(key.first - az);
        if (az_diff > 180) az_diff = 360 - az_diff;
        double el_diff = std::abs(key.second - el);
        double dist = az_diff * az_diff + el_diff * el_diff;

        if (dist < min_dist) {
            min_dist = dist;
            nearest_gain = gain;
        }
    }

    return nearest_gain;
}

double CsvPattern::get_gain_dbi(double azimuth_deg, double elevation_deg) const {
    return interpolate_2d(azimuth_deg, elevation_deg);
}

double CsvPattern::get_max_gain_dbi() const {
    return max_gain_dbi_;
}

// Factory functions
std::unique_ptr<IRadiationPattern> create_pattern(const std::string& filepath) {
    if (filepath.empty() || filepath == "isotropic") {
        return std::make_unique<IsotropicPattern>();
    }

    // Determine file type from extension
    std::string ext;
    size_t dot_pos = filepath.rfind('.');
    if (dot_pos != std::string::npos) {
        ext = filepath.substr(dot_pos);
        // Convert to lowercase
        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    }

    if (ext == ".msi" || ext == ".pln") {
        return std::make_unique<MsiPattern>(filepath);
    }
    else if (ext == ".csv") {
        return std::make_unique<CsvPattern>(filepath);
    }
    else {
        // Try MSI format as default
        return std::make_unique<MsiPattern>(filepath);
    }
}

std::unique_ptr<IRadiationPattern> create_isotropic_pattern() {
    return std::make_unique<IsotropicPattern>();
}

} // namespace emf
