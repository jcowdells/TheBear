import math

X = 0
Y = 1

U = 0
V = 1

def line_gradient(a, b):
    d_x = a[X] - b[X]
    d_y = a[Y] - b[Y]

    if d_x == 0 and d_y == 0:
        return 1, 1, 0
    elif math.fabs(d_x) > math.fabs(d_y):
        gradient = d_y / d_x
        intercept = a[Y] - gradient * a[X]
        return -gradient, 1, intercept
    else:
        gradient = d_x / d_y
        intercept = a[X] - gradient * a[Y]
        return 1, -gradient, intercept

def line_bbox(a, b):
    min_x = min(a[X], b[X])
    max_x = max(a[X], b[X])
    min_y = min(a[Y], b[Y])
    max_y = max(a[Y], b[Y])
    return min_x, min_y, max_x, max_y

def line_iter_points(a, b):
    gx, gy, c = line_gradient(a, b)
    min_x, min_y, max_x, max_y = line_bbox(a, b)

    if gy == 1:
        for x in range(min_x, max_x + 1):
            yield x, round(line_solve_y(x, gx, c))
    elif gx == 1:
        for y in range(min_y, max_y + 1):
            yield round(line_solve_x(y, gy, c)), y

def line_solve_x(y, m, c):
    return -m * y - c * -1

def line_solve_y(x, m, c):
    return -m * x - c * -1

def triangle_signed_area(a, b, c):
    area = (b[X] - a[X]) * (c[Y] - a[Y]) - (b[Y] - a[Y]) * (c[X] - a[X])
    return area

def triangle_uvw(a, b, c, p):
    d = (b[Y] - c[Y]) * (a[X] - c[X]) + (c[X] - b[X]) * (a[Y] - c[Y])
    u = ((b[Y] - c[Y]) * (p[X] - c[X]) + (c[X] - b[X]) * (p[Y] - c[Y])) / d
    v = ((c[Y] - a[Y]) * (p[X] - c[X]) + (a[X] - c[X]) * (p[Y] - c[Y])) / d
    w = 1 - u - v
    return u, v, w

def triangle_bbox(a, b, c):
    min_x = min(a[X], b[X], c[X])
    max_x = max(a[X], b[X], c[X])
    min_y = min(a[Y], b[Y], c[Y])
    max_y = max(a[Y], b[Y], c[Y])
    return min_x, min_y, max_x, max_y

def triangle_contains(a, b, c, p):
    area_a = triangle_signed_area(a, b, p)
    area_b = triangle_signed_area(b, c, p)
    area_c = triangle_signed_area(c, a, p)
    return area_a >= 0 and area_b >= 0 and area_c >= 0

def triangle_uv(a, b, c, uv_a, uv_b, uv_c, p):
    uf, vf, wf = triangle_uvw(a, b, c, p)
    u = uv_a[U] * uf + uv_b[U] * vf + uv_c[U] * wf
    v = uv_a[V] * uf + uv_b[V] * vf + uv_c[V] * wf
    return u, v

def point_rotate_centre(p, c, angle):
    cx = p[X] - c[X]
    cy = p[Y] - c[Y]
    rx = cx * math.cos(angle) - cy * math.sin(angle)
    ry = cx * math.sin(angle) + cy * math.cos(angle)
    return round(rx + c[X]), round(ry + c[Y])

def point_rotate(p, angle):
    rx = p[X] * math.cos(angle) - p[Y] * math.sin(angle)
    ry = p[X] * math.sin(angle) + p[Y] * math.cos(angle)
    return rx, ry

def point_centre(p, c):
    return p[X] - c[X], p[Y] - c[Y]

def point_divide(p, d):
    return p[X] / d, p[Y] / d

def point_add(a, b):
    return a[X] + b[X], a[Y] + b[Y]

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
    return round(point[X] * screen_width_ch), round(point[Y] * screen_height_ch)