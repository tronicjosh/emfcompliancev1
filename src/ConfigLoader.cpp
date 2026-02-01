#include "ConfigLoader.h"
#include <yaml-cpp/yaml.h>
#include <stdexcept>
#include <algorithm>

namespace emf {

SimulationConfig ConfigLoader::load(const std::string& filepath) {
    SimulationConfig config;

    try {
        YAML::Node yaml = YAML::LoadFile(filepath);

        // Simulation name (optional)
        if (yaml["name"]) {
            config.name = yaml["name"].as<std::string>();
        } else {
            config.name = "EMF Compliance Analysis";
        }

        // Grid configuration
        if (yaml["grid"]) {
            auto grid_node = yaml["grid"];
            config.grid.x_min = grid_node["x_min"].as<double>(-100.0);
            config.grid.x_max = grid_node["x_max"].as<double>(100.0);
            config.grid.y_min = grid_node["y_min"].as<double>(-100.0);
            config.grid.y_max = grid_node["y_max"].as<double>(100.0);
            config.grid.z_level = grid_node["z_level"].as<double>(1.5);
            config.grid.resolution = grid_node["resolution"].as<double>(1.0);
        } else {
            // Default grid
            config.grid.x_min = -100.0;
            config.grid.x_max = 100.0;
            config.grid.y_min = -100.0;
            config.grid.y_max = 100.0;
            config.grid.z_level = 1.5;
            config.grid.resolution = 1.0;
        }

        // Compliance configuration
        if (yaml["compliance"]) {
            auto comp_node = yaml["compliance"];
            config.compliance.standard = comp_node["standard"].as<std::string>("ICNIRP_2020");

            std::string category_str = comp_node["category"].as<std::string>("general_public");
            config.compliance.category = parse_exposure_category(category_str);
        } else {
            config.compliance.standard = "ICNIRP_2020";
            config.compliance.category = ExposureCategory::GENERAL_PUBLIC;
        }

        // Antennas
        if (yaml["antennas"]) {
            for (const auto& ant_node : yaml["antennas"]) {
                AntennaConfig antenna;

                antenna.id = ant_node["id"].as<std::string>("antenna_" + std::to_string(config.antennas.size() + 1));
                antenna.pattern_file = ant_node["pattern_file"].as<std::string>("");
                antenna.frequency_mhz = ant_node["frequency_mhz"].as<double>(1800.0);
                antenna.power_eirp_watts = ant_node["power_eirp_watts"].as<double>(100.0);

                // Position
                if (ant_node["position"]) {
                    auto pos = ant_node["position"];
                    antenna.position.x = pos["x"].as<double>(0.0);
                    antenna.position.y = pos["y"].as<double>(0.0);
                    antenna.position.z = pos["z"].as<double>(30.0);
                } else {
                    antenna.position = {0.0, 0.0, 30.0};
                }

                // Orientation
                if (ant_node["orientation"]) {
                    auto ori = ant_node["orientation"];
                    antenna.orientation.azimuth_deg = ori["azimuth_deg"].as<double>(0.0);
                    antenna.orientation.tilt_deg = ori["tilt_deg"].as<double>(0.0);
                } else {
                    antenna.orientation = {0.0, 0.0};
                }

                config.antennas.push_back(antenna);
            }
        }

        // If no antennas defined, create a default isotropic antenna
        if (config.antennas.empty()) {
            AntennaConfig default_antenna;
            default_antenna.id = "default";
            default_antenna.pattern_file = "isotropic";
            default_antenna.frequency_mhz = 1800.0;
            default_antenna.power_eirp_watts = 100.0;
            default_antenna.position = {0.0, 0.0, 30.0};
            default_antenna.orientation = {0.0, 0.0};
            config.antennas.push_back(default_antenna);
        }

    } catch (const YAML::Exception& e) {
        throw std::runtime_error("Failed to parse config file: " + std::string(e.what()));
    }

    return config;
}

bool ConfigLoader::validate(const SimulationConfig& config, std::string& error_message) {
    // Validate grid
    if (config.grid.x_min >= config.grid.x_max) {
        error_message = "Invalid grid: x_min must be less than x_max";
        return false;
    }
    if (config.grid.y_min >= config.grid.y_max) {
        error_message = "Invalid grid: y_min must be less than y_max";
        return false;
    }
    if (config.grid.resolution <= 0) {
        error_message = "Invalid grid: resolution must be positive";
        return false;
    }
    if (config.grid.resolution < 0.1) {
        error_message = "Warning: Very fine resolution may result in long computation times";
        // This is a warning, not an error - continue
    }

    // Validate antennas
    if (config.antennas.empty()) {
        error_message = "No antennas defined";
        return false;
    }

    for (const auto& antenna : config.antennas) {
        if (antenna.frequency_mhz <= 0) {
            error_message = "Invalid antenna " + antenna.id + ": frequency must be positive";
            return false;
        }
        if (antenna.power_eirp_watts < 0) {
            error_message = "Invalid antenna " + antenna.id + ": power must be non-negative";
            return false;
        }
    }

    return true;
}

} // namespace emf
