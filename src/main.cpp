#include "Types.h"
#include "ConfigLoader.h"
#include "Antenna.h"
#include "Grid.h"
#include "FieldSolver.h"
#include "Compliance.h"
#include "OutputWriter.h"

#include <iostream>
#include <string>
#include <filesystem>

namespace fs = std::filesystem;

void print_usage(const char* program) {
    std::cerr << "Usage: " << program << " [options] <config.yaml>\n"
              << "\nOptions:\n"
              << "  -o, --output <dir>   Output directory (default: ./output)\n"
              << "  -h, --help           Show this help message\n"
              << "  -v, --verbose        Verbose output\n"
              << "\nReturn codes:\n"
              << "  0  Success, all points compliant\n"
              << "  1  Success, non-compliant points found\n"
              << "  2  Configuration or runtime error\n";
}

int main(int argc, char* argv[]) {
    std::string config_path;
    std::string output_dir = "output";
    bool verbose = false;

    // Parse command line arguments
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        }
        else if (arg == "-v" || arg == "--verbose") {
            verbose = true;
        }
        else if ((arg == "-o" || arg == "--output") && i + 1 < argc) {
            output_dir = argv[++i];
        }
        else if (arg[0] != '-') {
            config_path = arg;
        }
        else {
            std::cerr << "Unknown option: " << arg << "\n";
            print_usage(argv[0]);
            return 2;
        }
    }

    if (config_path.empty()) {
        std::cerr << "Error: No configuration file specified\n";
        print_usage(argv[0]);
        return 2;
    }

    try {
        // Load configuration
        if (verbose) {
            std::cout << "Loading configuration from: " << config_path << "\n";
        }

        emf::SimulationConfig config = emf::ConfigLoader::load(config_path);

        // Validate configuration
        std::string validation_error;
        if (!emf::ConfigLoader::validate(config, validation_error)) {
            std::cerr << "Configuration error: " << validation_error << "\n";
            return 2;
        }

        if (verbose) {
            std::cout << "Simulation: " << config.name << "\n";
            std::cout << "Standard: " << config.compliance.standard << "\n";
            std::cout << "Grid: " << config.grid.x_min << " to " << config.grid.x_max
                      << " x " << config.grid.y_min << " to " << config.grid.y_max
                      << " @ z=" << config.grid.z_level << "m\n";
            std::cout << "Resolution: " << config.grid.resolution << "m\n";
            std::cout << "Antennas: " << config.antennas.size() << "\n";
        }

        // Create compliance checker
        emf::Compliance compliance(config.compliance.standard, config.compliance.category);

        // Create field solver and add antennas
        emf::FieldSolver solver;
        for (const auto& ant_config : config.antennas) {
            if (verbose) {
                std::cout << "Adding antenna: " << ant_config.id
                          << " @ (" << ant_config.position.x << ", "
                          << ant_config.position.y << ", "
                          << ant_config.position.z << ")\n";
            }
            solver.add_antenna(ant_config);
        }

        // Create calculation grid
        emf::Grid grid(config.grid);
        if (verbose) {
            std::cout << "Grid points: " << grid.total_points() << "\n";
        }

        // Solve
        if (verbose) {
            std::cout << "Calculating field strengths...\n";
        }
        emf::GridResults results = solver.solve(grid, compliance);

        // Generate summary
        emf::Compliance::Summary summary = compliance.generate_summary(results.get_results());

        // Find compliance boundaries
        if (verbose) {
            std::cout << "Finding compliance boundaries...\n";
        }
        auto boundaries = solver.find_all_compliance_boundaries(compliance);

        // Create output directory
        fs::create_directories(output_dir);

        // Write results
        std::string csv_path = output_dir + "/results.csv";
        std::string report_path = output_dir + "/report.json";

        if (verbose) {
            std::cout << "Writing results to: " << csv_path << "\n";
        }
        emf::OutputWriter::write_csv(csv_path, results);

        if (verbose) {
            std::cout << "Writing report to: " << report_path << "\n";
        }
        emf::OutputWriter::write_report(report_path, config, results, summary, boundaries);

        // Print summary
        std::cout << "\n=== EMF Compliance Analysis Results ===\n";
        std::cout << "Standard: " << summary.standard << " (" << summary.category << ")\n";
        std::cout << "Total points analyzed: " << summary.total_points << "\n";
        std::cout << "Compliant: " << summary.compliant_points
                  << " (" << (100.0 * summary.compliant_points / summary.total_points) << "%)\n";
        std::cout << "Marginal (80-100%): " << summary.marginal_points << "\n";
        std::cout << "Non-compliant: " << summary.non_compliant_points << "\n";
        std::cout << "Max field: " << summary.max_field_value << " V/m\n";
        std::cout << "Max % of limit: " << summary.max_percentage_of_limit << "%\n";
        std::cout << "\nCompliance boundaries:\n";
        for (const auto& [antenna_id, distance] : boundaries) {
            std::cout << "  " << antenna_id << ": " << distance << " m\n";
        }
        std::cout << "\nOverall: " << (summary.overall_compliant ? "COMPLIANT" : "NON-COMPLIANT") << "\n";

        // Return appropriate exit code
        return summary.overall_compliant ? 0 : 1;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 2;
    }
}
