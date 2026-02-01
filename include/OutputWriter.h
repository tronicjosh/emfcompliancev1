#ifndef OUTPUT_WRITER_H
#define OUTPUT_WRITER_H

#include "Types.h"
#include "Grid.h"
#include "Compliance.h"
#include <string>
#include <map>

namespace emf {

// Write simulation results to files
class OutputWriter {
public:
    // Write grid results to CSV file
    static void write_csv(const std::string& filepath, const GridResults& results);

    // Write compliance report to JSON file
    static void write_report(const std::string& filepath,
                             const SimulationConfig& config,
                             const GridResults& results,
                             const Compliance::Summary& summary,
                             const std::map<std::string, double>& boundaries);
};

} // namespace emf

#endif // OUTPUT_WRITER_H
