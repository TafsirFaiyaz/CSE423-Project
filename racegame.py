from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random
import time

# --- GLOBAL STATE ---
TRACK_WIDTH = 10.0
CONTROL_POINTS = []
SPLINE_POINTS = []
objects = []
particles = []
game_finished = [False, False]
current_level = 0
countdown_state = None  # None, 3, 2, 1, 'GO!', 'racing'
countdown_start_time = 0
round_winners = []  # Track winners of each round
level_completed = False
level_complete_time = 0

# Car state for two players
position = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
orientation = [0.0, 0.0]
velocity = [0.0, 0.0]
top_speed = 0.15
acceleration = 0.005
handling = 0.06
BOOSTED_TOP_SPEED = top_speed * 2.0
max_speed = [top_speed, top_speed]
boost_end_time = [0, 0]
car_colors = [(1, 0, 0), (0, 0, 1)]  # Red for P1, Blue for P2
camera_mode = [1, 1]  # 0 = first-person, 1 = third-person

# Input keys
keys = {
    'p1_accel': False, 'p1_left': False, 'p1_right': False,
    'p2_accel': False, 'p2_left': False, 'p2_right': False,
    'enter': False, 'restart': False
}

# --- TRACK GENERATION ---
def generate_control_points(n=2, length=150):
    return 0

def catmull_rom(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    def cr(a, b, c, d):
        return 0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
    return cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])

def generate_track():
    samples = 600
    for i in range(samples):
        t = i / float(samples)
        x = 0.0
        z = t * 150.0
        y = 0.0
        SPLINE_POINTS.append((x, y, z))

# --- OBJECT PLACEMENT ---
def generate_objects():
    num_obs = 50
    num_boost = 10
    objects.clear()
    N = len(SPLINE_POINTS)
    picks = random.sample(range(10, N - 10), num_obs + num_boost)
    kinds = ['obs'] * num_obs + ['boost'] * num_boost
    random.shuffle(kinds)
    for idx, kind in zip(picks, kinds):
        x, y, z = SPLINE_POINTS[idx]
        x = random.uniform(-TRACK_WIDTH / 2 + 0.25, TRACK_WIDTH / 2 - 0.25)
        objects.append({'type': kind, 'pos': (x, y, z), 'active': True})

# --- DRAW ROUTINES ---
def draw_track():
    glBegin(GL_QUADS)
    for i in range(len(SPLINE_POINTS) - 1):
        x1, y1, z1 = SPLINE_POINTS[i]
        x2, y2, z2 = SPLINE_POINTS[i + 1]
        nx, nz = -1, 0
        w = TRACK_WIDTH / 2
        if (i // 5) % 2 == 0:
            glColor3f(0.8, 0.8, 0.8)
        else:
            glColor3f(0.5, 0.5, 0.5)
        glVertex3f(x1 + nx * w, y1, z1 + nz * w)
        glVertex3f(x1 - nx * w, y1, z1 - nz * w)
        glVertex3f(x2 - nx * w, y2, z2 - nz * w)
        glVertex3f(x2 + nx * w, y2, z2 + nz * w)
    glEnd()

def draw_cube():
    glBegin(GL_QUADS)
    vertices = [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
                (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (3, 2, 6, 7), (0, 1, 5, 4), (0, 3, 7, 4), (1, 2, 6, 5)]
    for face in faces:
        for vertex in face:
            glVertex3f(*vertices[vertex])
    glEnd()

def draw_car(color):
    # Car Body
    glColor3f(*color)
    glPushMatrix()
    glScalef(1.0, 0.3, 0.5)
    glutSolidCube(1.0)
    glPopMatrix()

    # Car Window
    glColor3f(0.7, 0.7, 1.0)  # Light blue
    glPushMatrix()
    glTranslatef(0.0, 0.35, 0.0)
    glScalef(0.5, 0.25, 0.3)
    glutSolidCube(1.0)
    glPopMatrix()

    # Wheels
    glColor3f(0.0, 0.0, 0.0)
    wheel_radius = 0.2
    wheel_width = 0.1
    wheel_offset_x = 0.6
    wheel_offset_z = 0.35
    for x in [-wheel_offset_x, wheel_offset_x]:
        for z in [-wheel_offset_z, wheel_offset_z]:
            glPushMatrix()
            glTranslatef(x, -0.05, z)
            glRotatef(90, 0, 1, 0)
            glutSolidTorus(wheel_width / 2, wheel_radius, 20, 40)
            glPopMatrix()

def draw_objects():
    for obj in objects:
        if not obj['active']:
            continue
        x, y, z = obj['pos']
        glPushMatrix()
        glTranslatef(x, y + 0.125, z)
        if obj['type'] == 'obs':
            glColor3f(0.5, 0.5, 0.5)
            glScalef(0.25, 0.25, 0.25)
            draw_cube()
        else:
            glColor3f(1, 1, 0)
            glutSolidSphere(0.25, 16, 16)
        glPopMatrix()

def draw_particles():
    if current_level == 1:
        glColor3f(0.5, 0.5, 1.0)
        glBegin(GL_LINES)
        for p in particles:
            x, y, z = p['pos']
            glVertex3f(x, y, z)
            glVertex3f(x, y - 1.0, z)
        glEnd()
    elif current_level == 2:
        glColor3f(1.0, 1.0, 1.0)
        glPointSize(3.0)
        glBegin(GL_POINTS)
        for p in particles:
            x, y, z = p['pos']
            glVertex3f(x, y, z)
        glEnd()
        glPointSize(1.0)

def draw_sun():
    glPushMatrix()
    glTranslatef(0, 15, 150)
    glColor3f(1.0, 1.0, 0.0)
    glutSolidSphere(2.0, 20, 20)
    glBegin(GL_LINES)
    for i in range(12):
        angle = math.radians(i * 30)
        x = math.cos(angle) * 4.0
        y = math.sin(angle) * 4.0
        glVertex3f(0, 0, 0)
        glVertex3f(x, y, 0)
    glEnd()
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

def draw_countdown():
    global countdown_state, countdown_start_time
    if countdown_state is None or countdown_state == 'racing':
        return
    current_time = time.time()
    elapsed = current_time - countdown_start_time
    if countdown_state == 3 and elapsed > 1:
        countdown_state = 2
        countdown_start_time = current_time
    elif countdown_state == 2 and elapsed > 1:
        countdown_state = 1
        countdown_start_time = current_time
    elif countdown_state == 1 and elapsed > 1:
        countdown_state = 'GO!'
        countdown_start_time = current_time
    elif countdown_state == 'GO!' and elapsed > 1:
        countdown_state = 'racing'
    if countdown_state != 'racing':
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, 800, 0, 600, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glColor3f(1, 1, 1)
        text = str(countdown_state) if countdown_state != 'GO!' else 'GO!'
        glRasterPos2f(400 - len(text) * 14 / 2, 300)
        for char in text:
            glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(char))
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def show_overall_winner():
    p1_wins = round_winners.count(0)
    p2_wins = round_winners.count(1)
    winner_text = "Player 1 Won!" if p1_wins > p2_wins else "Player 2 Won!" if p2_wins > p1_wins else "It's a Tie!"
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, 800, 0, 600, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(1, 1, 1)
    draw_text(400 - len(winner_text) * 9 / 2, 300, winner_text)
    draw_text(400 - len("Press R to Restart") * 7 / 2, 280, "Press R to Restart")
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# --- PHYSICS & COLLISION ---
def aabb_collide(min1, max1, min2, max2):
    return all(min1[i] < max2[i] and max1[i] > min2[i] for i in range(3))

def check_collisions(player_id):
    global velocity, max_speed, boost_end_time
    cx, cy, cz = position[player_id]
    car_min = (cx - 0.1, cy - 0.1, cz - 0.1)
    car_max = (cx + 0.1, cy + 0.1, cz + 0.1)
    t = glutGet(GLUT_ELAPSED_TIME)
    for obj in objects:
        if not obj['active']:
            continue
        x, y, z = obj['pos']
        o_min = (x - 0.125, y - 0.125, z - 0.125)
        o_max = (x + 0.125, y + 0.125, z + 0.125)
        if aabb_collide(car_min, car_max, o_min, o_max):
            if obj['type'] == 'obs':
                velocity[player_id] = 0.0
            else:
                max_speed[player_id] = BOOSTED_TOP_SPEED
                boost_end_time[player_id] = t + 2000
            obj['active'] = False
    if boost_end_time[player_id] and t > boost_end_time[player_id]:
        max_speed[player_id] = top_speed
        boost_end_time[player_id] = 0

def check_car_collision():
    p1_x, p1_y, p1_z = position[0]
    p2_x, p2_y, p2_z = position[1]
    dx = p1_x - p2_x
    dz = p1_z - p2_z
    dist_squared = dx * dx + dz * dz
    if dist_squared < 0.04:
        velocity[0] *= 0.5
        velocity[1] *= 0.5
        push_dir = 0.05 if dx < 0 else -0.05
        position[0][0] += push_dir
        position[1][0] -= push_dir

def update_physics():
    global position, velocity, game_finished, level_completed, level_complete_time, current_level, round_winners, countdown_state
    if countdown_state != 'racing':
        return
    check_car_collision()
    for player_id in range(2):
        if game_finished[player_id]:
            continue
        check_collisions(player_id)
        accel_key = 'p1_accel' if player_id == 0 else 'p2_accel'
        left_key = 'p1_left' if player_id == 0 else 'p2_left'
        right_key = 'p1_right' if player_id == 0 else 'p2_right'
        if keys[accel_key]:
            velocity[player_id] += acceleration
        else:
            velocity[player_id] -= acceleration / 2 if velocity[player_id] > 0 else 0
        velocity[player_id] = max(0, min(max_speed[player_id], velocity[player_id]))
        if keys[left_key]:
            position[player_id][0] += handling
        if keys[right_key]:
            position[player_id][0] -= handling
        new_x = max(-TRACK_WIDTH / 2 + 0.1, min(TRACK_WIDTH / 2 - 0.1, position[player_id][0]))
        if new_x != position[player_id][0]:
            velocity[player_id] *= 0.9
        position[player_id][0] = new_x
        position[player_id][2] += velocity[player_id]
        if position[player_id][2] >= 150.0:
            game_finished[player_id] = True
    if all(game_finished) and not level_completed:
        level_completed = True
        level_complete_time = glutGet(GLUT_ELAPSED_TIME)
        if position[0][2] > position[1][2]:
            round_winners.append(0)
        elif position[1][2] > position[0][2]:
            round_winners.append(1)
        else:
            round_winners.append(-1)
    if level_completed and keys['enter'] and current_level < 2:
        next_level()
    if level_completed and current_level == 2 and keys['restart']:
        restart_game()
    for p in particles:
        p['pos'][0] += p['vel'][0]
        p['pos'][1] += p['vel'][1]
        p['pos'][2] += p['vel'][2]
        avg_z = (position[0][2] + position[1][2]) / 2
        if p['pos'][1] < -1:
            p['pos'] = [random.uniform(-5, 5), 20, random.uniform(max(0, avg_z - 20), min(150, avg_z + 20))]
            if current_level == 1:
                p['vel'] = [0, random.uniform(-2.5, -1.5), 0]
            elif current_level == 2:
                p['vel'] = [random.uniform(-0.02, 0.02), random.uniform(-0.7, -0.3), random.uniform(-0.02, 0.02)]

# --- LEVEL MANAGEMENT ---
def set_level_properties(level):
    global handling, particles
    if level == 0:
        handling = 0.06
        particles = []
    elif level == 1:
        handling = 0.03
        particles = [{'pos': [random.uniform(-10, 10), 20, random.uniform(-10, 10)],
                      'vel': [0, random.uniform(-1.0, -0.5), 0]} for _ in range(150)]
    elif level == 2:
        handling = 0.12

def next_level():
    global current_level, game_finished, position, velocity, max_speed, boost_end_time, level_completed, countdown_state, countdown_start_time
    current_level += 1
    game_finished = [False, False]
    position = [[-TRACK_WIDTH / 4, 0.0, 0.0], [TRACK_WIDTH / 4, 0.0, 0.0]]
    velocity = [0.0, 0.0]
    max_speed = [top_speed, top_speed]
    boost_end_time = [0, 0]
    level_completed = False
    set_level_properties(current_level)
    generate_objects()
    countdown_state = 3
    countdown_start_time = time.time()

def restart_game():
    global current_level, round_winners, countdown_state, countdown_start_time
    current_level = -1
    round_winners = []
    next_level()

# --- SPLIT SCREEN RENDERING ---
def setup_viewport(player_id, width, height):
    if player_id == 0:
        glViewport(0, 0, width // 2, height)
    else:
        glViewport(width // 2, 0, width // 2, height)

def draw_player_view(player_id, width, height):
    setup_viewport(player_id, width, height)
    if current_level == 0:
        glClearColor(0.5, 0.7, 1.0, 1.0)
    elif current_level == 1:
        glClearColor(0.3, 0.3, 0.3, 1.0)
    elif current_level == 2:
        glClearColor(0.6, 0.6, 0.7, 1.0)
    if player_id == 0:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    else:
        glClear(GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    px, py, pz = position[player_id]
    cos_o = math.cos(orientation[player_id])
    sin_o = math.sin(orientation[player_id])
    if camera_mode[player_id] == 0:  # First-person view
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
    glColor3f(0.0, 0.5, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(-10, -0.01, 0)
    glVertex3f(10, -0.01, 0)
    glVertex3f(10, -0.01, 150)
    glVertex3f(-10, -0.01, 150)
    glEnd()
    draw_track()
    draw_particles()
    draw_objects()
    for i in range(2):
        glPushMatrix()
        glTranslatef(*position[i])
        draw_car(car_colors[i])
        glPopMatrix()
    if current_level == 0:
        draw_sun()
    viewport_width = width // 2
    viewport_height = height
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, viewport_width, 0, viewport_height, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(*car_colors[player_id])
    player_text = f"Player {player_id + 1}"
    x_pos = 10
    y_pos = viewport_height - 20
    glRasterPos2f(x_pos, y_pos)
    for char in player_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    speed_text = f"Speed: {int(velocity[player_id] * 1000)}"
    glRasterPos2f(x_pos, y_pos - 20)
    for char in speed_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    level_names = ["Sunny", "Rainy", "Snowy"]
    level_text = f"Level: {current_level + 1} ({level_names[current_level]})"
    glRasterPos2f(x_pos, y_pos - 40)
    for char in level_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    if game_finished[player_id] and current_level < 2:
        finish_text = "FINISHED! Press Enter"
        glColor3f(1, 1, 0)
        x_pos = viewport_width // 2 - 50
        y_pos = viewport_height // 2
        glRasterPos2f(x_pos, y_pos)
        for char in finish_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    if player_id == 1:
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glColor3f(1, 1, 1)
        glBegin(GL_LINES)
        glVertex2f(width // 2, 0)
        glVertex2f(width // 2, height)
        glEnd()
        draw_countdown()
        if all(game_finished) and current_level < 2:
            glColor3f(1, 1, 1)
            progression_text = "Press Enter for Next Level"
            text_width = len(progression_text) * 9
            x_pos = width // 2 - text_width // 2
            y_pos = height // 2
            glRasterPos2f(x_pos, y_pos)
            for char in progression_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        if all(game_finished) and current_level == 2:
            show_overall_winner()
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

# --- GLUT CALLBACKS ---
def display():
    width = glutGet(GLUT_WINDOW_WIDTH)
    height = glutGet(GLUT_WINDOW_HEIGHT)
    draw_player_view(0, width, height)
    draw_player_view(1, width, height)
    glutSwapBuffers()

def reshape(width, height):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (width / 2) / height, 0.1, 200)
    glMatrixMode(GL_MODELVIEW)

def idle():
    update_physics()
    glutPostRedisplay()

def special_down(k, x, y):
    if k == GLUT_KEY_UP:
        keys['p2_accel'] = True
    elif k == GLUT_KEY_LEFT:
        keys['p2_left'] = True
    elif k == GLUT_KEY_RIGHT:
        keys['p2_right'] = True

def special_up(k, x, y):
    if k == GLUT_KEY_UP:
        keys['p2_accel'] = False
    elif k == GLUT_KEY_LEFT:
        keys['p2_left'] = False
    elif k == GLUT_KEY_RIGHT:
        keys['p2_right'] = False

def keyboard_down(k, x, y):
    global camera_mode
    if k == b'c' or k == b'C':
        camera_mode[0] = (camera_mode[0] + 1) % 2
    elif k == b'v' or k == b'V':
        camera_mode[1] = (camera_mode[1] + 1) % 2
    elif k == b'w' or k == b'W':
        keys['p1_accel'] = True
    elif k == b'a' or k == b'A':
        keys['p1_left'] = True
    elif k == b'd' or k == b'D':
        keys['p1_right'] = True
    elif k == b'\r':
        keys['enter'] = True
    elif k == b'r' or k == b'R':
        keys['restart'] = True

def keyboard_up(k, x, y):
    if k == b'w' or k == b'W':
        keys['p1_accel'] = False
    elif k == b'a' or k == b'A':
        keys['p1_left'] = False
    elif k == b'd' or k == b'D':
        keys['p1_right'] = False
    elif k == b'\r':
        keys['enter'] = False
    elif k == b'r' or k == b'R':
        keys['restart'] = False

# --- INITIALIZATION ---
def init():
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, 1500 / 900, 0.1, 500)
    glMatrixMode(GL_MODELVIEW)

def init_players():
    global position
    position[0][0] = -TRACK_WIDTH / 4
    position[1][0] = TRACK_WIDTH / 4

glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(1920, 1080)
glutCreateWindow(b"3D Car Racing Game")
init()
generate_control_points()
generate_track()
generate_objects()
init_players()
set_level_properties(current_level)
countdown_state = 3
countdown_start_time = time.time()
glutDisplayFunc(display)
glutReshapeFunc(reshape)
glutIdleFunc(idle)
glutSpecialFunc(special_down)
glutSpecialUpFunc(special_up)
glutKeyboardFunc(keyboard_down)
glutKeyboardUpFunc(keyboard_up)
glutMainLoop()
