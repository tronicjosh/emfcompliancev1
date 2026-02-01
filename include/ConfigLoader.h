#ifndef CONFIG_LOADER_H
#define CONFIG_LOADER_H

#include "Types.h"
#include <string>

namespace emf {

// Load simulation configuration from YAML file
class ConfigLoader {
public:
    // Load configuration from file
    static SimulationConfig load(const std::string& filepath);

    // Validate configuration
    static bool validate(const SimulationConfig& config, std::string& error_message);
};

} // namespace emf

#endif // CONFIG_LOADER_H
