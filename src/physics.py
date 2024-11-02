import time

from launchpadlib.testing.helpers import NoNetworkLaunchpad

from src.game import DisplayEntity, Player, Level, Bear, Menu, MenuInterface, TextBox
from src.util import Message
from enum import Enum, auto

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

TIMESTEP = 1 / 100

class GameState(Enum):
    MAIN_MENU = auto()
    GAME_SELECT = auto()
    OPTIONS_SELECT = auto()
    MENU = auto()
    GAME = auto()

def create_entity(entity_cls, entity_list, output_pipe, *args, visible=True):
    entity = entity_cls(*args)
    entity_list.append(entity)

    display_entity = DisplayEntity(entity.get_position(), entity.get_rotation(), entity.get_hitbox_radius(),
                                   entity_cls.SAMPLERS, entity.get_id(), entity_cls.DISPLAY_TYPE, visible)
    send_message(output_pipe, Message.ENTITY_CREATED, display_entity)
    return entity

def get_by_id(object_id, object_list):
    for object_ in object_list:
        if object_.get_id() == object_id:
            return object_
    return None

def show_entity(entity_id, output_pipe):
    send_message(output_pipe, Message.ENTITY_VISIBLE, (entity_id, True))

def hide_entity(entity_id, output_pipe):
    send_message(output_pipe, Message.ENTITY_VISIBLE, (entity_id, False))

def create_menu(menu_list, output_pipe, *args, **kwargs):
    menu = Menu(*args, **kwargs)
    menu_size = menu.get_num_items()
    menu_index = menu.get_active_index()
    menu_id = menu.get_id()
    menu_interface = MenuInterface(menu_size, menu_index, menu_id)
    menu_list.append(menu_interface)
    send_message(output_pipe, Message.MENU_CREATED, menu)
    return menu_id

def add_item_to_menu(menu_id, menu_list, menu_item, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    menu_interface.num_items += 1
    send_message(output_pipe, Message.MENU_ADD_ITEM, (menu_id, menu_item))

def set_active_index_menu(menu_id, menu_list, menu_index, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    if menu_index < menu_interface.num_items:
        menu_interface.active_index = menu_index
        send_message(output_pipe, Message.MENU_CHANGE_INDEX, (menu_id, menu_index))

def handle_menu_inputs(menu_id, menu_list, inputs, output_pipe):
    menu = get_by_id(menu_id, menu_list)
    if inputs[UP]:
        if menu.active_index > 0:
            set_active_index_menu(menu_id, menu_list, menu.active_index - 1, output_pipe)
        return True
    if inputs[DOWN]:
        if menu.active_index < menu.num_items - 1:
            set_active_index_menu(menu_id, menu_list, menu.active_index + 1, output_pipe)
        return True
    return False

def show_menu(menu_id, output_pipe):
    send_message(output_pipe, Message.MENU_VISIBLE, (menu_id, True))

def hide_menu(menu_id, output_pipe):
    send_message(output_pipe, Message.MENU_VISIBLE, (menu_id, False))

def create_text_box(text_box_list, output_pipe, *args, **kwargs):
    text_box = TextBox(*args, **kwargs)
    text_box_id = text_box.get_id()
    send_message(output_pipe, Message.TEXT_BOX_CREATED, text_box)
    text_box_list.append(text_box_id)
    return text_box_id

def show_text_box(text_box_id, output_pipe):
    send_message(output_pipe, Message.TEXT_BOX_VISIBLE, (text_box_id, True))

def hide_text_box(text_box_id, output_pipe):
    send_message(output_pipe, Message.TEXT_BOX_VISIBLE, (text_box_id, False))

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
    command = None
    input_cooldown = 0.2
    input_time = time.perf_counter()
    entity_list = []
    menu_list = []
    text_box_list = []
    level = Level("res/level/level0.json")
    game_state = GameState.MAIN_MENU
    main_menu_selector = 0
    send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
    send_message(output_pipe, Message.LEVEL_CHANGED, level)
    player = create_entity(Player, entity_list, output_pipe, (0, 0), 0, visible=False)
    bear = create_entity(Bear, entity_list, output_pipe, (-5, -5), 0, visible=False)

    games_menu_id = create_menu(menu_list, output_pipe, "SELECT GAME", visible=False)
    add_item_to_menu(games_menu_id, menu_list, ("GO BACK", "Return to the main menu"), output_pipe)
    add_item_to_menu(games_menu_id, menu_list, ("NEW GAME", "Start a new game"), output_pipe)

    options_menu_id = create_menu(menu_list, output_pipe, "SELECT OPTIONS", visible=False)
    add_item_to_menu(options_menu_id, menu_list, ("GO BACK", "Return to the main menu"), output_pipe)

    running = True
    paused  = False
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
            if message == Message.COMMAND:
                command = data
            if message == Message.INPUT_BEGIN:
                paused = True
            if message == Message.INPUT_END:
                paused = False

        curr_time = time.perf_counter()
        delta = curr_time - prev_time
        if delta < timestep:
            continue
        prev_time = curr_time

        if game_state == GameState.MAIN_MENU:
            if curr_time - input_time > input_cooldown:
                if inputs[UP]:
                    if main_menu_selector > 0:
                        main_menu_selector -= 1
                    send_message(output_pipe, Message.UPDATE_SETTING, ("MAIN_MENU_SELECTOR", main_menu_selector))
                    input_time = curr_time
                if inputs[DOWN]:
                    if main_menu_selector < 2:
                        main_menu_selector += 1
                    send_message(output_pipe, Message.UPDATE_SETTING, ("MAIN_MENU_SELECTOR", main_menu_selector))
                    input_time = curr_time
                if command is not None:
                    if main_menu_selector == 0:
                        game_state = GameState.GAME_SELECT
                        show_menu(games_menu_id, output_pipe)
                        send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
                    elif main_menu_selector == 1:
                        game_state = GameState.OPTIONS_SELECT
                        show_menu(options_menu_id, output_pipe)
                        send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
                    elif main_menu_selector == 2:
                        send_message(output_pipe, Message.EXIT, 0)
                    command = None

        if game_state == GameState.GAME_SELECT:
            games_menu = get_by_id(games_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(games_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if games_menu.active_index == 0:
                        hide_menu(games_menu_id, output_pipe)
                        game_state = GameState.MAIN_MENU
                        send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
                    elif games_menu.active_index == 1:
                        hide_menu(games_menu_id, output_pipe)
                        game_state = GameState.GAME
                        for entity in entity_list:
                            show_entity(entity.get_id(), output_pipe)
                        send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
                    command = None

        if game_state == GameState.OPTIONS_SELECT:
            options_menu = get_by_id(options_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(options_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if options_menu.active_index == 0:
                        hide_menu(options_menu_id, output_pipe)
                        game_state = GameState.MAIN_MENU
                        send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
                    command = None

        if game_state == GameState.GAME and not paused:
            if inputs[LEFT]:
                player.rotate(-Player.ROTATION_SPEED)
            if inputs[RIGHT]:
                player.rotate(Player.ROTATION_SPEED)

            if inputs[UP]:
                player.move_within_level(-Player.MOVEMENT_SPEED, level)
            if inputs[DOWN]:
                player.move_within_level(Player.MOVEMENT_SPEED, level)

            bear.move_towards(player.get_position(), level)
            bear.get_animation().tick()

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