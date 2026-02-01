#include "OutputWriter.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iomanip>
#include <stdexcept>

namespace emf {

using json = nlohmann::json;

void OutputWriter::write_csv(const std::string& filepath, const GridResults& results) {
    std::ofstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open output file: " + filepath);
    }

    // Write header
    file << "x,y,z,field_value_v_m,limit_v_m,percentage_of_limit,status\n";

    // Write data
    file << std::fixed << std::setprecision(6);
    for (const auto& point : results.get_results()) {
        file << point.x << ","
             << point.y << ","
             << point.z << ","
             << point.field_value << ","
             << point.limit << ","
             << point.percentage_of_limit << ","
             << to_string(point.status) << "\n";
    }

    file.close();
}

void OutputWriter::write_report(const std::string& filepath,
                                 const SimulationConfig& config,
                                 const GridResults& results,
                                 const Compliance::Summary& summary,
                                 const std::map<std::string, double>& boundaries) {
    json report;

    // Metadata
    report["metadata"] = {
        {"simulation_name", config.name},
        {"standard", summary.standard},
        {"category", summary.category}
    };

    // Grid info
    report["grid"] = {
        {"bounds", {
            {"x_min", config.grid.x_min},
            {"x_max", config.grid.x_max},
            {"y_min", config.grid.y_min},
            {"y_max", config.grid.y_max}
        }},
        {"z_level", config.grid.z_level},
        {"resolution", config.grid.resolution},
        {"total_points", summary.total_points}
    };

    // Antenna info
    json antennas_json = json::array();
    for (const auto& ant : config.antennas) {
        antennas_json.push_back({
            {"id", ant.id},
            {"frequency_mhz", ant.frequency_mhz},
            {"power_eirp_watts", ant.power_eirp_watts},
            {"position", {{"x", ant.position.x}, {"y", ant.position.y}, {"z", ant.position.z}}},
            {"orientation", {{"azimuth_deg", ant.orientation.azimuth_deg}, {"tilt_deg", ant.orientation.tilt_deg}}}
        });
    }
    report["antennas"] = antennas_json;

    // Summary
    report["summary"] = {
        {"overall_compliant", summary.overall_compliant},
        {"compliant_points", summary.compliant_points},
        {"marginal_points", summary.marginal_points},
        {"non_compliant_points", summary.non_compliant_points},
        {"max_field_value_v_m", summary.max_field_value},
        {"max_percentage_of_limit", summary.max_percentage_of_limit}
    };

    // Compliance boundaries
    json boundaries_json;
    for (const auto& [antenna_id, distance] : boundaries) {
        boundaries_json[antenna_id] = distance;
    }
    report["compliance_boundaries"] = boundaries_json;

    // Write to file
    std::ofstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open report file: " + filepath);
    }

    file << std::setw(2) << report << std::endl;
    file.close();
}

} // namespace emf
