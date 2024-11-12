import math

# Define some constants

HALF_PI = math.pi / 2

X = 0
Y = 1
Z = 2
W = 3

U = 0
V = 1

A = 0
B = 1

VISIBLE   = 0
INVISIBLE = 1
CLIP      = 2

# Find the gradient of a line ax + by + c = 0 from two points
def line_gradient(a, b):
    d_x = a[X] - b[X]
    d_y = a[Y] - b[Y]

    if d_x == 0 and d_y == 0:
        return 1, 1, 0
    elif math.fabs(d_x) > math.fabs(d_y): # Avoid having a very large gradient
        gradient = d_y / d_x
        intercept = a[Y] - gradient * a[X]
        return -gradient, 1, -intercept
    else:
        gradient = d_x / d_y
        intercept = a[X] - gradient * a[Y]
        return 1, -gradient, -intercept

# Get the bounding box of two points
def line_bbox(a, b):
    min_x = min(a[X], b[X])
    max_x = max(a[X], b[X])
    min_y = min(a[Y], b[Y])
    max_y = max(a[Y], b[Y])
    return min_x, min_y, max_x, max_y

# Iterate over points at integer intervals in a line
def line_iter_points(a, b, screen_x, screen_y):
    gx, gy, c = line_gradient(a, b)
    min_x, min_y, max_x, max_y = line_bbox(a, b)

    min_x = max(0, min_x)
    min_y = max(0, min_y)
    max_x = min(screen_x - 1, max_x)
    max_y = min(screen_y - 1, max_y)

    if gy == 1:
        for x in range(min_x, max_x + 1):
            yield x, round(line_solve_y(x, gx, c))
    elif gx == 1:
        for y in range(min_y, max_y + 1):
            yield round(line_solve_x(y, gy, c)), y

# Given a y coordinate, find the x coordinate
def line_solve_x(y, m, c):
    return -m * y - c

# Given an x coordinate, find the y coordinate
def line_solve_y(x, m, c):
    return -m * x - c

# Get the perpendicular line to ax + by + x = 0
def line_perpendicular(mx, my, p):
    return my, -mx, mx * p[Y] - my * p[X]

# Find the point where two lines intersect
def line_intersect(mx1, my1, c1, mx2, my2, c2):
      d = mx1 * my2 - mx2 * my1
      if d == 0:
          return math.inf, math.inf
      x = (my1 * c2 - my2 * c1) / d
      y = (mx2 * c1 - mx1 * c2) / d
      return x, y

# Get the length^2 of a line
def line_square_length(a, b):
    return (a[X] - b[X]) ** 2 + (a[Y] - b[Y]) ** 2

# Get the length of a line between two points
def line_length(a, b):
    return math.sqrt(line_square_length(a, b))

# Check if a point is within a radius of a line
def line_collision(a, b, p, r):
    mx1, my1, c1 = line_gradient(a, b)
    mx2, my2, c2 = line_perpendicular(mx1, my1, p)
    ip = line_intersect(mx1, my1, c1, mx2, my2, c2)

    if point_inside(a, b, ip): # If intersect not in the line, it can't hit
        return line_square_length(ip, p) < r
    else:
        return False

# Get the angle of a line
def line_angle(a, b):
    delta_x = b[X] - a[X]
    delta_y = b[Y] - a[Y]
    return math.atan2(delta_y, delta_x) + HALF_PI

# Get the signed area of a triangle
def triangle_signed_area(a, b, c):
    area = (b[X] - a[X]) * (c[Y] - a[Y]) - (b[Y] - a[Y]) * (c[X] - a[X])
    return area

# Get the u, v, w barycentric coordinates of a point inside a triangle
def triangle_uvw(a, b, c, p):
    d = (b[Y] - c[Y]) * (a[X] - c[X]) + (c[X] - b[X]) * (a[Y] - c[Y])
    if d != 0: # avoid division by 0 error
        u = ((b[Y] - c[Y]) * (p[X] - c[X]) + (c[X] - b[X]) * (p[Y] - c[Y])) / d # magic numbers
        v = ((c[Y] - a[Y]) * (p[X] - c[X]) + (a[X] - c[X]) * (p[Y] - c[Y])) / d
        w = 1 - u - v
    else:
        u = 1
        v = 0
        w = 0
    return u, v, w

# Get the bounding box of a triangle
def triangle_bbox(a, b, c):
    min_x = min(a[X], b[X], c[X])
    max_x = max(a[X], b[X], c[X])
    min_y = min(a[Y], b[Y], c[Y])
    max_y = max(a[Y], b[Y], c[Y])
    return min_x, min_y, max_x, max_y

# Check if a triangle contains a point
def triangle_contains(a, b, c, p):
    area_a = triangle_signed_area(a, b, p)
    area_b = triangle_signed_area(b, c, p)
    area_c = triangle_signed_area(c, a, p)
    return area_a >= 0 and area_b >= 0 and area_c >= 0

# Get the interpolated uv coordinates of a point inside a triangle
def triangle_uv(a, b, c, uv_a, uv_b, uv_c, p):
    uf, vf, wf = triangle_uvw(a, b, c, p)
    u = uv_a[U] * uf + uv_b[U] * vf + uv_c[U] * wf
    v = uv_a[V] * uf + uv_b[V] * vf + uv_c[V] * wf
    return u, v

# Rotate a point around a centre point
def point_rotate_centre(p, c, angle):
    cx = p[X] - c[X]
    cy = p[Y] - c[Y]
    rx = cx * math.cos(angle) - cy * math.sin(angle)
    ry = cx * math.sin(angle) + cy * math.cos(angle)
    return round(rx + c[X]), round(ry + c[Y])

# Rotate a point around (0, 0)
def point_rotate(p, angle):
    rx = p[X] * math.cos(angle) - p[Y] * math.sin(angle)
    ry = p[X] * math.sin(angle) + p[Y] * math.cos(angle)
    return rx, ry

# Centre a point around a new centre
def point_centre(p, c):
    return p[X] - c[X], p[Y] - c[Y]

# Divide a point
def point_divide(p, d):
    return p[X] / d, p[Y] / d

# Add two points
def point_add(a, b):
    return a[X] + b[X], a[Y] + b[Y]

# Subtract two points
def point_subtract(a, b):
    return a[X] - b[X], a[Y] - b[Y]

# Multiply a point
def point_multiply(p, m):
    return p[X] * m, p[Y] * m

# Transform a point based on screen size, centre, rotation
def point_transform(point, centre, rotation, max_view, screen_width_px, screen_height_px, screen_width_ch, screen_height_ch):
    point = point_centre(point, centre)
    point = point_rotate(point, rotation)
    point = point_divide(point, max_view)
    if screen_width_px > screen_height_px:
        scale = screen_height_px / screen_width_px
        point = point[X], point[Y] / scale
    else:
        scale = screen_width_px / screen_height_px
        point = point[X] / scale, point[Y]
    point = point_add(point, (1, 1))
    point = point_divide(point, 2)
    try:
        return round(point[X] * screen_width_ch), round(point[Y] * screen_height_ch)
    except ValueError:
        return -1, -1
    except OverflowError:
        return -1, -1

# Check if a point is inside a line
def point_inside(a, b, p):
    in_x = min(a[X], b[X]) <= p[X] <= max(a[X], b[X])
    if not in_x: return False
    in_y = min(a[Y], b[Y]) <= p[Y] <= max(a[Y], b[Y])
    return in_y

# Check if two points are within a radius of each other
def point_collision(a, p, r):
    return line_square_length(a, p) < r

# Get the normal of a point based on angle
def point_normal(a, p):
    v = vector_from_points(p, a)
    v = vector_perpendicular(v)
    v = vector_normalise(v)
    return v

# Create a vector based on an angle and a distance
def vector_from_angle(a, r):
    return r * math.cos(a + HALF_PI), r * math.sin(a + HALF_PI)

# Create a vector from two points
def vector_from_points(a, b):
    return b[X] - a[X], b[Y] - a[Y]

# Get the magnitude of a vector
def vector_magnitude(v):
    return math.sqrt(v[X] * v[X] + v[Y] * v[Y])

# Normalise a vector so its magnitude is 1
def vector_normalise(v):
    mag = vector_magnitude(v)
    return v[X] / mag, v[Y] / mag

# Compute the dot product of two vectors
def vector_dot(v, q):
    return v[X] * q[X] + v[Y] * q[Y]

# Compute the determinant of two vectors
def vector_determinant(v, q):
    return v[X] * q[Y] - v[Y] * q[X]

# Project a vector onto another
def vector_project(v, q):
    mul = vector_dot(v, q)
    return v[X] - q[X] * mul, v[Y] - q[Y] * mul

# Subtract two vectors
def vector_subtract(v, q):
    return v[X] - q[X], v[Y] - q[Y]

# Add two vectors
def vector_add(v, q):
    return v[X] + q[X], v[Y] + q[Y]

# Multiply a vector by a value
def vector_multiply(v, m):
    return v[X] * m, v[Y] * m

# Find a vector perpendicular to another
def vector_perpendicular(v):
    return v[Y], -v[X]

# Get the angle between two vectors
def vector_angle(v, q):
    dot = vector_dot(v, q)
    det = vector_determinant(v, q)
    return math.atan2(det, dot)

# Check if a path is obstructed by a line
def is_path_obstructed(a, b, l, r):
    mx1, my1, c1 = line_gradient(a, b)
    mx2, my2, c2 = line_gradient(*l)
    intersect = line_intersect(mx1, my1, c1, mx2, my2, c2)
    if not point_inside(a, b, intersect):
        return False
    if point_inside(*l, intersect):
        return True
    else: # If not directly touching, is it near the edges
        sr = r * r
        return line_square_length(l[A], intersect) < sr or line_square_length(l[B], intersect) < sr

# Linear interpolation between points
def lerp_p(a, b, t):
    return lerp_v(a[X], b[X], t), lerp_v(a[Y], b[Y], t)

# Linear interpolation between values
def lerp_v(a, b, t):
    return a + (b - a) * t

# Multiply a 4x4 matrix by a 4d point
def mat4_multiply(matrix, point):
    return (
        point[X] * matrix[0] +  point[Y] * matrix[1] +  point[Z] * matrix[2] +  point[W] * matrix[3],
        point[X] * matrix[4] +  point[Y] * matrix[5] +  point[Z] * matrix[6] +  point[W] * matrix[7],
        point[X] * matrix[8] +  point[Y] * matrix[9] +  point[Z] * matrix[10] + point[W] * matrix[11],
        point[X] * matrix[12] + point[Y] * matrix[13] + point[Z] * matrix[14] + point[W] * matrix[15]
    )

# Create a 4x4 rotation matrix in the Z axis
def mat4_rotation_z(angle):
    sin = math.sin(angle)
    cos = math.cos(angle)
    return (
        cos,  0, sin, 0,
        0,    1, 0,   0,
        -sin, 0, cos, 0,
        0,    0, 0,   1
    )

# Create a 3x3 translation matrix
def mat4_translation(t_x, t_y, t_z):
    return (
        1, 0, 0, t_x,
        0, 1, 0, t_y,
        0, 0, 1, t_z,
        0, 0, 0, 1
    )

# Create a 4x4 identity matrix
def mat4_identity():
    return (
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1
    )

# Create a 4x4 projection matrix
def mat4_projection(fov, aspect_ratio, near, far):
    tangent = math.tan(fov / 2)
    top     = near * tangent
    right   = top * aspect_ratio
    delta   = far - near

    return (
        near / right, 0, 0, 0,
        0, near / top, 0, 0,
        0, 0, -(far + near) / delta, -(2 * far * near) / delta,
        0, 0, -1, 0
    )

# Perform a perspective divide / divide by W
def point_perspective_divide(point):
    if point[W] == 0:
        return 0, 0, 0
    return point[X] / point[W], point[Y] / point[W], point[Z] / point[W]

# Scale a value from range(-1, 1) to range(0, 1)
def p_scalar(v):
    return (v + 1) / 2

# Scale a coordinate from ranges(-1, 1) to ranges(0, 1)
def p_scale_point(point):
    px = p_scalar(point[X])
    py = p_scalar(point[Y])
    pz = p_scalar(point[Z])
    return px, py, pz

# Scale a point from ranges(0, 1) to ranges(0, screen_size)
def point_to_screen(point, screen_width, screen_height):
    return round(point[X] * screen_width), round(point[Y] * screen_height), point[Z]

# Compute the boundary coordinates of a point
def point_boundary_coordinates(point):
    return (
        point[W] + point[X],
        point[W] - point[X],
        point[W] + point[Y],
        point[W] - point[Y],
        point[W] + point[Z],
        point[W] - point[Z]
    )

# Compute the region code of a point, where 0=out, 1=in, for +x,-x,+y,-y,+z,-z, as a 6bit binary number
def point_region_code(bounds):
    code = 0
    for i in range(6):
        if bounds[i] < 0:
            code |= 1 << i
    return code

# Solve a parametric equation of two points, scaling between 0 and 1
def parametric_s(a, b, t):
    return lerp_v(a[X], b[X], t), lerp_v(a[Y], b[Y], t), lerp_v(a[Z], b[Z], t), lerp_v(a[W], b[W], t)

# Compute the new coordinates of two points making up a line, which are cropped to the camera view volume
def line_clip(a, b):
    a_bounds = point_boundary_coordinates(a)
    b_bounds = point_boundary_coordinates(b)

    a_region = point_region_code(a_bounds)
    b_region = point_region_code(b_bounds)

    if a_region | b_region == 0: # Both points are within all 6 planes
        return a, b
    elif a_region & b_region != 0: # Both points are outside of the same plane: not visible
        return None

    t_in = 0
    t_out = 1
    for i in range(6): # For each plane, compute the distance across the line before intersecting
        if b_bounds[i] < 0:
            t_hit = a_bounds[i] / (a_bounds[i] - b_bounds[i])
            t_out = min(t_hit, t_out)
        elif a_bounds[i] < 0:
            t_hit = a_bounds[i] / (a_bounds[i] - b_bounds[i])
            t_in = max(t_hit, t_in)
        if t_in > t_out: # If left over area is less than 0, not visible
            return None

    # Update points where necessary
    if a_region != 0:
        a_out = parametric_s(a, b, t_in)
    else:
        a_out = a

    if b_region != 0:
        b_out = parametric_s(a, b, t_out)
    else:
        b_out = b

    return a_out, b_out

# Convert homogenous point to screen point
def point_clip_to_screen(p, screen_width, screen_height):
    p = point_perspective_divide(p)
    p = p_scale_point(p)
    return point_to_screen(p, screen_width, screen_height)

# Convert two homogenous points, and return a line with screen coordinates
def line_clip_to_screen(a, b, screen_width, screen_height):
    a = point_clip_to_screen(a, screen_width, screen_height)
    b = point_clip_to_screen(b, screen_width, screen_height)
    return a, b