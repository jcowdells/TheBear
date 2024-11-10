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

# Multiply a 3x3 matrix by a 3d point
def mat3_multiply(matrix, point):
    return (
        point[X] * matrix[0] + point[Y] * matrix[1] + point[Z] * matrix[2],
        point[X] * matrix[3] + point[Y] * matrix[4] + point[Z] * matrix[5],
        point[X] * matrix[6] + point[Y] * matrix[7] + point[Z] * matrix[8]
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
        0, 0, -(far + near) / delta, -1,
        0, 0, -(2 * far * near) / delta, 0
    )

def point_perspective_divide(point):
    return point[X] / point[W], point[Y] / point[W], point[Z] / point[W]

def p_scalar(v):
    return (v + 1) / 2

def p_scale_point(point):
    px = p_scalar(point[X])
    py = p_scalar(point[Y])
    pz = p_scalar(point[Z])
    return px, py, pz

def point_to_screen(point, screen_width, screen_height):
    return round(point[X] * screen_width), round(point[Y] * screen_height), point[Z]

def point_region_code(point):
    code = 0
    if point[X] < -point[W]:
        code |= 1 << 0
    if point[X] > point[W]:
        code |= 1 << 1
    if point[Y] < -point[W]:
        code |= 1 << 2
    if point[Y] > point[W]:
        code |= 1 << 3
    if point[Z] < -point[W]:
        code |= 1 << 4
    if point[Z] > point[W]:
        code |= 1 << 5
    return code

def line_visible(a, b):
    reg_a = point_region_code(a)
    reg_b = point_region_code(b)
    if reg_a & reg_b == 0:
        return CLIP
    if reg_b | reg_a == 0:
        return VISIBLE
    else:
        return INVISIBLE

def parametric_t(a, b, w):
    return (w - a) / (b - a)

def parametric_s(a, b, t):
    return lerp_v(a[X], b[X], t), lerp_v(a[Y], b[Y], t), lerp_v(a[Z], b[Z], t), lerp_v(a[W], b[W], t)

def line_clip(a, b):
    x = [a[X], b[X]]
    y = [a[Y], b[Y]]
    z = [a[Z], b[Z]]
    w = (a[W], b[W])

    print(a)
    print(b)
    print("-----")

    dx = b[X] - a[X]
    dy = b[Y] - a[Y]
    dz = b[Z] - a[Z]
    for i in range(2):
        v_min = -w[i]
        v_max = w[i]
        if x[i] != x[1 - i]:
            if x[i] < v_min:
                t = parametric_t(x[i], x[1 - i], v_min)
                if 0 < t < 1:
                    x[i] = lerp_v(x[i], x[1 - i], t)
            elif x[i] > v_max:
                t = parametric_t(x[i], x[1 - i], v_max)
                if 0 < t < 1:
                    x[i] = lerp_v(x[i], x[1 - i], t)
        if y[i] != y[1 - i]:
            if y[i] < v_min:
                t = parametric_t(y[i], y[1 - i], v_min)
                if 0 < t < 1:
                    y[i] = lerp_v(y[i], y[1 - i], t)
            elif y[i] > v_max:
                t = parametric_t(y[i], y[1 - i], v_max)
                if 0 < t < 1:
                    y[i] = lerp_v(y[i], y[1 - i], t)
        if z[i] != z[1 - i]:
            if z[i] < v_min:
                t = parametric_t(z[i], z[1 - i], v_min)
                if 0 < t < 1:
                    z[i] = lerp_v(z[i], z[1 - i], t)
            elif y[i] > v_max:
                t = parametric_t(z[i], z[1 - i], v_max)
                if 0 < t < 1:
                    z[i] = lerp_v(z[i], z[1 - i], t)
    return (x[0], y[0], z[0], a[W]), (x[1], y[1], z[1], b[W])

def point_clip_to_screen(p, screen_width, screen_height):
    p = point_perspective_divide(p)
    p = p_scale_point(p)
    return point_to_screen(p, screen_width, screen_height)

def line_clip_to_screen(a, b, screen_width, screen_height):
    a = point_clip_to_screen(a, screen_width, screen_height)
    b = point_clip_to_screen(b, screen_width, screen_height)
    return a, b