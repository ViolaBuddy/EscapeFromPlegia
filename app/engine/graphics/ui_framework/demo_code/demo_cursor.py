from typing import List
import pygame
import pygame.event
import pygame.draw
import random
from itertools import cycle

from pygame.math import Vector2

TILEWIDTH, TILEHEIGHT = 16, 16
TILEX, TILEY = 15, 10
WINWIDTH, WINHEIGHT = TILEX * TILEWIDTH, TILEY * TILEHEIGHT
import os 

DIR_PATH = os.path.dirname(os.path.realpath(__file__))

class Node():
    """This is a simulated "node" for informational purposes.
    Irrelevant to the demo.
    """
    def __init__(self, name: str, pos: Vector2, sprite):
        self.name = name
        self.pos = pos
        self.sprite = sprite

class Scene():
    """This is supposed to simulate the action of "getting" data from the overworld map.
    But this is also irrelevant to the action of the demo.
    """
    def __init__(self):
        node_sprite = pygame.image.load(os.path.join(DIR_PATH, "map_node.png"))
        fort_sprite = pygame.image.load(os.path.join(DIR_PATH, "fort.png"))
        self.nodes: List[Node] = [
            Node("Frelia Castle", Vector2(5, 4), fort_sprite),
            Node("Renais Outskirts", Vector2(9, 6), node_sprite),
            Node("Ide", Vector2(7, 7), fort_sprite)
        ]
        pass
    
    def get_node_name(self, pos: Vector2) -> str:
        for node in self.nodes:
            if node.pos == pos:
                return node.name
    
    def draw(self, surf):
        for node in self.nodes:
            topleft = node.pos.x * TILEWIDTH, node.pos.y * TILEHEIGHT
            surf.blit(node.sprite, topleft)

class Cursor():
    """Irrelevant to the demo.
    """
    def __init__(self):
        self.x = 0
        self.y = 0
        self.scene = Scene()
        
    def take_input(self, events: List[pygame.event.Event]):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:
                    self.x = max(self.x - 1, 0)
                if e.key == pygame.K_RIGHT:
                    self.x = min(self.x + 1, TILEX - 1)
                if e.key == pygame.K_UP:
                    self.y = max(self.y - 1, 0)
                if e.key == pygame.K_DOWN:
                    self.y = min(self.y + 1, TILEY - 1)
                
    def get_hover(self) -> str:
        return self.scene.get_node_name(Vector2(self.x, self.y))
    
    def draw(self, surf):
        rec_size = Vector2(TILEWIDTH, TILEHEIGHT)
        topleft = Vector2(self.x * TILEWIDTH, self.y * TILEHEIGHT)
        cursor_rect = pygame.Rect(topleft, rec_size)
        pygame.draw.rect(surf, pygame.Color(200, 0, 0), cursor_rect, width=3)
