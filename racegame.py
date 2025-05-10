from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import ctypes
import math
import random

# --- GLOBAL STATE ---
TRACK_WIDTH = 5.0
CONTROL_POINTS = []
SPLINE_POINTS = []
objects = []  # obstacles & boosts
particles = []  # weather particles
game_finished = False
weather = 0  # 0: sunny, 1: rain, 2: snow

# Car state
position    = [0.0, 0.0, 0.0]
orientation = 0.0  # Fixed at 0 for straight movement
velocity    = 0.0
top_speed   = 0.15
acceleration = 0.005
handling    = 0.06
BOOSTED_TOP_SPEED = top_speed * 2.0
max_speed   = top_speed
boost_end_time = 0

# Input keys
keys = {'accel': False, 'left': False, 'right': False, 'restart': False}

# Texture handle
track_tex = None

# Camera state
camera_mode = 1  # 0 = first-person, 1 = third-person

# --- TRACK GENERATION ---
def generate_control_points(n=2, length=150):
    CONTROL_POINTS.clear()
    # Straight track along z-axis
    CONTROL_POINTS.append((0, 0))
    CONTROL_POINTS.append((0, length))

def catmull_rom(p0, p1, p2, p3, t):
    t2, t3 = t*t, t*t*t
    def cr(a, b, c, d):
        return 0.5 * (2*b + (c-a)*t + (2*a - 5*b + 4*c - d)*t2 + (-a + 3*b - 3*c + d)*t3)
    return cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])

def generate_track():
    SPLINE_POINTS.clear()
    samples = 300
    for i in range(samples):
        t = i / float(samples)
        x = 0.0
        z = t * 150.0
        y = 0.0
        SPLINE_POINTS.append((x, y, z))

# --- OBJECT PLACEMENT ---
def generate_objects():

    num_obs = int(len(SPLINE_POINTS) / 10)  # 1 obstacle every 10 segments
    num_boost = int(len(SPLINE_POINTS) / 50)  # 1 boost every 50 segments

    objects.clear()
    N = len(SPLINE_POINTS)
    picks = random.sample(range(10, N-10), num_obs + num_boost)
    kinds = ['obs'] * num_obs + ['boost'] * num_boost
    random.shuffle(kinds)
    for idx, kind in zip(picks, kinds):
        x, y, z = SPLINE_POINTS[idx]
        x = random.uniform(-TRACK_WIDTH/2 + 0.25, TRACK_WIDTH/2 - 0.25)
        objects.append({'type': kind, 'pos': (x, y, z), 'active': True})

# --- PROCEDURAL CHECKERBOARD TEXTURE ---
def create_checkerboard_texture(size=64, check_size=8):
    tex_data = (ctypes.c_ubyte * (size * size * 3))()
    for y in range(size):
        for x in range(size):
            c = ((x // check_size) % 2) ^ ((y // check_size) % 2)
            color = 255 if c else 50
            idx = (y * size + x) * 3
            tex_data[idx]   = color
            tex_data[idx+1] = color
            tex_data[idx+2] = color
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, size, size, 0, GL_RGB, GL_UNSIGNED_BYTE, tex_data)
    return tex_id

# --- DRAW ROUTINES ---
def draw_track():
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, track_tex)
    glColor3f(1,1,1)
    glBegin(GL_QUADS)
    repeat = len(SPLINE_POINTS) / 10.0
    for i in range(len(SPLINE_POINTS)-1):
        x1,y1,z1 = SPLINE_POINTS[i]
        x2,y2,z2 = SPLINE_POINTS[i+1]
        nx, nz = -1, 0
        w = TRACK_WIDTH/2

        s1 = i / repeat
        s2 = (i+1) / repeat
        glTexCoord2f(s1, 0); glVertex3f(x1+nx*w, y1, z1+nz*w)
        glTexCoord2f(s1, 1); glVertex3f(x1-nx*w, y1, z1-nz*w)
        glTexCoord2f(s2, 1); glVertex3f(x2-nx*w, y2, z2-nz*w)
        glTexCoord2f(s2, 0); glVertex3f(x2+nx*w, y2, z2+nz*w)
    glEnd()
    glDisable(GL_TEXTURE_2D)

def draw_cube():
    glBegin(GL_QUADS)
    glVertex3f(-1,-1,1); glVertex3f(1,-1,1)
    glVertex3f(1,1,1);   glVertex3f(-1,1,1)
    glVertex3f(-1,-1,-1);glVertex3f(1,-1,-1)
    glVertex3f(1,1,-1);  glVertex3f(-1,1,-1)
    glVertex3f(-1,1,-1); glVertex3f(1,1,-1)
    glVertex3f(1,1,1);   glVertex3f(-1,1,1)
    glVertex3f(-1,-1,-1);glVertex3f(1,-1,-1)
    glVertex3f(1,-1,1);  glVertex3f(-1,-1,1)
    glVertex3f(-1,-1,-1);glVertex3f(-1,-1,1)
    glVertex3f(-1,1,1);  glVertex3f(-1,1,-1)
    glVertex3f(1,-1,-1); glVertex3f(1,-1,1)
    glVertex3f(1,1,1);   glVertex3f(1,1,-1)
    glEnd()

def draw_car():
    glPushMatrix()
    glTranslatef(*position)
    glRotatef(-math.degrees(orientation), 0,1,0)
    glScalef(0.2, 0.2, 0.2)
    glColor3f(1,0,0)
    draw_cube()
    glPopMatrix()

def draw_objects():
    for obj in objects:
        if not obj['active']:
            continue
        x,y,z = obj['pos']
        glPushMatrix()
        glTranslatef(x,y+0.125,z)
        if obj['type']=='obs':
            glColor3f(0.5,0.5,0.5)
            glScalef(0.25,0.25,0.25)
            draw_cube()
        else:
            glColor3f(1,1,0)
            glutSolidSphere(0.25,16,16)
        glPopMatrix()

def draw_particles():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_LIGHTING)
    if weather == 1:  # Rain
        glColor4f(0.5, 0.5, 1.0, 0.7)  # Semi-transparent blue
        glBegin(GL_LINES)
        for p in particles:
            x, y, z = p['pos']
            glVertex3f(x, y, z)
            glVertex3f(x, y - 1.0, z)
        glEnd()
    elif weather == 2:  # Snow
        glColor4f(1.0, 1.0, 1.0, 0.9)  # Semi-transparent white
        glPointSize(3.0)
        glBegin(GL_POINTS)
        for p in particles:
            x, y, z = p['pos']
            glVertex3f(x, y, z)
        glEnd()
        glPointSize(1.0)
    glEnable(GL_LIGHTING)
    glDisable(GL_BLEND)

def draw_sun():
    glPushMatrix()
    glTranslatef(0, 15, 150)  # Moved to end of track
    glColor3f(1.0, 1.0, 0.0)  # Yellow sun
    glutSolidSphere(4.0, 20, 20)  # Slightly smaller for distance
    glPopMatrix()

def draw_text(x, y, text):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, 800, 0, 600, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# --- PHYSICS & COLLISION ---
def aabb_collide(min1, max1, min2, max2):
    return all(min1[i] < max2[i] and max1[i] > min2[i] for i in range(3))

def check_collisions():
    global velocity, max_speed, boost_end_time
    cx,cy,cz = position
    car_min = (cx-0.1, cy-0.1, cz-0.1)
    car_max = (cx+0.1, cy+0.1, cz+0.1)
    t = glutGet(GLUT_ELAPSED_TIME)
    for obj in objects:
        if not obj['active']:
            continue
        x,y,z = obj['pos']
        o_min = (x-0.125, y-0.125, z-0.125)
        o_max = (x+0.125, y+0.125, z+0.125)
        if aabb_collide(car_min, car_max, o_min, o_max):
            if obj['type'] == 'obs':
                velocity = 0.0
            else:
                max_speed = BOOSTED_TOP_SPEED
                boost_end_time = t + 2000
            obj['active'] = False
    if boost_end_time and t > boost_end_time:
        max_speed = top_speed
        boost_end_time = 0

def update_physics():
    global position, velocity, game_finished
    if game_finished:
        return

    check_collisions()
    if keys['accel']:
        velocity += acceleration
    else:
        velocity -= acceleration / 2 if velocity > 0 else 0
    velocity = max(0, min(max_speed, velocity))

    if keys['left']:
        position[0] += handling  # Move right (positive x)
    if keys['right']:
        position[0] -= handling  # Move left (negative x)

    # Constrain to track with slowdown on boundary hit
    new_x = max(-TRACK_WIDTH/2 + 0.1, min(TRACK_WIDTH/2 - 0.1, position[0]))
    if new_x != position[0]:  # Hit boundary
        velocity *= 0.9  # Reduce velocity by 10%
    position[0] = new_x

    position[2] += velocity

    # Update particles
    for p in particles:
        p['pos'][0] += p['vel'][0]
        p['pos'][1] += p['vel'][1]
        p['pos'][2] += p['vel'][2]
        if p['pos'][1] < -1:  # Fall below screen
            p['pos'] = [random.uniform(-5, 5), 20, random.uniform(max(0, position[2] - 20), min(150, position[2] + 20))]
            if weather == 1:  # Rain
                p['vel'] = [0, random.uniform(-2.5, -1.5), 0]  # Random speed
            elif weather == 2:  # Snow
                p['vel'] = [random.uniform(-0.02, 0.02), random.uniform(-0.7, -0.3), random.uniform(-0.02, 0.02)]  # Random speed

    if position[2] >= 150.0:
        game_finished = True

# --- GLUT CALLBACKS ---
def display():
    # Set background color based on weather
    if weather == 0:  # Sunny
        glClearColor(0.5, 0.7, 1.0, 1.0)  # Light blue sky
    elif weather == 1:  # Rainy
        glClearColor(0.3, 0.3, 0.3, 1.0)  # Dark gray for clouds
    elif weather == 2:  # Snowy
        glClearColor(0, 0, 0.7, 1.0)  # Light gray for snowy clouds

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    px, py, pz = position
    cos_o = math.cos(orientation)
    sin_o = math.sin(orientation)

    if camera_mode == 0:  # First-person view
        eye_x = px + 0.3 * sin_o
        eye_y = py + 0.1
        eye_z = pz + 0.3 * cos_o
        center_x = px + 0.8 * sin_o
        center_y = py + 0.1
        center_z = pz + 0.8 * cos_o
        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0, 1, 0)
    else:  # Third-person view
        eye_x = px - 4.0 * sin_o
        eye_y = py + 2.5
        eye_z = pz - 6.0 * cos_o
        center_x = px
        center_y = py + 0.5
        center_z = pz + 5.0
        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0, 1, 0)

    # Draw green ground plane
    glDisable(GL_TEXTURE_2D)
    glColor3f(0.0, 0.5, 0.0)  # Green
    glBegin(GL_QUADS)
    glVertex3f(-10, -0.01, 0)
    glVertex3f(10, -0.01, 0)
    glVertex3f(10, -0.01, 150)
    glVertex3f(-10, -0.01, 150)
    glEnd()

    draw_track()
    draw_particles()
    draw_objects()
    draw_car()

    if weather == 0:  # Sunny
        draw_sun()

    if game_finished:
        glColor3f(1, 1, 1)
        draw_text(300, 300, "Press R to Restart")

    glutSwapBuffers()

def idle():
    update_physics()
    glutPostRedisplay()

def special_down(k, x, y):
    if k == GLUT_KEY_UP:    keys['accel'] = True
    elif k == GLUT_KEY_LEFT: keys['left'] = True
    elif k == GLUT_KEY_RIGHT: keys['right'] = True

def special_up(k, x, y):
    if k == GLUT_KEY_UP:    keys['accel'] = False
    elif k == GLUT_KEY_LEFT: keys['left'] = False
    elif k == GLUT_KEY_RIGHT: keys['right'] = False

def set_weather(new_weather):
    global weather, handling, particles
    weather = new_weather
    if weather == 0:  # Sunny
        handling = 0.06
        particles = []
    elif weather == 1:  # Rain
        handling = 0.03
        particles = [{'pos': [random.uniform(-10, 10), 20, random.uniform(-10, 10)],
                      'vel': [0, random.uniform(-1.0, -0.5), 0]} for _ in range(150)]  # Slower rain, 150 particles
    elif weather == 2:  # Snow
        handling = 0.12
        particles = [{'pos': [random.uniform(-10, 10), 20, random.uniform(-10, 10)],
                      'vel': [random.uniform(-0.05, 0.05), random.uniform(-0.3, -0.1), random.uniform(-0.05, 0.05)]} for
                     _ in range(300)]  # Slower snow, 300 particles


def keyboard_down(k, x, y):
    global camera_mode, game_finished, position, velocity, objects, weather
    if k == b'c' or k == b'C':
        camera_mode = (camera_mode + 1) % 2
    elif k == b'w' or k == b'W':
        set_weather((weather + 1) % 3)
    elif (k == b'r' or k == b'R') and game_finished:
        game_finished = False
        position = [0.0, 0.0, 0.0]
        velocity = 0.0
        max_speed = top_speed
        boost_end_time = 0
        generate_objects()

# --- INITIALIZATION ---
def init():
    global track_tex
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, [0,10,0,0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1,1,1,1])
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    track_tex = create_checkerboard_texture()

    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, 800/600, 0.1, 200)  # Extended far plane
    glMatrixMode(GL_MODELVIEW)

glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(1500,900)
glutCreateWindow(b"3D Car Simulation with Textures & Lighting")

init()
generate_control_points()
generate_track()
generate_objects()

# Set random weather at startup
set_weather(random.randint(0, 2))

glutDisplayFunc(display)
glutIdleFunc(idle)
glutSpecialFunc(special_down)
glutSpecialUpFunc(special_up)
glutKeyboardFunc(keyboard_down)
glutMainLoop()