# =====================================================================
#  DEFESA DO CASTELO  -  joguinho py5.Script
# ---------------------------------------------------------------------
#  OBJETIVO: o castelo (com a bandeira do Flamengo) tem 3 vidas.
#  Bonecos de neve atacam em hordas pelas 5 linhas e marcham ate o castelo.
#  Cada FASE tem varias ondas; na ultima onda vem um BOSS. Ao terminar a
#  fase, voce escolhe se quer jogar a proxima ou parar.
#
#  INIMIGOS:
#     - normal    : 1 linha
#     - MINI BOSS : ocupa 2 linhas, bem mais vida
#     - BOSS      : ocupa 3 linhas, muito mais vida
#
#  CONTROLE (defesa): voce ajusta os PONTOS DE CONTROLE de uma B-spline.
#  Subir um ponto -> o canhao daquela linha sobe e o ALCANCE aumenta.
#  (O TERRENO agora fica sempre plano: so a curva se mexe.)
#
#  PODERES ESPECIAIS:
#     1) TIRO RAPIDO : ao matar um MINI BOSS cai uma BOLINHA flutuante onde
#        ele morreu. Pegue-a com a tecla G. Cada bolinha vale +1 carga.
#        Para usar: B -> numero do canhao (1-5 ou A/D) -> B (confirma).
#        Acelera o tiro do canhao escolhido por um tempo.
#     2) BOMBA DE NEVE : ao matar um BOSS voce ganha direto +1 carga.
#        Para usar: U -> numero do canhao (1-5 ou A/D) -> U (confirma).
#        O PROXIMO tiro daquele canhao vira uma bomba: mais dano e mais area
#        (atinge tambem as linhas vizinhas).
#     As cargas acumuladas aparecem no HUD, logo abaixo dos coracoes.
#
#  MODOS (tela inicial, antes de jogar):
#     1 / N         : NORMAL (bonecos comuns + mini boss/boss nas ondas)
#     2 / H         : DIFICIL (so MINI BOSS e BOSS - bom para testar poderes)
#     A/D + ESPACO/ENTER tambem escolhem.
#
#  TECLAS (jogando):
#     A / D  (ou setas <- ->) : escolher a linha
#     W / S  (ou setas ^ v)   : subir / descer o ponto selecionado
#     1..5                    : selecionar a linha diretamente
#     G                       : pegar a(s) bolinha(s) de poder no campo
#     B                       : ativar/confirmar TIRO RAPIDO
#     U                       : ativar/confirmar BOMBA DE NEVE
#     P                       : pausar
#     R                       : reiniciar (volta para a tela de modo)
#     mouse                   : arrastar para girar a camera (orbit)
#
#  GAME OVER: tela cheia com botao "jogar de novo" (clique no botao ou R).
# =====================================================================

import random
import math

# ----------------------------- CONFIG --------------------------------
CANVAS_W = 2000
CANVAS_H = 1500

LANE_X   = [-150.0, -75.0, 0.0, 75.0, 150.0]   # x das 5 linhas
Z_CASTLE_FRONT = -50.0
Z_HIT    = -45.0          # boneco machuca o castelo quando z <= isso
Z_CANNON =  0.0
Z_CTRL   =  40.0
Z_SPAWN  = 440.0          # bonecos nascem bem longe (pista grande)

R_MIN, R_MAX = 20.0, 360.0    # alcance maximo do tiro aumentado
A_MIN, A_MAX = 40.0, 150.0
T_MIN, T_MAX = 12,  20

FIRE_PERIOD = 45
EXPLOSION_RAD    = 34.0
START_LIVES = 3           # <<< 3 VIDAS
WAVES_PER_PHASE = 5       # ondas por fase (boss na ultima)
CANON_ANG   = 0.15            # cada seta sobe/desce mais o ponto (mais altura)

SNOW_N = 250

# --------- PODERES ESPECIAIS (parametros) ---------
PICKUP_TTL        = 360      # quadros que a bolinha do mini boss fica no campo
FIRE_BOOST_FRAMES = 600      # duracao do TIRO RAPIDO (em quadros)
FIRE_BOOST_PERIOD = 15       # periodo do tiro quando acelerado (menor = + rapido)
BOMB_DMG          = 4        # dano da BOMBA DE NEVE
BOMB_EXPLOSION_RAD     = EXPLOSION_RAD * 1.9   # alcance (em z) da bomba

# Posicao do HUD (coracoes/marcadores) no MUNDO, perto do topo da visao.
# Se quiser subir/abaixar o HUD, mexa nestes dois valores:
HUD_Y = -305.0
HUD_Z = 130.0
# Centro dos paineis de fim de fase / parar:
OVR_Y = -120.0
OVR_Z = 130.0

# Tela cheia de GAME OVER (botao "jogar de novo")
BTN_W  = 520.0     # largura do botao
BTN_H  = 160.0     # altura do botao
BTN_CY = 230.0     # posicao vertical do botao (abaixo do centro)

# --------------------------- HELPERS ---------------------------------

def remap(value, start1, stop1, start2, stop2):
    return start2 + (stop2 - start2) * ((value - start1) / float(stop1 - start1))

def elevacoes_suavizadas(pontos_controle):
    n = len(pontos_controle)
    out = []
    for i in range(n):
        anterior = pontos_controle[i - 1] if i - 1 >= 0 else pontos_controle[0]
        atual = pontos_controle[i]
        proximo = pontos_controle[i + 1] if i + 1 < n else pontos_controle[-1]
        out.append(constrain((anterior + 4.0 * atual + proximo) / 6.0, -1.0, 1.0))
    return out

def _bspline_seg(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    b0 = (-t3 + 3 * t2 - 3 * t + 1) / 6.0
    b1 = (3 * t3 - 6 * t2 + 4) / 6.0
    b2 = (-3 * t3 + 3 * t2 + 3 * t + 1) / 6.0
    b3 = t3 / 6.0
    return (b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0],
            b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1],
            b0 * p0[2] + b1 * p1[2] + b2 * p2[2] + b3 * p3[2])

def bspline_points(ctrl, steps=10):
    pts = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(len(pts) - 3):
        for s in range(steps + 1):
            t = s / float(steps)
            out.append(_bspline_seg(pts[i], pts[i + 1], pts[i + 2], pts[i + 3], t))
    return out

def altura_canhao_de_controle(valor_controle):
    # curva de controle agora vai de -1 (vale) a +1 (colina); 0 = plano
    return remap(valor_controle, -1.0, 1.0, -20.0, -170.0)


# ----------------------- TEXTURA DE GELO (tijolos) -------------------
# OTIMIZADO: em vez de centenas de box() individuais por parede/torre,
# desenha 1 forma base (box/cylinder/cone) + linhas de argamassa por cima.
# Isso reduz ~2500 draw calls para ~300, mantendo o visual de tijolos.

def cor_gelo_com_flash():
    # cor base do gelo; mistura pra vermelho quando o castelo acabou de
    # levar um hit (game.flash_castle > 0), criando um flash de dano.
    intensidade_flash = constrain(game.flash_castle / 12.0, 0.0, 1.0)
    r = lerp(82.0, 255.0, intensidade_flash)
    g = lerp(212.0, 35.0, intensidade_flash)
    b = lerp(250.0, 35.0, intensidade_flash)
    return (r, g, b)


def muro_de_gelo(largura, altura, profundidade, num_blocos_x=None, num_blocos_y=None):
    # 1 box base + linhas de argamassa em ambas as faces (frente e tras).
    largura_tijolo = 8.0
    altura_tijolo = 4.0
    if num_blocos_x is None:
        num_blocos_x = max(2, int(largura / largura_tijolo))
    if num_blocos_y is None:
        num_blocos_y = max(2, int(altura / altura_tijolo))
    tamanho_bloco_x = largura / float(num_blocos_x)
    tamanho_bloco_y = altura / float(num_blocos_y)
    push()
    # bloco solido de gelo
    no_stroke()
    cr, cg, cb = cor_gelo_com_flash()
    fill(cr, cg, cb, 220)
    box(largura, altura, profundidade)
    # linhas de argamassa nas duas faces (z = +profundidade/2 e -profundidade/2)
    deslocamento_z = profundidade / 2.0 + 0.12
    stroke(195, 235, 255, 150)
    stroke_weight(0.4)
    for face_sinal in (1.0, -1.0):
        face_z = face_sinal * deslocamento_z
        # horizontais
        for linha in range(1, num_blocos_y):
            y = -altura / 2.0 + linha * tamanho_bloco_y
            line(-largura / 2.0, y, face_z, largura / 2.0, y, face_z)
        # verticais (tijolo alternado)
        for linha in range(num_blocos_y):
            offset_x = (tamanho_bloco_x * 0.5) if (linha % 2 == 1) else 0.0
            y0 = -altura / 2.0 + linha * tamanho_bloco_y
            y1 = y0 + tamanho_bloco_y
            x = -largura / 2.0 + offset_x
            while x <= largura / 2.0 + 0.01:
                if x >= -largura / 2.0:
                    line(x, y0, face_z, x, y1, face_z)
                x += tamanho_bloco_x
    pop()


def cilindro_de_gelo(raio, altura, segmentos=12, linhas_blocos=None):
    # 1 cylinder base + aneis horizontais + verticais de argamassa.
    altura_tijolo = 4.5
    if linhas_blocos is None:
        linhas_blocos = max(2, int(altura / altura_tijolo))
    tamanho_bloco_y = altura / float(linhas_blocos)
    resolucao_anel = segmentos * 2       # resolucao dos aneis de linha
    push()
    # cilindro solido
    no_stroke()
    cr, cg, cb = cor_gelo_com_flash()
    fill(cr, cg, cb, 220)
    cylinder(raio, altura, segmentos, 1)
    # raio um pouquinho maior para as linhas ficarem na superficie
    raio_linhas = raio * 1.008
    stroke(195, 235, 255, 140)
    stroke_weight(0.3)
    # aneis horizontais
    for linha in range(linhas_blocos + 1):
        y = altura / 2.0 - linha * tamanho_bloco_y
        begin_shape()
        for s in range(resolucao_anel + 1):
            angulo = s * (TWO_PI / resolucao_anel)
            vertex(raio_linhas * math.cos(angulo), y, raio_linhas * math.sin(angulo))
        end_shape()
    # verticais (alternadas)
    for linha in range(linhas_blocos):
        deslocamento_angular = (PI / segmentos) if (linha % 2 == 1) else 0.0
        y0 = altura / 2.0 - linha * tamanho_bloco_y
        y1 = y0 - tamanho_bloco_y
        for s in range(segmentos):
            angulo = s * (TWO_PI / segmentos) + deslocamento_angular
            cx = raio_linhas * math.cos(angulo)
            cz = raio_linhas * math.sin(angulo)
            line(cx, y0, cz, cx, y1, cz)
    pop()



# ----------------------- GRAMA ANIMADA (bezier) ----------------------
# OTIMIZADO: sistema de templates com batching por cor.
# Folhas da mesma cor (mesmo blade do mesmo template) em todas as posicoes
# sao agrupadas num unico begin_shape(LINES), reduzindo de ~630 draw calls
# para ~112 (16 templates × 7 blades).

GRASS_TEMPLATES    = []    # lista de templates (cada um = lista de folhas)
GRASS_BY_TEMPLATE  = {}    # tidx -> [(gx, gz, ph_off)]  (agrupado no init)
GRASS_N_TEMPLATES  = 14    # templates distintos
GRASS_BLADES_PER   = 7     # folhas por template
GRASS_SEGMENTS     = 3     # segmentos por curva (3 e suficiente)
# Grid de distribuicao uniforme (colunas x linhas) com jitter
GRASS_GRID_COLS    = 15
GRASS_GRID_ROWS    = 12

def _init_grass():
    global GRASS_TEMPLATES, GRASS_BY_TEMPLATE
    GRASS_TEMPLATES = []
    for _ in range(GRASS_N_TEMPLATES):
        blades = []
        for _ in range(GRASS_BLADES_PER):
            blades.append({
                'dx':    random.uniform(-8.0, 8.0),
                'dz':    random.uniform(-6.0, 6.0),
                'h':     random.uniform(6.0, 10.0),
                'sway':  random.uniform(2.0, 7.0),
                'phase': random.uniform(0.0, TWO_PI),
                'r':     random.randint(18, 70),
                'g':     random.randint(50, 130),
            })
        GRASS_TEMPLATES.append(blades)

    # Distribuicao em GRID com jitter: garante cobertura uniforme
    x_min, x_max = -200.0, 200.0
    z_min, z_max = Z_CASTLE_FRONT + 8.0, Z_SPAWN - 15.0
    cell_w = (x_max - x_min) / float(GRASS_GRID_COLS)
    cell_h = (z_max - z_min) / float(GRASS_GRID_ROWS)
    jitter_x = cell_w * 0.4   # jitter de ate 40% da celula
    jitter_z = cell_h * 0.4

    GRASS_BY_TEMPLATE = {i: [] for i in range(GRASS_N_TEMPLATES)}
    for row in range(GRASS_GRID_ROWS):
        for col in range(GRASS_GRID_COLS):
            # centro da celula + jitter aleatorio
            gx = x_min + (col + 0.5) * cell_w + random.uniform(-jitter_x, jitter_x)
            gz = z_min + (row + 0.5) * cell_h + random.uniform(-jitter_z, jitter_z)
            tidx = random.randint(0, GRASS_N_TEMPLATES - 1)
            ph = random.uniform(0.0, TWO_PI)
            GRASS_BY_TEMPLATE[tidx].append((gx, gz, ph))


def bezier_cubica_ponto(p0x,p0y,p0z, p1x,p1y,p1z, p2x,p2y,p2z, p3x,p3y,p3z, t):
    u = 1.0 - t; u2 = u * u; t2 = t * t
    a = u2 * u; b = 3.0 * u2 * t; c = 3.0 * u * t2; d = t2 * t
    return (a*p0x + b*p1x + c*p2x + d*p3x,
            a*p0y + b*p1y + c*p2y + d*p3y,
            a*p0z + b*p1z + c*p2z + d*p3z)


def draw_grass():
    if not GRASS_BY_TEMPLATE:
        return
    no_fill()
    tempo_atual = frame_count
    speed = 0.065
    numero_segmentos = GRASS_SEGMENTS
    inverso_segmentos = 1.0 / numero_segmentos
    # pre-compute os valores do parâmetro 't' (tempo da curva)
    valores_t_precalculados = [indice_segmento * inverso_segmentos for indice_segmento in range(numero_segmentos + 1)]

    for indice_template in range(GRASS_N_TEMPLATES):
        posicoes_no_mapa = GRASS_BY_TEMPLATE.get(indice_template)
        if not posicoes_no_mapa:
            continue
        template_atual = GRASS_TEMPLATES[indice_template]
        for folha in template_atual:
            # balanço individual desta folha (constante para todas as posicoes clonadas)
            balanco_individual = math.sin(folha['phase'] + tempo_atual * 0.02) * 1.2
            desloc_x = folha['dx']
            desloc_z = folha['dz']
            altura_folha = folha['h']
            forca_balanco = folha['sway']
            stroke(folha['r'], folha['g'], 25, 200)
            stroke_weight(1.1)
            # BATCH: desenha todas as folhas idênticas de uma só vez
            begin_shape(LINES)
            for x_global, z_global, diferenca_fase in posicoes_no_mapa:
                vento_base  = math.sin(tempo_atual * speed + diferenca_fase)
                vento_ponta = math.sin(tempo_atual * speed * 1.3 + diferenca_fase + 1.0) * 0.5
                x_base = x_global + desloc_x
                z_base = z_global + desloc_z
                inclinacao_vento  = forca_balanco * vento_base + balanco_individual
                inclinacao_vento_ponta = forca_balanco * vento_ponta
                # pontos de controle da curva de Bezier
                p0x = x_base;                             p0y = 0.0;                       p0z = z_base
                p1x = x_base + inclinacao_vento * 0.3;    p1y = -altura_folha * 0.35;      p1z = z_base + inclinacao_vento_ponta * 0.2
                p2x = x_base + inclinacao_vento * 0.6;    p2y = -altura_folha * 0.7;       p2z = z_base + inclinacao_vento_ponta * 0.5
                p3x = x_base + inclinacao_vento;          p3y = -altura_folha;             p3z = z_base + inclinacao_vento_ponta
                # emite pares de vertices (segmentos retos) para montar a curva
                ponto_anterior = bezier_cubica_ponto(p0x, p0y, p0z, p1x, p1y, p1z, p2x, p2y, p2z, p3x, p3y, p3z, 0)
                for indice_segmento in range(1, numero_segmentos + 1):
                    ponto_atual = bezier_cubica_ponto(p0x, p0y, p0z, p1x, p1y, p1z, p2x, p2y, p2z, p3x, p3y, p3z, valores_t_precalculados[indice_segmento])
                    vertex(ponto_anterior[0], ponto_anterior[1], ponto_anterior[2])
                    vertex(ponto_atual[0],    ponto_atual[1],    ponto_atual[2])
                    ponto_anterior = ponto_atual
            end_shape()


# ------------------------- NEVE (atmosfera) --------------------------
neve_pos_x = [random.uniform(-220.0, 220.0) for _ in range(SNOW_N)]
neve_pos_y = [random.uniform(-420.0, 180.0) for _ in range(SNOW_N)]
neve_pos_z = [random.uniform(-260.0, 260.0) for _ in range(SNOW_N)]
neve_tamanho = [random.uniform(0.6, 2.2) for _ in range(SNOW_N)]

# =========================== CLASSES =================================
class Enemy:
    def __init__(self, lanes, hp, speed, kind):
        self.lanes = lanes
        self.kind = kind              # 'normal' / 'mini' / 'boss'
        self.x = sum(LANE_X[l] for l in lanes) / float(len(lanes))
        self.z = Z_SPAWN + random.uniform(0.0, 50.0)
        self.hp = hp
        self.maxhp = hp
        self.speed = speed
        if kind == 'boss':
            self.r = 40.0
        elif kind == 'mini':
            self.r = 28.0
        else:
            self.r = 16.0
        self.flash = 0
        self.phase = random.uniform(0.0, 6.28)
        self.alive = True


class Ball:
    def __init__(self, lane, elevacao_alvo, momento_nascimento):
        self.lane = lane
        self.x = LANE_X[lane]
        self.z0 = Z_CANNON
        self.alcance_z = remap(elevacao_alvo, -1.0, 1.0, R_MIN, R_MAX)
        self.altura_parabola = remap(elevacao_alvo, -1.0, 1.0, A_MIN, A_MAX)
        self.duracao_frames_tiro = int(remap(elevacao_alvo, -1.0, 1.0, T_MIN, T_MAX))
        self.momento_nascimento = momento_nascimento
        self.alive = True
        self.exploded = False
        self.bomb = False          # se True, vira BOMBA DE NEVE (mais dano/area)

    def pos(self, tempo_atual):
        progresso = (tempo_atual - self.momento_nascimento) / float(self.duracao_frames_tiro)
        if progresso > 1.0:
            progresso = 1.0
        z = self.z0 + self.alcance_z * progresso
        y = -4.0 * self.altura_parabola * progresso * (1.0 - progresso)
        return self.x, y, z, progresso


class Boom:
    def __init__(self, x, y, z, momento_nascimento, explosao_grande=False):
        self.x = x
        self.y = y
        self.z = z
        self.momento_nascimento = momento_nascimento
        self.explosao_grande = explosao_grande             # explosao grande (bomba de neve)


class Pickup:
    # Bolinha flutuante de poder (TIRO RAPIDO), deixada quando um MINI BOSS morre.
    def __init__(self, x, z, momento_nascimento):
        self.x = x
        self.z = z
        self.momento_nascimento = momento_nascimento
        self.alive = True


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        # volta para a TELA DE ESCOLHA DE MODO (antes do jogo)
        self.mode = 'normal'        # 'normal' / 'hard'  (destaque no menu)
        self._init_run()
        self.state = 'menu'         # 'menu'/'play'/'phase_clear'/'over'/'stopped'
        print("=== ESCOLHA O MODO ===")
        print("    Use as setas ESQUERDA e DIREITA para escolher.")
        print("    Aperte ENTER para confirmar.")

    def _init_run(self):
        # zera tudo de uma partida (usado pelo menu e ao iniciar um modo)
        self.pontos_controle = [0.0, 0.0, 0.0, 0.0, 0.0]   # comeca plano: canhoes na altura do castelo
        self.linha_selecionada = 2
        self.lives = START_LIVES
        self.score = 0
        self.enemies = []
        self.balls = []
        self.booms = []
        self.fire_timer = [i * 14 for i in range(5)]
        self.phase = 1
        self.wave = 0
        self.pending = []
        self.paused = False
        self.start_next_wave_pending = True
        self.wave_break_until = 90
        self.flash_castle = 0
        self.now = 0
        # ---- poderes especiais ----
        self.powers = {'fire': 0, 'bomb': 0}   # cargas acumuladas
        self.pickups = []                        # bolinhas no campo
        self.power_mode = None                   # None / 'fire' / 'bomb'
        self.fire_boost = [0, 0, 0, 0, 0]        # quadros restantes de tiro rapido
        self.bomb_charge = [0, 0, 0, 0, 0]       # tiros-bomba pendentes por canhao

    def start_game(self, mode):
        # inicia uma partida no modo escolhido
        self.mode = mode
        self._init_run()
        self.state = 'play'
        # Reseta a camera para a visao inicial do jogo
        camera(0, -290.0, 660.0, 0.0, -40.0, 40.0, 0.0, 1.0, 0.0)
        if mode == 'hard':
            print("=== MODO DIFICIL ===  so MINI BOSS e BOSS!")
        else:
            print("=== FASE 1 ===  |  Defenda o castelo (3 vidas)")

    def next_phase(self):
        self.phase += 1
        self.wave = 0
        self.enemies = []
        self.balls = []
        self.booms = []
        self.pending = []
        self.pickups = []
        self.power_mode = None
        self.start_next_wave_pending = True
        self.wave_break_until = self.now + 120
        self.state = 'play'
        print("=== FASE", self.phase, "===  inimigos mais numerosos e resistentes")

    def build_wave(self):
        self.wave += 1
        base = self.now + 30
        if self.mode == 'hard':
            self.build_wave_hard(base)
            return
        speed = 0.45 + self.wave * 0.05 + (self.phase - 1) * 0.05
        count = 10 + self.wave * 5 + (self.phase - 1) * 2

        lanes = [i % 5 for i in range(count)]
        random.shuffle(lanes)
        self.pending = []
        for i in range(count):
            spawn = base + i * random.randint(26, 44)
            lane = lanes[i]
            big = (random.random() < min(0.10 + 0.06 * self.wave, 0.45))
            hp = 2 if big else 1
            # Acelera os bonecos normais multiplicando a velocidade base por 1.6 (ou 1.35 se 'big')
            speed_adj = speed * (1.35 if big else 1.6) + random.uniform(-0.03, 0.05)
            self.pending.append({'t': spawn, 'lanes': [lane], 'hp': hp,
                                 'speed': speed_adj, 'kind': 'normal'})

        # MINI BOSS (2 linhas) em ondas impares >= 3
        if 3 <= self.wave < WAVES_PER_PHASE and self.wave % 2 == 1:
            k = random.randint(0, 3)
            mini_hp = 6 + self.phase * 2
            self.pending.append({'t': base + count * 9, 'lanes': [k, k + 1],
                                 'hp': mini_hp, 'speed': speed * 0.70, 'kind': 'mini'})

        # BOSS (3 linhas) na ultima onda
        if self.wave >= WAVES_PER_PHASE:
            k = random.randint(0, 2)
            boss_hp = 14 + self.phase * 4
            self.pending.append({'t': base + 50, 'lanes': [k, k + 1, k + 2],
                                 'hp': boss_hp, 'speed': speed * 0.55, 'kind': 'boss'})

        self.start_next_wave_pending = False
        print("== Fase", self.phase, "- Onda", self.wave, "de", WAVES_PER_PHASE,
              "-> inimigos:", count)

    def build_wave_hard(self, base):
        # MODO DIFICIL: so MINI BOSS e BOSS. Os minis entram primeiro (soltam
        # as bolinhas de TIRO RAPIDO) e o(s) boss(es) vem depois (dao BOMBA).
        speed = 0.40 + self.wave * 0.04 + (self.phase - 1) * 0.04
        self.pending = []
        n_mini = min(2 + self.wave, 6)
        for i in range(n_mini):
            k = random.randint(0, 3)              # ocupa k e k+1
            mini_hp = 5 + self.phase * 2 + self.wave
            spawn = base + i * random.randint(45, 75)
            self.pending.append({'t': spawn, 'lanes': [k, k + 1],
                                 'hp': mini_hp, 'speed': speed * 0.70,
                                 'kind': 'mini'})
        last_mini = base + n_mini * 75
        n_boss = 2 if self.wave >= WAVES_PER_PHASE else 1
        for i in range(n_boss):
            k = random.randint(0, 2)              # ocupa k, k+1 e k+2
            boss_hp = 12 + self.phase * 4 + self.wave * 2
            spawn = last_mini + 40 + i * 110
            self.pending.append({'t': spawn, 'lanes': [k, k + 1, k + 2],
                                 'hp': boss_hp, 'speed': speed * 0.55,
                                 'kind': 'boss'})
        self.start_next_wave_pending = False
        print("== [DIFICIL] Fase", self.phase, "- Onda", self.wave, "de",
              WAVES_PER_PHASE, "->", n_mini, "mini boss +", n_boss, "boss")

    def maybe_start_wave(self):
        if self.start_next_wave_pending and self.now >= self.wave_break_until:
            self.build_wave()

    def spawn_update(self):
        still = []
        for p in self.pending:
            if self.now >= p['t']:
                self.enemies.append(Enemy(p['lanes'], p['hp'], p['speed'], p['kind']))
            else:
                still.append(p)
        self.pending = still

    def fire_update(self):
        elevacoes = elevacoes_suavizadas(self.pontos_controle)
        for k in range(5):
            self.fire_timer[k] -= 1
            if self.fire_timer[k] <= 0:
                boosted = self.fire_boost[k] > 0
                self.fire_timer[k] = FIRE_BOOST_PERIOD if boosted else FIRE_PERIOD
                b = Ball(k, elevacoes[k], self.now)
                # se o canhao tem bomba armada, o PROXIMO tiro vira bomba
                if self.bomb_charge[k] > 0:
                    b.bomb = True
                    self.bomb_charge[k] -= 1
                self.balls.append(b)
            # tempo de tiro rapido escoa a cada quadro
            if self.fire_boost[k] > 0:
                self.fire_boost[k] -= 1

    def kill_enemy(self, en):
        en.alive = False
        pts = {'boss': 12, 'mini': 5}.get(en.kind, 1)
        self.score += pts
        print("Pontos:", self.score)
        if en.kind == 'mini':
            # deixa uma bolinha de poder flutuante onde o mini boss morreu
            self.pickups.append(Pickup(en.x, en.z, self.now))
            print(">> MINI BOSS derrotado! Pegue a bolinha (tecla G)"
                  " p/ ganhar +1 TIRO RAPIDO")
        elif en.kind == 'boss':
            # boss da o poder direto
            self.powers['bomb'] += 1
            print(">> BOSS derrotado! +1 BOMBA DE NEVE (tecla U). Total:",
                  self.powers['bomb'])

    def explode_at(self, ball, x, y, z):
        ball.exploded = True
        ball.alive = False
        is_bomb = ball.bomb
        self.booms.append(Boom(x, y, z, self.now, explosao_grande=is_bomb))
        dmg = BOMB_DMG if is_bomb else 1
        splash = BOMB_EXPLOSION_RAD if is_bomb else EXPLOSION_RAD
        # bomba atinge tambem as linhas vizinhas; tiro normal so a linha do canhao
        if is_bomb:
            hit_lanes = {ball.lane - 1, ball.lane, ball.lane + 1}
        else:
            hit_lanes = {ball.lane}
        for en in self.enemies:
            if not en.alive:
                continue
            if any(l in hit_lanes for l in en.lanes) and abs(en.z - z) < splash:
                en.hp -= dmg
                en.flash = 8
                if en.hp <= 0:
                    self.kill_enemy(en)

    def balls_update(self):
        for b in self.balls:
            x, y, z, t = b.pos(self.now)
            if t >= 1.0 and not b.exploded:
                self.explode_at(b, x, 0.0, z)
        self.balls = [b for b in self.balls if b.alive]

    def enemies_update(self):
        for en in self.enemies:
            if not en.alive:
                continue
            en.z -= en.speed
            if en.flash > 0:
                en.flash -= 1
            if en.z <= Z_HIT:
                en.alive = False
                self.lives -= 1
                self.flash_castle = 12
        self.enemies = [en for en in self.enemies if en.alive]

    def booms_cleanup(self):
        self.booms = [b for b in self.booms
                      if (self.now - b.momento_nascimento) <= (26 if b.explosao_grande else 22)]

    def pickups_update(self):
        self.pickups = [p for p in self.pickups
                        if p.alive and (self.now - p.momento_nascimento) <= PICKUP_TTL]

    # ----- controle dos poderes -----
    def collect_pickups(self):
        got = 0
        for p in self.pickups:
            if p.alive:
                p.alive = False
                self.powers['fire'] += 1
                got += 1
        if got:
            self.pickups = [p for p in self.pickups if p.alive]
            print(">> Pegou", got, "bolinha(s)! TIRO RAPIDO total:",
                  self.powers['fire'])
        else:
            print("   (nenhuma bolinha no campo agora)")

    def start_power(self, kind):
        if self.powers.get(kind, 0) <= 0:
            nome = "TIRO RAPIDO" if kind == 'fire' else "BOMBA DE NEVE"
            print("   (sem carga de", nome, "disponivel)")
            return
        self.power_mode = kind
        nome = "TIRO RAPIDO" if kind == 'fire' else "BOMBA DE NEVE"
        tecla = 'B' if kind == 'fire' else 'U'
        print(">>", nome + ": mova ate o canhao (A/D ou 1-5) e", tecla,
              "p/ confirmar | canhao atual:", self.linha_selecionada + 1)

    def confirm_power(self):
        kind = self.power_mode
        lane = self.linha_selecionada
        if kind is None or self.powers.get(kind, 0) <= 0:
            self.power_mode = None
            return
        self.powers[kind] -= 1
        if kind == 'fire':
            self.fire_boost[lane] += FIRE_BOOST_FRAMES
            print(">> TIRO RAPIDO ativado no canhao", lane + 1)
        else:
            self.bomb_charge[lane] += 1
            print(">> BOMBA DE NEVE armada no canhao", lane + 1, "(proximo tiro)")
        self.power_mode = None

    def update(self, now):
        self.now = now
        self.maybe_start_wave()
        self.spawn_update()
        self.fire_update()
        self.balls_update()
        self.enemies_update()
        self.booms_cleanup()
        self.pickups_update()
        if self.flash_castle > 0:
            self.flash_castle -= 1
        if self.lives <= 0:
            self.state = 'over'
            self.power_mode = None
            print("### GAME OVER - castelo caiu na fase", self.phase,
                  "| pontos:", self.score, "(R reinicia) ###")
            return
        self.check_wave()

    def check_wave(self):
        if (not self.enemies and not self.pending
                and not self.start_next_wave_pending):
            if self.wave >= WAVES_PER_PHASE:
                self.state = 'phase_clear'
                self.power_mode = None
                print("*** FASE", self.phase, "COMPLETA! ***")
                print("    S / ESPACO / ENTER = jogar a proxima fase")
                print("    N = parar por aqui")
            else:
                self.start_next_wave_pending = True
                self.wave_break_until = self.now + 150
                print("-- Onda", self.wave, "completa! Prepare-se...")


game = Game()

# ============================ SETUP / DRAW ===========================
def setup():
    create_canvas(CANVAS_W, CANVAS_H, WEBGL)
    # VISAO ORIGINAL: de frente para os canhoes (olho em +z, olhando -z)
    camera(0, -290.0, 660.0, 0.0, -40.0, 40.0, 0.0, 1.0, 0.0)
    _init_grass()   # gera as posicoes das folhas de grama
    print("DEFESA DO CASTELO | A/D linha, W/S sobe/desce, 1-5 linha,",
          "G pega bolinha, B tiro rapido, U bomba de neve,",
          "P pausa, R reinicia | arraste o mouse para girar")


def draw():
    # GAME OVER em tela cheia (com botao de jogar de novo)
    if game.state == 'over':
        draw_game_over_screen()
        return

    # TELA INICIAL de escolha de modo (antes de ver o cenario)
    if game.state == 'menu':
        draw_menu_screen()
        return

    background(200, 245, 255)
    ambient_light(150)
    directional_light(255, 255, 255, 0.4, 0.6, -0.5)
    orbit_control()                      # camera volta a girar com o mouse

    if game.state == 'play' and not game.paused:
        game.update(frame_count)
    else:
        game.now = frame_count

    draw_terrain()
    draw_grass()     # grama animada na pista
    draw_castle()
    desenha_sol_nuvem_arco_iris()
    desenha_neve_atmosferica()

    draw_cannons()
    draw_reticles()
    draw_power_target()                  # marca o canhao alvo na escolha de poder
    draw_bspline()
    desenha_inimigos()
    desenha_bolinhas_poder()                       # bolinhas flutuantes de poder
    desenha_bolas_canhao()
    desenha_explosoes()

    draw_hud()                           # coracoes + poderes + marcadores + telas


def key_pressed():
    k = key
    try:
        kl = k.lower()
    except AttributeError:
        return

    if game.state == 'menu':
        if k == 'ArrowLeft':
            game.mode = 'normal'
        elif k == 'ArrowRight':
            game.mode = 'hard'
        elif kl == 'enter':
            game.start_game(game.mode)
        return

    if game.state == 'phase_clear':
        if kl in ('s', 'y', ' ', 'enter'):
            game.next_phase()
        elif kl == 'n':
            game.state = 'stopped'
            print("Voce parou na fase", game.phase, "| pontos:", game.score,
                  "(R recomeca)")
        elif kl == 'r':
            game.reset()
        return

    if game.state in ('over', 'stopped'):
        if kl == 'r':
            game.reset()
        return

    # --- escolha de poder ativa ---
    # B/U confirmam o poder no canhao SELECIONADO; a outra tecla (ou ESC)
    # cancela. Qualquer outra tecla cai nos controles normais logo abaixo,
    # entao mover/subir/baixar a lane NUNCA trava durante a escolha.
    if game.power_mode is not None:
        if (kl == 'b' and game.power_mode == 'fire') or \
           (kl == 'u' and game.power_mode == 'bomb'):
            game.confirm_power()
            return
        if kl in ('b', 'u', 'escape'):
            game.power_mode = None
            print("   escolha cancelada")
            return
        # senao: nao retorna; segue para o controle normal de lane/altura

    if kl == 'a' or k == 'ArrowLeft':
        game.linha_selecionada = max(0, game.linha_selecionada - 1)
    elif kl == 'd' or k == 'ArrowRight':
        game.linha_selecionada = min(4, game.linha_selecionada + 1)
    elif kl == 'w' or k == 'ArrowUp':
        game.pontos_controle[game.linha_selecionada] = constrain(game.pontos_controle[game.linha_selecionada] + CANON_ANG, -1.0, 1.0)
    elif kl == 's' or k == 'ArrowDown':
        game.pontos_controle[game.linha_selecionada] = constrain(game.pontos_controle[game.linha_selecionada] - CANON_ANG, -1.0, 1.0)
    elif kl in ('1', '2', '3', '4', '5'):
        game.linha_selecionada = int(kl) - 1
    elif kl == 'g':
        game.collect_pickups()
    elif kl == 'b':
        game.start_power('fire')
    elif kl == 'u':
        game.start_power('bomb')
    elif kl == 'p':
        game.paused = not game.paused
    elif kl == 'r':
        game.reset()

keyPressed = key_pressed


def mouse_pressed():
    # na tela de GAME OVER, clicar no botao verde recomeca a partida
    if game.state == 'over' and mouse_sobre_botao_reiniciar():
        game.reset()

mousePressed = mouse_pressed

# ======================= DESENHOS DO JOGO ============================
_COLUNAS_TERRENO = None


def _colunas_terreno():
    # colunas x da malha: amostra uniforme + as posicoes EXATAS das lanes
    # (assim a superficie desenhada bate com a altura usada pelo canhao)
    global _COLUNAS_TERRENO
    if _COLUNAS_TERRENO is None:
        s = set()
        n = 24
        for i in range(n + 1):
            s.add(round(lerp(-360.0, 360.0, i / float(n)), 3))
        for lx in LANE_X:
            s.add(float(lx))
        _COLUNAS_TERRENO = sorted(s)
    return _COLUNAS_TERRENO


def draw_terrain():
    z0, z1 = -440.0, Z_SPAWN + 60.0
    nz = 26
    xs = _colunas_terreno()
    no_stroke()
    for iz in range(nz):
        za = lerp(z0, z1, iz / float(nz))
        zb = lerp(z0, z1, (iz + 1) / float(nz))
        begin_shape(QUAD_STRIP)
        for x in xs:
            # Como o terreno é sempre plano, a cor base é estática
            br, bg, bb = 120, 205, 130
            # marcador da lane: apenas troca de cor no trecho dela (sem overlay)
            m = constrain(1.0 - abs(x - LANE_X[game.linha_selecionada]) / 38.0, 0.0, 1.0) * 0.6
            fill(br + (250 - br) * m, bg + (238 - bg) * m, bb + (120 - bb) * m)
            vertex(x, 0.0, za)
            vertex(x, 0.0, zb)
        end_shape()


def draw_castle():
    push()
    translate(0, -34, 0)
    castelo()
    pop()


def draw_cannons():
    elevacoes = elevacoes_suavizadas(game.pontos_controle)
    for k in range(5):
        draw_cannon(LANE_X[k], elevacoes[k], k)


def draw_cannon(x, e, k):
    push()
    translate(x, -13.0, Z_CANNON)
    no_stroke()
    # base do canhao muda de cor quando tem poder ativo/armado naquela linha
    if game.bomb_charge[k] > 0:
        fill('#7FD4FF')          # azul: bomba de neve armada
    elif game.fire_boost[k] > 0:
        fill('#FF6A00')          # laranja forte: tiro rapido ativo
    else:
        fill('#FFB800')
    sphere(15.0)
    theta = remap(e, -1.0, 1.0, math.radians(12), math.radians(58))
    rotate_x(HALF_PI + theta)
    translate(0, 15.0, 0)
    fill('#C74726')
    cylinder(7.5, 30.0)
    push()
    translate(0, 15.0, 0)
    fill('#450000')
    cylinder(7.8, 4.0)
    pop()
    pop()


def draw_reticles():
    elevacoes = elevacoes_suavizadas(game.pontos_controle)
    rad = 16.0
    segs = 30
    no_fill()
    stroke(255, 70, 70, 200)
    stroke_weight(2)
    for k in range(5):
        cxr = LANE_X[k]
        zl = Z_CANNON + remap(elevacoes[k], -1.0, 1.0, R_MIN, R_MAX)
        # monta o anel ponto a ponto, cada ponto pousado na superficie do
        # terreno -> acompanha a deformacao (sem partes cobertas/descobertas)
        prev = None
        for i in range(segs + 1):
            a = i * (TWO_PI / segs)
            px = cxr + rad * math.cos(a)
            pz = zl + rad * math.sin(a)
            py = -1.5
            if prev is not None:
                line(prev[0], prev[1], prev[2], px, py, pz)
            prev = (px, py, pz)


def draw_power_target():
    # marcador pulsante sobre o canhao alvo enquanto escolhe o poder
    if game.power_mode is None:
        return
    k = game.linha_selecionada
    x = LANE_X[k]
    yb = -13.0
    col = (255, 150, 40) if game.power_mode == 'fire' else (120, 210, 255)
    pulse = 0.6 + 0.4 * math.sin(game.now * 0.25)
    push()
    no_stroke()
    translate(x, yb - 30.0, Z_CANNON)
    fill(col[0], col[1], col[2], int(200 * pulse))
    sphere(6.0 + 4.0 * pulse)
    push()
    translate(0, -14.0, 0)
    rotate_x(PI)
    fill(col[0], col[1], col[2], 220)
    cone(5.0, -12.0)
    pop()
    pop()


def draw_bspline():
    ctrl = []
    for k in range(5):
        ctrl.append((LANE_X[k], altura_canhao_de_controle(game.pontos_controle[k]), Z_CTRL))
    pts = bspline_points(ctrl, 12)

    push()
    no_stroke()
    fill(120, 220, 255, 120)
    begin_shape(QUAD_STRIP)
    for p in pts:
        vertex(p[0], p[1], p[2])
        vertex(p[0], p[1] + 16.0, p[2])
    end_shape()
    pop()

    push()
    stroke(0, 150, 210)
    stroke_weight(2)
    for i in range(len(pts) - 1):
        a = pts[i]
        b = pts[i + 1]
        line(a[0], a[1], a[2], b[0], b[1], b[2])
    pop()

    for k in range(5):
        cx = LANE_X[k]
        cy = altura_canhao_de_controle(game.pontos_controle[k])
        cz = Z_CTRL
        push()
        stroke(255, 255, 255, 130)
        stroke_weight(1)
        line(cx, cy, cz, cx, -13.0, Z_CANNON)
        pop()
        push()
        no_stroke()
        translate(cx, cy, cz)
        if k == game.linha_selecionada:
            fill(255, 210, 40)
            sphere(8.0)
            push()
            translate(0, -16.0, 0)
            fill(255, 160, 0)
            rotate_x(PI)
            cone(5.0, -12.0)
            pop()
        else:
            fill(60, 150, 230)
            sphere(5.5)
        pop()


def desenha_inimigos():
    for en in game.enemies:
        desenha_inimigo(en)


def desenha_inimigo(e):
    base_y = 0.0
    push()
    translate(e.x, base_y, e.z)
    escala_tamanho = e.r / 16.0
    escala_largura = 1.0 + 0.22 * (len(e.lanes) - 1)
    scale(escala_tamanho * escala_largura, escala_tamanho, escala_tamanho)
    rotate_y(PI)
    oscilacao_andar = math.sin(frame_count * 0.18 + e.phase) * 3.0
    rotate_z(math.radians(oscilacao_andar * 0.4))
    no_stroke()

    if e.flash > 0:
        cor_corpo = (255, 150, 150)
    elif e.kind == 'boss':
        cor_corpo = (205, 230, 255)
    elif e.kind == 'mini':
        cor_corpo = (235, 245, 255)
    else:
        cor_corpo = (255, 255, 255)

    fill(cor_corpo[0], cor_corpo[1], cor_corpo[2])
    push()
    translate(0, -13.0, 0)
    sphere(13.0)
    pop()
    fill(20)
    for i in range(3):
        pos_y_botao = -9.0 - i * 4.0
        distancia_centro_botao = 169.0 - (pos_y_botao + 13.0) ** 2
        pos_z_botao = (distancia_centro_botao if distancia_centro_botao > 0 else 0.0) ** 0.5
        push()
        translate(0, pos_y_botao, pos_z_botao)
        sphere(1.0)
        pop()
    fill(cor_corpo[0], cor_corpo[1], cor_corpo[2])
    push()
    translate(0, -30.0, 0)
    sphere(8.0)
    pop()
    fill(10)
    push()
    translate(-2.6, -32.0, 6.8)
    sphere(1.3)
    pop()
    push()
    translate(2.6, -32.0, 6.8)
    sphere(1.3)
    pop()
    fill(255, 120, 0)
    push()
    translate(0, -29.5, 7.0)
    rotate_x(-HALF_PI)
    cone(1.8, -10.0)
    pop()
    fill(0)
    for i in range(-3, 4):
        push()
        translate(i * 1.0, -26.0 - (i * i) / 12.0, 7.2)
        sphere(0.35)
        pop()
    fill(15)
    push()
    translate(0, -37.0, 0)
    cylinder(9.0, 1.2)
    translate(0, -4.5, 0)
    cylinder(5.5, 7.0)
    pop()
    if e.kind == 'boss':
        fill(220, 180, 30)
    else:
        fill(150, 20, 20)
    push()
    translate(0, -22.0, 0)
    rotate_x(HALF_PI)
    torus(8.5, 1.8)
    pop()
    stroke(110, 60, 40)
    stroke_weight(1.2)
    line(-10.0, -15.0, 0, -20.0, -22.0, 0)
    line(10.0, -15.0, 0, 20.0, -22.0, 0)
    no_stroke()
    if e.kind in ('mini', 'boss'):
        fill(255, 215, 0)
        push()
        translate(0, -47.0, 0)
        sphere(2.5 if e.kind == 'mini' else 3.6)
        pop()
    pop()

    if e.kind in ('mini', 'boss'):
        desenha_barra_vida(e, base_y)


def desenha_barra_vida(e, base_y):
    largura_barra = e.r * 1.7
    pos_y_barra = base_y - (e.r * 2.7 + 16.0)
    push()
    no_stroke()
    translate(e.x, pos_y_barra, e.z)
    fill(25, 25, 30)
    box(largura_barra + 3.0, 6.0, 3.0)
    porcentagem_vida = constrain(e.hp / float(e.maxhp), 0.0, 1.0)
    push()
    translate(-(largura_barra - largura_barra * porcentagem_vida) / 2.0, 0, 2.0)
    fill(90, 220, 100)
    box(largura_barra * porcentagem_vida, 4.5, 3.0)
    pop()
    pop()


def desenha_bolinhas_poder():
    # bolinha flutuante deixada pelo mini boss; pisca quando vai sumir
    for p in game.pickups:
        idade_frames = game.now - p.momento_nascimento
        progresso_vida = constrain(idade_frames / float(PICKUP_TTL), 0.0, 1.0)
        oscilacao_y = math.sin(game.now * 0.12 + p.x) * 6.0
        altura_base = 0.0
        y = altura_base - 34.0 + oscilacao_y
        alpha = 255 if progresso_vida < 0.7 else int(255 * (1.0 - (progresso_vida - 0.7) / 0.3))
        if alpha < 0:
            alpha = 0
        push()
        translate(p.x, y, p.z)
        no_stroke()
        # halo
        fill(255, 225, 120, alpha // 4)
        sphere(13.0)
        # nucleo (laranja = tiro rapido)
        fill(255, 165, 30, alpha)
        sphere(7.0)
        # setinha indicando "pegue (G)"
        fill(255, 245, 200, alpha)
        push()
        translate(0, -14.0, 0)
        rotate_x(PI)
        cone(4.0, -9.0)
        pop()
        pop()


def desenha_bolas_canhao():
    no_stroke()
    for b in game.balls:
        x, y, z, progresso = b.pos(game.now)
        push()
        translate(x, y, z)
        if b.bomb:
            fill(150, 215, 255)
            sphere(11.0)
            fill(255)
            sphere(6.0)
        else:
            fill(255)
            sphere(7.0)
        pop()


def desenha_explosoes():
    for b in game.booms:
        desenha_explosao(b)


def desenha_explosao(b):
    duracao = 26.0 if b.explosao_grande else 22.0
    idade_frames = game.now - b.momento_nascimento
    progresso_animacao = idade_frames / duracao
    if progresso_animacao > 1.0:
        progresso_animacao = 1.0
    escala = 1.9 if b.explosao_grande else 1.0
    quantidade_particulas = 18 if b.explosao_grande else 12
    push()
    translate(b.x, b.y, b.z)
    no_stroke()
    alpha = int(220 * (1.0 - progresso_animacao))
    if alpha < 0:
        alpha = 0
    for i in range(quantidade_particulas):
        angulo = i * (TWO_PI / quantidade_particulas)
        raio_particula = idade_frames * 1.5 * escala
        px = math.cos(angulo) * raio_particula
        pz = math.sin(angulo) * raio_particula
        py = -abs(math.sin(i * 1.3)) * idade_frames * 0.9
        tamanho_esfera = 3.5 * escala * (1.0 - progresso_animacao)
        if tamanho_esfera < 0.5:
            tamanho_esfera = 0.5
        if b.explosao_grande:
            fill(190, 230, 255, alpha)
        else:
            fill(255, 255, 255, alpha)
        push()
        translate(px, py, pz)
        sphere(tamanho_esfera)
        pop()
    pop()

# ============================== HUD ==================================
#  Montado com primitivas 3D (sphere/box) que o ambiente desenha de fato.
#  Fica perto do topo da visao; com o mouse (orbit) ele acompanha a cena.

def contorno_coracao(passos_resolucao):
    # contorno do coracao a partir de uma CURVA (equacao parametrica),
    # normalizado para ~[-1, 1]
    pontos_contorno = []
    for i in range(passos_resolucao):
        angulo = (i / float(passos_resolucao)) * TWO_PI
        pos_x = 16.0 * (math.sin(angulo) ** 3)
        pos_y = -(13.0 * math.cos(angulo) - 5.0 * math.cos(2.0 * angulo)
               - 2.0 * math.cos(3.0 * angulo) - math.cos(4.0 * angulo))
        pontos_contorno.append((pos_x / 16.0, pos_y / 16.0))
    return pontos_contorno


def desenha_coracao(centro_x, centro_y, centro_z, tamanho, preenchido):
    # Coracao como SUPERFICIE/MALHA: o contorno vem da curva acima e e
    # "inflado" ao longo de z (loft), gerando uma malha 3D suave em vez de
    # juntar esferas/cubos. Cada anel e um QUAD_STRIP da malha.
    if preenchido:
        r, g, b = 235.0, 45.0, 65.0
    else:
        r, g, b = 70.0, 72.0, 82.0
    resolucao_contorno = 36          # resolucao ao redor do contorno (curva)
    aneis_volume = 11          # aneis do loft (da o volume em z)
    espessura_z = tamanho * 0.6
    pontos_contorno = contorno_coracao(resolucao_contorno)
    push()
    translate(centro_x, centro_y, centro_z)
    no_stroke()
    for j in range(aneis_volume):
        angulo_anel_atual = (j / float(aneis_volume)) * PI
        angulo_proximo_anel = ((j + 1) / float(aneis_volume)) * PI
        escala_anel_atual = math.sin(angulo_anel_atual)          # escala do anel (0 nas pontas, 1 no meio)
        escala_proximo_anel = math.sin(angulo_proximo_anel)
        pos_z_anel_atual = -espessura_z * math.cos(angulo_anel_atual)  # avanca de -espessura_z (tras) a +espessura_z (frente)
        pos_z_proximo_anel = -espessura_z * math.cos(angulo_proximo_anel)
        fator_sombreado = 0.55 + 0.45 * math.sin((angulo_anel_atual + angulo_proximo_anel) * 0.5)   # sombreado suave
        fill(r * fator_sombreado, g * fator_sombreado, b * fator_sombreado)
        begin_shape(QUAD_STRIP)
        for i in range(resolucao_contorno + 1):
            pos_x_normalizado, pos_y_normalizado = pontos_contorno[i % resolucao_contorno]
            x = pos_x_normalizado * tamanho
            y = pos_y_normalizado * tamanho
            vertex(x * escala_anel_atual, y * escala_anel_atual, pos_z_anel_atual)
            vertex(x * escala_proximo_anel, y * escala_proximo_anel, pos_z_proximo_anel)
        end_shape()
    pop()


_SEG = {
    0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc',
    5: 'afgcd', 6: 'afgecd', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg',
}


def segmento_horizontal(x, y, comprimento, espessura):
    push()
    translate(x, y, 0)
    box(comprimento, espessura, espessura)
    pop()


def segmento_vertical(x, y, comprimento, espessura):
    push()
    translate(x, y, 0)
    box(espessura, comprimento, espessura)
    pop()


def desenha_digito(digito, meia_largura, meia_altura, espessura):
    segmentos = _SEG.get(digito, '')
    if 'a' in segmentos:
        segmento_horizontal(0.0, -meia_altura, 2 * meia_largura, espessura)
    if 'g' in segmentos:
        segmento_horizontal(0.0, 0.0, 2 * meia_largura, espessura)
    if 'd' in segmentos:
        segmento_horizontal(0.0, meia_altura, 2 * meia_largura, espessura)
    if 'f' in segmentos:
        segmento_vertical(-meia_largura, -meia_altura * 0.5, meia_altura, espessura)
    if 'b' in segmentos:
        segmento_vertical(meia_largura, -meia_altura * 0.5, meia_altura, espessura)
    if 'e' in segmentos:
        segmento_vertical(-meia_largura, meia_altura * 0.5, meia_altura, espessura)
    if 'c' in segmentos:
        segmento_vertical(meia_largura, meia_altura * 0.5, meia_altura, espessura)


def desenha_numero(valor, centro_x, centro_y, centro_z, cor_r, cor_g, cor_b):
    texto_numero = str(int(valor))
    meia_largura, meia_altura, espessura, espacamento = 6.0, 10.0, 3.0, 5.0
    passo_x = 2 * meia_largura + espacamento
    largura_total = len(texto_numero) * passo_x - espacamento
    pos_x = centro_x - largura_total * 0.5 + meia_largura
    no_stroke()
    fill(cor_r, cor_g, cor_b)
    for caractere in texto_numero:
        push()
        translate(pos_x, centro_y, centro_z)
        desenha_digito(int(caractere), meia_largura, meia_altura, espessura)
        pop()
        pos_x += passo_x


def draw_power_icon(kind, cx, cy, cz, big=False):
    # icone de poder no HUD. 'fire' = bola laranja com setinha; 'bomb' = bola azul
    push()
    translate(cx, cy, cz)
    no_stroke()
    base = 9.0 if big else 7.0
    if kind == 'fire':
        fill(255, 165, 30)
        sphere(base)
        fill(255, 240, 180)
        push()
        translate(0, -11.0, 0)
        rotate_x(PI)
        cone(4.0, -8.0)
        pop()
    else:
        fill(120, 210, 255)
        sphere(base)
        fill(255, 255, 255)
        push()
        translate(0, 0, base * 0.7)
        sphere(base * 0.4)
        pop()
    pop()


def draw_hud():
    n = START_LIVES
    sz = 13.0
    spacing = 38.0
    # Desloca os corações em +9.0 para centralizar com os poderes (cujo centro é 9.0)
    x0 = -((n - 1) * spacing) / 2.0 + 9.0

    # vidas (coracoes) no alto
    for i in range(n):
        desenha_coracao(x0 + i * spacing, HUD_Y, HUD_Z, sz, i < game.lives)

    # numeros acima das vidas: FASE (azul, esquerda) e ONDA (dourado, direita)
    ny = HUD_Y - 46.0
    desenha_numero(game.phase, -46.0, ny, HUD_Z, 95, 175, 255)   # fase (azul)
    desenha_numero(game.wave, 46.0, ny, HUD_Z, 255, 205, 55)     # onda (dourado)

    # ---- PODERES (logo ABAIXO dos coracoes) ----
    py = HUD_Y + 42.0
    fire_big = (game.power_mode == 'fire')
    bomb_big = (game.power_mode == 'bomb')
    # grupo esquerdo: TIRO RAPIDO (laranja)
    draw_power_icon('fire', -56.0, py, HUD_Z, big=fire_big)
    desenha_numero(game.powers['fire'], -30.0, py, HUD_Z, 255, 180, 60)
    # grupo direito: BOMBA DE NEVE (azul)
    desenha_numero(game.powers['bomb'], 48.0, py, HUD_Z, 150, 210, 255)
    draw_power_icon('bomb', 74.0, py, HUD_Z, big=bomb_big)

    # durante a escolha, mostra o canhao alvo (lane selecionada) piscando
    if game.power_mode is not None and (game.now // 12) % 2 == 0:
        col = (255, 180, 60) if game.power_mode == 'fire' else (150, 210, 255)
        desenha_numero(game.linha_selecionada + 1, 0.0, py + 36.0, HUD_Z, *col)

    # pausa (dois tracos)
    if game.paused and game.state == 'play':
        fill(255, 255, 255, 230)
        push()
        translate(-8.0, HUD_Y + 86.0, HUD_Z)
        box(6, 22, 6)
        pop()
        push()
        translate(8.0, HUD_Y + 86.0, HUD_Z)
        box(6, 22, 6)
        pop()

    if game.state == 'phase_clear':
        draw_panel_phase_clear()
    elif game.state == 'stopped':
        draw_panel_stopped()

# ----------------------- TITULO (fonte vetorial) ----------------------
# text() nao renderiza no modo WEBGL sem uma fonte carregada via loadFont(),
# entao o titulo e desenhado como tracos (linhas), igual a logo CRF() abaixo.
# Cobre so as letras usadas no titulo do jogo, numa grade 5x7 (x:0-4, y:0-6).
_VEC_FONT = {
    'A': [[(0, 6), (2, 0), (4, 6)], [(1, 3.6), (3, 3.6)]],
    'C': [[(3.6, 0.6), (1.2, 0), (0, 1.6), (0, 4.4), (1.2, 6), (3.6, 5.4)]],
    'D': [[(0, 0), (0, 6)],
          [(0, 0), (2, 0), (3.6, 1.2), (4, 3), (3.6, 4.8), (2, 6), (0, 6)]],
    'E': [[(0, 0), (0, 6)], [(0, 0), (3, 0)], [(0, 3), (2.4, 3)], [(0, 6), (3, 6)]],
    'F': [[(0, 0), (0, 6)], [(0, 0), (3, 0)], [(0, 3), (2.4, 3)]],
    'G': [[(3.6, 0.6), (1.2, 0), (0, 1.6), (0, 4.4), (1.2, 6), (3.6, 5.4),
           (3.6, 3.4), (2.0, 3.4)]],
    'L': [[(0, 0), (0, 6)], [(0, 6), (3, 6)]],
    'O': [[(2, 0), (3.8, 1.2), (4, 3), (3.8, 4.8), (2, 6), (0.2, 4.8),
           (0, 3), (0.2, 1.2), (2, 0)]],
    'S': [[(4, 1.2), (2, 0), (0.2, 1), (0, 2.2), (2, 3), (4, 3.8),
           (3.8, 5), (2, 6), (0, 5)]],
    'T': [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
}

LETTER_W = 4.0   # largura da grade (x: 0..4)
LETTER_H = 6.0   # altura da grade (y: 0..6)


def desenha_letra_vetorial(caractere, centro_x, centro_y, centro_z, escala):
    tracos_letra = _VEC_FONT.get(caractere)
    if not tracos_letra:
        return
    meia_largura_grade = LETTER_W / 2.0
    meia_altura_grade = LETTER_H / 2.0
    for poligono in tracos_letra:
        for i in range(len(poligono) - 1):
            x0, y0 = poligono[i]
            x1, y1 = poligono[i + 1]
            line(centro_x + (x0 - meia_largura_grade) * escala, centro_y + (y0 - meia_altura_grade) * escala, centro_z,
                 centro_x + (x1 - meia_largura_grade) * escala, centro_y + (y1 - meia_altura_grade) * escala, centro_z)


def desenha_texto_vetorial(texto, centro_x, centro_y, centro_z, escala, espacamento=2.2):
    # 'texto' deve estar em MAIUSCULAS (so as letras do dict acima sao suportadas)
    passo_x = (LETTER_W + espacamento) * escala
    largura_total = len(texto) * passo_x - espacamento * escala
    pos_x = centro_x - largura_total / 2.0 + (LETTER_W * escala) / 2.0
    for caractere in texto:
        if caractere != ' ':
            desenha_letra_vetorial(caractere, pos_x, centro_y, centro_z, escala)
        pos_x += passo_x

def draw_menu_snowman(is_evil):
    push()
    scale(9.0)  # Zoom enorme nos bonecos
    # corpo
    fill(255)
    push()
    translate(0, -13.0, 0)
    sphere(13.0)
    pop()
    # botoes
    fill(20)
    for i in range(3):
        ybotao = -9.0 - i * 4.0
        d = 169.0 - (ybotao + 13.0) ** 2
        zbotao = (d if d > 0 else 0.0) ** 0.5
        push()
        translate(0, ybotao, zbotao)
        sphere(1.0)
        pop()
    # cabeca
    fill(255)
    push()
    translate(0, -30.0, 0)
    sphere(8.0)
    pop()
    # olhos e sobrancelhas
    if is_evil:
        fill(255, 0, 0)
        push()
        translate(-2.6, -32.0, 6.8)
        sphere(1.3)
        pop()
        push()
        translate(2.6, -32.0, 6.8)
        sphere(1.3)
        pop()
        # sobrancelhas de mau
        stroke(0)
        stroke_weight(2)
        line(-4.5, -34.5, 7.5, -1.0, -33.0, 7.5)
        line(4.5, -34.5, 7.5, 1.0, -33.0, 7.5)
        no_stroke()
    else:
        fill(10)
        push()
        translate(-2.6, -32.0, 6.8)
        sphere(1.3)
        pop()
        push()
        translate(2.6, -32.0, 6.8)
        sphere(1.3)
        pop()

    # nariz
    fill(255, 120, 0)
    push()
    translate(0, -29.5, 7.0)
    rotate_x(-HALF_PI)
    cone(1.8, -10.0)
    pop()

    # boca
    fill(0)
    for i in range(-3, 4):
        push()
        x_boca = i * 1.0
        if is_evil:
            # Centro mais alto (-27.5), bordas mais baixas (-26.6) = Frown (triste/bravo)
            y_boca = -27.5 + (i * i) / 10.0
        else:
            # Centro mais baixo (-26.0), bordas mais altas (-26.75) = Smile (sorrindo)
            y_boca = -26.0 - (i * i) / 12.0
        
        # Projetar exatamente na superficie da cabeca (centro y=-30, raio=8)
        delta_y_cabeca = y_boca - (-30.0)
        z_quadrado = 64.0 - x_boca**2 - delta_y_cabeca**2
        z_boca = (z_quadrado**0.5 if z_quadrado > 0 else 7.0) + 0.2  # +0.2 para saltar da neve
        
        translate(x_boca, y_boca, z_boca)
        sphere(0.35)
        pop()

    # chapeu
    fill(15)
    push()
    translate(0, -37.0, 0)
    cylinder(9.0, 1.2)
    translate(0, -4.5, 0)
    cylinder(5.5, 7.0)
    pop()

    # cachecol
    if is_evil:
        fill(150, 20, 20)
    else:
        fill(20, 150, 255)
    push()
    translate(0, -22.0, 0)
    rotate_x(HALF_PI)
    torus(8.5, 1.8)
    pop()

    # bracos
    stroke(110, 60, 40)
    stroke_weight(1.2)
    if is_evil:
        line(-10.0, -15.0, 0, -20.0, -28.0, 0) # bracos pra cima
        line(10.0, -15.0, 0, 20.0, -28.0, 0)
    else:
        line(-10.0, -15.0, 0, -20.0, -10.0, 0) # bracos abertos
        line(10.0, -15.0, 0, 20.0, -10.0, 0)
    no_stroke()
    pop()


def draw_menu_screen():
    # Tela cheia de escolha de modo, desenhada em 2D (antes do cenario 3D).
    background(18, 22, 42)
    eye_z = (CANVAS_H / 2.0) / math.tan(math.radians(30))
    camera(0, 0, eye_z, 0, 0, 0, 0, 1, 0)
    ambient_light(255)
    no_stroke()

    # TITULO (linhas vetoriais, ja que text() nao funciona no modo WEBGL)
    push()
    no_fill()
    title_scale = 10.0
    # contorno grosso azul-gelo escuro (da contraste com o fundo)
    stroke(20, 70, 120, 220)
    stroke_weight(9)
    desenha_texto_vetorial("DEFESA DO CASTELO DE GELO", 0, -280, 0, title_scale)
    # traco fino claro por cima
    stroke(190, 230, 255, 255)
    stroke_weight(4)
    desenha_texto_vetorial("DEFESA DO CASTELO DE GELO", 0, -280, 0, title_scale)
    pop()
    # NEVE decorativa caindo no fundo
    fill(255, 255, 255, 160)
    for i in range(30):
        sx = math.sin(i * 3.7 + frame_count * 0.008) * 500
        sy = ((frame_count * 0.8 + i * 47) % 900) - 450
        push()
        translate(sx, sy, -20.0)
        sphere(3.0 + (i % 3))
        pop()

    # OPCAO 1 - NORMAL (esquerda) - Boneco de neve fofinho
    push()
    no_stroke()
    translate(-160.0, 200.0, 0.0) # Base do desenho eh a argola
    
    # Boneco (Pula se estiver selecionado)
    push()
    y_off = 15.0 * abs(math.sin(frame_count * 0.15)) if game.mode == 'normal' else 0.0
    translate(0, -y_off, 0)
    draw_menu_snowman(is_evil=False)
    pop()

    # Anel no chao (sempre pulsa)
    push()
    rotate_x(HALF_PI)
    no_fill()
    stroke(180, 255, 200, int(140 + 80 * math.sin(frame_count * 0.12)))
    stroke_weight(6)
    torus(140, 3)
    pop()
    no_stroke()
    pop()

    # OPCAO 2 - DIFICIL (direita) - Boneco de neve malvado
    push()
    no_stroke()
    translate(160.0, 200.0, 0.0) # Base do desenho eh a argola
    
    # Boneco (Pula se estiver selecionado)
    push()
    y_off = 15.0 * abs(math.sin(frame_count * 0.15)) if game.mode == 'hard' else 0.0
    translate(0, -y_off, 0)
    draw_menu_snowman(is_evil=True)
    pop()

    # Anel no chao (sempre pulsa)
    push()
    rotate_x(HALF_PI)
    no_fill()
    stroke(255, 180, 160, int(140 + 80 * math.sin(frame_count * 0.12)))
    stroke_weight(6)
    torus(140, 3)
    pop()
    no_stroke()
    pop()


def draw_panel_phase_clear():
    push()
    no_stroke()
    translate(0, OVR_Y, OVR_Z)
    fill(20, 38, 72, 230)
    box(380, 150, 8)
    # CONTINUAR: esfera verde (S / ESPACO / ENTER) a esquerda
    push()
    translate(-85, 0, 10)
    fill(70, 205, 100)
    sphere(34)
    pop()
    # PARAR: X vermelho (N) a direita
    push()
    translate(85, 0, 12)
    fill(235, 70, 70)
    push()
    rotate_z(math.radians(45))
    box(74, 14, 8)
    pop()
    push()
    rotate_z(math.radians(-45))
    box(74, 14, 8)
    pop()
    pop()
    pop()


def draw_panel_stopped():
    push()
    no_stroke()
    translate(0, OVR_Y, OVR_Z)
    fill(10, 30, 22, 210)
    box(380, 150, 8)
    # taca dourada simples
    fill(255, 210, 60)
    push()
    translate(0, -10, 12)
    sphere(34)
    pop()
    push()
    translate(0, 30, 12)
    box(16, 34, 10)
    pop()
    push()
    translate(0, 52, 12)
    box(64, 12, 10)
    pop()
    pop()


# ---------------------- TELA CHEIA DE GAME OVER ----------------------
def mouse_sobre_botao_reiniciar():
    # mouse sobre o botao "jogar de novo"? (coordenadas de tela, centro = 0,0)
    if game.state != 'over':
        return False
    mx = mouse_x - CANVAS_W / 2.0
    my = mouse_y - CANVAS_H / 2.0
    return abs(mx) <= BTN_W / 2.0 and abs(my - BTN_CY) <= BTN_H / 2.0


def draw_game_over_screen():
    background(28, 8, 10)                  # limpa cor + profundidade
    # camera padrao -> desenha em pixels, com o centro da tela em (0,0)
    eye_z = (CANVAS_H / 2.0) / math.tan(math.radians(30))
    camera(0, 0, eye_z, 0, 0, 0, 0, 1, 0)
    ambient_light(255)                     # ilumina o overlay por igual
    no_stroke()

    # X grande vermelho (o castelo caiu)
    push()
    translate(0.0, -250.0, 0.0)
    fill(230, 60, 60)
    push()
    rotate_z(math.radians(45))
    box(360, 46, 12)
    pop()
    push()
    rotate_z(math.radians(-45))
    box(360, 46, 12)
    pop()
    pop()

    # pontuacao final em dourado (numeros 7-seg, maiores)
    push()
    translate(0.0, -40.0, 0.0)
    scale(2.6)
    desenha_numero(game.score, 0.0, 0.0, 0.0, 255, 210, 70)
    pop()

    # botao "JOGAR DE NOVO": retangulo verde + triangulo de play branco
    hover = mouse_sobre_botao_reiniciar()
    push()
    translate(0.0, BTN_CY, 0.0)
    fill(80, 220, 120) if hover else fill(55, 170, 90)
    box(BTN_W, BTN_H, 14)
    fill(255)
    begin_shape()
    vertex(-46.0, -54.0, 16.0)
    vertex(-46.0, 54.0, 16.0)
    vertex(52.0, 0.0, 16.0)
    end_shape()
    pop()

# ======================= CENARIO (reaproveitado) =====================
def desenha_neve_atmosferica():
    no_stroke()
    fill(255, 255, 255, 200)
    push()
    translate(0, 25.0, -200.0)
    for i in range(SNOW_N):
        neve_pos_y[i] += 0.6
        if neve_pos_y[i] > 20.0:
            neve_pos_y[i] = random.uniform(-220.0, -260.0)
            neve_pos_x[i] = random.uniform(-220.0, 220.0)
        push()
        translate(neve_pos_x[i], neve_pos_y[i], neve_pos_z[i])
        sphere(neve_tamanho[i])
        pop()
    pop()


def desenha_sol_nuvem_arco_iris():
    push()
    translate(150.0, -220.0, -200.0)
    no_stroke()
    fill(255, 230, 0)
    sphere(30.0)
    for i in range(12):
        rotate_z(PI / 6)
        push()
        translate(30.0, 0, 0)
        rotate_z(HALF_PI)
        fill('orange')
        cone(6.0, -28.0)
        pop()
    pop()
    push()
    translate(-150.0, -250.0, -200.0)
    scale(3.0)
    for desloc_x in [-10.0, 10.0]:
        push()
        translate(desloc_x, 20, 0)
        no_stroke()
        fill(250, 255, 255)
        nuvem_central = 5.0
        nuvem_lateral = 3.5
        push()
        translate(0, 0, 0)
        sphere(nuvem_central)
        pop()
        push()
        translate(-nuvem_central, 0, 0)
        sphere(nuvem_lateral)
        pop()
        push()
        translate(nuvem_central, 0, 0)
        sphere(nuvem_lateral)
        pop()
        pop()
    push()
    translate(0, 20, 0)
    no_fill()
    stroke_weight(3)
    cores = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#8B00FF"]
    for i, c in enumerate(cores):
        stroke(c)
        arc(0, 0, 25.0 - i * 2.0, 25.0 - i * 2.0, PI, TWO_PI)
    pop()
    pop()


def castelo():
    push()
    translate(0, 25.0, -200.0)
    scale(3.0)
    # --- PAREDES com textura de tijolos de gelo ---
    # Parede traseira (z = -50)
    push()
    translate(0, -10.0, -50.0)
    muro_de_gelo(100.0, 25.0, 2.0)
    pop()
    # Parede frontal (z = +50)
    push()
    translate(0, -10.0, 50.0)
    muro_de_gelo(100.0, 25.0, 2.0)
    pop()
    # Parede esquerda (x = -50)
    push()
    translate(-50.0, -10.0, 0)
    rotate_y(HALF_PI)
    muro_de_gelo(100.0, 25.0, 2.0)
    pop()
    # Parede direita (x = +50)
    push()
    translate(50.0, -10.0, 0)
    rotate_y(HALF_PI)
    muro_de_gelo(100.0, 25.0, 2.0)
    pop()
    portao()
    torre(0, -25, 0, 22, 50)
    torre(30, -25, 0, 15, 35)
    torre(-30, -25, 0, 15, 35)
    for x, z in [(-50, -50), (50, -50), (-50, 50), (50, 50)]:
        push()
        translate(x, -15.0, z)
        # Torres dos cantos com textura de gelo
        cilindro_de_gelo(8, 30, segmentos=10, linhas_blocos=8)
        translate(0, -22.5, 0)
        stroke(255, 100)
        fill(180, 210, 240)
        cone(10, -15, 8)
        pop()
    bandeira_flamengo()
    pop()


def portao():
    no_stroke()
    fill(139, 69, 19)
    push()
    translate(0, 2.5, 50.0)   # deslocado para baixo ate o chao da parede
    push()
    translate(0, -6.0, 0)
    box(16.0, 12.0, 3.0)
    pop()
    push()
    translate(0, -12.0, 0)
    rotate_x(HALF_PI)
    cylinder(8.0, 3.0)
    pop()
    fill(0)
    push()
    translate(0, -10.0, 1.6)
    box(0.2, 20.0, 0.2)
    pop()
    push()
    translate(-2.5, -10.0, 2.3)
    sphere(0.8)
    pop()
    push()
    translate(2.5, -10.0, 2.3)
    sphere(0.8)
    pop()
    pop()


def torre(x, y, z, raio_torre, altura_torre):
    push()
    translate(x, y, z)
    # Corpo da torre com textura de tijolos de gelo
    segmentos_cilindro = max(8, int(raio_torre * 0.7))
    linhas_tijolos = max(4, int(altura_torre / 3.5))
    cilindro_de_gelo(raio_torre, altura_torre, segmentos=segmentos_cilindro, linhas_blocos=linhas_tijolos)
    translate(0, -(altura_torre / 2 + 10), 0)
    stroke(255, 100)
    fill(180, 210, 240)
    cone(raio_torre * 1.35, -30.0, 12)
    pop()


def bandeira_flamengo():
    larg_band = 15.0
    alt_band = 10.0
    segmentos = 5
    listras = 8
    # Uma bandeira animada
    push()
    translate(0, -75.0, 0)
    
    desenha_mastro()

    tempo_anim = frame_count * 0.1
    amplitude_onda = 1.8
    frequencia_onda = 0.5
    largura_bandeira = 18.0
    altura_bandeira = 12.0
    y_topo = -20.0
    qtd_listras = 8
    altura_listra = altura_bandeira / qtd_listras

    largura_fundo_logo = largura_bandeira * (4.0 / qtd_listras)
    altura_fundo_logo = 4 * altura_listra
    num_segmentos = 15

    no_stroke()
    desenha_fundo_vermelho_logo(largura_fundo_logo, altura_fundo_logo, y_topo, num_segmentos, tempo_anim, amplitude_onda, frequencia_onda)
    desenha_listras_bandeira(qtd_listras, altura_listra, largura_fundo_logo, y_topo, largura_bandeira, num_segmentos, tempo_anim, amplitude_onda, frequencia_onda)
    desenha_logo_crf(largura_fundo_logo, y_topo, altura_fundo_logo, tempo_anim, amplitude_onda, frequencia_onda)

    pop()
    pop()


def desenha_mastro():
    fill(50)
    no_stroke()
    push()
    translate(0, -10.0, 0)
    cylinder(0.5, 20.0)
    pop()


def desenha_fundo_vermelho_logo(largura_fundo_logo, altura_fundo_logo, y_topo, num_segmentos, tempo_anim, amplitude_onda, frequencia_onda):
    fill(200, 0, 0)
    num_segmentos_quadro = max(2, int(num_segmentos * 0.45) + 1)
    begin_shape(QUAD_STRIP)
    for i in range(num_segmentos_quadro + 1):
        rx = i * (largura_fundo_logo / num_segmentos_quadro)
        z_o = sin(tempo_anim - rx * frequencia_onda) * amplitude_onda
        vertex(rx, y_topo, z_o)
        vertex(rx, y_topo + altura_fundo_logo, z_o)
    end_shape()


def desenha_listras_bandeira(qtd_listras, altura_listra, largura_fundo_logo, y_topo, largura_bandeira, num_segmentos, tempo_anim, amplitude_onda, frequencia_onda):
    for j in range(qtd_listras):
        fill(200, 0, 0) if j % 2 == 0 else fill(20, 20, 20)
        yt = y_topo + j * altura_listra
        yb = yt + altura_listra
        sx = largura_fundo_logo if j < 4 else 0.0
        begin_shape(QUAD_STRIP)
        z0 = sin(tempo_anim - sx * frequencia_onda) * amplitude_onda
        vertex(sx, yt, z0)
        vertex(sx, yb, z0)
        for i in range(1, num_segmentos + 1):
            rx = i * (largura_bandeira / num_segmentos)
            if rx > sx:
                z_o = sin(tempo_anim - rx * frequencia_onda) * amplitude_onda
                vertex(rx, yt, z_o)
                vertex(rx, yb, z_o)
        end_shape()


def desenha_logo_crf(largura_fundo_logo, y_topo, altura_fundo_logo, tempo_anim, amplitude_onda, frequencia_onda):
    centro_x = largura_fundo_logo / 2.0
    centro_y = y_topo + altura_fundo_logo / 2.0
    push()
    translate(centro_x, centro_y + 0.7, 0)
    stroke(255)
    stroke_weight(0.8)

    def traco(x1, y1, x2, y2):
        desenha_traco_ondulado(x1, y1, x2, y2, centro_x, tempo_anim, frequencia_onda, amplitude_onda)
    traco(2.4, -2.4, -2.0, -2.4)
    traco(-2.0, -2.4, -2.0, 2.4)
    traco(-2.0, 2.4, 2.4, 2.4)
    traco(-0.8, -2.0, -0.8, 2.0)
    traco(-0.8, -2.0, 1.2, -2.0)
    traco(1.2, -2.0, 1.2, 0.0)
    traco(1.2, 0.0, -0.8, 0.0)
    traco(-0.8, 0.0, 1.2, 2.0)
    traco(0.4, -2.0, 0.4, 1.6)
    traco(0.4, -2.0, 2.4, -2.0)
    traco(0.4, 0.0, 1.8, 0.0)
    pop()


def desenha_traco_ondulado(x1, y1, x2, y2, centro_x, tempo_anim, frequencia_onda, amplitude_onda):
    z1 = sin(tempo_anim - (centro_x + x1) * frequencia_onda) * amplitude_onda + 0.3
    z2 = sin(tempo_anim - (centro_x + x2) * frequencia_onda) * amplitude_onda + 0.3
    line(x1, y1, z1, x2, y2, z2)