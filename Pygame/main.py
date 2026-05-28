import pygame
from sys import exit
import random
import json
import os

# ─── Constants ────────────────────────────────────────────────────────────────
GAME_WIDTH  = 360
GAME_HEIGHT = 640
FPS         = 60
SAVE_FILE   = "flappy_save.json"

PIPE_WIDTH   = 64
PIPE_HEIGHT  = 512
BIRD_WIDTH   = 34
BIRD_HEIGHT  = 24
OPENING      = GAME_HEIGHT // 4
PIPE_SPEED   = -2
GRAVITY      = 0.4
FLAP_POWER   = -6
PIPE_INTERVAL= 1500  # ms

# ─── Colours ──────────────────────────────────────────────────────────────────
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
YELLOW = (255, 220,  50)
ORANGE = (255, 140,   0)
GREEN  = ( 80, 200, 120)
BLUE   = ( 70, 130, 200)
DARK   = ( 20,  20,  30)
GREY   = (180, 180, 180)
RED    = (220,  60,  60)
GOLD   = (255, 195,  0)

# ─── Persistence ──────────────────────────────────────────────────────────────
def load_save():
    defaults = {"high_score": 0, "bg_choice": 0, "bird_choice": 0}
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
    return defaults

def write_save(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

# ─── Asset helpers ────────────────────────────────────────────────────────────
def load_image(path, size=None, fallback_color=None, fallback_size=(64, 64)):
    """Load an image; draw a coloured rectangle if file is missing."""
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    # Fallback surface
    s = pygame.Surface(size or fallback_size, pygame.SRCALPHA)
    s.fill(fallback_color or (128, 128, 128, 200))
    return s

def make_fallback_bg(color1, color2, w, h):
    """Simple gradient-ish fallback background."""
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / h
        r = int(color1[0] * (1-t) + color2[0] * t)
        g = int(color1[1] * (1-t) + color2[1] * t)
        b = int(color1[2] * (1-t) + color2[2] * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    return surf

# ─── pygame init (must be before image loading) ───────────────────────────────
pygame.init()
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()

# ─── Load assets ──────────────────────────────────────────────────────────────
BG_FILES   = ["back1.png", "back2.png", "back3.png", "back4.png"]
BG_COLORS  = [((30,120,200),(10,60,120)), ((30,160,80),(10,80,30)),
              ((200,100,30),(120,50,10)), ((80,30,160),(30,10,80))]
BG_LABELS  = ["Ocean",     "Forest",    "Sunset",    "Night"]

BIRD_FILES  = ["bird1.png", "bird2.png", "bird3.png"]
BIRD_COLORS = [(YELLOW, ORANGE), (GREEN, (0,150,0)), (BLUE, (30,80,160))]
BIRD_LABELS = ["Classic", "Parrot", "Blue Jay"]

backgrounds = []
for i, f in enumerate(BG_FILES):
    if os.path.exists(f):
        img = pygame.image.load(f).convert()
        img = pygame.transform.scale(img, (GAME_WIDTH, GAME_HEIGHT))
    else:
        img = make_fallback_bg(*BG_COLORS[i], GAME_WIDTH, GAME_HEIGHT)
    backgrounds.append(img)

bird_images = []
for i, f in enumerate(BIRD_FILES):
    if os.path.exists(f):
        img = pygame.image.load(f).convert_alpha()
        img = pygame.transform.scale(img, (BIRD_WIDTH, BIRD_HEIGHT))
    else:
        # Draw a simple bird silhouette
        surf = pygame.Surface((BIRD_WIDTH, BIRD_HEIGHT), pygame.SRCALPHA)
        body_col, wing_col = BIRD_COLORS[i]
        pygame.draw.ellipse(surf, body_col, (4, 4, 22, 16))
        pygame.draw.polygon(surf, wing_col, [(4,12),(0,20),(14,14)])  # wing
        pygame.draw.circle(surf, WHITE, (24, 8), 5)                   # head
        pygame.draw.circle(surf, BLACK, (26, 7), 2)                   # eye
        pygame.draw.polygon(surf, ORANGE, [(28,9),(34,10),(28,12)])   # beak
        img = surf
    bird_images.append(img)

def load_pipe_images():
    top = load_image("toppipe.png",    (PIPE_WIDTH, PIPE_HEIGHT), (80,160,80))
    bot = load_image("bottompipe.png", (PIPE_WIDTH, PIPE_HEIGHT), (80,160,80))
    return top, bot

top_pipe_image, bottom_pipe_image = load_pipe_images()

logo_image = load_image("rafi.png", None, (50, 50, 50), (180, 80))

# ─── Fonts ────────────────────────────────────────────────────────────────────
try:
    font_lg = pygame.font.SysFont("Arial Rounded MT Bold", 52)
    font_md = pygame.font.SysFont("Arial Rounded MT Bold", 32)
    font_sm = pygame.font.SysFont("Arial Rounded MT Bold", 22)
    font_xs = pygame.font.SysFont("Arial Rounded MT Bold", 16)
except Exception:
    font_lg = pygame.font.SysFont(None, 52)
    font_md = pygame.font.SysFont(None, 32)
    font_sm = pygame.font.SysFont(None, 22)
    font_xs = pygame.font.SysFont(None, 16)

# ─── Game-object classes ──────────────────────────────────────────────────────
class Bird(pygame.Rect):
    def __init__(self, img):
        super().__init__(GAME_WIDTH // 8, GAME_HEIGHT // 2, BIRD_WIDTH, BIRD_HEIGHT)
        self.img       = img
        self.vel       = 0
        self.angle     = 0
        self.alive     = True

    def flap(self):
        self.vel = FLAP_POWER

    def update(self):
        self.vel += GRAVITY
        self.y   += int(self.vel)
        # Clamp to screen top
        if self.y < 0:
            self.y  = 0
            self.vel = 0
        # Rotation: dive down when falling, nose-up when flapping
        self.angle = max(-30, min(30, -self.vel * 3))

    def draw(self, surf):
        rotated = pygame.transform.rotate(self.img, self.angle)
        rect    = rotated.get_rect(center=self.center)
        surf.blit(rotated, rect)

    def is_dead(self):
        return self.y > GAME_HEIGHT


class Pipe(pygame.Rect):
    def __init__(self, img, x, y):
        super().__init__(x, y, PIPE_WIDTH, PIPE_HEIGHT)
        self.img    = img
        self.passed = False

    def update(self):
        self.x += PIPE_SPEED

    def draw(self, surf):
        surf.blit(self.img, self)


def make_pipes(x=GAME_WIDTH):
    rand_y = -PIPE_HEIGHT // 4 - random.random() * (PIPE_HEIGHT // 2)
    top    = Pipe(top_pipe_image,    x, rand_y)
    bot    = Pipe(bottom_pipe_image, x, rand_y + PIPE_HEIGHT + OPENING)
    return top, bot

# ─── UI helpers ───────────────────────────────────────────────────────────────
def draw_text_centered(surf, text, font, color, cx, y, shadow=True):
    if shadow:
        sh = font.render(text, True, (0, 0, 0, 160))
        sr = sh.get_rect(centerx=cx, top=y+2)
        surf.blit(sh, sr)
    tx = font.render(text, True, color)
    tr = tx.get_rect(centerx=cx, top=y)
    surf.blit(tx, tr)
    return tr

def draw_button(surf, text, font, rect, color, text_color=WHITE, hover=False, radius=12):
    col = tuple(min(255, c + 30) for c in color) if hover else color
    pygame.draw.rect(surf, col,    rect, border_radius=radius)
    pygame.draw.rect(surf, WHITE,  rect, 2, border_radius=radius)
    tx  = font.render(text, True, text_color)
    tr  = tx.get_rect(center=rect.center)
    surf.blit(tx, tr)

def draw_panel(surf, rect, alpha=180, color=DARK, radius=16):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*color, alpha), panel.get_rect(), border_radius=radius)
    surf.blit(panel, rect)

def mx_my():
    return pygame.mouse.get_pos()

def clicked(rect):
    if pygame.mouse.get_pressed()[0]:
        return rect.collidepoint(mx_my())
    return False

# ─── Scrolling ground strip ───────────────────────────────────────────────────
GROUND_H   = 20
ground_x   = 0

def draw_ground(surf):
    global ground_x
    ground_x = (ground_x + abs(PIPE_SPEED)) % (GAME_WIDTH // 2)
    gw = GAME_WIDTH // 2
    pygame.draw.rect(surf, (180, 140, 80),
                     (0, GAME_HEIGHT - GROUND_H, GAME_WIDTH, GROUND_H))
    for i in range(4):
        tx = (i * gw) - ground_x
        pygame.draw.rect(surf, (160, 120, 60),
                         (tx, GAME_HEIGHT - GROUND_H, gw, GROUND_H))
        pygame.draw.rect(surf, (200, 160, 90),
                         (tx, GAME_HEIGHT - GROUND_H, gw, 4))

# ─── Particle system ──────────────────────────────────────────────────────────
particles = []

def spawn_particles(x, y, color=(255, 220, 50), n=18):
    for _ in range(n):
        angle = random.uniform(0, 360)
        speed = random.uniform(1, 5)
        vx    = speed * pygame.math.Vector2(1, 0).rotate(angle).x
        vy    = speed * pygame.math.Vector2(1, 0).rotate(angle).y
        life  = random.randint(20, 50)
        r     = random.randint(3, 8)
        particles.append([x, y, vx, vy, life, life, r, color])

def update_draw_particles(surf):
    alive = []
    for p in particles:
        p[0] += p[2]; p[1] += p[3]
        p[3] += 0.15  # gravity on particles
        p[4] -= 1
        alpha = int(255 * p[4] / p[5])
        col   = (*p[7][:3], alpha)
        tmp   = pygame.Surface((p[6]*2, p[6]*2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, col, (p[6], p[6]), p[6])
        surf.blit(tmp, (int(p[0]-p[6]), int(p[1]-p[6])))
        if p[4] > 0:
            alive.append(p)
    particles[:] = alive

# ─── State machine ────────────────────────────────────────────────────────────
STATE_HOME     = "home"
STATE_BG_SEL   = "bg_sel"
STATE_BIRD_SEL = "bird_sel"
STATE_PLAY     = "play"
STATE_GAMEOVER = "gameover"

save       = load_save()
state      = STATE_HOME
bg_idx     = save["bg_choice"]
bird_idx   = save["bird_choice"]
high_score = save["high_score"]
score      = 0
bird       = None
pipes      = []
game_tick  = 0
pipe_timer = 0

# ─── Custom pygame timer event ────────────────────────────────────────────────
CREATE_PIPE = pygame.USEREVENT + 1

def start_game():
    global bird, pipes, score, game_tick, pipe_timer, state, ground_x
    particles.clear()
    bird       = Bird(bird_images[bird_idx])
    pipes      = []
    score      = 0
    game_tick  = 0
    pipe_timer = 0
    ground_x   = 0
    state      = STATE_PLAY
    pygame.time.set_timer(CREATE_PIPE, PIPE_INTERVAL)

def stop_pipe_timer():
    pygame.time.set_timer(CREATE_PIPE, 0)

# ─── Screen drawers ───────────────────────────────────────────────────────────

def draw_home(events):
    global state, bg_idx, bird_idx, high_score
    window.blit(backgrounds[bg_idx], (0, 0))

    # Animated demo bird
    demo_x = GAME_WIDTH // 2
    demo_y = int(GAME_HEIGHT * 0.28 + 12 * pygame.math.Vector2(0, 1)
                 .rotate(pygame.time.get_ticks() / 5).y)
    rotated = pygame.transform.rotate(bird_images[bird_idx], 0)
    window.blit(rotated, rotated.get_rect(center=(demo_x, demo_y)))

    # Logo
    logo_r = logo_image.get_rect(centerx=GAME_WIDTH//2, top=10)
    window.blit(logo_image, logo_r)

    # Title
    draw_text_centered(window, "FLAPPY BIRD", font_lg, GOLD,
                       GAME_WIDTH//2, logo_r.bottom + 6)

    mx, my = mx_my()

    btn_w, btn_h = 200, 48
    bx = GAME_WIDTH//2 - btn_w//2

    # --- Start ---
    r_start = pygame.Rect(bx, 310, btn_w, btn_h)
    hov = r_start.collidepoint(mx, my)
    draw_button(window, "▶  Start Game", font_sm, r_start,
                GREEN, WHITE, hov)

    # --- Background ---
    r_bg = pygame.Rect(bx, 370, btn_w, btn_h)
    hov2 = r_bg.collidepoint(mx, my)
    draw_button(window, "🌄  Background", font_sm, r_bg,
                BLUE, WHITE, hov2)

    # --- Bird ---
    r_bird = pygame.Rect(bx, 430, btn_w, btn_h)
    hov3 = r_bird.collidepoint(mx, my)
    draw_button(window, "🐦  Choose Bird", font_sm, r_bird,
                ORANGE, WHITE, hov3)

    # High score display
    hs_panel = pygame.Rect(GAME_WIDTH//2 - 90, 500, 180, 44)
    draw_panel(window, hs_panel)
    draw_text_centered(window, f"🏆  Best: {int(high_score)}", font_sm,
                       GOLD, GAME_WIDTH//2, 511, shadow=False)

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if r_start.collidepoint(event.pos):
                start_game()
            elif r_bg.collidepoint(event.pos):
                state = STATE_BG_SEL
            elif r_bird.collidepoint(event.pos):
                state = STATE_BIRD_SEL


def draw_bg_select(events):
    global state, bg_idx
    window.blit(backgrounds[bg_idx], (0, 0))

    # Dark overlay
    ov = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 140))
    window.blit(ov, (0, 0))

    draw_text_centered(window, "Choose Background", font_md, WHITE,
                       GAME_WIDTH//2, 30)

    thumb_w, thumb_h = 140, 90
    gap = 16
    start_x = (GAME_WIDTH - (thumb_w*2 + gap)) // 2
    start_y = 90

    mx, my = mx_my()
    for i, bg in enumerate(backgrounds):
        col = i % 2
        row = i // 2
        x   = start_x + col * (thumb_w + gap)
        y   = start_y + row * (thumb_h + 60)
        rect= pygame.Rect(x, y, thumb_w, thumb_h)

        thumb = pygame.transform.scale(bg, (thumb_w, thumb_h))
        window.blit(thumb, rect)

        border_col = GOLD if i == bg_idx else WHITE
        border_w   = 4 if i == bg_idx else 2
        pygame.draw.rect(window, border_col, rect, border_w, border_radius=6)

        label = font_xs.render(BG_LABELS[i], True, WHITE)
        window.blit(label, label.get_rect(centerx=rect.centerx,
                                          top=rect.bottom + 4))

        if i == bg_idx:
            chk = font_xs.render("✔ Selected", True, GOLD)
            window.blit(chk, chk.get_rect(centerx=rect.centerx,
                                           top=rect.bottom + 20))

    # Back button
    r_back = pygame.Rect(GAME_WIDTH//2 - 70, GAME_HEIGHT - 60, 140, 40)
    hov    = r_back.collidepoint(mx, my)
    draw_button(window, "← Back", font_sm, r_back, RED, WHITE, hov)

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if r_back.collidepoint(event.pos):
                state = STATE_HOME
                save["bg_choice"] = bg_idx
                write_save(save)
            else:
                for i in range(4):
                    col = i % 2; row = i // 2
                    x   = start_x + col * (thumb_w + gap)
                    y   = start_y + row * (thumb_h + 60)
                    if pygame.Rect(x, y, thumb_w, thumb_h).collidepoint(event.pos):
                        bg_idx = i
                        save["bg_choice"] = bg_idx
                        write_save(save)


def draw_bird_select(events):
    global state, bird_idx
    window.blit(backgrounds[bg_idx], (0, 0))

    ov = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 140))
    window.blit(ov, (0, 0))

    draw_text_centered(window, "Choose Your Bird", font_md, WHITE,
                       GAME_WIDTH//2, 30)

    card_w, card_h = 90, 120
    total_w = card_w * 3 + 20 * 2
    sx = (GAME_WIDTH - total_w) // 2
    sy = 110

    mx, my = mx_my()
    t = pygame.time.get_ticks() / 1000

    for i, bimg in enumerate(bird_images):
        cx   = sx + i * (card_w + 20) + card_w // 2
        cy   = sy + card_h // 2
        # Hover bob
        bob  = int(8 * pygame.math.Vector2(0,1).rotate((t*120 + i*120)).y)
        card = pygame.Rect(cx - card_w//2, sy + bob, card_w, card_h)

        border_col = GOLD if i == bird_idx else (100, 100, 120)
        panel_col  = (40, 40, 60) if i == bird_idx else (20, 20, 40)
        draw_panel(window, card, 200, panel_col)
        pygame.draw.rect(window, border_col, card, 3, border_radius=10)

        # Bird preview (2x scaled)
        big = pygame.transform.scale(bimg, (BIRD_WIDTH*2, BIRD_HEIGHT*2))
        window.blit(big, big.get_rect(centerx=cx, centery=sy + card_h//2 + bob))

        # Label
        lbl = font_xs.render(BIRD_LABELS[i], True, WHITE)
        window.blit(lbl, lbl.get_rect(centerx=cx, top=sy + card_h + bob + 4))

        if i == bird_idx:
            chk = font_xs.render("✔", True, GOLD)
            window.blit(chk, chk.get_rect(centerx=cx, top=sy + card_h + bob + 22))

    # Back button
    r_back = pygame.Rect(GAME_WIDTH//2 - 70, GAME_HEIGHT - 60, 140, 40)
    hov    = r_back.collidepoint(mx, my)
    draw_button(window, "← Back", font_sm, r_back, RED, WHITE, hov)

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if r_back.collidepoint(event.pos):
                state = STATE_HOME
                save["bird_choice"] = bird_idx
                write_save(save)
            else:
                for i in range(3):
                    cx   = sx + i * (card_w + 20) + card_w // 2
                    card = pygame.Rect(cx - card_w//2, sy, card_w, card_h)
                    if card.collidepoint(event.pos):
                        bird_idx = i
                        save["bird_choice"] = bird_idx
                        write_save(save)


def draw_play(events):
    global score, high_score, state, pipe_timer

    # Background
    window.blit(backgrounds[bg_idx], (0, 0))

    # Pipes
    for pipe in pipes:
        pipe.update()
        pipe.draw(window)

    # Ground
    draw_ground(window)

    # Particles
    update_draw_particles(window)

    # Bird
    bird.update()
    bird.draw(window)

    # Pipe collision / scoring
    for pipe in pipes:
        if bird.colliderect(pipe):
            spawn_particles(bird.centerx, bird.centery, RED)
            stop_pipe_timer()
            state = STATE_GAMEOVER
            if score > high_score:
                high_score = score
                save["high_score"] = int(high_score)
                write_save(save)
            return

        if not pipe.passed and bird.x > pipe.x + PIPE_WIDTH:
            score  += 0.5
            pipe.passed = True
            if score == int(score):          # whole point scored
                spawn_particles(bird.centerx, bird.centery - 20, GOLD, 10)

    # Remove off-screen pipes
    while pipes and pipes[0].x < -PIPE_WIDTH:
        pipes.pop(0)

    # Bird fell off screen
    if bird.is_dead():
        stop_pipe_timer()
        spawn_particles(bird.centerx, bird.centery, RED)
        state = STATE_GAMEOVER
        if score > high_score:
            high_score = score
            save["high_score"] = int(high_score)
            write_save(save)
        return

    # Score HUD
    score_str = str(int(score))
    draw_text_centered(window, score_str, font_lg, WHITE, GAME_WIDTH//2, 14)

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_x):
                bird.flap()
        if event.type == pygame.MOUSEBUTTONDOWN:
            bird.flap()
        if event.type == CREATE_PIPE:
            top, bot = make_pipes()
            pipes.extend([top, bot])


def draw_gameover(events):
    global state, score, high_score
    window.blit(backgrounds[bg_idx], (0, 0))

    for pipe in pipes:
        pipe.draw(window)
    draw_ground(window)
    update_draw_particles(window)
    bird.draw(window)

    # Semi-transparent overlay panel
    panel = pygame.Rect(30, 160, GAME_WIDTH - 60, 280)
    draw_panel(window, panel, 210, DARK)

    draw_text_centered(window, "GAME OVER", font_lg, RED,
                       GAME_WIDTH//2, 175)

    is_new = int(score) >= int(high_score) and score > 0

    draw_text_centered(window, f"Score:  {int(score)}", font_md,
                       WHITE, GAME_WIDTH//2, 250)

    hs_color = GOLD if is_new else GREY
    draw_text_centered(window, f"Best:   {int(high_score)}", font_md,
                       hs_color, GAME_WIDTH//2, 295)

    if is_new:
        draw_text_centered(window, "🎉 New High Score!", font_sm,
                           GOLD, GAME_WIDTH//2, 335)

    mx, my = mx_my()
    btn_w = 150; btn_h = 44
    r_restart = pygame.Rect(GAME_WIDTH//2 - btn_w - 8, 470, btn_w, btn_h)
    r_home    = pygame.Rect(GAME_WIDTH//2 + 8,          470, btn_w, btn_h)

    draw_button(window, "▶ Retry",    font_sm, r_restart, GREEN, WHITE,
                r_restart.collidepoint(mx, my))
    draw_button(window, "🏠 Home",    font_sm, r_home,    BLUE,  WHITE,
                r_home.collidepoint(mx, my))

    draw_text_centered(window, "Space / Tap to Retry", font_xs,
                       GREY, GAME_WIDTH//2, GAME_HEIGHT - 30, shadow=False)

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if r_restart.collidepoint(event.pos):
                start_game()
            elif r_home.collidepoint(event.pos):
                state = STATE_HOME
                particles.clear()
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_x, pygame.K_RETURN):
                start_game()

# ─── Main loop ────────────────────────────────────────────────────────────────
while True:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            write_save(save)
            pygame.quit()
            exit()

    if state == STATE_HOME:
        draw_home(events)
    elif state == STATE_BG_SEL:
        draw_bg_select(events)
    elif state == STATE_BIRD_SEL:
        draw_bird_select(events)
    elif state == STATE_PLAY:
        draw_play(events)
    elif state == STATE_GAMEOVER:
        draw_gameover(events)

    pygame.display.update()
    clock.tick(FPS)