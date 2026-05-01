"""
Roguelike Survival Game - Mobile Version
使用 Kivy 框架开发，支持触屏控制
"""

import math
import random
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.properties import NumericProperty, BooleanProperty, ListProperty

# 设置窗口大小（移动端适配）
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
Window.size = (SCREEN_WIDTH, SCREEN_HEIGHT)

# 颜色定义
WHITE = (1, 1, 1, 1)
BLACK = (0, 0, 0, 1)
RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)
BLUE = (0, 0, 1, 1)
YELLOW = (1, 1, 0, 1)
ORANGE = (1, 0.5, 0, 1)
PURPLE = (0.5, 0, 1, 1)
CYAN = (0, 1, 1, 1)
GRAY = (0.5, 0.5, 0.5, 1)


def get_spawn_interval(game_time):
    if game_time < 30:
        return 4.0
    elif game_time < 60:
        return 3.5
    elif game_time < 120:
        return 3.0
    elif game_time < 180:
        return 2.5
    else:
        return 2.0


def get_stat_bounds(game_time):
    if game_time < 60:
        return 30, 60, 0.2, 0.3, 0, 2
    elif game_time < 120:
        return 80, 160, 0.25, 0.4, 2, 6
    elif game_time < 180:
        return 150, 300, 0.3, 0.5, 4, 10
    elif game_time < 300:
        return 250, 500, 0.35, 0.6, 6, 14
    elif game_time < 480:
        return 400, 800, 0.4, 0.7, 10, 20
    else:
        return 600 + (game_time - 480) * 1.5, 1200 + (game_time - 480) * 3, 0.45, 0.8, 12, 25


def get_exp_multiplier(game_time):
    if game_time < 30:
        return 1.0
    elif game_time < 60:
        return 1.5
    elif game_time < 120:
        return 2.0
    elif game_time < 180:
        return 3.0
    elif game_time < 300:
        return 4.0
    else:
        return 5.0


class JoystickWidget(Widget):
    """触屏摇杆控件"""
    stick_radius = NumericProperty(40)
    base_radius = NumericProperty(80)
    is_active = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (200, 200)
        self.center_x = 120
        self.center_y = 120
        self.base_center_x = self.center_x
        self.base_center_y = self.center_y
        self.stick_pos_x = self.center_x
        self.stick_pos_y = self.center_y
        self.touch_id = None
        self.dx = 0
        self.dy = 0
        
        # 定时重绘
        Clock.schedule_interval(self.draw, 1/60)
    
    def draw(self, dt):
        self.canvas.clear()
        with self.canvas:
            # 底座
            Color(0.3, 0.3, 0.3, 0.5)
            Ellipse(
                pos=(self.base_center_x - self.base_radius, 
                     self.base_center_y - self.base_radius),
                size=(self.base_radius * 2, self.base_radius * 2)
            )
            
            # 摇杆
            Color(0.6, 0.6, 0.6, 0.8)
            Ellipse(
                pos=(self.stick_pos_x - self.stick_radius,
                     self.stick_pos_y - self.stick_radius),
                size=(self.stick_radius * 2, self.stick_radius * 2)
            )
        
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not self.touch_id:
            self.touch_id = touch.uid
            self.is_active = True
            self._update_stick(touch.x, touch.y)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if touch.uid == self.touch_id:
            self._update_stick(touch.x, touch.y)
            return True
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        if touch.uid == self.touch_id:
            self.touch_id = None
            self.is_active = False
            self.stick_pos_x = self.base_center_x
            self.stick_pos_y = self.base_center_y
            self.dx = 0
            self.dy = 0
            return True
        return super().on_touch_up(touch)
    
    def _update_stick(self, x, y):
        dx = x - self.base_center_x
        dy = y - self.base_center_y
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist > self.base_radius:
            ratio = self.base_radius / dist
            self.stick_pos_x = self.base_center_x + dx * ratio
            self.stick_pos_y = self.base_center_y + dy * ratio
            self.dx = dx * ratio / self.base_radius
            self.dy = dy * ratio / self.base_radius
        else:
            self.stick_pos_x = x
            self.stick_pos_y = y
            self.dx = dx / self.base_radius
            self.dy = dy / self.base_radius


class Player:
    """玩家类"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 3.0
        self.hp = 100
        self.max_hp = 100
        self.exp = 0
        self.exp_to_level = 100
        self.level = 1
        
        self.weapon = "sword"
        self.weapon_level = 1
        self.attack_cooldown = 0
        self.attack_range = 80
        self.attack_damage = 30
        self.facing_angle = 0
        self.is_attacking = False
        self.attack_timer = 0
        self.sword_hit_monsters = []
        
        self.skills = {}
        self.skill_levels = {}
        self.skill_cooldowns = {}
        self.radius = 20
    
    def update(self, dx, dy, dt):
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed
        
        if 50 < new_x < SCREEN_WIDTH - 50:
            self.x = new_x
        if 50 < new_y < SCREEN_HEIGHT - 50:
            self.y = new_y
        
        if dx != 0 or dy != 0:
            self.facing_angle = math.degrees(math.atan2(dy, dx))
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        
        if self.is_attacking:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.is_attacking = False
        
        for skill in self.skill_cooldowns:
            if self.skill_cooldowns[skill] > 0:
                self.skill_cooldowns[skill] -= dt
    
    def attack(self):
        if self.attack_cooldown <= 0:
            self.is_attacking = True
            self.attack_timer = 0.2
            self.sword_hit_monsters = []
            
            if self.weapon == "sword":
                self.attack_cooldown = 0.5
            elif self.weapon == "staff":
                self.attack_cooldown = 0.4
            elif self.weapon == "gun":
                if self.weapon_level >= 10:
                    self.attack_cooldown = 0.5
                elif 6 <= self.weapon_level < 10:
                    self.attack_cooldown = 1.0
                elif self.weapon_level == 4:
                    self.attack_cooldown = 0.25
                else:
                    self.attack_cooldown = 0.8
            elif self.weapon == "zeus_spear":
                self.attack_cooldown = 0.8
            
            return True
        return False
    
    def get_attack_damage(self):
        if self.weapon == "sword":
            return self.attack_damage + self.weapon_level * 15
        elif self.weapon == "staff":
            return self.attack_damage + self.weapon_level * 8
        elif self.weapon == "gun":
            if self.weapon_level >= 10:
                return 250
            elif self.weapon_level >= 6:
                return (self.attack_damage * 2 + self.weapon_level * 15) * 5
            elif self.weapon_level >= 4:
                return int((self.attack_damage * 2 + self.weapon_level * 15) * 0.7)
            else:
                return self.attack_damage * 2 + self.weapon_level * 15
        elif self.weapon == "zeus_spear":
            if self.weapon_level >= 10:
                return self.attack_damage * 3 + self.weapon_level * 20
            elif self.weapon_level >= 6:
                return self.attack_damage * 2 + self.weapon_level * 15
            elif self.weapon_level >= 4:
                return self.attack_damage * 1.5 + self.weapon_level * 10
            else:
                return self.attack_damage + self.weapon_level * 8
        return self.attack_damage
    
    def gain_exp(self, amount, multiplier):
        actual_exp = int(amount * multiplier)
        self.exp += actual_exp
        return self.exp >= self.exp_to_level
    
    def level_up(self):
        self.exp -= self.exp_to_level
        self.level += 1
        
        if self.level <= 5:
            growth_rate = 1.3
        elif self.level <= 10:
            growth_rate = 1.2
        elif self.level <= 15:
            growth_rate = 1.15
        else:
            growth_rate = 1.1
        
        self.exp_to_level = int(self.exp_to_level * growth_rate)
    
    def upgrade_weapon(self):
        self.weapon_level += 1
        if self.weapon == "sword":
            self.attack_damage += 10
            self.attack_range += 5
        elif self.weapon == "staff":
            self.attack_damage += 12
        elif self.weapon == "gun":
            self.attack_damage += 15
    
    def change_weapon(self, new_weapon, level=1):
        self.weapon = new_weapon
        self.weapon_level = level
        if new_weapon == "sword":
            self.attack_damage = 30 + (level - 1) * 15
            self.attack_range = 80 + (level - 1) * 5
            self.attack_cooldown = 0
        elif new_weapon == "staff":
            self.attack_damage = 35 + (level - 1) * 12
            self.attack_range = 300
            self.attack_cooldown = 0
        elif new_weapon == "gun":
            self.attack_damage = 40 + (level - 1) * 15
            self.attack_range = 500
            self.attack_cooldown = 0
    
    def unlock_skill(self, skill_name):
        if skill_name not in self.skills:
            self.skills[skill_name] = True
            self.skill_levels[skill_name] = 1
            self.skill_cooldowns[skill_name] = 0
        else:
            self.skill_levels[skill_name] += 1


class Monster:
    """怪物类"""
    def __init__(self, x, y, hp, speed, defense):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.base_speed = speed
        self.speed = speed
        self.defense = defense
        self.radius = 15 + int(min(30, max(8, hp / 13)))
        self.frozen_timer = 0
        self.slow_timer = 0
        self.alive = True
    
    def update(self, player_x, player_y, dt):
        if self.frozen_timer > 0:
            self.frozen_timer -= dt
            if self.frozen_timer <= 0:
                self.slow_timer = 3.0
        
        if self.slow_timer > 0:
            self.slow_timer -= dt
            self.speed = self.base_speed * 0.5
            if self.slow_timer <= 0:
                self.speed = self.base_speed
        
        dx = player_x - self.x
        dy = player_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0 and self.frozen_timer <= 0:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
    
    def take_damage(self, damage):
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False
    
    def apply_freeze(self, freeze_duration, slow_duration):
        self.frozen_timer = freeze_duration
        self.slow_timer = slow_duration


class Boss:
    """Boss 类"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp = 500
        self.max_hp = 500
        self.speed = 0.4
        self.radius = 50
        self.alive = True
        self.attack_timer = 0
        self.phase = 1
    
    def update(self, player_x, player_y, dt):
        dx = player_x - self.x
        dy = player_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
        
        self.attack_timer -= dt
    
    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False
            return True
        if self.hp < 250 and self.phase == 1:
            self.phase = 2
            self.speed = 0.6
        return False


class Projectile:
    """投射物类"""
    def __init__(self, x, y, angle, speed, damage, is_player, p_type="normal"):
        self.x = x
        self.y = y
        self.angle = math.radians(angle)
        self.speed = speed
        self.damage = damage
        self.is_player = is_player
        self.p_type = p_type
        self.alive = True
        self.radius = 10
        self.lifetime = 3.0
    
    def update(self, dt):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.lifetime -= dt
        if self.lifetime <= 0 or self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.alive = False


class UpgradeCard:
    """升级卡片"""
    def __init__(self, card_type, title, description):
        self.card_type = card_type
        self.title = title
        self.description = description


class UpgradeModal(ModalView):
    """升级选择弹窗"""
    def __init__(self, cards, game_widget, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.9, 0.6)
        self.cards = cards
        self.game_widget = game_widget
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        title = Label(text="选择升级", font_size=30, size_hint_y=0.15)
        layout.add_widget(title)
        
        cards_layout = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=0.7)
        
        for i, card in enumerate(self.cards):
            btn = Button(
                text=f"{card.title}\n\n{card.description}",
                font_size=16,
                size_hint_x=0.33
            )
            btn.bind(on_press=lambda instance, idx=i: self.select_upgrade(idx))
            cards_layout.add_widget(btn)
        
        layout.add_widget(cards_layout)
        self.add_widget(layout)
    
    def select_upgrade(self, card_index):
        self.game_widget.apply_upgrade(self.cards[card_index])
        self.dismiss()


class GameWidget(Widget):
    """游戏主控件"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = "playing"  # playing, levelup, gameover
        self.player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.monsters = []
        self.projectiles = []
        self.boss = None
        self.game_time = 0
        self.last_spawn = 0
        self.score = 0
        self.boss_spawned = False
        self.boss_killed = False
        
        # 创建摇杆
        self.joystick = JoystickWidget()
        self.add_widget(self.joystick)
        
        # 创建攻击按钮
        self.attack_btn = Button(
            text="攻击",
            size=(120, 120),
            pos=(SCREEN_WIDTH - 140, 20),
            font_size=20
        )
        self.attack_btn.bind(on_press=self.on_attack_press)
        self.add_widget(self.attack_btn)
        
        # 开始游戏循环
        Clock.schedule_interval(self.update, 1/60)
    
    def on_attack_press(self, instance):
        if self.game_state == "playing":
            if self.player.attack():
                self.spawn_projectile()
    
    def spawn_projectile(self):
        if self.player.weapon == "staff":
            proj = Projectile(
                self.player.x,
                self.player.y,
                self.player.facing_angle,
                8,
                self.player.get_attack_damage(),
                True,
                "fireball"
            )
            self.projectiles.append(proj)
        elif self.player.weapon == "gun":
            proj = Projectile(
                self.player.x,
                self.player.y,
                self.player.facing_angle,
                12,
                self.player.get_attack_damage(),
                True,
                "bullet"
            )
            self.projectiles.append(proj)
            if self.player.weapon_level >= 5:
                for offset in [-15, 15]:
                    proj2 = Projectile(
                        self.player.x,
                        self.player.y,
                        self.player.facing_angle + offset,
                        12,
                        self.player.get_attack_damage(),
                        True,
                        "bullet"
                    )
                    self.projectiles.append(proj2)
    
    def spawn_monster(self):
        side = random.randint(0, 3)
        if side == 0:
            x = random.randint(50, SCREEN_WIDTH - 50)
            y = -30
        elif side == 1:
            x = SCREEN_WIDTH + 30
            y = random.randint(50, SCREEN_HEIGHT - 50)
        elif side == 2:
            x = random.randint(50, SCREEN_WIDTH - 50)
            y = SCREEN_HEIGHT + 30
        else:
            x = -30
            y = random.randint(50, SCREEN_HEIGHT - 50)
        
        hp_min, hp_max, speed_min, speed_max, def_min, def_max = get_stat_bounds(self.game_time)
        hp = random.randint(hp_min, hp_max)
        speed = random.uniform(speed_min, speed_max)
        defense = random.randint(def_min, def_max)
        
        monster = Monster(x, y, hp, speed, defense)
        self.monsters.append(monster)
    
    def update(self, dt):
        if self.game_state != "playing":
            return
        
        self.game_time += dt
        
        # 玩家更新
        self.player.update(self.joystick.dx, self.joystick.dy, dt)
        
        # 自动攻击
        if self.player.weapon != "sword":
            if self.player.attack_cooldown <= 0:
                self.player.attack()
                self.spawn_projectile()
        
        # 生成怪物
        spawn_interval = get_spawn_interval(self.game_time)
        if self.game_time - self.last_spawn > spawn_interval and not self.boss:
            self.spawn_monster()
            self.last_spawn = self.game_time
        
        # Boss 战
        if self.game_time > 300 and not self.boss_spawned and not self.boss_killed:
            self.boss = Boss(SCREEN_WIDTH / 2, -100)
            self.boss_spawned = True
        
        # 更新怪物
        for monster in self.monsters:
            monster.update(self.player.x, self.player.y, dt)
            
            # 检查怪物攻击玩家
            dx = monster.x - self.player.x
            dy = monster.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance < monster.radius + self.player.radius:
                self.player.hp -= 1
                if self.player.hp <= 0:
                    self.game_state = "gameover"
        
        # 更新 Boss
        if self.boss and self.boss.alive:
            self.boss.update(self.player.x, self.player.y, dt)
            
            # 检查 Boss 攻击玩家
            dx = self.boss.x - self.player.x
            dy = self.boss.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance < self.boss.radius + self.player.radius:
                self.player.hp -= 2
                if self.player.hp <= 0:
                    self.game_state = "gameover"
        
        # 更新投射物
        for proj in self.projectiles:
            proj.update(dt)
            
            # 检查玩家投射物命中怪物
            if proj.is_player:
                for monster in self.monsters:
                    if monster.alive:
                        dx = proj.x - monster.x
                        dy = proj.y - monster.y
                        distance = math.sqrt(dx * dx + dy * dy)
                        if distance < proj.radius + monster.radius:
                            if monster.take_damage(proj.damage):
                                if self.player.gain_exp(10, get_exp_multiplier(self.game_time)):
                                    self.show_levelup()
                                self.score += 10
                            proj.alive = False
                            break
                
                # 检查命中 Boss
                if self.boss and self.boss.alive:
                    dx = proj.x - self.boss.x
                    dy = proj.y - self.boss.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < proj.radius + self.boss.radius:
                        if self.boss.take_damage(proj.damage):
                            self.boss_killed = True
                            self.boss = None
                            self.score += 1000
                            if self.player.gain_exp(200, get_exp_multiplier(self.game_time)):
                                self.show_levelup()
                        proj.alive = False
        
        # 剑攻击（近战）
        if self.player.weapon == "sword" and self.player.is_attacking:
            for monster in self.monsters:
                if monster.alive and monster not in self.player.sword_hit_monsters:
                    dx = monster.x - self.player.x
                    dy = monster.y - self.player.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    monster_angle = math.degrees(math.atan2(dy, dx))
                    angle_diff = abs(monster_angle - self.player.facing_angle)
                    if angle_diff > 180:
                        angle_diff = 360 - angle_diff
                    
                    if distance < self.player.attack_range and angle_diff < 60:
                        damage = self.player.get_attack_damage()
                        if monster.take_damage(damage):
                            if self.player.gain_exp(10, get_exp_multiplier(self.game_time)):
                                self.show_levelup()
                            self.score += 10
                        self.player.sword_hit_monsters.append(monster)
        
        # 清理死亡怪物
        self.monsters = [m for m in self.monsters if m.alive]
        
        # 清理消失的投射物
        self.projectiles = [p for p in self.projectiles if p.alive]
        
        # 重新绘制
        self.draw()
    
    def show_levelup(self):
        self.game_state = "levelup"
        self.player.level_up()
        
        cards = []
        upgrade_types = ["heal", "max_hp", "speed", "attack", "weapon"]
        random.shuffle(upgrade_types)
        selected = upgrade_types[:3]
        
        for t in selected:
            if t == "heal":
                cards.append(UpgradeCard("heal", "治疗", "恢复 30 点生命值"))
            elif t == "max_hp":
                cards.append(UpgradeCard("max_hp", "生命提升", "最大生命值 +20"))
            elif t == "speed":
                cards.append(UpgradeCard("speed", "速度提升", "移动速度 +0.5"))
            elif t == "attack":
                cards.append(UpgradeCard("attack", "攻击提升", "攻击力 +15"))
            elif t == "weapon":
                cards.append(UpgradeCard("weapon", "武器强化", "武器等级 +1"))
        
        modal = UpgradeModal(cards, self)
        modal.open()
    
    def apply_upgrade(self, card):
        if card.card_type == "heal":
            self.player.hp = min(self.player.max_hp, self.player.hp + 30)
        elif card.card_type == "max_hp":
            self.player.max_hp += 20
            self.player.hp += 20
        elif card.card_type == "speed":
            self.player.speed += 0.5
        elif card.card_type == "attack":
            self.player.attack_damage += 15
        elif card.card_type == "weapon":
            self.player.upgrade_weapon()
        
        self.game_state = "playing"
    
    def draw(self):
        self.canvas.clear()
        
        with self.canvas:
            # 背景
            Color(0.1, 0.1, 0.15, 1)
            Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))
            
            # 绘制怪物
            for monster in self.monsters:
                if monster.frozen_timer > 0:
                    Color(0.5, 0.8, 1, 1)
                else:
                    Color(0.8, 0.2, 0.2, 1)
                Ellipse(
                    pos=(monster.x - monster.radius, monster.y - monster.radius),
                    size=(monster.radius * 2, monster.radius * 2)
                )
                
                # 怪物血条
                hp_ratio = monster.hp / monster.max_hp
                Color(1, 0, 0, 1)
                Rectangle(
                    pos=(monster.x - 20, monster.y + monster.radius + 5),
                    size=(40, 5)
                )
                Color(0, 1, 0, 1)
                Rectangle(
                    pos=(monster.x - 20, monster.y + monster.radius + 5),
                    size=(40 * hp_ratio, 5)
                )
            
            # 绘制 Boss
            if self.boss and self.boss.alive:
                Color(1, 0.5, 0, 1)
                Ellipse(
                    pos=(self.boss.x - self.boss.radius, self.boss.y - self.boss.radius),
                    size=(self.boss.radius * 2, self.boss.radius * 2)
                )
                
                # Boss 血条
                hp_ratio = self.boss.hp / self.boss.max_hp
                Color(1, 0, 0, 1)
                Rectangle(
                    pos=(SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT - 40),
                    size=(300, 20)
                )
                Color(1, 0.5, 0, 1)
                Rectangle(
                    pos=(SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT - 40),
                    size=(300 * hp_ratio, 20)
                )
            
            # 绘制玩家
            Color(0.2, 0.7, 1, 1)
            Ellipse(
                pos=(self.player.x - self.player.radius, self.player.y - self.player.radius),
                size=(self.player.radius * 2, self.player.radius * 2)
            )
            
            # 攻击效果
            if self.player.is_attacking:
                Color(1, 1, 0, 0.5)
                attack_angle_rad = math.radians(self.player.facing_angle)
                attack_end_x = self.player.x + math.cos(attack_angle_rad) * self.player.attack_range
                attack_end_y = self.player.y + math.sin(attack_angle_rad) * self.player.attack_range
                Line(
                    points=[self.player.x, self.player.y, attack_end_x, attack_end_y],
                    width=3
                )
            
            # 投射物
            for proj in self.projectiles:
                if proj.p_type == "fireball":
                    Color(1, 0.5, 0, 1)
                elif proj.p_type == "bullet":
                    Color(1, 1, 0, 1)
                else:
                    Color(0.5, 0.5, 1, 1)
                Ellipse(
                    pos=(proj.x - proj.radius, proj.y - proj.radius),
                    size=(proj.radius * 2, proj.radius * 2)
                )
            
            # UI - 玩家血条
            hp_ratio = self.player.hp / self.player.max_hp
            Color(0.5, 0.5, 0.5, 0.8)
            Rectangle(pos=(20, SCREEN_HEIGHT - 30), size=(200, 20))
            Color(0, 1, 0, 0.8)
            Rectangle(pos=(20, SCREEN_HEIGHT - 30), size=(200 * hp_ratio, 20))
            
            # UI - 经验条
            exp_ratio = self.player.exp / self.player.exp_to_level
            Color(0.5, 0.5, 0.5, 0.8)
            Rectangle(pos=(20, SCREEN_HEIGHT - 55), size=(200, 15))
            Color(0, 0.7, 1, 0.8)
            Rectangle(pos=(20, SCREEN_HEIGHT - 55), size=(200 * exp_ratio, 15))
            
            # UI - 文字信息
            Color(1, 1, 1, 1)
            # 我们这里简单用图形表示，实际文字需要 Label 控件


class RoguelikeApp(App):
    def build(self):
        game = GameWidget()
        
        # 添加文字标签
        self.hp_label = Label(
            text=f"HP: 100/100",
            pos=(25, SCREEN_HEIGHT - 55),
            font_size=16,
            color=(1, 1, 1, 1)
        )
        self.level_label = Label(
            text="Lv: 1",
            pos=(250, SCREEN_HEIGHT - 55),
            font_size=16,
            color=(1, 1, 1, 1)
        )
        self.time_label = Label(
            text="Time: 0:00",
            pos=(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30),
            font_size=16,
            color=(1, 1, 1, 1)
        )
        self.score_label = Label(
            text="Score: 0",
            pos=(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 55),
            font_size=16,
            color=(1, 1, 1, 1)
        )
        
        game.add_widget(self.hp_label)
        game.add_widget(self.level_label)
        game.add_widget(self.time_label)
        game.add_widget(self.score_label)
        
        # 更新标签的定时任务
        Clock.schedule_interval(lambda dt: self.update_labels(game), 0.1)
        
        return game
    
    def update_labels(self, game):
        self.hp_label.text = f"HP: {int(game.player.hp)}/{game.player.max_hp}"
        self.hp_label.pos = (25, SCREEN_HEIGHT - 55)
        
        self.level_label.text = f"Lv: {game.player.level}"
        self.level_label.pos = (250, SCREEN_HEIGHT - 55)
        
        minutes = int(game.game_time // 60)
        seconds = int(game.game_time % 60)
        self.time_label.text = f"Time: {minutes}:{seconds:02d}"
        self.time_label.pos = (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30)
        
        self.score_label.text = f"Score: {game.score}"
        self.score_label.pos = (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 55)


if __name__ == "__main__":
    RoguelikeApp().run()