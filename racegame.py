from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import ctypes
import math
import random

# --- GLOBAL STATE ---
TRACK_WIDTH = 10.0
CONTROL_POINTS = []
SPLINE_POINTS = []
objects = []  # obstacles & boosts
particles = []  # weather particles
game_finished = [False, False]  # Track finish state for both players
weather = 0  # 0: sunny, 1: rain, 2: snow

# Car state for two players
position = [
    [0.0, 0.0, 0.0],       # Player 1 (left side of track)
    [0.0, 0.0, 0.0]        # Player 2 (right side of track)
]
orientation = [0.0, 0.0]   # Fixed at 0 for straight movement
velocity = [0.0, 0.0]
top_speed = 0.15
acceleration = 0.005
handling = 0.06
BOOSTED_TOP_SPEED = top_speed * 2.0
max_speed = [top_speed, top_speed]
boost_end_time = [0, 0]
car_colors = [(1, 0, 0), (0, 0, 1)]  # Red for P1, Blue for P2

# Input keys for both players
keys = {
    'p1_accel': False, 'p1_left': False, 'p1_right': False,
    'p2_accel': False, 'p2_left': False, 'p2_right': False,
    'restart': False
}

# Texture handle
track_tex = None

# Camera state for both players
camera_mode = [1, 1]  # 0 = first-person, 1 = third-person

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

def draw_car(player_id):
    glPushMatrix()
    glTranslatef(*position[player_id])
    glRotatef(-math.degrees(orientation[player_id]), 0,1,0)
    glScalef(0.2, 0.2, 0.2)
    glColor3f(*car_colors[player_id])
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

def check_collisions(player_id):
    global velocity, max_speed, boost_end_time
    cx,cy,cz = position[player_id]
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
                velocity[player_id] = 0.0
            else:
                max_speed[player_id] = BOOSTED_TOP_SPEED
                boost_end_time[player_id] = t + 2000
            obj['active'] = False
    if boost_end_time[player_id] and t > boost_end_time[player_id]:
        max_speed[player_id] = top_speed
        boost_end_time[player_id] = 0

def update_physics():
    global position, velocity, game_finished
    
    # Check for car-to-car collisions
    check_car_collision()
    
    # Update both players
    for player_id in range(2):
        if game_finished[player_id]:
            continue

        check_collisions(player_id)
        
        # Apply key controls for respective player
        accel_key = 'p1_accel' if player_id == 0 else 'p2_accel'
        left_key = 'p1_left' if player_id == 0 else 'p2_left'
        right_key = 'p1_right' if player_id == 0 else 'p2_right'
        
        if keys[accel_key]:
            velocity[player_id] += acceleration
        else:
            velocity[player_id] -= acceleration / 2 if velocity[player_id] > 0 else 0
        velocity[player_id] = max(0, min(max_speed[player_id], velocity[player_id]))

        if keys[left_key]:
            position[player_id][0] += handling  # Move right (positive x)
        if keys[right_key]:
            position[player_id][0] -= handling  # Move left (negative x)

        # Constrain to track with slowdown on boundary hit
        new_x = max(-TRACK_WIDTH/2 + 0.1, min(TRACK_WIDTH/2 - 0.1, position[player_id][0]))
        if new_x != position[player_id][0]:  # Hit boundary
            velocity[player_id] *= 0.9  # Reduce velocity by 10%
        position[player_id][0] = new_x

        position[player_id][2] += velocity[player_id]

        # Check if player has finished the race
        if position[player_id][2] >= 150.0:
            game_finished[player_id] = True

    # Update particles
    for p in particles:
        p['pos'][0] += p['vel'][0]
        p['pos'][1] += p['vel'][1]
        p['pos'][2] += p['vel'][2]
        
        # Get average z position of both cars for particle respawn
        avg_z = (position[0][2] + position[1][2]) / 2
        
        if p['pos'][1] < -1:  # Fall below screen
            p['pos'] = [random.uniform(-5, 5), 20, random.uniform(max(0, avg_z - 20), min(150, avg_z + 20))]
            if weather == 1:  # Rain
                p['vel'] = [0, random.uniform(-2.5, -1.5), 0]  # Random speed
            elif weather == 2:  # Snow
                p['vel'] = [random.uniform(-0.02, 0.02), random.uniform(-0.7, -0.3), random.uniform(-0.02, 0.02)]  # Random speed

def check_car_collision():
    # Simple collision detection between two cars
    p1_x, p1_y, p1_z = position[0]
    p2_x, p2_y, p2_z = position[1]
    
    # Distance check (rough collision)
    dx = p1_x - p2_x
    dz = p1_z - p2_z
    dist_squared = dx*dx + dz*dz
    
    if dist_squared < 0.04:  # Cars are too close (colliding)
        # Slow down both cars
        velocity[0] *= 0.5
        velocity[1] *= 0.5
        
        # Push cars apart slightly
        push_dir = 0.05 if dx < 0 else -0.05
        position[0][0] += push_dir
        position[1][0] -= push_dir

# --- SPLIT SCREEN RENDERING ---
def setup_viewport(player_id, width, height):
    if player_id == 0:  # Left half for player 1
        glViewport(0, 0, width // 2, height)
    else:  # Right half for player 2
        glViewport(width // 2, 0, width // 2, height)

def draw_player_view(player_id, width, height):
    setup_viewport(player_id, width, height)
    
    # Set background color based on weather
    if weather == 0:  # Sunny
        glClearColor(0.5, 0.7, 1.0, 1.0)  # Light blue sky
    elif weather == 1:  # Rainy
        glClearColor(0.3, 0.3, 0.3, 1.0)  # Dark gray for clouds
    elif weather == 2:  # Snowy
        glClearColor(0, 0, 0.7, 1.0)  # Light gray for snowy clouds

    # Only clear the portion of the screen for this player
    if player_id == 0:  # First player - clear both buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    else:  # Second player - only clear depth buffer to preserve first player's rendering
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
    
    # Draw both cars
    draw_car(0)
    draw_car(1)

    if weather == 0:  # Sunny
        draw_sun()

    # Draw player-specific UI elements
    viewport_width = width // 2
    viewport_height = height
    
    # Setup for 2D overlay
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, viewport_width, 0, viewport_height, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw player label
    glColor3f(*car_colors[player_id])
    player_text = f"Player {player_id+1}"
    x_pos = 10
    y_pos = viewport_height - 20
    glRasterPos2f(x_pos, y_pos)
    for char in player_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Draw speed indicator
    speed_text = f"Speed: {int(velocity[player_id] * 1000)}"
    glRasterPos2f(x_pos, y_pos - 20)
    for char in speed_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Draw finish message if player has finished
    if game_finished[player_id]:
        finish_text = "FINISHED!"
        glColor3f(1, 1, 0)  # Yellow
        x_pos = viewport_width // 2 - 50
        y_pos = viewport_height // 2
        glRasterPos2f(x_pos, y_pos)
        for char in finish_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Reset projection
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # Draw divider line between viewports
    if player_id == 1:  # Only draw after second viewport is rendered
        glViewport(0, 0, width, height)  # Full screen for divider
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw vertical divider
        glColor3f(1, 1, 1)  # White divider
        glBegin(GL_LINES)
        glVertex2f(width // 2, 0)
        glVertex2f(width // 2, height)
        glEnd()
        
        # If all players finished, show restart message
        if all(game_finished):
            glColor3f(1, 1, 1)
            restart_text = "Press R to Restart"
            text_width = len(restart_text) * 9  # Approximate width
            x_pos = width // 2 - text_width // 2
            y_pos = height // 2
            glRasterPos2f(x_pos, y_pos)
            for char in restart_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

# --- GLUT CALLBACKS ---
def display():
    width = glutGet(GLUT_WINDOW_WIDTH)
    height = glutGet(GLUT_WINDOW_HEIGHT)
    
    # Draw each player's view
    draw_player_view(0, width, height)  # Player 1 (left side)
    draw_player_view(1, width, height)  # Player 2 (right side)
    
    glutSwapBuffers()

def reshape(width, height):
    # Reset the projection matrix for each viewport
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (width/2)/height, 0.1, 200)  # Adjusted aspect ratio for split screen
    glMatrixMode(GL_MODELVIEW)

def idle():
    update_physics()
    glutPostRedisplay()

def special_down(k, x, y):
    if k == GLUT_KEY_UP:    keys['p1_accel'] = True
    elif k == GLUT_KEY_LEFT: keys['p1_left'] = True
    elif k == GLUT_KEY_RIGHT: keys['p1_right'] = True

def special_up(k, x, y):
    if k == GLUT_KEY_UP:    keys['p1_accel'] = False
    elif k == GLUT_KEY_LEFT: keys['p1_left'] = False
    elif k == GLUT_KEY_RIGHT: keys['p1_right'] = False

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
    
    # Player 1 camera toggle
    if k == b'c' or k == b'C':
        camera_mode[0] = (camera_mode[0] + 1) % 2
    
    # Player 2 camera toggle
    elif k == b'v' or k == b'V':
        camera_mode[1] = (camera_mode[1] + 1) % 2
    
    # Weather toggle
    elif k == b'z' or k == b'Z':
        set_weather((weather + 1) % 3)
    
    # Player 2 controls (WASD)
    elif k == b'w' or k == b'W':
        keys['p2_accel'] = True
    elif k == b'a' or k == b'A':
        keys['p2_left'] = True
    elif k == b'd' or k == b'D':
        keys['p2_right'] = True
    
    # Restart game when all players finished
    elif (k == b'r' or k == b'R') and all(game_finished):
        game_finished = [False, False]
        position = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0]
        ]
        velocity = [0.0, 0.0]
        max_speed = [top_speed, top_speed]
        boost_end_time = [0, 0]
        generate_objects()

def keyboard_up(k, x, y):
    # Player 2 controls (WASD) release
    if k == b'w' or k == b'W':
        keys['p2_accel'] = False
    elif k == b'a' or k == b'A':
        keys['p2_left'] = False
    elif k == b'd' or k == b'D':
        keys['p2_right'] = False

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

def init_players():
    global position
    # Start positions: player 1 on left, player 2 on right
    position[0][0] = -TRACK_WIDTH/4
    position[1][0] = TRACK_WIDTH/4

glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(1500,900)
glutCreateWindow(b"3D Car Simulation - Two Player Split Screen")

init()
generate_control_points()
generate_track()
generate_objects()
init_players()

# Set random weather at startup
set_weather(random.randint(0, 2))

glutDisplayFunc(display)
glutReshapeFunc(reshape)
glutIdleFunc(idle)
glutSpecialFunc(special_down)
glutSpecialUpFunc(special_up)
glutKeyboardFunc(keyboard_down)
glutKeyboardUpFunc(keyboard_up)
glutMainLoop()