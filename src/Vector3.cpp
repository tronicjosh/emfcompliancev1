#include "Vector3.h"
#include <cmath>

namespace emf {

Vector3::Vector3() : x(0), y(0), z(0) {}

Vector3::Vector3(double x, double y, double z) : x(x), y(y), z(z) {}

Vector3 Vector3::operator+(const Vector3& other) const {
    return Vector3(x + other.x, y + other.y, z + other.z);
}

Vector3 Vector3::operator-(const Vector3& other) const {
    return Vector3(x - other.x, y - other.y, z - other.z);
}

Vector3 Vector3::operator*(double scalar) const {
    return Vector3(x * scalar, y * scalar, z * scalar);
}

Vector3 Vector3::operator/(double scalar) const {
    return Vector3(x / scalar, y / scalar, z / scalar);
}

Vector3& Vector3::operator+=(const Vector3& other) {
    x += other.x;
    y += other.y;
    z += other.z;
    return *this;
}

Vector3& Vector3::operator-=(const Vector3& other) {
    x -= other.x;
    y -= other.y;
    z -= other.z;
    return *this;
}

Vector3& Vector3::operator*=(double scalar) {
    x *= scalar;
    y *= scalar;
    z *= scalar;
    return *this;
}

Vector3 Vector3::operator-() const {
    return Vector3(-x, -y, -z);
}

double Vector3::magnitude() const {
    return std::sqrt(x * x + y * y + z * z);
}

double Vector3::magnitude_squared() const {
    return x * x + y * y + z * z;
}

Vector3 Vector3::normalized() const {
    double mag = magnitude();
    if (mag < 1e-10) {
        return Vector3(0, 0, 0);
    }
    return *this / mag;
}

double Vector3::dot(const Vector3& other) const {
    return x * other.x + y * other.y + z * other.z;
}

Vector3 Vector3::cross(const Vector3& other) const {
    return Vector3(
        y * other.z - z * other.y,
        z * other.x - x * other.z,
        x * other.y - y * other.x
    );
}

void Vector3::to_spherical(double& azimuth_rad, double& elevation_rad) const {
    double r_xy = std::sqrt(x * x + y * y);

    // Azimuth: angle from +X axis in XY plane
    azimuth_rad = std::atan2(y, x);

    // Elevation: angle from XY plane
    elevation_rad = std::atan2(z, r_xy);
}

Vector3 Vector3::from_spherical(double azimuth_rad, double elevation_rad) {
    double cos_elev = std::cos(elevation_rad);
    return Vector3(
        cos_elev * std::cos(azimuth_rad),
        cos_elev * std::sin(azimuth_rad),
        std::sin(elevation_rad)
    );
}

Vector3 Vector3::rotate_around_z(double angle_rad) const {
    double c = std::cos(angle_rad);
    double s = std::sin(angle_rad);
    return Vector3(
        x * c - y * s,
        x * s + y * c,
        z
    );
}

Vector3 Vector3::rotate_around_y(double angle_rad) const {
    double c = std::cos(angle_rad);
    double s = std::sin(angle_rad);
    return Vector3(
        x * c + z * s,
        y,
        -x * s + z * c
    );
}

Vector3 Vector3::rotate_around_x(double angle_rad) const {
    double c = std::cos(angle_rad);
    double s = std::sin(angle_rad);
    return Vector3(
        x,
        y * c - z * s,
        y * s + z * c
    );
}

} // namespace emf
