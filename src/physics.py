import time

from src.game import DisplayEntity, Player, Level
from src.util import Message

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

TIMESTEP = 1 / 100

def create_entity(entity_cls, entity_list, output_pipe, *args):
    entity = entity_cls(*args)
    entity_list.append(entity)

    display_entity = DisplayEntity(entity.get_position(), entity.get_rotation(), entity.get_hitbox_radius(),
                                   entity_cls.SAMPLERS, entity.get_id(), entity_cls.DISPLAY_TYPE)
    output_pipe.send((Message.ENTITY_CREATED, display_entity))
    return entity

def get_entity(entity_id, entity_list):
    for entity in entity_list:
        if entity.get_id() == entity_id:
            return entity
    return None

def recv_message(input_pipe):
    return input_pipe.recv()

def send_message(output_pipe, message, value):
    output_pipe.send((message, value))

def physics_thread(input_pipe, output_pipe):
    timestep = TIMESTEP
    prev_time = time.perf_counter()
    inputs = {
        UP:    False,
        DOWN:  False,
        LEFT:  False,
        RIGHT: False
    }
    entity_list = []
    level = Level("res/level/level0.json")
    send_message(output_pipe, Message.LEVEL_CHANGED, level)
    player = create_entity(Player, entity_list, output_pipe, (0, 0), 0)
    running = True
    while running:
        while input_pipe.poll():
            message, data = recv_message(input_pipe)
            if message == Message.EXIT:
                running = False
            if message == Message.TIMESTEP:
                timestep = data
            if message == Message.KEY_PRESS:
                if data in inputs.keys():
                    inputs[data] = True
            if message == Message.KEY_RELEASE:
                if data in inputs.keys():
                    inputs[data] = False

        curr_time = time.perf_counter()
        delta = curr_time - prev_time
        if delta > timestep:
            prev_time = curr_time

            if inputs[LEFT]:
                player.rotate(-Player.ROTATION_SPEED)
            if inputs[RIGHT]:
                player.rotate(Player.ROTATION_SPEED)

            if inputs[UP]:
                player.move_within_level(-Player.MOVEMENT_SPEED, level)
            if inputs[DOWN]:
                player.move_within_level(Player.MOVEMENT_SPEED, level)

            if inputs[UP] or inputs[DOWN]:
                player.get_animation().tick()
            else:
                player.get_animation().reset()

            for entity in entity_list:
                send_message(output_pipe, Message.ENTITY_UPDATE,
                             (entity.get_id(), entity.get_position(), entity.get_rotation()))
                send_message(output_pipe, Message.ENTITY_ANIMATE,
                             (entity.get_id(), entity.get_animation().get_current_state()))
            send_message(output_pipe, Message.DELTA, delta)