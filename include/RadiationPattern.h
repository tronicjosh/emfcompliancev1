#ifndef RADIATION_PATTERN_H
#define RADIATION_PATTERN_H

#include <string>
#include <vector>
#include <memory>
#include <map>

namespace emf {

// Abstract interface for radiation patterns
class IRadiationPattern {
public:
    virtual ~IRadiationPattern() = default;

    // Get gain in dBi at specified angles
    // azimuth_deg: angle from boresight in horizontal plane (0-360)
    // elevation_deg: angle from horizontal (positive = up, -90 to +90)
    virtual double get_gain_dbi(double azimuth_deg, double elevation_deg) const = 0;

    // Get linear gain (not dB) at specified angles
    double get_gain_linear(double azimuth_deg, double elevation_deg) const;

    // Get maximum gain
    virtual double get_max_gain_dbi() const = 0;
};

// Isotropic pattern (0 dBi everywhere)
class IsotropicPattern : public IRadiationPattern {
public:
    double get_gain_dbi(double azimuth_deg, double elevation_deg) const override;
    double get_max_gain_dbi() const override;
};

// MSI/PLN file format pattern
class MsiPattern : public IRadiationPattern {
public:
    explicit MsiPattern(const std::string& filepath);

    double get_gain_dbi(double azimuth_deg, double elevation_deg) const override;
    double get_max_gain_dbi() const override;

private:
    void load_msi(const std::string& filepath);
    double interpolate(const std::vector<double>& pattern, double angle_deg) const;

    std::string name_;
    double frequency_mhz_;
    double max_gain_dbi_;
    std::vector<double> horizontal_pattern_;  // 360 values, 1-degree spacing
    std::vector<double> vertical_pattern_;    // 360 values, 1-degree spacing
};

// CSV format pattern (azimuth, elevation, gain_dbi)
class CsvPattern : public IRadiationPattern {
public:
    explicit CsvPattern(const std::string& filepath);

    double get_gain_dbi(double azimuth_deg, double elevation_deg) const override;
    double get_max_gain_dbi() const override;

private:
    void load_csv(const std::string& filepath);
    double interpolate_2d(double azimuth_deg, double elevation_deg) const;

    double max_gain_dbi_;
    // Map of (azimuth_deg, elevation_deg) -> gain_dbi
    std::map<std::pair<int, int>, double> gain_map_;
    double azimuth_step_;
    double elevation_step_;
};

// Factory function to create appropriate pattern from file
std::unique_ptr<IRadiationPattern> create_pattern(const std::string& filepath);

// Create isotropic pattern
std::unique_ptr<IRadiationPattern> create_isotropic_pattern();

} // namespace emf

#endif // RADIATION_PATTERN_H
