#include "Compliance.h"
#include <yaml-cpp/yaml.h>
#include <cmath>
#include <stdexcept>
#include <algorithm>

namespace emf {

Compliance::Compliance(const std::string& standard, ExposureCategory category)
    : standard_name_(standard), category_(category) {

    // Convert standard name to uppercase for comparison
    std::string std_upper = standard;
    std::transform(std_upper.begin(), std_upper.end(), std_upper.begin(), ::toupper);

    if (std_upper == "ICNIRP_2020" || std_upper == "ICNIRP") {
        load_icnirp_2020();
    } else if (std_upper == "FCC") {
        load_fcc();
    } else if (std_upper == "ICASA") {
        load_icasa();
    } else {
        // Assume it's a file path
        load_from_yaml(standard);
    }
}

void Compliance::load_icnirp_2020() {
    // ICNIRP 2020 Guidelines for RF EMF (100 kHz to 300 GHz)
    // Reference levels for general public exposure

    limits_.clear();

    if (category_ == ExposureCategory::GENERAL_PUBLIC) {
        // General public limits
        // 100 kHz - 30 MHz: E = 87 V/m, S = 20 W/m²
        limits_.push_back({0.1, 30.0, 87.0, 20.0, "87 V/m (100 kHz - 30 MHz)"});

        // 30 MHz - 400 MHz: E = 28 V/m, S = 2 W/m²
        limits_.push_back({30.0, 400.0, 28.0, 2.0, "28 V/m (30 - 400 MHz)"});

        // 400 MHz - 2000 MHz: E = 1.375*f^0.5 V/m, S = f/200 W/m²
        // We'll use representative values at key frequencies
        limits_.push_back({400.0, 2000.0, 61.4, 10.0, "1.375*sqrt(f) V/m (400 - 2000 MHz)"});

        // 2 GHz - 300 GHz: E = 61 V/m, S = 10 W/m²
        limits_.push_back({2000.0, 300000.0, 61.0, 10.0, "61 V/m (2 - 300 GHz)"});
    } else {
        // Occupational limits (5x power density, sqrt(5) E-field)
        limits_.push_back({0.1, 30.0, 194.6, 100.0, "194.6 V/m (100 kHz - 30 MHz)"});
        limits_.push_back({30.0, 400.0, 62.6, 10.0, "62.6 V/m (30 - 400 MHz)"});
        limits_.push_back({400.0, 2000.0, 137.3, 50.0, "3.07*sqrt(f) V/m (400 - 2000 MHz)"});
        limits_.push_back({2000.0, 300000.0, 137.0, 50.0, "137 V/m (2 - 300 GHz)"});
    }

    standard_name_ = "ICNIRP_2020";
}

void Compliance::load_fcc() {
    // FCC OET Bulletin 65 limits
    limits_.clear();

    if (category_ == ExposureCategory::GENERAL_PUBLIC) {
        // General population/uncontrolled exposure
        limits_.push_back({0.3, 1.34, 614.0, 1000.0, "614 V/m (0.3 - 1.34 MHz)"});
        limits_.push_back({1.34, 30.0, 824.0 / std::sqrt(1.34), 180.0, "824/f V/m (1.34 - 30 MHz)"});
        limits_.push_back({30.0, 300.0, 27.5, 2.0, "27.5 V/m (30 - 300 MHz)"});
        limits_.push_back({300.0, 1500.0, 27.5, 1.0, "27.5 V/m, f/1500 mW/cm² (300 - 1500 MHz)"});
        limits_.push_back({1500.0, 100000.0, 61.4, 10.0, "61.4 V/m (1.5 - 100 GHz)"});
    } else {
        // Occupational/controlled exposure
        limits_.push_back({0.3, 3.0, 614.0, 1000.0, "614 V/m (0.3 - 3 MHz)"});
        limits_.push_back({3.0, 30.0, 1842.0 / 3.0, 900.0, "1842/f V/m (3 - 30 MHz)"});
        limits_.push_back({30.0, 300.0, 61.4, 10.0, "61.4 V/m (30 - 300 MHz)"});
        limits_.push_back({300.0, 1500.0, 61.4, 10.0, "61.4 V/m, f/300 mW/cm² (300 - 1500 MHz)"});
        limits_.push_back({1500.0, 100000.0, 137.0, 50.0, "137 V/m (1.5 - 100 GHz)"});
    }

    standard_name_ = "FCC";
}

void Compliance::load_icasa() {
    // ICASA (South Africa) follows ICNIRP with some local considerations
    // For simplicity, we use ICNIRP 2020 values
    load_icnirp_2020();
    standard_name_ = "ICASA";
}

void Compliance::load_from_yaml(const std::string& filepath) {
    try {
        YAML::Node config = YAML::LoadFile(filepath);

        if (config["name"]) {
            standard_name_ = config["name"].as<std::string>();
        }

        if (config["limits"]) {
            limits_.clear();
            for (const auto& entry : config["limits"]) {
                LimitEntry limit;
                limit.freq_min_mhz = entry["freq_min_mhz"].as<double>();
                limit.freq_max_mhz = entry["freq_max_mhz"].as<double>();
                limit.e_field_limit = entry["e_field_limit"].as<double>();
                limit.s_limit = entry["s_limit"].as<double>(0.0);
                if (entry["formula"]) {
                    limit.formula = entry["formula"].as<std::string>();
                }
                limits_.push_back(limit);
            }
        }
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to load compliance limits from: " + filepath + " - " + e.what());
    }
}

double Compliance::get_e_field_limit(double frequency_mhz) const {
    // Special handling for ICNIRP frequency-dependent formulas
    if (standard_name_ == "ICNIRP_2020" || standard_name_ == "ICASA") {
        if (frequency_mhz >= 400.0 && frequency_mhz <= 2000.0) {
            if (category_ == ExposureCategory::GENERAL_PUBLIC) {
                // E = 1.375 * sqrt(f) V/m
                return 1.375 * std::sqrt(frequency_mhz);
            } else {
                // E = 3.07 * sqrt(f) V/m
                return 3.07 * std::sqrt(frequency_mhz);
            }
        }
    }

    // Find the applicable limit entry
    for (const auto& entry : limits_) {
        if (frequency_mhz >= entry.freq_min_mhz && frequency_mhz <= entry.freq_max_mhz) {
            return entry.e_field_limit;
        }
    }

    // Default to most conservative limit if frequency not found
    if (!limits_.empty()) {
        double min_limit = limits_[0].e_field_limit;
        for (const auto& entry : limits_) {
            if (entry.e_field_limit < min_limit) {
                min_limit = entry.e_field_limit;
            }
        }
        return min_limit;
    }

    // Fallback default (ICNIRP general public at 2 GHz+)
    return 61.0;
}

double Compliance::get_power_density_limit(double frequency_mhz) const {
    // Special handling for ICNIRP frequency-dependent formulas
    if (standard_name_ == "ICNIRP_2020" || standard_name_ == "ICASA") {
        if (frequency_mhz >= 400.0 && frequency_mhz <= 2000.0) {
            if (category_ == ExposureCategory::GENERAL_PUBLIC) {
                // S = f/200 W/m²
                return frequency_mhz / 200.0;
            } else {
                // S = f/40 W/m²
                return frequency_mhz / 40.0;
            }
        }
    }

    // Find the applicable limit entry
    for (const auto& entry : limits_) {
        if (frequency_mhz >= entry.freq_min_mhz && frequency_mhz <= entry.freq_max_mhz) {
            return entry.s_limit;
        }
    }

    // Default
    return 10.0;
}

ComplianceStatus Compliance::evaluate(double field_value, double limit) const {
    double percentage = (field_value / limit) * 100.0;

    if (percentage >= 100.0) {
        return ComplianceStatus::NON_COMPLIANT;
    } else if (percentage >= 80.0) {
        return ComplianceStatus::MARGINAL;
    }
    return ComplianceStatus::COMPLIANT;
}

Compliance::Summary Compliance::generate_summary(const std::vector<PointResult>& results) const {
    Summary summary;
    summary.standard = standard_name_;
    summary.category = to_string(category_);
    summary.total_points = results.size();
    summary.compliant_points = 0;
    summary.marginal_points = 0;
    summary.non_compliant_points = 0;
    summary.max_field_value = 0.0;
    summary.max_percentage_of_limit = 0.0;

    for (const auto& result : results) {
        switch (result.status) {
            case ComplianceStatus::COMPLIANT:
                summary.compliant_points++;
                break;
            case ComplianceStatus::MARGINAL:
                summary.marginal_points++;
                break;
            case ComplianceStatus::NON_COMPLIANT:
                summary.non_compliant_points++;
                break;
        }

        if (result.field_value > summary.max_field_value) {
            summary.max_field_value = result.field_value;
        }
        if (result.percentage_of_limit > summary.max_percentage_of_limit) {
            summary.max_percentage_of_limit = result.percentage_of_limit;
        }
    }

    summary.overall_compliant = (summary.non_compliant_points == 0);

    return summary;
}

} // namespace emf
