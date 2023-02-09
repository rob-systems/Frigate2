import pygame, sys
import math, random
from shapely import affinity
from shapely.geometry import Point, Polygon

####################################################################

pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
font = pygame.font.SysFont("Verdana", 60)
font_med = pygame.font.SysFont("Verdana", 30)
font_small = pygame.font.SysFont("Verdana", 20)

def disp_icon():
    logo = pygame.image.load("logo.png")
    pygame.display.set_icon(logo)

####################################################################


####################################################################
####################################################################

def get_list_from_polygon(polygon):
    #because I can't seem to directly iterate over shapely's polygons
    l = []
    xx, yy = polygon.exterior.coords.xy
    newxcoords, newycoords = [], []
    for x in xx:
        newxcoords.append(x)
    for y in yy:
        newycoords.append(y)
    for i, x in enumerate(newxcoords):
        l.append((newxcoords[i], newycoords[i]))
    return l

def get_polygon_center(points):
    totalx, totaly = 0, 0
    for point in points:
        totalx += point[0]
        totaly += point[1]
    return (totalx/len(points), totaly/len(points))

def rotate_polygon(polygon, rotation):
    new_triangle = affinity.rotate(polygon, rotation, get_polygon_center(get_list_from_polygon(polygon)))
    xx, yy = new_triangle.exterior.coords.xy
    l = []
    for i, x in enumerate(xx):
        l.append((xx[i], yy[i]))
    return l

def move_polygon(poly, movement_tuple):
    new_poly = []
    for coord in poly:
        new_poly.append((coord[0] + movement_tuple[0], coord[1] + movement_tuple[1]))
    return new_poly

def get_vector_length(x, y):
    return math.sqrt(x*x + y*y)

def normalize_vector(x, y):
    norm = get_vector_length(x, y)
    if norm != 0:
        return x/norm, y/norm
    else:
        return x, y

####################################################################
####################################################################

class Island(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.image = pygame.Surface((50,50))
        self.image.fill((255,255,255))
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = data["pos"][0], data["pos"][1]
        self.is_friendly = True

    def move(self, dx, dy):
        self.rect.move_ip(dx, dy)

    def draw(self, map_surface):
        map_surface.blit(self.image, self.rect)

class Shrapnel(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.start_pos = data["start_pos"]
        self.contents = []
        self.is_friendly = data["is_friendly"]
        self.iter = 0

    def spawn(self, shell_mov_vec):
        for x in range(0, random.randint(5,7)):
            self.contents.append({ "pos": self.start_pos,
                                   "dir": (
                                       random.random() if shell_mov_vec[0] < 0 else -random.random(),
                                       random.random() if shell_mov_vec[1] < 0 else -random.random()
                                       )
                                   })

    def de_spawn(self, all_sprites):
        all_sprites.remove(self)

    def move(self, all_sprites):
        new_contents = []
        if not self.iter > 10:
            for x in self.contents:
                new_contents.append({ "pos": (x["pos"][0] + x["dir"][0], x["pos"][1] + x["dir"][1]),
                                      "dir": x["dir"] })
            self.contents = new_contents
            self.iter += 1
        else:
            self.de_spawn(all_sprites)

    def draw(self, map_surface):
        for piece in self.contents:
            pygame.draw.line(map_surface,
                             (255, 165, 0),
                             self.start_pos,
                             (self.start_pos[0] + piece["dir"][0] * self.iter, self.start_pos[1] + piece["dir"][1] * self.iter),
                             1)

class Sink_Spot(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.position = data["pos"]
        self.radius = 15.0
        self.is_friendly = False

    def move(self, all_sprites):
        self.radius -= 0.1 if self.radius > 10 else 0.2
        if self.radius <= 0:
            self.de_spawn(all_sprites)

    def de_spawn(self, all_sprites):
        all_sprites.remove(self)

    def draw(self, map_surface):
        pygame.draw.circle(map_surface, (255, 255, 255), self.position, self.radius)
        pygame.draw.circle(map_surface, (150,150, 150), self.position, self.radius - 3)

class Shell(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.is_friendly = data
        self.cur_pos = Point(0,0)
        self.dx, self.dy = 0, 0
        self.firing_speed = 5
        self.iter = 0

    def spawn(self, start_pos, end_pos):
        self.cur_pos = Point(start_pos)
        raw_dx, raw_dy = end_pos[0] - self.cur_pos.x, end_pos[1] - self.cur_pos.y
        normalized_vector = normalize_vector(raw_dx, raw_dy)
        self.dx, self.dy = normalized_vector[0], normalized_vector[1]

    def de_spawn(self, all_sprites):
        all_sprites.remove(self)

    def move(self, all_sprites):
        self.iter += 1
        speed = self.firing_speed - (self.iter / 300 * self.firing_speed)
        if speed <= 3.5 or self.clamp_to_screen():
            self.de_spawn(all_sprites)
        self.cur_pos = Point(self.cur_pos.x + self.dx * speed, self.cur_pos.y + self.dy * speed)

    def clamp_to_screen(self):
        return self.cur_pos.x >= SCREEN_WIDTH or self.cur_pos.x <= 0 or self.cur_pos.y >= SCREEN_HEIGHT or self.cur_pos.y <= 0

    def hit_target(self, all_sprites):
        shrapnel = Shrapnel({ "start_pos":(self.cur_pos.x, self.cur_pos.y), "is_friendly": self.is_friendly })
        all_sprites.add(shrapnel)
        shrapnel.spawn((self.dx, self.dy))
        self.de_spawn(all_sprites)

    def draw(self, map_surface):
        pygame.draw.line(map_surface,
                         (255,255,0),
                         (self.cur_pos.x, self.cur_pos.y),
                         ( self.cur_pos.x - self.dx * 4, self.cur_pos.y - self.dy * 4 ),
                         3)

class Boat(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.create_hull(data["pos"], data["fwards_or_bwards"])
        self.cur_turn, self.turn_by, self.movement_dir = 0, 0, 0
        self.tur_end_pos = (0,0)

    def set_tur_end_pos(self, center):
        target_pos = pygame.mouse.get_pos() if self.is_friendly else self.target
        x, y = target_pos[0] - center[0], target_pos[1] - center[1]
        if x == 0 or y == 0:
            tur_angle = 0 if x == 0 else math.radians(90 if x > 0 else -90)
        else:
            tur_angle = (math.radians(-180) if x <= 0 else 0) + math.atan(y/x)
        self.tur_end_pos = (center[0] + 15 * math.cos(tur_angle), center[1] + 15 * math.sin(tur_angle))

    def fire(self, all_sprites, target_pos):
        S1 = Shell(self.is_friendly)
        S1.spawn(self.tur_end_pos, target_pos)
        all_sprites.add(S1)

    def create_hull(self, center, facing=-1):
        boat_length, boat_width, stern_length = 50, 15, 13
        if facing == 1:
            self.hull = Polygon([(center[0] ,center[1]-(boat_length / 2)),
                                 (center[0] - (boat_width /2), center[1] - (boat_length / 2) + stern_length),
                                 (center[0] - (boat_width /2), center[1] + (boat_length / 2)),
                                 (center[0] + (boat_width /2), center[1] + (boat_length / 2)),
                                 (center[0] + (boat_width /2), center[1] - (boat_length / 2) + stern_length)])
        elif facing == -1:
            self.hull = Polygon([(center[0] ,center[1]+(boat_length / 2)),
                                 (center[0] + (boat_width /2), center[1] + (boat_length / 2) - stern_length),
                                 (center[0] + (boat_width /2), center[1] - (boat_length / 2)),
                                 (center[0] - (boat_width /2), center[1] - (boat_length / 2)),
                                 (center[0] - (boat_width /2), center[1] + (boat_length / 2) - stern_length)])

    def take_damage(self):
        self.health -= 10
        return self.health <= 0

    def de_spawn(self, all_sprites):
        self.sink(all_sprites)
        all_sprites.remove(self)

    def sink(self, all_sprites):
        sink_spot = Sink_Spot({ "pos": get_polygon_center(get_list_from_polygon(self.hull)) })
        all_sprites.add(sink_spot)

    def draw(self, map_surface):
        self.draw_hull(map_surface)
        self.draw_turret(map_surface, get_polygon_center(get_list_from_polygon(self.hull)))
        if self.__class__.__name__ == "Enemy":
            self.draw_health_bar(map_surface)

    def draw_hull(self, map_surface):
        self.hull_poly_coords = rotate_polygon(self.hull, self.cur_turn)
        pygame.draw.polygon(map_surface, (255,255,255), self.hull_poly_coords)

    def draw_turret(self, map_surface, centered_at):
        center = centered_at
        self.set_tur_end_pos(center)
        pygame.draw.circle(map_surface, (150,150,150), center, 5)
        pygame.draw.line(map_surface, (150,150,150), center, self.tur_end_pos, 3)

    def draw_health_bar(self, map_surface):
        position = get_polygon_center(get_list_from_polygon(self.hull))
        rect = pygame.Rect(position[0] - 18, position[1] - 29, 7, self.health)
        pygame.draw.rect(map_surface, (255,0,0), rect)

    def move(self, all_sprites):
        hull_coords = move_polygon(get_list_from_polygon(self.hull), (0, 0.25))
        self.hull = Polygon(hull_coords)

class Enemy(Boat):
    def __init__(self, data):
        super().__init__(data)
        self.is_friendly = False
        self.target = (0,0)
        self.health = 50

    def update(self, user, all_sprites):
        self.target = user.get_position()
        self.auto_fire(all_sprites)

    def auto_fire(self, all_sprites):
        ifuckedup = get_polygon_center(get_list_from_polygon(self.hull))
        var = round(get_vector_length(self.target[0] - ifuckedup[0], self.target[1] - ifuckedup[1]))
        if var < 300:
            self.fire(all_sprites, self.target)
        pass
        

class User(Boat):
    def __init__(self, data):
        super().__init__(data)
        self.is_friendly = True
        self.movement_dir = 0
        self.turn_by = 0

    def mouse_fire(self, all_sprites, mouse_pos):
        self.fire(all_sprites, mouse_pos)

    def start_turn(self, rotation):
        self.turn_by = rotation

    def end_turn(self):
        self.turn_by = 0

    def start_move(self, direction):
        self.movement_dir = direction

    def end_move(self, direction):
        if direction == self.movement_dir:
            self.movement_dir = 0

    def move(self, all_sprites):
        if (self.turn_by != 0):
            self.cur_turn += self.turn_by / (1 if self.movement_dir > 0 else 2)
        dx = self.movement_dir * math.sin(math.radians(self.cur_turn)) / (2 if self.movement_dir > 0 else 4)
        dy = -self.movement_dir * math.cos(math.radians(self.cur_turn)) / (2 if self.movement_dir > 0 else 4)
        hull_coords = move_polygon(get_list_from_polygon(self.hull), (dx, dy))
        self.hull = Polygon(hull_coords)

    def get_position(self):
        return get_polygon_center(get_list_from_polygon(self.hull))

    #def hack enemy ship

class Game():
    def __init__(self, data):
        self.map_surface = pygame.Surface((data["s_w"], data["s_h"]))
        self.rect = self.map_surface.get_rect()
        self.dy = 0
        self.progress = 0
        self.level = 0
        self.direction = 0
        self.user_score = 0
        self.wave_iter = 0

    def handle_key_down(self, event, user):
        if event.unicode == 'w':
            user.start_move(1)
            if user.get_position()[1] < SCREEN_HEIGHT / 2:
                self.dy = -1
        if event.unicode == 's':
            user.start_move(-1)
            #self.dy = 1
        if event.unicode == 'a':
            user.start_turn(-1)
        if event.unicode == 'd':
            user.start_turn(1)

    def handle_key_up(self, event, user):
        if event.unicode == 'w':
            user.end_move(1)
            #self.dy = 0
        if event.unicode == 's':
            user.end_move(-1)
            #self.dy = 0
        if event.unicode == 'a' and user.turn_by != 0:
            user.end_turn()
        if event.unicode == 'd' and user.turn_by != 0:
            user.end_turn()

    def scroll_map(self, all_sprites):
        if self.dy != 0:
            self.progress -= self.dy
            for sprite in all_sprites:
                if sprite.__class__.__name__ == "Island":
                    sprite.move(0, -self.dy)
        if self.progress >= 100 and self.level == 0:
            I1 = Island({ "pos": (0,0) })
            all_sprites.add(I1)
            self.level += 1

    def draw(self, screen, all_sprites):
        self.map_surface.fill((0,0,255))
        nwavesx = 64
        nwavesy = 48
        #get some wavey action
        for y in range(0, int(SCREEN_HEIGHT / nwavesy)):
            for x in range(0, int(SCREEN_WIDTH / nwavesx)):
                #pygame.draw.arc(self.map_surface, (255,255,255), (x * 64, y * 48, 8, 6), 0.1, 0.9, 1)
                pygame.draw.arc(self.map_surface, (200,200,200), (32 + self.wave_iter + x * 64 + 2, 24 + y * 48, 8, 6), 1, 3, 1)
        self.wave_iter = self.wave_iter + 0.5 if self.wave_iter < 50 else 0
        #draw sprites
        for sprite in all_sprites:
             sprite.draw(self.map_surface)
        self.draw_score()
        #put map on screen
        screen.blit(self.map_surface, self.rect)

    def draw_score(self):
        scores = font_small.render(str(self.user_score), True, (255,255,255))
        self.map_surface.blit(scores, (10,10))

    def handle_shells(self, all_sprites, user):
        for sprite in all_sprites:
            if sprite.__class__.__name__ == "Shell":
                for spriteT in all_sprites:
                    if spriteT.__class__.__name__ == "Enemy":
                        if sprite.cur_pos.within(spriteT.hull):
                            sprite.hit_target(all_sprites)
                            has_died = spriteT.take_damage()
                            if has_died:
                                spriteT.de_spawn(all_sprites)
                                self.user_score += 5
                            

    def update(self, all_sprites, user):
        self.scroll_map(all_sprites)
        self.handle_shells(all_sprites, user)
        for sprite in all_sprites:
            if not sprite.__class__.__name__ == "Island":
                sprite.move(all_sprites)
            if not sprite.is_friendly:
                #print(sprite.__class__ == '.Boat')
                sprite.update(user, all_sprites)
                #sprite.fire(all_sprites, user.get_position())

class Menu():
    def __init__(self):
        self.items = ["Play Game", "High Scores"]
        self.item_positions = [(200, 200), (200, 250)]
        self.selected = None

    def draw(self,screen):
        screen.blit(font.render("Frigate", True, (0,0,0)), (230, 120))
        for i, item in enumerate(self.items):
            menu_item = font_med.render(item, True, (0,0,0) if item == "Play Game" else (100,100,100))
            screen.blit(menu_item, (self.item_positions[i][0], self.item_positions[i][1]))

    def update(self, screen, mouse_pos):
        for i, position in enumerate(self.item_positions):
            box = Polygon([position, (position[0] + 200, position[1]), (position[0] + 200, position[1] + 35), (position[0], position[1] + 35)])
            mouse = Point(mouse_pos)
            if mouse.within(box):
                if i == 0:
                    pygame.draw.line(screen, (0,0,0), (position[0], position[1] + 35), (position[0] + 200, position[1] + 35), 3)
                    self.selected = self.items[i]
            else:
                self.selected = None if self.selected == self.items[i] else self.selected

    def select(self):
        game_started = False
        if self.selected == "Play Game":
            game_started = True
            #print(game_started)
        else:
            game_started = False
        return game_started
        

def order_all_sprites(all_sprites):
    order =["Sink_Spot", "User", "Enemy", "Shell", "Shrapnel"]
    new_all_sprites = pygame.sprite.Group()
    for i in order:
        for sprite in all_sprites:
            if sprite.__class__.__name__ == i:
                new_all_sprites.add(sprite)
    return new_all_sprites

def main():
    
    disp_icon()
    pygame.display.set_caption("minimal program")
    screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
    game_started = False
    game_over = False
    ########### SPRITE INITIALIZATION
    G1 = Game({ "s_h": SCREEN_HEIGHT, "s_w": SCREEN_WIDTH })
    all_sprites = pygame.sprite.Group()
    user = User({ "pos": (SCREEN_WIDTH /2,  SCREEN_HEIGHT - 30), "fwards_or_bwards": 1})
    enemy = Enemy({ "pos": (100, 100), "fwards_or_bwards": -1 })
    all_sprites.add(user, enemy)
    ###########
    running = True
    menu = Menu()
    while running:
        if not game_started:
            for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        pygame.quit()
                        sys.exit()

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        game_started = menu.select()
            screen.fill((255,255,255))
            menu.update(screen,pygame.mouse.get_pos())
            menu.draw(screen)
            pygame.event.pump()
            pygame.display.update()
        elif game_started and not game_over:
            
            for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        pygame.quit()
                        sys.exit()

                    if event.type == pygame.KEYDOWN:
                        G1.handle_key_down(event, user)

                    if event.type == pygame.KEYUP:
                        G1.handle_key_up(event, user)

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        user.mouse_fire(all_sprites, pygame.mouse.get_pos())

            G1.update(all_sprites, user)

            screen.fill((255,255,255))
            all_sprites = order_all_sprites(all_sprites)
            G1.draw(screen, all_sprites)
        
            pygame.event.pump()
            pygame.display.update()

        elif game_over:
            screen.fill((255, 0, 0))
            screen.blit(font.render("Game Over", True, (0,0,0)), (30,250))
            pygame.display.update()
            time.sleep(1.5)
            pygame.quit()
            sys.exit() 


# run the main function only if this module is executed as the main script
# (if you import this as a module then nothing is executed)
if __name__=="__main__":
    # call the main function
    main()
