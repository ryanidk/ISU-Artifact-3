import pygame
import math
from random import randint
import asyncio

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
FPS = 60
FONT = pygame.font.Font(None, 36)
LARGE_FONT = pygame.font.Font(None, 50)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
YELLOW = (255, 255, 0)
DARK_GREEN = (34, 139, 34)
PURPLE = (128, 0, 128)
BROWN = (165, 42, 42)
UI_BG = (50, 50, 50)
UI_HIGHLIGHT = (70, 70, 70)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("tower defense isu")
clock = pygame.time.Clock()

MAPS = {
    "Easy": [(100, 100), (400, 100), (400, 300), (600, 300), (600, 500), (1000, 500)],
    "Medium": [(50, 400), (300, 400), (300, 200), (600, 200), (600, 600), (1100, 600)],
    "Hard": [(150, 100), (150, 500), (400, 500), (400, 300), (800, 300), (800, 700)],
    "Very Hard": [(50, 50), (50, 750), (300, 750), (300, 50), (600, 50), (600, 750), (1100, 750)],
    "Bruh": [(50, 400), (200, 100), (400, 700), (600, 300), (800, 600), (1100, 400)]
}

coins = 300
lives = 20
wave = 1
game_speed = 1
game_running = False
placing_tower = False
selected_tower_type = None
towers = []
enemies = []
spawning = False
enemy_spawn_count = 0
selected_map = "Easy"
PATH = MAPS[selected_map]

TOWER_TYPES = {
    "basic": {"cost": 50, "damage": 15, "range": 150, "attack_speed": 1, "color": BLUE},
    "far": {"cost": 120, "damage": 40, "range": 300, "attack_speed": 0.5, "color": RED},
    "fast": {"cost": 80, "damage": 8, "range": 100, "attack_speed": 3, "color": GREEN},
    "bomb": {"cost": 200, "damage": 70, "range": 200, "attack_speed": 0.8, "color": BLACK},
    "slow": {"cost": 150, "damage": 10, "range": 150, "attack_speed": 1.5, "color": (100, 200, 255), "slow_effect": 0.5},
    "lgtn": {"cost": 400, "damage": 30, "range": 250, "attack_speed": 1.4, "color": YELLOW, "chain": 3}
}

ENEMY_TYPES = [
    {"speed": 2, "health": 50, "reward": 10, "color": RED, "min_wave": 1},
    {"speed": 3, "health": 75, "reward": 20, "color": YELLOW, "min_wave": 1},
    {"speed": 1, "health": 150, "reward": 30, "color": DARK_GREEN, "min_wave": 2},
    {"speed": 3, "health": 200, "reward": 35, "color": BLUE, "min_wave": 3},
    {"speed": 3, "health": 300, "reward": 40, "color": BLACK, "min_wave": 3},
    {"speed": 3.5, "health": 400, "reward": 50, "color": PURPLE, "min_wave": 4},
    {"speed": 3.5, "health": 600, "reward": 60, "color": BROWN, "min_wave": 5},
    {"speed": 4.2, "health": 800, "reward": 80, "color": GREEN, "min_wave": 5},
    {"speed": 5, "health": 950, "reward": 95, "color": RED, "min_wave": 6},
]


class Enemy:
    def __init__(self, enemy_type):
        self.path = PATH
        self.current_point = 0
        self.x, self.y = self.path[0]
        self.base_speed = enemy_type["speed"]
        self.speed = self.base_speed
        self.health = enemy_type["health"]
        self.max_health = self.health
        self.reward = enemy_type["reward"]
        self.color = enemy_type["color"]
        self.slow_duration = 0

    def move(self):
        if self.slow_duration > 0:
            self.speed = self.base_speed * 0.5
            self.slow_duration -= 1
        else:
            self.speed = self.base_speed

        if self.current_point < len(self.path) - 1:
            target_x, target_y = self.path[self.current_point + 1]
            direction = (target_x - self.x, target_y - self.y)
            distance = math.sqrt(direction[0] ** 2 + direction[1] ** 2)
            if distance > self.speed:
                self.x += self.speed * direction[0] / distance
                self.y += self.speed * direction[1] / distance
            else:
                self.current_point += 1

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 15)
        pygame.draw.rect(screen, RED, (self.x - 20, self.y - 30, 40, 5))
        pygame.draw.rect(screen, GREEN, (self.x - 20, self.y -
                         30, 40 * (self.health / self.max_health), 5))


class Tower:
    def __init__(self, x, y, tower_type):
        self.x = x
        self.y = y
        self.tower_type = tower_type
        self.range = tower_type["range"]
        self.damage = tower_type["damage"]
        self.attack_speed = tower_type["attack_speed"]
        self.color = tower_type["color"]
        self.last_attack_time = 0
        self.level = 1
        self.targets = []

    def attack(self, enemies, current_time):
        reward = 0
        if current_time - self.last_attack_time >= 1000 / self.attack_speed:
            targets = []
            for enemy in enemies:
                distance = math.sqrt((self.x - enemy.x) **
                                     2 + (self.y - enemy.y) ** 2)
                if distance <= self.range:
                    targets.append(enemy)

            if targets:
                if "chain" in self.tower_type:
                    chain_count = min(len(targets), self.tower_type["chain"])
                    for i in range(chain_count):
                        targets[i].health -= self.damage
                        if targets[i].health <= 0:
                            reward += targets[i].reward
                elif "slow_effect" in self.tower_type:
                    for target in targets:
                        target.slow_duration = 60
                        target.health -= self.damage
                        if target.health <= 0:
                            reward += target.reward
                else:
                    targets[0].health -= self.damage
                    if targets[0].health <= 0:
                        reward += targets[0].reward

                self.last_attack_time = current_time
                self.targets = targets[:self.tower_type.get("chain", 1)]
        return reward

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), 20)
        pygame.draw.circle(screen, GRAY, (self.x, self.y), self.range, 1)

        for target in self.targets:
            pygame.draw.line(screen, self.color,
                             (self.x, self.y), (target.x, target.y), 2)


def get_available_enemies(wave):
    return [enemy for enemy in ENEMY_TYPES if enemy["min_wave"] <= wave]


def scale_enemy_stats(enemy, wave):
    scaled = enemy.copy()
    scaled["health"] *= 1 + (wave * 0.175)
    scaled["speed"] *= 1 + (wave * 0.1)
    scaled["reward"] *= 1 - (wave * 0.075)
    return scaled


def draw_ui():
    pygame.draw.rect(
        screen, UI_BG, (0, SCREEN_HEIGHT - 150, SCREEN_WIDTH, 150))
    buttons = {}

    buttons["start"] = pygame.draw.rect(
        screen, UI_HIGHLIGHT, (50, SCREEN_HEIGHT - 120, 150, 60))
    start_text = FONT.render("new wave", True, WHITE)
    screen.blit(start_text, (buttons["start"].x + 25, buttons["start"].y + 15))

    x_offset = 250
    for tower_name, tower_data in TOWER_TYPES.items():
        button = pygame.draw.rect(
            screen, UI_HIGHLIGHT, (x_offset, SCREEN_HEIGHT - 120, 120, 60))
        buttons[tower_name.lower()] = button

        text = FONT.render(f"{tower_name}", True, WHITE)
        cost_text = FONT.render(f"${tower_data['cost']}", True, WHITE)
        screen.blit(text, (button.x + 10, button.y + 10))
        screen.blit(cost_text, (button.x + 10, button.y + 35))
        x_offset += 140

    coins_text = FONT.render(f"mony: {coins}", True, RED)
    lives_text = FONT.render(f"life: {lives}", True, GREEN)
    wave_text = FONT.render(f"wave: {wave}", True, BLUE)

    screen.blit(coins_text, (SCREEN_WIDTH - 200, 20))
    screen.blit(lives_text, (SCREEN_WIDTH - 200, 50))
    screen.blit(wave_text, (SCREEN_WIDTH - 200, 80))

    return buttons


async def main():
    global coins, lives, wave, game_running, enemies, spawning, enemy_spawn_count, towers
    global selected_tower_type, selected_map, PATH

    running = True
    spawn_timer = 0

    while running:
        screen.fill(WHITE)
        dt = clock.tick(FPS) * game_speed

        for i in range(len(PATH) - 1):
            pygame.draw.line(screen, BLACK, PATH[i], PATH[i + 1], 5)

        buttons = draw_ui()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                for button_name, button in buttons.items():
                    if button.collidepoint(mouse_pos):
                        if button_name == "start" and not game_running and not spawning:
                            game_running = True
                            spawning = True
                            enemy_spawn_count = wave * 8
                        elif button_name in [t.lower() for t in TOWER_TYPES.keys()]:
                            tower_type = TOWER_TYPES[button_name]
                            if coins >= tower_type["cost"]:
                                selected_tower_type = button_name
                                placing_tower = True

                if placing_tower and mouse_pos[1] < SCREEN_HEIGHT - 150:
                    tower_type = TOWER_TYPES[selected_tower_type]
                    towers.append(
                        Tower(mouse_pos[0], mouse_pos[1], tower_type))
                    coins -= tower_type["cost"]
                    placing_tower = False
                    selected_tower_type = None

        current_time = pygame.time.get_ticks()

        if spawning and enemy_spawn_count > 0 and current_time - spawn_timer > 1000:
            available_enemies = get_available_enemies(wave)
            if available_enemies:
                enemy_type = scale_enemy_stats(
                    available_enemies[randint(0, len(available_enemies)-1)], wave)
                enemies.append(Enemy(enemy_type))
                spawn_timer = current_time
                enemy_spawn_count -= 1

        for enemy in enemies[:]:
            enemy.move()
            if enemy.current_point >= len(PATH) - 1:
                enemies.remove(enemy)
                lives -= 1
            elif enemy.health <= 0:
                enemies.remove(enemy)
                coins += enemy.reward

        for tower in towers:
            coins += tower.attack(enemies, current_time)
        for tower in towers:
            tower.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)

        if game_running and spawning and enemy_spawn_count == 0 and not enemies:
            spawning = False
            game_running = False
            wave += 1

            completion_text = LARGE_FONT.render(
                f"wave {wave-1} complete", True, GREEN)
            screen.blit(completion_text, (SCREEN_WIDTH //
                                          2 - 150, SCREEN_HEIGHT//2 - 100))

            if wave == 3:
                selected_map = "Medium"
                PATH = MAPS[selected_map]
            elif wave == 5:
                selected_map = "Hard"
                PATH = MAPS[selected_map]
            elif wave == 7:
                selected_map = "Very Hard"
                PATH = MAPS[selected_map]
            elif wave == 10:
                selected_map = "Bruh"
                PATH = MAPS[selected_map]

        if lives <= 0:
            game_over_text = LARGE_FONT.render("Game Over!", True, RED)
            screen.blit(game_over_text, (SCREEN_WIDTH //
                        2 - 100, SCREEN_HEIGHT//2 - 25))
            game_running = False
            spawning = False

        pygame.display.flip()

    pygame.quit()


asyncio.run(main())
