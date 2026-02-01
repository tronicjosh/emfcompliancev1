#ifndef VECTOR3_H
#define VECTOR3_H

#include <cmath>

namespace emf {

class Vector3 {
public:
    double x, y, z;

    // Constructors
    Vector3();
    Vector3(double x, double y, double z);

    // Arithmetic operators
    Vector3 operator+(const Vector3& other) const;
    Vector3 operator-(const Vector3& other) const;
    Vector3 operator*(double scalar) const;
    Vector3 operator/(double scalar) const;
    Vector3& operator+=(const Vector3& other);
    Vector3& operator-=(const Vector3& other);
    Vector3& operator*=(double scalar);
    Vector3 operator-() const;

    // Vector operations
    double magnitude() const;
    double magnitude_squared() const;
    Vector3 normalized() const;
    double dot(const Vector3& other) const;
    Vector3 cross(const Vector3& other) const;

    // Spherical coordinate conversion
    // Returns (azimuth_rad, elevation_rad) from this vector direction
    // Azimuth: angle from +X axis in XY plane, counter-clockwise
    // Elevation: angle from XY plane (positive = up)
    void to_spherical(double& azimuth_rad, double& elevation_rad) const;

    // Create unit vector from spherical coordinates
    static Vector3 from_spherical(double azimuth_rad, double elevation_rad);

    // Rotate this vector around an axis
    Vector3 rotate_around_z(double angle_rad) const;
    Vector3 rotate_around_y(double angle_rad) const;
    Vector3 rotate_around_x(double angle_rad) const;
};

// Scalar * vector
inline Vector3 operator*(double scalar, const Vector3& v) {
    return v * scalar;
}

} // namespace emf

#endif // VECTOR3_H
