#ifndef COMPLIANCE_H
#define COMPLIANCE_H

#include "Types.h"
#include <string>
#include <vector>
#include <map>

namespace emf {

// Represents a frequency-dependent limit entry
struct LimitEntry {
    double freq_min_mhz;    // Minimum frequency (inclusive)
    double freq_max_mhz;    // Maximum frequency (inclusive)
    double e_field_limit;   // E-field limit in V/m
    double s_limit;         // Power density limit in W/m²
    std::string formula;    // Formula description (for reference)
};

// Compliance assessment against EMF exposure limits
class Compliance {
public:
    // Create compliance checker with specified standard
    // standard: "ICNIRP_2020", "FCC", "ICASA", or path to custom YAML file
    // category: exposure category (general public or occupational)
    Compliance(const std::string& standard, ExposureCategory category);

    // Get E-field limit for a given frequency (V/m)
    double get_e_field_limit(double frequency_mhz) const;

    // Get power density limit for a given frequency (W/m²)
    double get_power_density_limit(double frequency_mhz) const;

    // Get standard name
    const std::string& get_standard_name() const { return standard_name_; }

    // Get exposure category
    ExposureCategory get_category() const { return category_; }

    // Evaluate compliance status for a field value
    ComplianceStatus evaluate(double field_value, double limit) const;

    // Generate summary statistics
    struct Summary {
        std::string standard;
        std::string category;
        bool overall_compliant;
        size_t total_points;
        size_t compliant_points;
        size_t marginal_points;
        size_t non_compliant_points;
        double max_field_value;
        double max_percentage_of_limit;
    };

    Summary generate_summary(const std::vector<PointResult>& results) const;

private:
    void load_icnirp_2020();
    void load_fcc();
    void load_icasa();
    void load_from_yaml(const std::string& filepath);

    std::string standard_name_;
    ExposureCategory category_;
    std::vector<LimitEntry> limits_;
};

} // namespace emf

#endif // COMPLIANCE_H
