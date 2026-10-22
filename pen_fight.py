"""
PEN FIGHT DELUXE - Complete Edition with Main Menu, Themes & Procedural BGM.

Flick your pen so it smacks your friend's pen off the desk!
100% self-contained in a single file: procedural SFX + BGM synthesizer,
interactive Main Menu, 4 Global UI Themes, 4 Table Skins, and 4 Pen Skins.

Install:  pip install pygame
Run:      python pen_fight.py

Controls
  Mouse   : Navigate menu OR click & drag on YOUR pen to flick
  Esc     : Toggle between Match and Main Menu
  T       : Cycle Table Skin
  1 / 2   : Cycle Pen Skin for Player 1 / Player 2
  V       : Cycle Global UI Theme
  B       : Cycle Background Music (Lo-Fi / Chiptune / Synthwave / Off)
  M       : Mute / Unmute SFX
  C       : Switch between 2-Player and vs Computer
  R       : Restart match
"""
import array
import math
import random
import sys

import pygame

# ----------------------------------------------------------------- settings
W, H = 1080, 680
DESK_X, DESK_Y, DESK_W, DESK_H = 90, 100, 900, 495

PEN_LEN = 154.0
PEN_R = 6.5
HALF_LEN = PEN_LEN / 2
CORE_HALF = HALF_LEN - PEN_R
MASS = 1.0
INERTIA = MASS * PEN_LEN ** 2 / 12

FRICTION = 980.0
SPIN_FRICTION = 24.0
RESTITUTION = 0.58
CONTACT_FRICTION = 0.15
SUBSTEPS = 8

MAX_PULL = 175.0
POWER_K = 6.6
MAX_SPEED = MAX_PULL * POWER_K
MAX_SPIN = 15.0

BLUE = (52, 130, 246)
RED = (238, 68, 68)
NAMES = ("Blue", "Red")
COLORS = (BLUE, RED)

TABLE_SKINS = ["Classic School Desk", "Green Cutting Mat", "Royal Marble", "Cyber Neon Grid"]
PEN_SKINS = ["Classic Gel", "HB #2 Pencil", "Fountain Pen", "Neon Saber"]
BGM_NAMES = ["Chill Lo-Fi", "8-Bit Arcade", "Synthwave Pulse", "Off"]
WIN_GOALS = [3, 5, 7]

THEMES = [
    {
        "name": "Midnight Classroom",
        "bg": (22, 26, 38),
        "bg_accent": (34, 42, 62),
        "panel": (16, 19, 28, 215),
        "border": (110, 150, 255),
        "text": (240, 244, 255),
        "subtext": (170, 182, 205),
        "btn": (35, 44, 68),
        "btn_hover": (52, 68, 104),
    },
    {
        "name": "Cyber Arcade",
        "bg": (11, 8, 24),
        "bg_accent": (32, 14, 52),
        "panel": (18, 12, 34, 220),
        "border": (0, 235, 255),
        "text": (245, 240, 255),
        "subtext": (255, 110, 195),
        "btn": (36, 20, 62),
        "btn_hover": (68, 30, 110),
    },
    {
        "name": "Sunset Lounge",
        "bg": (40, 24, 26),
        "bg_accent": (68, 36, 34),
        "panel": (30, 18, 20, 218),
        "border": (255, 165, 75),
        "text": (255, 244, 232),
        "subtext": (225, 180, 150),
        "btn": (62, 34, 34),
        "btn_hover": (96, 52, 46),
    },
    {
        "name": "Minimal Daylight",
        "bg": (218, 224, 234),
        "bg_accent": (196, 205, 220),
        "panel": (245, 248, 252, 225),
        "border": (70, 110, 180),
        "text": (28, 34, 46),
        "subtext": (85, 98, 120),
        "btn": (224, 230, 242),
        "btn_hover": (198, 212, 235),
    },
]


# ----------------------------------------- procedural SFX & BGM synthesizer
class SoundManager:
    """Synthesizes both sound effects and looping background music tracks in RAM."""
    def __init__(self):
        self.muted = False
        self.enabled = False
        self.sounds = {}
        self.bgm_tracks = []
        self.bgm_idx = 0
        self.bgm_channel = None
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
            pygame.mixer.set_num_channels(8)
            self.bgm_channel = pygame.mixer.Channel(7)
            self.enabled = True
            self._build_sfx()
            self._build_bgm()
            self.play_bgm(0)
        except Exception:
            self.enabled = False

    def _make_sound(self, samples):
        buf = array.array("h", [max(-32767, min(32767, int(s * 32767))) for s in samples])
        return pygame.mixer.Sound(buffer=buf)

    def _build_sfx(self):
        sr = 44100
        rng = random.Random(42)

        # Clack
        clack = []
        for i in range(int(sr * 0.08)):
            t = i / sr
            env = math.exp(-t * 65.0)
            sig = (
                0.55 * math.sin(2 * math.pi * 820 * t)
                + 0.30 * math.sin(2 * math.pi * 1750 * t)
                + 0.35 * (rng.random() * 2 - 1) * math.exp(-t * 140.0)
            )
            clack.append(sig * env * 0.85)
        self.sounds["clack"] = self._make_sound(clack)

        # Flick whoosh
        whoosh = []
        for i in range(int(sr * 0.14)):
            t = i / sr
            env = math.sin(math.pi * (t / 0.14)) ** 1.4
            freq = 180 + 480 * (1 - t / 0.14)
            sig = 0.45 * math.sin(2 * math.pi * freq * t) + 0.35 * (rng.random() * 2 - 1)
            whoosh.append(sig * env * 0.45)
        self.sounds["flick"] = self._make_sound(whoosh)

        # Fall off desk
        fall = []
        for i in range(int(sr * 0.38)):
            t = i / sr
            if t < 0.24:
                freq = 520 - 1100 * t
                sig = math.sin(2 * math.pi * freq * t) * (1 - t / 0.24) * 0.4
            else:
                t2 = t - 0.24
                env = math.exp(-t2 * 28.0)
                sig = (0.7 * math.sin(2 * math.pi * 95 * t2) + 0.3 * (rng.random() * 2 - 1)) * env * 0.7
            fall.append(sig)
        self.sounds["fall"] = self._make_sound(fall)

        # Score chime
        score = []
        notes = [(523.25, 0.0, 0.12), (659.25, 0.10, 0.28)]
        for i in range(int(sr * 0.30)):
            t = i / sr
            val = 0.0
            for freq, start, end in notes:
                if start <= t <= end:
                    lt = t - start
                    val += 0.45 * (math.sin(2 * math.pi * freq * lt) + 0.25 * math.sin(4 * math.pi * freq * lt)) * math.exp(-lt * 10.0)
            score.append(val)
        self.sounds["score"] = self._make_sound(score)

        # Win fanfare
        win = []
        chord = [(523.25, 0.0, 0.14), (659.25, 0.11, 0.25), (783.99, 0.22, 0.36), (1046.50, 0.33, 0.75)]
        for i in range(int(sr * 0.76)):
            t = i / sr
            val = 0.0
            for freq, start, end in chord:
                if start <= t <= end:
                    lt = t - start
                    val += 0.38 * (math.sin(2 * math.pi * freq * lt) + 0.3 * math.sin(3 * math.pi * freq * lt)) * math.exp(-lt * 5.5)
            win.append(val)
        self.sounds["win"] = self._make_sound(win)

        # UI click
        click = []
        for i in range(int(sr * 0.025)):
            t = i / sr
            click.append(math.sin(2 * math.pi * 1250 * t) * math.exp(-t * 160.0) * 0.4)
        self.sounds["click"] = self._make_sound(click)

    def _build_bgm(self):
        sr = 44100
        dur = 6.4  # 8-bar loop at 0.8s per bar
        total = int(sr * dur)

        # Track 1: Chill Lo-Fi Study (warm Rhodes chords + soft pulse)
        lofi = [0.0] * total
        chords = [
            [261.63, 329.63, 392.00, 493.88],  # Cmaj7
            [220.00, 261.63, 329.63, 392.00],  # Am7
            [174.61, 220.00, 261.63, 349.23],  # Fmaj7
            [196.00, 246.94, 293.66, 349.23],  # G7
        ]
        for i in range(total):
            t = i / sr
            bar = int(t / 1.6) % 4
            lt = t % 1.6
            env = math.exp(-lt * 1.4) * min(1.0, lt * 35.0)
            sig = sum(math.sin(2 * math.pi * f * t) for f in chords[bar]) * 0.055 * env
            # Soft kick on beat
            beat_t = t % 0.8
            kick = math.sin(2 * math.pi * (95 * math.exp(-beat_t * 18)) * beat_t) * math.exp(-beat_t * 14) * 0.12
            lofi[i] = sig + kick
        self.bgm_tracks.append(self._make_sound(lofi))

        # Track 2: 8-Bit Arcade Chiptune (upbeat arpeggio)
        chip = [0.0] * total
        melody = [
            523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.00, 698.46,
            493.88, 587.33, 783.99, 587.33, 523.25, 659.25, 783.99, 1046.50,
        ]
        step_len = dur / 32
        for i in range(total):
            t = i / sr
            step = int(t / step_len) % 16
            lt = t % step_len
            freq = melody[step]
            env = math.exp(-lt * 8.0)
            sq = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            bass_f = freq * 0.25
            bass = 1.0 if math.sin(2 * math.pi * bass_f * t) >= 0 else -1.0
            chip[i] = (sq * 0.06 * env) + (bass * 0.045)
        self.bgm_tracks.append(self._make_sound(chip))

        # Track 3: Synthwave Pulse (driving bass + neon pad)
        synth = [0.0] * total
        bass_notes = [110.0, 110.0, 87.31, 98.0]
        for i in range(total):
            t = i / sr
            bar = int(t / 1.6) % 4
            bf = bass_notes[bar]
            pulse_t = t % 0.2
            env = math.exp(-pulse_t * 11.0)
            saw = 2.0 * ((t * bf) - math.floor(0.5 + t * bf))
            pad = (math.sin(2 * math.pi * bf * 2 * t) + math.sin(2 * math.pi * bf * 3 * t)) * 0.04
            synth[i] = saw * env * 0.09 + pad
        self.bgm_tracks.append(self._make_sound(synth))

    def play(self, name, volume=1.0):
        if not self.enabled or self.muted or name not in self.sounds:
            return
        snd = self.sounds[name]
        snd.set_volume(max(0.05, min(1.0, volume)))
        snd.play()

    def play_bgm(self, idx):
        self.bgm_idx = idx % len(BGM_NAMES)
        if not self.enabled or self.bgm_channel is None:
            return
        self.bgm_channel.stop()
        if self.bgm_idx < len(self.bgm_tracks):
            self.bgm_channel.play(self.bgm_tracks[self.bgm_idx], loops=-1)
            self.bgm_channel.set_volume(0.55)

    def cycle_bgm(self):
        self.play("click")
        self.play_bgm(self.bgm_idx + 1)


# ------------------------------------------------------------------- vectors
class Vec:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def __add__(self, o):
        return Vec(self.x + o.x, self.y + o.y)

    def __sub__(self, o):
        return Vec(self.x - o.x, self.y - o.y)

    def __mul__(self, k):
        return Vec(self.x * k, self.y * k)

    __rmul__ = __mul__

    def dot(self, o):
        return self.x * o.x + self.y * o.y

    def cross(self, o):
        return self.x * o.y - self.y * o.x

    def length(self):
        return math.hypot(self.x, self.y)

    def unit(self):
        n = self.length()
        return Vec(self.x / n, self.y / n) if n > 1e-9 else Vec(1.0, 0.0)

    def xy(self):
        return (self.x, self.y)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def shade(c, f):
    return tuple(int(clamp(v * f, 0, 255)) for v in c)


def mix_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def closest_point_on_segment(p, a, b):
    ab = b - a
    t = clamp((p - a).dot(ab) / ab.dot(ab), 0.0, 1.0)
    return a + ab * t


def closest_points_between_segments(p1, q1, p2, q2):
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1.dot(d1), d2.dot(d2), d2.dot(r)
    if a <= 1e-9 and e <= 1e-9:
        return p1, p2
    if a <= 1e-9:
        s, t = 0.0, clamp(f / e, 0.0, 1.0)
    else:
        c = d1.dot(r)
        if e <= 1e-9:
            s, t = clamp(-c / a, 0.0, 1.0), 0.0
        else:
            b = d1.dot(d2)
            denom = a * e - b * b
            s = clamp((b * f - c * e) / denom, 0.0, 1.0) if denom > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t, s = 0.0, clamp(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t, s = 1.0, clamp((b - c) / a, 0.0, 1.0)
    return p1 + d1 * s, p2 + d2 * t


# ------------------------------------------------------------------- physics
class Pen:
    def __init__(self, x, y, angle, color, name, skin=0):
        self.pos = Vec(x, y)
        self.angle = angle
        self.vel = Vec()
        self.w = 0.0
        self.color = color
        self.name = name
        self.skin = skin
        self.fallen = False
        self.fall_time = 0.0
        self.trail = []

    def axis(self):
        return Vec(math.cos(self.angle), math.sin(self.angle))

    def core(self):
        u = self.axis() * CORE_HALF
        return self.pos - u, self.pos + u

    def moving(self):
        return self.vel.length() > 1e-6 or abs(self.w) > 1e-6

    def integrate(self, h):
        speed = self.vel.length()
        if speed > 0:
            self.vel = self.vel * (max(0.0, speed - FRICTION * h) / speed)
        if self.w != 0:
            self.w = math.copysign(max(0.0, abs(self.w) - SPIN_FRICTION * h), self.w)
        self.pos = self.pos + self.vel * h
        self.angle += self.w * h


def _apply_impulse(pen, r, imp):
    pen.vel = pen.vel + imp * (1.0 / MASS)
    pen.w += r.cross(imp) / INERTIA


def collide(a, b):
    a1, a2 = a.core()
    b1, b2 = b.core()
    c1, c2 = closest_points_between_segments(a1, a2, b1, b2)
    delta = c2 - c1
    dist = delta.length()
    min_dist = 2 * PEN_R
    if dist >= min_dist:
        return None

    n = delta * (1.0 / dist) if dist > 1e-6 else (b.pos - a.pos).unit()
    overlap = min_dist - dist
    cp = (c1 + c2) * 0.5

    a.pos = a.pos - n * (overlap * 0.5)
    b.pos = b.pos + n * (overlap * 0.5)

    ra, rb = cp - a.pos, cp - b.pos

    def rel_vel():
        va = a.vel + Vec(-a.w * ra.y, a.w * ra.x)
        vb = b.vel + Vec(-b.w * rb.y, b.w * rb.x)
        return vb - va

    vn = rel_vel().dot(n)
    if vn >= 0:
        return None

    ran, rbn = ra.cross(n), rb.cross(n)
    denom = 2.0 / MASS + (ran * ran + rbn * rbn) / INERTIA
    j = -(1 + RESTITUTION) * vn / denom
    imp = n * j
    _apply_impulse(a, ra, imp * -1.0)
    _apply_impulse(b, rb, imp)

    t = Vec(-n.y, n.x)
    vt = rel_vel().dot(t)
    rat, rbt = ra.cross(t), rb.cross(t)
    denom_t = 2.0 / MASS + (rat * rat + rbt * rbt) / INERTIA
    jt = clamp(-vt / denom_t, -CONTACT_FRICTION * j, CONTACT_FRICTION * j)
    _apply_impulse(a, ra, t * -jt)
    _apply_impulse(b, rb, t * jt)
    return cp, j


def flick(pen, grab_point, direction, power):
    J = direction * (clamp(power, 0.0, MAX_PULL) * POWER_K)
    pen.vel = pen.vel + J * (1.0 / MASS)
    lever = (grab_point - pen.pos) * 0.35
    pen.w = clamp(pen.w + lever.cross(J) / INERTIA, -MAX_SPIN, MAX_SPIN)


def on_desk(p):
    return DESK_X <= p.x <= DESK_X + DESK_W and DESK_Y <= p.y <= DESK_Y + DESK_H


# ----------------------------------------------------------------- particles
class Particle:
    def __init__(self, pos, vel, color, size, life):
        self.pos = Vec(pos.x, pos.y)
        self.vel = vel
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.pos = self.pos + self.vel * dt
        self.vel = self.vel * max(0.0, 1.0 - 4.5 * dt)
        self.life -= dt


# ---------------------------------------------------------------- game logic
class Game:
    def __init__(self, sfx):
        self.sfx = sfx
        self.ai = {1}                   # Default: vs Computer
        self.table_skin = 0
        self.pen_skins = [0, 2]
        self.theme_idx = 0
        self.win_goal_idx = 0
        self.in_menu = True
        self.menu_buttons = []
        self.top_menu_btn = pygame.Rect(W // 2 - 55, 16, 110, 28)
        self.rebuild_tables()
        self.reset()

    @property
    def theme(self):
        return THEMES[self.theme_idx]

    @property
    def win_score(self):
        return WIN_GOALS[self.win_goal_idx]

    def rebuild_tables(self):
        bg = self.theme["bg"]
        accent = self.theme["bg_accent"]
        self.table_surfaces = [make_desk_surface(i, bg, accent) for i in range(len(TABLE_SKINS))]

    def reset(self):
        self.scores = [0, 0]
        self.first = 0
        self.winner = None
        self.new_round()

    def toggle_ai(self):
        self.ai = set() if self.ai else {1}
        self.sfx.play("click")
        self.reset()

    def cycle_table_skin(self):
        self.table_skin = (self.table_skin + 1) % len(TABLE_SKINS)
        self.sfx.play("click")

    def cycle_pen_skin(self, player_idx):
        self.pen_skins[player_idx] = (self.pen_skins[player_idx] + 1) % len(PEN_SKINS)
        self.pens[player_idx].skin = self.pen_skins[player_idx]
        self.sfx.play("click")

    def cycle_theme(self):
        self.theme_idx = (self.theme_idx + 1) % len(THEMES)
        self.rebuild_tables()
        self.sfx.play("click")

    def cycle_win_goal(self):
        self.win_goal_idx = (self.win_goal_idx + 1) % len(WIN_GOALS)
        self.sfx.play("click")
        self.reset()

    def new_round(self):
        cx, cy = DESK_X + DESK_W / 2, DESK_Y + DESK_H / 2
        self.pens = [
            Pen(cx - 240, cy + random.uniform(-60, 60), math.pi / 2 + random.uniform(-0.4, 0.4),
                BLUE, NAMES[0], self.pen_skins[0]),
            Pen(cx + 240, cy + random.uniform(-60, 60), math.pi / 2 + random.uniform(-0.4, 0.4),
                RED, NAMES[1], self.pen_skins[1]),
        ]
        self.turn = self.first
        self.msg = ""
        self.timer = 0.0
        self.hit_fx = []
        self.particles = []
        self.shake = 0.0
        self.begin_turn()

    def begin_turn(self):
        self.state = "aim"
        self.drag = None
        self.ai_timer = random.uniform(0.75, 1.3)

    def spawn_hit_fx(self, pos, impulse):
        self.hit_fx.append([pos, 0.0, min(1.6, impulse / 400.0)])
        count = min(28, int(6 + impulse / 45))
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(60, 260 + impulse * 0.35)
            col = random.choice([(255, 240, 150), (255, 255, 255), (255, 180, 70), COLORS[0], COLORS[1]])
            self.particles.append(
                Particle(pos, Vec(math.cos(ang) * spd, math.sin(ang) * spd),
                         col, random.uniform(2.5, 5.5), random.uniform(0.18, 0.45))
            )

    def mouse_down(self, pos):
        if self.in_menu:
            for rect, action in self.menu_buttons:
                if rect.collidepoint(pos.x, pos.y):
                    action()
                    return
            return

        if self.top_menu_btn.collidepoint(pos.x, pos.y):
            self.sfx.play("click")
            self.in_menu = True
            return

        if self.state != "aim" or self.turn in self.ai:
            return
        a, b = self.pens[self.turn].core()
        g = closest_point_on_segment(pos, a, b)
        if (pos - g).length() <= PEN_R + 26:
            self.drag = g

    def mouse_up(self, pos):
        if self.in_menu or self.drag is None:
            return
        grab, self.drag = self.drag, None
        pull = grab - pos
        if pull.length() < 12:
            return
        power = min(pull.length(), MAX_PULL)
        flick(self.pens[self.turn], grab, pull.unit(), power)
        self.sfx.play("flick", 0.35 + 0.65 * (power / MAX_PULL))
        self.state = "moving"

    def ai_shoot(self):
        me, opp = self.pens[self.turn], self.pens[1 - self.turn]
        target = opp.pos + opp.axis() * (CORE_HALF * random.uniform(-0.5, 0.5))
        grab = me.pos + me.axis() * random.uniform(-25, 25)
        d = target - grab
        ang = math.atan2(d.y, d.x) + random.gauss(0, 0.055)
        speed = math.sqrt(2 * FRICTION * d.length()) * random.uniform(1.3, 1.75)
        speed = min(speed, MAX_SPEED)
        power = speed / POWER_K
        flick(me, grab, Vec(math.cos(ang), math.sin(ang)), power)
        self.sfx.play("flick", 0.35 + 0.65 * (power / MAX_PULL))
        self.state = "moving"

    def update(self, dt):
        if self.in_menu:
            return

        a, b = self.pens
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            a.integrate(h)
            b.integrate(h)
            if not (a.fallen or b.fallen):
                hit = collide(a, b)
                if hit and hit[1] > 45:
                    cp, imp = hit
                    self.spawn_hit_fx(cp, imp)
                    self.shake = min(14.0, self.shake + imp / 65.0)
                    self.sfx.play("clack", min(1.0, imp / 650.0))

        for p in self.pens:
            if not p.fallen and p.vel.length() > 140:
                p.trail.append((Vec(p.pos.x, p.pos.y), p.angle, 0.16))
            p.trail = [(tp, ta, tl - dt) for tp, ta, tl in p.trail if tl - dt > 0]

            if p.fallen:
                p.fall_time += dt
            elif not on_desk(p.pos):
                p.fallen = True
                self.sfx.play("fall", 0.85)
                self.shake = max(self.shake, 6.0)

        for fx in self.hit_fx:
            fx[1] += dt
        self.hit_fx = [fx for fx in self.hit_fx if fx[1] < 0.32]

        for pt in self.particles:
            pt.update(dt)
        self.particles = [pt for pt in self.particles if pt.life > 0]

        self.shake = max(0.0, self.shake - 42.0 * dt)

        if self.state == "aim":
            if self.turn in self.ai:
                self.ai_timer -= dt
                if self.ai_timer <= 0:
                    self.ai_shoot()
        elif self.state == "moving":
            if a.fallen or b.fallen:
                self.end_round()
            elif not (a.moving() or b.moving()):
                self.turn = 1 - self.turn
                self.begin_turn()
        elif self.state == "round_over":
            self.timer -= dt
            if self.timer <= 0:
                if self.winner is not None:
                    self.state = "game_over"
                else:
                    self.first = 1 - self.first
                    self.new_round()

    def end_round(self):
        a, b = self.pens
        if a.fallen and b.fallen:
            self.msg = "Double Knockout! No point."
        elif a.fallen:
            self.scores[1] += 1
            self.msg = f"{a.name}'s pen fell off!  {b.name} scores!"
        else:
            self.scores[0] += 1
            self.msg = f"{b.name}'s pen fell off!  {a.name} scores!"
        for i in (0, 1):
            if self.scores[i] >= self.win_score:
                self.winner = i
        if self.winner is not None:
            self.sfx.play("win", 0.95)
        elif not (a.fallen and b.fallen):
            self.sfx.play("score", 0.85)
        self.state = "round_over"
        self.timer = 2.1

    # ----------------------------------------------------------------- drawing
    def draw(self, screen, fonts, mouse):
        ox = random.uniform(-self.shake, self.shake) if self.shake > 0.2 else 0
        oy = random.uniform(-self.shake, self.shake) if self.shake > 0.2 else 0

        canvas = pygame.Surface((W, H))
        canvas.blit(self.table_surfaces[self.table_skin], (0, 0))

        # Motion trails
        trail_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for p in self.pens:
            for tp, ta, tl in p.trail:
                alpha = int(85 * (tl / 0.16))
                u = Vec(math.cos(ta), math.sin(ta)) * (HALF_LEN * 0.85)
                pygame.draw.line(trail_surf, (*p.color, alpha), (tp - u).xy(), (tp + u).xy(), int(PEN_R * 1.3))
        canvas.blit(trail_surf, (0, 0))

        # Pen shadows
        shadow_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for p in self.pens:
            if not p.fallen:
                draw_pen_skin(shadow_surf, p, scale=1.0, shadow=True)
        canvas.blit(shadow_surf, (0, 0))

        # Pens
        for p in self.pens:
            scale = max(0.35, 1.0 - 0.75 * p.fall_time) if p.fallen else 1.0
            draw_pen_skin(canvas, p, scale=scale, shadow=False)

        # Aim indicator & Slingshot
        if not self.in_menu and self.state == "aim":
            pen = self.pens[self.turn]
            t_ms = pygame.time.get_ticks()
            pulse = 88 + 5 * math.sin(t_ms / 140)
            ring_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*COLORS[self.turn], 170), pen.pos.xy(), pulse, 2)
            pygame.draw.circle(ring_surf, (*COLORS[self.turn], 70), pen.pos.xy(), pulse + 6, 2)
            canvas.blit(ring_surf, (0, 0))
            if self.drag is not None:
                self.draw_aim(canvas, mouse)

        # Impact shockwaves & particles
        fx_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for pos, age, intensity in self.hit_fx:
            alpha = int(255 * (1.0 - age / 0.32))
            radius = int(10 + age * 210 * intensity)
            pygame.draw.circle(fx_surf, (255, 255, 255, alpha), pos.xy(), radius, max(1, int(4 * (1 - age / 0.32))))
        for pt in self.particles:
            alpha = int(255 * (pt.life / pt.max_life))
            pygame.draw.circle(fx_surf, (*pt.color, alpha), pt.pos.xy(), max(1, int(pt.size * (pt.life / pt.max_life))))
        canvas.blit(fx_surf, (0, 0))

        if self.in_menu:
            self.draw_main_menu(canvas, fonts, mouse)
        else:
            self.draw_hud(canvas, fonts, mouse)

        screen.blit(canvas, (int(ox), int(oy)))

    def draw_aim(self, screen, mouse):
        pull = self.drag - mouse
        length = min(pull.length(), MAX_PULL)
        d = pull.unit()
        ratio = length / MAX_PULL
        color = mix_color((80, 235, 120), (255, 65, 65), ratio)
        end = self.drag - d * length

        pygame.draw.line(screen, (30, 30, 35), self.drag.xy(), end.xy(), 8)
        pygame.draw.line(screen, color, self.drag.xy(), end.xy(), 4)
        pygame.draw.circle(screen, (255, 255, 255), self.drag.xy(), 5)
        pygame.draw.circle(screen, color, end.xy(), 8)

        for i in range(1, int(ratio * 13) + 3):
            p = self.drag + d * (i * 22)
            r = max(2, 5 - i // 4)
            pygame.draw.circle(screen, (20, 20, 25), p.xy(), r + 1)
            pygame.draw.circle(screen, color, p.xy(), r)

    def draw_hud(self, screen, fonts, mouse):
        th = self.theme
        hud = pygame.Surface((W - 80, 72), pygame.SRCALPHA)
        pygame.draw.rect(hud, th["panel"], (0, 0, W - 80, 72), border_radius=16)
        pygame.draw.rect(hud, (*th["border"], 90), (0, 0, W - 80, 72), width=2, border_radius=16)
        screen.blit(hud, (40, 12))

        # Player 1 Score & Skin
        text(screen, fonts["big"], f"{NAMES[0].upper()}  {self.scores[0]}", BLUE, (68, 38), "midleft")
        text(screen, fonts["tiny"], f"[1] {PEN_SKINS[self.pen_skins[0]]}", th["subtext"], (68, 66), "midleft")

        # Player 2 Score & Skin
        text(screen, fonts["big"], f"{self.scores[1]}  {NAMES[1].upper()}", RED, (W - 68, 38), "midright")
        text(screen, fonts["tiny"], f"[2] {PEN_SKINS[self.pen_skins[1]]}", th["subtext"], (W - 68, 66), "midright")

        # Top Menu Button
        hover_menu = self.top_menu_btn.collidepoint(mouse.x, mouse.y)
        pygame.draw.rect(screen, th["btn_hover"] if hover_menu else th["btn"], self.top_menu_btn, border_radius=8)
        pygame.draw.rect(screen, th["border"], self.top_menu_btn, width=1, border_radius=8)
        text(screen, fonts["tiny"], "MENU (Esc)", th["text"], self.top_menu_btn.center, "center")

        # Turn status
        if self.state == "aim":
            who = self.turn
            if who in self.ai:
                text(screen, fonts["small"], "Computer is lining up a shot...", COLORS[who], (W // 2, 62), "center")
            else:
                text(screen, fonts["small"], f"{NAMES[who]}'s Turn  —  Drag back on pen to flick",
                     COLORS[who], (W // 2, 62), "center")
        elif self.state == "moving":
            text(screen, fonts["small"], "CLACK!", th["text"], (W // 2, 62), "center")

        # Bottom shortcut bar
        sound_str = "Muted" if self.sfx.muted else "ON"
        footer = (
            f"[T] Table: {TABLE_SKINS[self.table_skin]}  |  "
            f"[V] Theme: {th['name']}  |  "
            f"[B] BGM: {BGM_NAMES[self.sfx.bgm_idx]}  |  "
            f"[M] SFX: {sound_str}  |  "
            f"[Esc] Menu"
        )
        text(screen, fonts["tiny"], footer, th["subtext"], (W // 2, H - 22), "center")

        if self.state in ("round_over", "game_over"):
            line2 = f"First to {self.win_score} points wins"
            line1 = self.msg
            color = th["text"]
            if self.state == "game_over":
                line1 = f"{NAMES[self.winner].upper()} WINS THE CHAMPIONSHIP!"
                line2 = "Press R to play again or Esc for Menu"
                color = COLORS[self.winner]
            banner(screen, fonts, line1, line2, color, th)

    def draw_main_menu(self, screen, fonts, mouse):
        th = self.theme
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 165))
        screen.blit(overlay, (0, 0))

        # Main Card
        card_w, card_h = 860, 560
        card_x, card_y = (W - card_w) // 2, (H - card_h) // 2
        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card, th["panel"], (0, 0, card_w, card_h), border_radius=24)
        pygame.draw.rect(card, th["border"], (0, 0, card_w, card_h), width=2, border_radius=24)
        screen.blit(card, (card_x, card_y))

        # Title Header
        text(screen, fonts["title"], "PEN FIGHT DELUXE", th["text"], (W // 2, card_y + 46), "center")
        text(screen, fonts["small"], "Customize your pens, desk arena, visual theme & soundtrack",
             th["subtext"], (W // 2, card_y + 82), "center")

        # Live Pen Preview Box inside Menu
        prev_rect = pygame.Rect(card_x + 45, card_y + 108, card_w - 90, 96)
        pygame.draw.rect(screen, th["bg"], prev_rect, border_radius=14)
        pygame.draw.rect(screen, (*th["border"], 110), prev_rect, width=1, border_radius=14)

        t_sec = pygame.time.get_ticks() / 1000.0
        wobble = math.sin(t_sec * 2.2) * 0.08
        p1_prev = Pen(prev_rect.left + 210, prev_rect.centery + 6, wobble, BLUE, NAMES[0], self.pen_skins[0])
        p2_prev = Pen(prev_rect.right - 210, prev_rect.centery + 6, math.pi - wobble, RED, NAMES[1], self.pen_skins[1])
        draw_pen_skin(screen, p1_prev, scale=1.05, shadow=False)
        draw_pen_skin(screen, p2_prev, scale=1.05, shadow=False)
        text(screen, fonts["tiny"], f"BLUE: {PEN_SKINS[self.pen_skins[0]]}", BLUE, (prev_rect.left + 210, prev_rect.top + 18), "center")
        text(screen, fonts["tiny"], "VS", th["border"], (prev_rect.centerx, prev_rect.centery), "center")
        text(screen, fonts["tiny"], f"RED: {PEN_SKINS[self.pen_skins[1]]}", RED, (prev_rect.right - 210, prev_rect.top + 18), "center")

        # Interactive Menu Buttons (2 Columns)
        self.menu_buttons = []
        col_w, row_h = 370, 48
        left_x = card_x + 45
        right_x = card_x + card_w - 45 - col_w
        start_y = card_y + 222
        gap_y = 58

        mode_label = "Play vs Computer (AI)" if self.ai else "2-Player Local Pass"
        sfx_label = "OFF" if self.sfx.muted else "ON"

        specs = [
            # Left column
            (left_x, start_y + 0 * gap_y, f"Mode: {mode_label}", self.toggle_ai),
            (left_x, start_y + 1 * gap_y, f"Table Skin: {TABLE_SKINS[self.table_skin]}", self.cycle_table_skin),
            (left_x, start_y + 2 * gap_y, f"Blue Pen: {PEN_SKINS[self.pen_skins[0]]}", lambda: self.cycle_pen_skin(0)),
            (left_x, start_y + 3 * gap_y, f"Red Pen: {PEN_SKINS[self.pen_skins[1]]}", lambda: self.cycle_pen_skin(1)),
            # Right column
            (right_x, start_y + 0 * gap_y, f"UI Theme: {th['name']}", self.cycle_theme),
            (right_x, start_y + 1 * gap_y, f"BGM Track: {BGM_NAMES[self.sfx.bgm_idx]}", self.sfx.cycle_bgm),
            (right_x, start_y + 2 * gap_y, f"Match Goal: First to {self.win_score}", self.cycle_win_goal),
            (right_x, start_y + 3 * gap_y, f"Sound Effects (SFX): {sfx_label}", self._toggle_sfx),
        ]

        for bx, by, label, action in specs:
            rect = pygame.Rect(bx, by, col_w, row_h)
            hovered = rect.collidepoint(mouse.x, mouse.y)
            pygame.draw.rect(screen, th["btn_hover"] if hovered else th["btn"], rect, border_radius=12)
            pygame.draw.rect(screen, th["border"] if hovered else (*th["border"], 90), rect, width=2 if hovered else 1, border_radius=12)
            text(screen, fonts["small"], label, th["text"], rect.center, "center")
            self.menu_buttons.append((rect, action))

        # Bottom Action Buttons (Play / Quit)
        play_rect = pygame.Rect(card_x + 150, card_y + card_h - 82, 340, 54)
        quit_rect = pygame.Rect(card_x + 510, card_y + card_h - 82, 200, 54)

        play_hover = play_rect.collidepoint(mouse.x, mouse.y)
        pygame.draw.rect(screen, (46, 168, 92) if play_hover else (36, 138, 76), play_rect, border_radius=14)
        pygame.draw.rect(screen, (180, 255, 205), play_rect, width=2, border_radius=14)
        text(screen, fonts["mid"], "START / RESUME MATCH", (255, 255, 255), play_rect.center, "center")
        self.menu_buttons.append((play_rect, self._close_menu))

        quit_hover = quit_rect.collidepoint(mouse.x, mouse.y)
        pygame.draw.rect(screen, (195, 55, 55) if quit_hover else (150, 42, 42), quit_rect, border_radius=14)
        pygame.draw.rect(screen, (255, 185, 185), quit_rect, width=2, border_radius=14)
        text(screen, fonts["mid"], "QUIT", (255, 255, 255), quit_rect.center, "center")
        self.menu_buttons.append((quit_rect, self._quit_game))
        # --- Developer Credit Badge (First Page / Main Menu Footer) ---
        credit_rect = pygame.Rect(W // 2 - 230, card_y + card_h - 24, 460, 22)
        text(
            screen,
            fonts["small"],
            "Created and Developed by Hasib Khandoker",
            th["border"],
            credit_rect.center,
            "center",
        )

    def _toggle_sfx(self):
        self.sfx.muted = not self.sfx.muted
        self.sfx.play("click")

    def _close_menu(self):
        self.sfx.play("click")
        self.in_menu = False

    def _quit_game(self):
        pygame.quit()
        sys.exit()


# ------------------------------------------------------- pen & table renderers
def draw_pen_skin(screen, pen, scale=1.0, shadow=False):
    u = pen.axis()
    n = Vec(-u.y, u.x)
    c = pen.pos + (Vec(7, 10) if shadow else Vec(0, 0))
    s = scale
    hw = PEN_R * s
    back = c - u * (HALF_LEN * s - hw)
    front = c + u * ((HALF_LEN - 24) * s)
    tip = c + u * (HALF_LEN * s)

    def poly(col, *pts):
        pygame.draw.polygon(screen, col, [p.xy() for p in pts])

    if shadow:
        sh_col = (0, 0, 0, 75)
        poly(sh_col, back + n * hw, front + n * hw, tip, front - n * hw, back - n * hw)
        pygame.draw.circle(screen, sh_col, back.xy(), max(1, int(hw)))
        return

    skin = pen.skin
    base = pen.color
    dark = shade(base, 0.58)
    light = mix_color(base, (255, 255, 255), 0.48)

    if skin == 0:  # Classic Gel Pen
        poly(base, back + n * hw, front + n * hw, front - n * hw, back - n * hw)
        pygame.draw.circle(screen, dark, back.xy(), max(1, int(hw)))
        g1 = front - u * (38 * s)
        g2 = front - u * (8 * s)
        poly(dark, g1 + n * (hw * 1.05), g2 + n * (hw * 1.05), g2 - n * (hw * 1.05), g1 - n * (hw * 1.05))
        for i in range(5):
            gx = g1 + u * ((6 + i * 6) * s)
            pygame.draw.line(screen, (30, 32, 40), (gx + n * hw).xy(), (gx - n * hw).xy(), max(1, int(2 * s)))
        c1 = back + u * (10 * s) + n * (hw * 1.35)
        c2 = back + u * (48 * s) + n * (hw * 1.25)
        pygame.draw.line(screen, (220, 225, 235), c1.xy(), c2.xy(), max(2, int(3 * s)))
        poly((215, 220, 230), front + n * hw, tip + n * (1.8 * s), tip - n * (1.8 * s), front - n * hw)
        pygame.draw.circle(screen, base, tip.xy(), max(1, int(2.2 * s)))
        pygame.draw.line(screen, light, (back + u * (14 * s) - n * (hw * 0.45)).xy(),
                         (front - u * (42 * s) - n * (hw * 0.45)).xy(), max(1, int(2 * s)))

    elif skin == 1:  # HB #2 Pencil
        gold = (245, 190, 45) if base == BLUE else (235, 145, 40)
        stripe = mix_color(gold, base, 0.35)
        poly(gold, back + n * hw, front + n * hw, front - n * hw, back - n * hw)
        poly(stripe, back + n * (hw * 0.4), front + n * (hw * 0.4), front - n * (hw * 0.4), back - n * (hw * 0.4))
        er_end = back - u * (6 * s)
        poly((242, 138, 165), er_end + n * hw, back + u * (10 * s) + n * hw,
             back + u * (10 * s) - n * hw, er_end - n * hw)
        pygame.draw.circle(screen, (242, 138, 165), er_end.xy(), max(1, int(hw)))
        f1, f2 = back + u * (10 * s), back + u * (24 * s)
        poly((200, 208, 218), f1 + n * hw, f2 + n * hw, f2 - n * hw, f1 - n * hw)
        pygame.draw.line(screen, (130, 135, 145), (f1 + u * (5 * s) + n * hw).xy(), (f1 + u * (5 * s) - n * hw).xy(), 1)
        pygame.draw.line(screen, (130, 135, 145), (f1 + u * (10 * s) + n * hw).xy(), (f1 + u * (10 * s) - n * hw).xy(), 1)
        lead = front + u * (15 * s)
        poly((228, 190, 145), front + n * hw, tip + n * (1.2 * s), tip - n * (1.2 * s), front - n * hw)
        poly(base, lead + n * (hw * 0.38), tip + n * (1.2 * s), tip - n * (1.2 * s), lead - n * (hw * 0.38))

    elif skin == 2:  # Executive Fountain Pen
        body_col = shade(base, 0.72)
        gold = (242, 202, 85)
        poly(body_col, back + n * hw, front + n * hw, front - n * hw, back - n * hw)
        pygame.draw.circle(screen, gold, back.xy(), max(1, int(hw * 0.95)))
        mid = c - u * (8 * s)
        poly(gold, mid + n * hw, mid + u * (8 * s) + n * hw, mid + u * (8 * s) - n * hw, mid - n * hw)
        poly(gold, front - u * (5 * s) + n * hw, front + n * hw, front - n * hw, front - u * (5 * s) - n * hw)
        nib_mid = front + u * (12 * s)
        poly(gold, front + n * (hw * 0.75), nib_mid + n * (hw * 0.95), tip, nib_mid - n * (hw * 0.95), front - n * (hw * 0.75))
        pygame.draw.line(screen, (60, 45, 15), nib_mid.xy(), tip.xy(), 1)
        pygame.draw.circle(screen, (60, 45, 15), nib_mid.xy(), max(1, int(2 * s)))
        pygame.draw.line(screen, light, (back + u * (14 * s) + n * (hw * 0.45)).xy(),
                         (front - u * (10 * s) + n * (hw * 0.45)).xy(), max(1, int(2 * s)))

    else:  # Neon Saber
        hilt_end = back + u * (36 * s)
        poly((65, 70, 82), back + n * (hw * 1.1), hilt_end + n * (hw * 1.1),
             hilt_end - n * (hw * 1.1), back - n * (hw * 1.1))
        pygame.draw.circle(screen, (40, 44, 52), back.xy(), max(1, int(hw * 1.1)))
        glow_outer = mix_color(base, (255, 255, 255), 0.25)
        poly(base, hilt_end + n * (hw * 1.15), tip + n * (hw * 0.7), tip - n * (hw * 0.7), hilt_end - n * (hw * 1.15))
        poly(glow_outer, hilt_end + n * (hw * 0.75), tip + n * (hw * 0.45), tip - n * (hw * 0.45), hilt_end - n * (hw * 0.75))
        pygame.draw.line(screen, (255, 255, 255), hilt_end.xy(), tip.xy(), max(2, int(4 * s)))
        pygame.draw.circle(screen, (255, 255, 255), tip.xy(), max(2, int(hw * 0.65)))


def make_desk_surface(skin_idx, bg_color, accent_color):
    surf = pygame.Surface((W, H))
    surf.fill(bg_color)
    # Subtle room floor stripes
    for y in range(0, H, 40):
        pygame.draw.line(surf, accent_color, (0, y), (W, y), 2)

    rng = random.Random(10 + skin_idx)

    if skin_idx == 0:  # Classic School Wood Desk
        pygame.draw.rect(surf, (10, 12, 18), (DESK_X + 12, DESK_Y + 14, DESK_W, DESK_H), border_radius=20)
        pygame.draw.rect(surf, (128, 86, 46), (DESK_X - 8, DESK_Y - 8, DESK_W + 16, DESK_H + 16), border_radius=22)
        pygame.draw.rect(surf, (206, 158, 104), (DESK_X, DESK_Y, DESK_W, DESK_H), border_radius=16)

        for py in range(DESK_Y + 100, DESK_Y + DESK_H, 100):
            pygame.draw.line(surf, (168, 122, 74), (DESK_X + 6, py), (DESK_X + DESK_W - 6, py), 2)

        for y in range(DESK_Y + 12, DESK_Y + DESK_H - 10, 11):
            x = DESK_X + 14
            while x < DESK_X + DESK_W - 20:
                seg = rng.randint(50, 210)
                col = (190, 142, 90) if rng.random() < 0.6 else (218, 172, 118)
                pygame.draw.line(surf, col, (x, y + rng.randint(-1, 1)),
                                 (min(x + seg, DESK_X + DESK_W - 14), y), 2)
                x += seg + rng.randint(12, 45)

        pygame.draw.rect(surf, (145, 102, 58), (DESK_X + 240, DESK_Y + 18, DESK_W - 480, 10), border_radius=5)
        pygame.draw.rect(surf, (175, 130, 82), (DESK_X + 242, DESK_Y + 21, DESK_W - 484, 5), border_radius=3)

        for cx, cy in [(DESK_X + 10, DESK_Y + 10), (DESK_X + DESK_W - 10, DESK_Y + 10),
                       (DESK_X + 10, DESK_Y + DESK_H - 10), (DESK_X + DESK_W - 10, DESK_Y + DESK_H - 10)]:
            pygame.draw.circle(surf, (180, 145, 75), (cx, cy), 6)
            pygame.draw.circle(surf, (110, 85, 40), (cx, cy), 2)

    elif skin_idx == 1:  # Green Cutting Mat
        pygame.draw.rect(surf, (12, 16, 15), (DESK_X + 12, DESK_Y + 14, DESK_W, DESK_H), border_radius=18)
        pygame.draw.rect(surf, (28, 92, 68), (DESK_X - 6, DESK_Y - 6, DESK_W + 12, DESK_H + 12), border_radius=20)
        pygame.draw.rect(surf, (38, 124, 92), (DESK_X, DESK_Y, DESK_W, DESK_H), border_radius=14)

        for x in range(DESK_X + 25, DESK_X + DESK_W, 25):
            col = (95, 185, 148) if (x - DESK_X) % 100 == 0 else (54, 145, 110)
            pygame.draw.line(surf, col, (x, DESK_Y + 15), (x, DESK_Y + DESK_H - 15), 1)
        for y in range(DESK_Y + 25, DESK_Y + DESK_H, 25):
            col = (95, 185, 148) if (y - DESK_Y) % 100 == 0 else (54, 145, 110)
            pygame.draw.line(surf, col, (DESK_X + 15, y), (DESK_X + DESK_W - 15, y), 1)

        cx, cy = DESK_X + DESK_W // 2, DESK_Y + DESK_H // 2
        pygame.draw.circle(surf, (115, 205, 168), (cx, cy), 140, 2)
        pygame.draw.circle(surf, (115, 205, 168), (cx, cy), 70, 1)

    elif skin_idx == 2:  # Royal Carrara Marble
        pygame.draw.rect(surf, (12, 12, 16), (DESK_X + 12, DESK_Y + 14, DESK_W, DESK_H), border_radius=18)
        pygame.draw.rect(surf, (212, 175, 85), (DESK_X - 7, DESK_Y - 7, DESK_W + 14, DESK_H + 14), border_radius=20)
        pygame.draw.rect(surf, (238, 240, 245), (DESK_X, DESK_Y, DESK_W, DESK_H), border_radius=15)

        for _ in range(28):
            vx = rng.randint(DESK_X + 20, DESK_X + DESK_W - 20)
            vy = rng.randint(DESK_Y + 20, DESK_Y + DESK_H - 20)
            ang = rng.uniform(-0.6, 0.6)
            col = rng.choice([(205, 210, 220), (188, 194, 206), (220, 215, 200)])
            pts = [(vx, vy)]
            for _ in range(rng.randint(6, 14)):
                ang += rng.uniform(-0.35, 0.35)
                vx = clamp(vx + math.cos(ang) * 28, DESK_X + 10, DESK_X + DESK_W - 10)
                vy = clamp(vy + math.sin(ang) * 28, DESK_Y + 10, DESK_Y + DESK_H - 10)
                pts.append((vx, vy))
            if len(pts) > 1:
                pygame.draw.lines(surf, col, False, pts, rng.randint(1, 3))

        pygame.draw.rect(surf, (212, 175, 85), (DESK_X + 16, DESK_Y + 16, DESK_W - 32, DESK_H - 32), width=2, border_radius=10)

    else:  # Cyber Neon Arena
        pygame.draw.rect(surf, (0, 220, 255), (DESK_X - 6, DESK_Y - 6, DESK_W + 12, DESK_H + 12), border_radius=20)
        pygame.draw.rect(surf, (18, 20, 36), (DESK_X, DESK_Y, DESK_W, DESK_H), border_radius=16)

        for x in range(DESK_X + 45, DESK_X + DESK_W, 45):
            pygame.draw.line(surf, (32, 38, 72), (x, DESK_Y + 8), (x, DESK_Y + DESK_H - 8), 1)
        for y in range(DESK_Y + 45, DESK_Y + DESK_H, 45):
            pygame.draw.line(surf, (32, 38, 72), (DESK_X + 8, y), (DESK_X + DESK_W - 8, y), 1)

        cx, cy = DESK_X + DESK_W // 2, DESK_Y + DESK_H // 2
        pygame.draw.line(surf, (255, 0, 128), (cx, DESK_Y + 12), (cx, DESK_Y + DESK_H - 12), 2)
        pygame.draw.circle(surf, (0, 220, 255), (cx, cy), 95, 2)
        pygame.draw.circle(surf, (255, 0, 128), (cx, cy), 45, 1)

    return surf


def text(screen, font, s, color, pos, anchor):
    img = font.render(s, True, color)
    rect = img.get_rect(**{anchor: pos})
    screen.blit(img, rect)


def banner(screen, fonts, line1, line2, color, theme):
    panel = pygame.Surface((720, 138 if line2 else 94), pygame.SRCALPHA)
    pygame.draw.rect(panel, theme["panel"], panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, color, panel.get_rect(), width=2, border_radius=18)
    rect = panel.get_rect(center=(W // 2, DESK_Y + DESK_H // 2))
    screen.blit(panel, rect)
    text(screen, fonts["mid"], line1, color, (W // 2, rect.centery - (18 if line2 else 0)), "center")
    if line2:
        text(screen, fonts["small"], line2, theme["subtext"], (W // 2, rect.centery + 28), "center")


# --------------------------------------------------------------------- main
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Pen Fight Deluxe")
    clock = pygame.time.Clock()
    fonts = {
        "title": pygame.font.Font(None, 64),
        "big": pygame.font.Font(None, 54),
        "mid": pygame.font.Font(None, 36),
        "small": pygame.font.Font(None, 25),
        "tiny": pygame.font.Font(None, 20),
    }
    sfx = SoundManager()
    game = Game(sfx)

    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    sfx.play("click")
                    game.in_menu = not game.in_menu
                elif e.key == pygame.K_r:
                    sfx.play("click")
                    game.reset()
                elif e.key == pygame.K_c:
                    game.toggle_ai()
                elif e.key == pygame.K_t:
                    game.cycle_table_skin()
                elif e.key == pygame.K_v:
                    game.cycle_theme()
                elif e.key == pygame.K_b:
                    sfx.cycle_bgm()
                elif e.key == pygame.K_g:
                    game.cycle_win_goal()
                elif e.key == pygame.K_1:
                    game.cycle_pen_skin(0)
                elif e.key == pygame.K_2:
                    game.cycle_pen_skin(1)
                elif e.key == pygame.K_m:
                    sfx.muted = not sfx.muted
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                game.mouse_down(Vec(*e.pos))
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                game.mouse_up(Vec(*e.pos))

        game.update(dt)
        game.draw(screen, fonts, Vec(*pygame.mouse.get_pos()))
        pygame.display.flip()
        pygame.display.set_caption("Pen Fight Deluxe — Created and Developed by Hasib Khandoker")

if __name__ == "__main__":
    main()