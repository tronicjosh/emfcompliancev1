cmake_minimum_required(VERSION 3.14)
project(emfcompliance VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find required packages
find_package(yaml-cpp REQUIRED)

# nlohmann/json is header-only, we'll fetch it
include(FetchContent)
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

# Define source files
set(SOURCES
    src/Vector3.cpp
    src/RadiationPattern.cpp
    src/Antenna.cpp
    src/Grid.cpp
    src/FieldSolver.cpp
    src/Compliance.cpp
    src/ConfigLoader.cpp
    src/OutputWriter.cpp
    src/main.cpp
)

# Define header files
set(HEADERS
    include/Types.h
    include/Vector3.h
    include/RadiationPattern.h
    include/Antenna.h
    include/Grid.h
    include/FieldSolver.h
    include/Compliance.h
    include/ConfigLoader.h
    include/OutputWriter.h
)

# Create executable
add_executable(emfcompliance ${SOURCES} ${HEADERS})

# Include directories
target_include_directories(emfcompliance PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Link libraries
target_link_libraries(emfcompliance PRIVATE
    yaml-cpp
    nlohmann_json::nlohmann_json
)

# Enable warnings
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(emfcompliance PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
    target_compile_options(emfcompliance PRIVATE /W4)
endif()

# Installation
install(TARGETS emfcompliance DESTINATION bin)
